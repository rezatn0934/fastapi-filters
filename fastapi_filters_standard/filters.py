from collections import defaultdict
from collections.abc import Container, Iterator
from dataclasses import asdict, make_dataclass
from typing import (
    Annotated,
    Any,
    cast,
    get_args,
    get_origin,
)

from fastapi import Depends, Query
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from .config import ConfigVar
from .fields import FilterField
from .operators import FilterOperator
from .schemas import CSVList
from .types import (
    AbstractFilterOperator,
    FilterAliasGenerator,
    FilterFieldDef,
    FilterPlace,
    FiltersResolver,
    FilterValues,
)
from .utils import async_safe, fields_include_exclude, is_seq, unwrap_annotated, unwrap_seq_type

# Django-style lookup expressions mapping
LOOKUP_EXPRESSIONS = {
    FilterOperator.eq: "",  # exact - no suffix
    FilterOperator.ne: "__ne",  # not equal
    FilterOperator.gt: "__gt",
    FilterOperator.ge: "__gte",
    FilterOperator.lt: "__lt",
    FilterOperator.le: "__lte",
    FilterOperator.like: "__contains",  # like -> contains
    FilterOperator.not_like: "__not_like",
    FilterOperator.ilike: "__icontains",  # ilike -> icontains
    FilterOperator.not_ilike: "__not_ilike",
    FilterOperator.in_: "__in",
    FilterOperator.not_in: "__not_in",
    FilterOperator.is_null: "__isnull",
    FilterOperator.overlap: "__overlap",
    FilterOperator.not_overlap: "__not_overlap",
    FilterOperator.contains: "__contains",
    FilterOperator.not_contains: "__not_contains",
}


def default_alias_generator(
    name: str,
    op: AbstractFilterOperator,
    alias: str | None = None,
) -> str:
    name = alias or name
    lookup_expr = LOOKUP_EXPRESSIONS.get(op, f"__{op.name.rstrip('_')}")

    # If lookup_expr is empty (exact match), return just the name
    if not lookup_expr:
        return name

    return f"{name}{lookup_expr}"


alias_generator_config: ConfigVar[FilterAliasGenerator] = ConfigVar(
    "alias_generator",
    default=default_alias_generator,
)


def _is_csv_list_type(tp: Any) -> bool:
    """Check if type is CSVList (Annotated[list[T], ...])."""
    # CSVList is Annotated[list[T], ...], so we need to unwrap Annotated
    origin = get_origin(tp)
    
    # If it's Annotated, get the first argument (the actual type)
    if origin is Annotated:
        args = get_args(tp)
        if args:
            inner_type = args[0]
            # Check if inner type is list
            inner_origin = get_origin(inner_type)
            if inner_origin is list:
                return True
            if inner_type is list:
                return True
    
    # Check if it's directly a list type
    if origin is list:
        return True
    if tp is list:
        return True
    
    return False


def _create_query_param(alias: str | None, tp: Any, op: AbstractFilterOperator, field: FilterField[Any], original_tp: type[Any], in_: FilterPlace) -> Any:
    """Create Query parameter with explode=False for CSVList types."""
    # Check if this operation needs CSVList:
    # 1. in_ and not_in operations always use CSVList
    # 2. Sequence types (list, tuple, etc.) use CSVList
    # 3. If type is already CSVList
    needs_csv = (
        op in {FilterOperator.in_, FilterOperator.not_in}
        or is_seq(original_tp)
        or _is_csv_list_type(tp)
    )
    
    if needs_csv:
        if alias:
            return in_(alias=alias, explode=False)
        return in_(explode=False)
    if alias:
        return in_(alias=alias)
    return in_


def adapt_type(
    field: FilterField[Any],
    tp: type[Any],
    op: AbstractFilterOperator,
) -> Any:
    if field.op_types and op in field.op_types:
        return field.op_types[op]

    if is_seq(tp):
        return CSVList[unwrap_seq_type(tp)]  # type: ignore[misc]

    if op in {
        FilterOperator.like,
        FilterOperator.ilike,
        FilterOperator.not_like,
        FilterOperator.not_ilike,
    }:
        return str

    if op == FilterOperator.is_null:
        return bool

    if op in {FilterOperator.in_, FilterOperator.not_in}:
        return CSVList[tp]  # type: ignore[valid-type]

    return tp


def _get_field_name(name: str, op: AbstractFilterOperator) -> str:
    """Get field name for dataclass field, ensuring uniqueness."""
    lookup_expr = LOOKUP_EXPRESSIONS.get(op, f"__{op.name.rstrip('_')}")

    # If lookup_expr is empty (exact match), use __{op.name} for uniqueness
    if not lookup_expr:
        return f"{name}__{op.name}"

    # Remove leading __ from lookup_expr and add it to name
    if lookup_expr.startswith("__"):
        return f"{name}{lookup_expr}"

    return f"{name}__{lookup_expr}"


def field_filter_to_raw_fields(
    name: str,
    field: FilterField[Any],
    alias_generator: FilterAliasGenerator | None = None,
) -> Iterator[tuple[str, Any, AbstractFilterOperator, str | None]]:
    if alias_generator is None:
        alias_generator = alias_generator_config.get()

    yield name, field.type, cast(AbstractFilterOperator, field.default_op), field.alias

    for op in field.operators or ():
        yield (
            _get_field_name(name, op),
            field.type,
            op,
            alias_generator(
                name,
                op,
                field.alias,
            ),
        )


def create_filters_from_model(
    model: type[BaseModel],
    *,
    in_: FilterPlace | None = None,
    alias_generator: FilterAliasGenerator | None = None,
    include: Container[str] | None = None,
    exclude: Container[str] | None = None,
    **overrides: FilterFieldDef,
) -> FiltersResolver:
    checker = fields_include_exclude(model.model_fields, include, exclude)

    def _get_type(f: FieldInfo) -> Any:
        if f.metadata:
            return Annotated[(f.annotation, *f.metadata)]

        return f.annotation

    return create_filters(
        in_=in_,
        alias_generator=alias_generator,
        **{
            **{name: _get_type(field) for name, field in model.model_fields.items() if checker(name)},
            **(overrides or {}),
        },
    )


def create_filters(
    *,
    in_: FilterPlace | None = None,
    alias_generator: FilterAliasGenerator | None = None,
    **kwargs: FilterFieldDef,
) -> FiltersResolver:
    if in_ is None:
        in_ = Query

    fields: dict[str, FilterField[Any]] = {
        name: f_def if isinstance(f_def, FilterField) else FilterField(f_def) for name, f_def in kwargs.items()
    }

    fields_defs = [
        (name, fname, field, tp, alias, op)
        for name, field in fields.items()
        for fname, tp, op, alias in field_filter_to_raw_fields(
            name,
            field,
            alias_generator,
        )
    ]

    defs = {fname: (name, op) for name, fname, *_, op in fields_defs}

    filter_model = make_dataclass(
        "Filters",
        [
            (
                fname,
                Annotated[
                    adapt_type(field, tp, op),
                    _create_query_param(alias, adapt_type(field, tp, op), op, field, tp, in_),
                ],
                None,
            )
            for _, fname, field, tp, alias, op in fields_defs
        ],
    )

    async def _get_filters(f: Any = Depends(async_safe(filter_model))) -> FilterValues:
        values: FilterValues = defaultdict(dict)

        for key, value in asdict(f).items():
            if value is not None:
                name, op = defs[key]
                values[name][op] = value

        return {**values}

    _get_filters.__model__ = filter_model  # type: ignore[attr-defined]
    _get_filters.__defs__ = defs  # type: ignore[attr-defined]
    _get_filters.__filters__ = fields  # type: ignore[attr-defined]

    return cast(FiltersResolver, _get_filters)


__all__ = [
    "alias_generator_config",
    "create_filters",
    "create_filters_from_model",
]
