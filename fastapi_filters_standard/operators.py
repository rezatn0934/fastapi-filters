from __future__ import annotations

from collections.abc import Callable, Container, Iterator
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import TYPE_CHECKING

from .config import ConfigVar
from .utils import (
    is_optional,
    is_seq,
    lenient_issubclass,
    unwrap_annotated,
    unwrap_optional_type,
    unwrap_type,
)

if TYPE_CHECKING:
    from .types import AbstractFilterOperator


class FilterOperator(str, Enum):
    eq = "eq"
    ne = "ne"
    gt = "gt"
    ge = "ge"
    lt = "lt"
    le = "le"
    like = "like"
    not_like = "not_like"
    ilike = "ilike"
    not_ilike = "not_ilike"
    in_ = "in"
    not_in = "not_in"
    is_null = "is_null"
    overlap = "overlap"
    not_overlap = "not_overlap"
    contains = "contains"
    not_contains = "not_contains"
    range = "range"
    date = "date"
    year = "year"
    month = "month"
    day = "day"
    hour = "hour"
    minute = "minute"
    second = "second"
    time = "time"

    def __repr__(self) -> str:
        return f"{type(self).__name__}.{self.name}"


DEFAULT_OPERATORS = [
    FilterOperator.eq,
    FilterOperator.ne,
    FilterOperator.in_,
    FilterOperator.not_in,
]

NUM_OPERATORS = [
    FilterOperator.gt,
    FilterOperator.ge,
    FilterOperator.lt,
    FilterOperator.le,
]

BOOL_OPERATORS = [
    FilterOperator.eq,
    FilterOperator.ne,
]

STR_OPERATORS = [
    FilterOperator.like,
    FilterOperator.ilike,
    FilterOperator.not_like,
    FilterOperator.not_ilike,
]

SEQ_OPERATORS = [
    FilterOperator.overlap,
    FilterOperator.not_overlap,
    FilterOperator.contains,
    FilterOperator.not_contains,
]

DATE_LOOKUP_OPERATORS = [
    FilterOperator.range,
    FilterOperator.year,
    FilterOperator.month,
    FilterOperator.day,
]

DATETIME_LOOKUP_OPERATORS = [
    *DATE_LOOKUP_OPERATORS,
    FilterOperator.date,
    FilterOperator.hour,
    FilterOperator.minute,
    FilterOperator.second,
    FilterOperator.time,
]

TIME_LOOKUP_OPERATORS = [
    FilterOperator.range,
    FilterOperator.hour,
    FilterOperator.minute,
    FilterOperator.second,
]


def default_filter_operators_generator(t: type) -> Iterator[AbstractFilterOperator]:
    t = unwrap_annotated(t)

    if is_optional(t):
        t = unwrap_optional_type(t)
        yield FilterOperator.is_null

    if is_seq(t):
        yield from SEQ_OPERATORS
        return

    tp = unwrap_type(t)

    if lenient_issubclass(tp, bool):
        yield from BOOL_OPERATORS
        return

    yield from DEFAULT_OPERATORS

    if lenient_issubclass(tp, str):
        yield from STR_OPERATORS

    if lenient_issubclass(tp, datetime):
        yield from DATETIME_LOOKUP_OPERATORS
    elif lenient_issubclass(tp, date):
        yield from DATE_LOOKUP_OPERATORS
    elif lenient_issubclass(tp, time):
        yield from TIME_LOOKUP_OPERATORS

    if lenient_issubclass(tp, (int, float, date, datetime, time, timedelta)):
        yield from NUM_OPERATORS


disabled_filters_config: ConfigVar[Container[AbstractFilterOperator]] = ConfigVar(
    "disabled_filters",
    default=(),
)
filter_operators_generator_config: ConfigVar[Callable[[type], Iterator[AbstractFilterOperator]]] = ConfigVar(
    "filter_operators_generator",
    default=default_filter_operators_generator,
)


def get_filter_operators(t: type) -> Iterator[AbstractFilterOperator]:
    disabled = disabled_filters_config.get()
    operator_generator = filter_operators_generator_config.get()

    for op in operator_generator(t):
        if op not in disabled:
            yield op


__all__ = [
    "DATETIME_LOOKUP_OPERATORS",
    "DATE_LOOKUP_OPERATORS",
    "DEFAULT_OPERATORS",
    "NUM_OPERATORS",
    "SEQ_OPERATORS",
    "STR_OPERATORS",
    "TIME_LOOKUP_OPERATORS",
    "FilterOperator",
    "default_filter_operators_generator",
    "disabled_filters_config",
    "filter_operators_generator_config",
    "get_filter_operators",
]
