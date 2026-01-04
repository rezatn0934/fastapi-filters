import pytest

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

from fastapi_filters_standard.ext.sqlalchemy import create_filters_from_orm
from fastapi_filters_standard.operators import FilterOperator


# -------------------------------------------------------------------
# ORM MODELS (self-contained)
# -------------------------------------------------------------------

Base = declarative_base()


class Address(Base):
    __tablename__ = "address"

    id = Column(Integer, primary_key=True)
    city = Column(String)
    zip_code = Column(Integer)


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    address_id = Column(Integer, ForeignKey("address.id"))

    address = relationship(Address)


# -------------------------------------------------------------------
# TESTS
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nested_orm_filters_fields_exist():
    """
    Ensure nested ORM fields are converted to filter fields correctly.
    """
    resolver = create_filters_from_orm(
        User,
        nested=True,
    )

    model = resolver.__model__
    defs = resolver.__defs__

    field_names = set(model.__annotations__.keys())

    # Base model fields
    assert "id__eq" in field_names
    assert "name__eq" in field_names

    # Nested relationship fields
    assert "address__city__eq" in field_names
    assert "address__zip_code__eq" in field_names

    # Operator mapping correctness
    assert defs["address__city__eq"] == ("address__city", FilterOperator.eq)
    assert defs["name__eq"] == ("name", FilterOperator.eq)


@pytest.mark.asyncio
async def test_nested_orm_filters_runtime_resolution():
    """
    Ensure resolver output structure is correct for nested fields.
    """
    resolver = create_filters_from_orm(
        User,
        nested=True,
    )

    FilterModel = resolver.__model__

    filters = FilterModel(
        name__eq="Reza",
        address__city__eq="Tehran",
        address__zip_code__eq=12345,
    )

    resolved = await resolver(filters)

    assert resolved == {
        "name": {
            FilterOperator.eq: "Reza",
        },
        "address__city": {
            FilterOperator.eq: "Tehran",
        },
        "address__zip_code": {
            FilterOperator.eq: 12345,
        },
    }


@pytest.mark.asyncio
async def test_nested_orm_max_depth_zero():
    """
    max_depth=0 should disable relationship traversal.
    """
    resolver = create_filters_from_orm(
        User,
        nested=True,
        max_depth=0,
    )

    field_names = set(resolver.__model__.__annotations__.keys())

    # Base fields still exist
    assert "id__eq" in field_names
    assert "name__eq" in field_names

    # Nested fields must NOT exist
    assert "address__city__eq" not in field_names
    assert "address__zip_code__eq" not in field_names


@pytest.mark.asyncio
async def test_non_nested_behavior_unchanged():
    """
    Backward compatibility: nested=False must behave like before.
    """
    resolver = create_filters_from_orm(
        User,
        nested=False,
    )

    field_names = set(resolver.__model__.__annotations__.keys())

    assert "id__eq" in field_names
    assert "name__eq" in field_names

    # Relationship fields must not exist
    assert "address__city__eq" not in field_names
    assert "address__zip_code__eq" not in field_names
