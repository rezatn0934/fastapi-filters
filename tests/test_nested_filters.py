import pytest

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    create_engine,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

from fastapi_filters_standard.ext.sqlalchemy import apply_filters


# --------------------------------------------
# SQLAlchemy test setup (self-contained)
# --------------------------------------------
class Base(DeclarativeBase):
    pass


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False)


class State(Base):
    __tablename__ = "states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fa_name: Mapped[str] = mapped_column(String, nullable=False)

    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"))
    country: Mapped["Country"] = relationship(Country)


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"))
    state: Mapped["State"] = relationship(State)


@pytest.fixture(scope="module")
def engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def session(engine):
    Session = sessionmaker(bind=engine)
    return Session()


# --------------------------------------------
# Tests
# --------------------------------------------
def test_nested_filter_eq():
    stmt = select(City)

    stmt = apply_filters(
        stmt,
        {
            "state__fa_name": {
                "eq": "Tehran",
            }
        },
        model=City,
        nested=True,
    )

    sql = str(stmt)

    assert "JOIN states" in sql
    assert "states.fa_name" in sql
    assert "=" in sql


def test_nested_filter_disabled_by_default():
    stmt = select(City)

    with pytest.raises(ValueError, match=r"Unknown field state__fa_name"):
        apply_filters(
            stmt,
            {
                "state__fa_name": {
                    "eq": "Tehran",
                }
            },
            model=City,
            nested=False,
        )


def test_nested_filter_requires_model():
    stmt = select(City)

    with pytest.raises(
        RuntimeError,
        match=r"Nested filters require passing `model=`",
    ):
        apply_filters(
            stmt,
            {
                "state__fa_name": {
                    "eq": "Tehran",
                }
            },
            nested=True,
        )


def test_nested_filter_unknown_relationship():
    stmt = select(City)

    with pytest.raises(ValueError, match=r"Unknown relationship"):
        apply_filters(
            stmt,
            {
                "unknown__fa_name": {
                    "eq": "test",
                }
            },
            model=City,
            nested=True,
        )


def test_nested_filter_unknown_field():
    stmt = select(City)

    with pytest.raises(ValueError, match=r"Unknown field"):
        apply_filters(
            stmt,
            {
                "state__unknown_field": {
                    "eq": "test",
                }
            },
            model=City,
            nested=True,
        )


def test_nested_filter_multiple_levels():
    stmt = select(City)

    stmt = apply_filters(
        stmt,
        {
            "state__country__code": {
                "eq": "IR",
            }
        },
        model=City,
        nested=True,
    )

    sql = str(stmt)

    assert "JOIN states" in sql
    assert "JOIN countries" in sql
    assert "countries.code" in sql


def test_nested_filter_unknown_operator():
    stmt = select(City)

    with pytest.raises(
        NotImplementedError,
        match=r"Operator unknown is not implemented",
    ):
        apply_filters(
            stmt,
            {
                "state__fa_name": {
                    "unknown": "test",
                }
            },
            model=City,
            nested=True,
        )


import pytest
from pydantic import BaseModel

from fastapi_filters_standard.filters import create_filters_from_model
from fastapi_filters_standard.operators import FilterOperator


# ---------- Test Models ----------


class Address(BaseModel):
    city: str
    zip_code: int


class User(BaseModel):
    id: int
    name: str
    address: Address


# ---------- Tests ----------


@pytest.mark.asyncio
async def test_nested_filters_basic():
    """
    Basic test:
    - nested=True
    - flattening address.city and address.zip_code
    """

    resolver = create_filters_from_model(
        User,
        nested=True,
    )

    # The resolver itself must expose metadata
    assert hasattr(resolver, "__model__")
    assert hasattr(resolver, "__defs__")

    filter_model = resolver.__model__
    defs = resolver.__defs__

    # ---------- Check generated fields ----------
    field_names = set(filter_model.__annotations__.keys())

    # Top-level fields
    assert "id__eq" in field_names
    assert "name__eq" in field_names

    # Nested fields
    assert "address__city__eq" in field_names
    assert "address__zip_code__eq" in field_names

    # ---------- Check defs (field -> operator map) ----------
    assert defs["address__city__eq"] == ("address__city", FilterOperator.eq)
    assert defs["address__zip_code__eq"] == ("address__zip_code", FilterOperator.eq)


@pytest.mark.asyncio
async def test_nested_filters_with_operators():
    """
    Test additional operators on nested fields
    """

    resolver = create_filters_from_model(
        User,
        nested=True,
    )

    filter_model = resolver.__model__
    defs = resolver.__defs__

    field_names = set(filter_model.__annotations__.keys())

    # String operators
    assert "address__city__contains" in field_names
    assert "address__city__icontains" in field_names

    assert defs["address__city__contains"][1] == FilterOperator.like
    assert defs["address__city__icontains"][1] == FilterOperator.ilike


@pytest.mark.asyncio
async def test_nested_filters_runtime_resolution():
    """
    End-to-end test:
    instantiate the filter model and resolve the output via the resolver
    """

    resolver = create_filters_from_model(
        User,
        nested=True,
    )

    FilterModel = resolver.__model__

    # Simulate query input
    filters_instance = FilterModel(
        address__city__eq="Tehran",
        address__zip_code__eq=12345,
        name__eq="Reza",
    )

    result = await resolver(filters_instance)

    assert result == {
        "address__city": {
            FilterOperator.eq: "Tehran",
        },
        "address__zip_code": {
            FilterOperator.eq: 12345,
        },
        "name": {
            FilterOperator.eq: "Reza",
        },
    }


@pytest.mark.asyncio
async def test_nested_max_depth():
    """
    Test max_depth for nested filters
    """

    class Country(BaseModel):
        name: str

    class Address2(BaseModel):
        city: str
        country: Country

    class User2(BaseModel):
        id: int
        address: Address2

    resolver = create_filters_from_model(
        User2,
        nested=True,
        max_depth=1,  # only address.* is allowed
    )

    field_names = set(resolver.__model__.__annotations__.keys())

    assert "address__city__eq" in field_names
    assert "address__country__name__eq" not in field_names
