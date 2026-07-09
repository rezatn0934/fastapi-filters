from datetime import date, datetime, time, timedelta

import pytest

from fastapi_filters_standard.operators import (
    DATE_LOOKUP_OPERATORS,
    DATETIME_LOOKUP_OPERATORS,
    DEFAULT_OPERATORS,
    NUM_OPERATORS,
    SEQ_OPERATORS,
    TIME_LOOKUP_OPERATORS,
    FilterOperator,
    get_filter_operators,
)


@pytest.mark.parametrize(
    ("tp", "operators"),
    [
        *[(tp, SEQ_OPERATORS) for tp in (list[int], tuple[float, ...])],
        (bool, [FilterOperator.eq, FilterOperator.ne]),
        *[(tp, DEFAULT_OPERATORS + NUM_OPERATORS) for tp in (int, float, timedelta)],
        *[(tp, DEFAULT_OPERATORS + NUM_OPERATORS + DATE_LOOKUP_OPERATORS) for tp in (date,)],
        *[(tp, DEFAULT_OPERATORS + NUM_OPERATORS + DATETIME_LOOKUP_OPERATORS) for tp in (datetime,)],
        *[(tp, DEFAULT_OPERATORS + NUM_OPERATORS + TIME_LOOKUP_OPERATORS) for tp in (time,)],
        (int | None, [FilterOperator.is_null, *DEFAULT_OPERATORS, *NUM_OPERATORS]),
        (list[int], SEQ_OPERATORS),
        (tuple[float, ...], SEQ_OPERATORS),
    ],
    ids=str,
)
def test_get_default_operators(tp, operators):
    assert {*get_filter_operators(tp)} == {*operators}
