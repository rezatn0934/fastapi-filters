from collections.abc import Container, Generator, Sequence
from types import UnionType
from typing import Annotated, Any, Literal, cast, get_args, get_origin

from fastapi import Query
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from .schemas import CSVList
from .types import FilterPlace, SortingNulls, SortingResolver, SortingValues
from .utils import fields_include_exclude, is_complex_field


def _extract_pydantic_model(annotation: Any) -> type[BaseModel] | None:
    """
    Extract BaseModel from annotations like:

    - UserSchema
    - UserSchema | None
    - Optional[UserSchema]
    - Annotated[UserSchema, ...]
    - list[UserSchema]
    - Sequence[UserSchema]
    """

    if annotation is None:
        return None

    origin = get_origin(annotation)

    if origin is None:
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return annotation
        return None

    # Annotated[T, ...]
    if origin is Annotated:
        return _extract_pydantic_model(get_args(annotation)[0])

    # Optional / Union
    if origin in (UnionType, __import__("typing").Union):
        for arg in get_args(annotation):
            model = _extract_pydantic_model(arg)
            if model is not None:
                return model
        return None

    # list[T], Sequence[T], tuple[T], set[T]
    if origin in (list, set, tuple, Sequence):
        args = get_args(annotation)
        if args:
            return _extract_pydantic_model(args[0])

    return None


def _iter_over_model_fields_nested(
    model: type[BaseModel],
    *,
    prefix: str = "",
    depth: int,
    max_depth: int,
    include: Container[str] | None,
    exclude: Container[str] | None,
    separator: str,
) -> Generator[tuple[str, FieldInfo], None, None]:
    checker = fields_include_exclude(
        model.model_fields,
        include,
        exclude,
    )

    for name, field in model.model_fields.items():
        if not checker(name):
            continue

        full_name = f"{prefix}{separator}{name}" if prefix else name

        nested_model = _extract_pydantic_model(field.annotation)

        if nested_model is not None and depth < max_depth:
            yield from _iter_over_model_fields_nested(
                nested_model,
                prefix=full_name,
                depth=depth + 1,
                max_depth=max_depth,
                include=None,
                exclude=None,
                separator=separator,
            )
            continue

        if not is_complex_field(field):
            yield full_name, field


def create_sorting_from_model(
    model: type[BaseModel],
    *,
    default: str | None = None,
    in_: FilterPlace | None = None,
    include: Container[str] | None = None,
    exclude: Container[str] | None = None,
    nested: bool = False,
    nested_separator: str = "__",
    max_depth: int = 1,
) -> SortingResolver:
    if nested:
        fields = [
            name
            for name, _ in _iter_over_model_fields_nested(
                model,
                depth=0,
                max_depth=max_depth,
                include=include,
                exclude=exclude,
                separator=nested_separator,
            )
        ]
    else:
        checker = fields_include_exclude(
            model.model_fields,
            include,
            exclude,
        )

        fields = [name for name, field in model.model_fields.items() if checker(name) and not is_complex_field(field)]

    return create_sorting(
        *fields,
        in_=in_,
        default=default,
    )


def create_sorting(
    *fields: str | tuple[str, SortingNulls],
    in_: FilterPlace | None = None,
    default: str | list[str] | None = None,
    alias: str | None = None,
) -> SortingResolver:
    if in_ is None:
        in_ = Query

    normalized_fields = [(f, None) if isinstance(f, str) else f for f in fields]

    defs = {f"{d}{f}": (f, v, n) for (v, d) in (("asc", "+"), ("desc", "-")) for f, n in normalized_fields}
    tp = Literal[tuple(defs)]  # type: ignore[valid-type]

    default = [default] if isinstance(default, str) else default

    if default and (diff := {*default} - {*defs}):
        raise ValueError(
            f"Default sort field {','.join(diff)} is not in {','.join(f for f, _ in normalized_fields)}",
        )

    async def _get_sorters(
        sort: Annotated[CSVList[tp], in_(alias=alias, explode=False)] = default,  # type: ignore[valid-type,assignment]
    ) -> SortingValues:
        return cast(SortingValues, [defs[f] for f in sort or ()])

    _get_sorters.__tp__ = tp  # type: ignore[attr-defined]
    _get_sorters.__defs__ = defs  # type: ignore[attr-defined]

    return cast(SortingResolver, _get_sorters)


__all__ = [
    "create_sorting",
    "create_sorting_from_model",
]
