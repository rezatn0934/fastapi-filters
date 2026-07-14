<h1 align="center">
<img alt="logo" src="https://raw.githubusercontent.com/uriyyo/fastapi-filters/main/logo.png">
</h1>

<div align="center">
<img alt="license" src="https://img.shields.io/badge/License-MIT-lightgrey">
<img alt="test" src="https://github.com/rezatn0934/fastapi-filters/workflows/Test/badge.svg">
<img alt="codecov" src="https://codecov.io/gh/rezatn0934/fastapi-filters/branch/main/graph/badge.svg">
<a href="https://pepy.tech/project/fastapi_filters_standard"><img alt="downloads" src="https://pepy.tech/badge/fastapi_filters_standard"></a>
<a href="https://pypi.org/project/fastapi_filters_standard"><img alt="pypi" src="https://img.shields.io/pypi/v/fastapi_filters_standard"></a>
<img alt="black" src="https://img.shields.io/badge/code%20style-black-000000.svg">
</div>

## Introduction

`fastapi_filters_standard` is a **fork of [fastapi-filters](https://github.com/uriyyo/fastapi-filters)** providing filtering and sorting features for [FastAPI](https://fastapi.tiangolo.com/) applications.

### Additional features in this fork

Compared to the original `fastapi-filters`, this fork adds:

- Standard query parameter syntax using `field__operation`.
- Nested filtering (`state__fa_name__icontains=tehran`).
- Nested sorting (`sort=+state__fa_name,-name`).
- Comma-separated values for multi-value filters.
- Raw Mode for forwarding filters without parsing.
- SQLAlchemy relationship-aware filtering and sorting.
- Django-inspired lookup names.
---

## Installation

```bash
pip install fastapi_filters_standard
```
## What's Different?

This fork changes several behaviors compared to the original package.

### Standard query syntax

Instead of:

```text
field[gte]=18
```

use:

```text
field__gte=18
```

### Nested lookups

Nested relationships can be filtered using Django-style syntax.

```text
GET /cities?state__fa_name__icontains=tehran
```

### Multi-value filters

List values are passed as comma-separated values.

```text
GET /users?id__in=1,2,3
```

instead of repeating the same query parameter.

### Raw Mode

Filters can optionally be returned exactly as received from the request without parsing.

---

## Quickstart

Filters can be defined either **manually** or **automatically from Pydantic models**.

```python
from typing import List

from fastapi import FastAPI, Depends
from pydantic import BaseModel, Field

from fastapi_filters_standard import (
    create_filters,
    create_filters_from_model,
    create_sorting_from_model,
    FilterValues,
    RawFilterValues,
    SortingValues,
)

app = FastAPI()


class UserOut(BaseModel):
    name: str = Field(..., example="Steve")
    surname: str = Field(..., example="Rogers")
    age: int = Field(..., example=102)


# Manual filters
@app.get("/users/manual")
async def get_users_manual_filters(
    filters: FilterValues = Depends(create_filters(name=str, surname=str, age=int)),
) -> List[UserOut]:
    pass


# Automatic filters from Pydantic model
@app.get("/users/auto")
async def get_users_auto_filters(
    filters: FilterValues = Depends(create_filters_from_model(UserOut)),
) -> List[UserOut]:
    pass


# Raw Mode example
@app.get("/users/raw")
async def get_users_raw_filters(
    filters: RawFilterValues = Depends(
        create_filters_from_model(UserOut, raw_mode=True)
    ),
) -> RawFilterValues:
    pass

```

---

## Nested Filters Example

```python
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import select

from db.models import City
from fastapi_filters_standard import create_filters_from_model, FilterValues
from fastapi_filters_standard.ext.sqlalchemy import apply_filters

app = FastAPI()


class StateRead(BaseModel):
    fa_name: str


class CityRead(BaseModel):
    id: int
    fa_name: str
    state: StateRead


@app.get("/cities")
async def list_cities(
        filters: FilterValues = Depends(
            create_filters_from_model(
                CityRead,
                nested=True,
                max_depth=1,  # allow filtering one level deep (City -> State)
            )
        ),
):
    """
    Example usage:
    GET /cities?state__fa_name__icontains=تهران

    This produces:
    filters = {'state__fa_name': {'icontains': 'تهران'}}
    """
    query = apply_filters(select(City), filters, model=City)
    result = await db.scalars(query)
    return result.all()

```

This allows filtering cities based on fields of the related `state` object.

---
## Nested Sorting Example

class FastAPI:
pass

```python
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import select

from db.models import City
from fastapi_filters_standard import (
    SortingValues,
    create_sorting_from_model,
)
from fastapi_filters_standard.ext.sqlalchemy import apply_sorting

app = FastAPI()


class StateRead(BaseModel):
    fa_name: str


class CityRead(BaseModel):
    id: int
    fa_name: str
    state: StateRead


@app.get("/cities")
async def list_cities(
    sorting: SortingValues = Depends(
        create_sorting_from_model(
            CityRead,
            nested=True,
            max_depth=1,
        )
    ),
):
    """
    Example usage:

    GET /cities?sort=+state__fa_name,-fa_name
    """

    query = apply_sorting(
        select(City),
        sorting,
        model=City,
        nested=True,
    )

    result = await db.scalars(query)
    return result.all()

```

This allows ordering by fields of related models using the same double-underscore syntax as nested filters.

Examples:

```
GET /cities?sort=+state__fa_name
GET /cities?sort=-state__fa_name,+fa_name
GET /cities?sort=+country__name,-state__fa_name,+created_at
```

## SQLAlchemy Integration

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_filters_standard.ext.sqlalchemy import apply_filters

@app.get("/users")
async def get_users(
    db: AsyncSession = Depends(get_db),
    filters: FilterValues = Depends(create_filters_from_model(UserOut)),
) -> List[UserOut]:
    query = apply_filters(select(User), filters)
    result = await db.scalars(query)
    return result.all()
```

---

## Raw Mode Example with pytest

```python
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastapi_filters_standard import create_filters_from_model, RawFilterValues


@pytest.mark.asyncio
async def test_raw_mode():
    app = FastAPI()

    class UserModel(BaseModel):
        username: str
        age: int

    @app.get("/")
    async def route(
            filters: RawFilterValues = Depends(create_filters_from_model(UserModel, raw_mode=True))
    ) -> RawFilterValues:
        return filters

    client = TestClient(app)
    res = client.get("/", params={"username__contains": "09001", "age__gte": "18"})

    assert res.status_code == 200
    assert res.json() == {"username__contains": "09001", "age__gte": "18"}
```

---

### Features of this fork

* Standardized query parameter syntax (`field__operation`)
* Standardized operation names
* Comma-separated list support for multi-value filters
* Full support for filtering and sorting
* * **Nested filters and sorting** are supported, allowing filtering and ordering on related objects.

  Examples:

  ```text
  GET /cities?state__fa_name__icontains=تهران
  GET /cities?sort=+state__fa_name,-country__name
  ```
* **Raw Mode**: receive filters exactly as sent, for forwarding to external services
* Compatible with FastAPI and SQLAlchemy async
* Backwards compatible with most `fastapi-filters` features

## Supported Lookup Operators

| Lookup            | Description | Example |
|-------------------|-------------|---------|
| `exact`           | Exact match (default lookup) | `?name=John` |
| `ne`              | Not equal | `?age__ne=18` |
| `gt`              | Greater than | `?age__gt=18` |
| `gte`             | Greater than or equal | `?age__gte=18` |
| `lt`              | Less than | `?age__lt=65` |
| `lte`             | Less than or equal | `?age__lte=65` |
| `contains`        | Contains (String, ARRAY, JSON) | `?tags__contains=python` |
| `icontains`       | Case-insensitive contains | `?name__icontains=john` |
| `not_contains`    | Does not contain | `?tags__not_contains=python` |
| `not_icontains`   | Does not Case-insensitive contain | `?tags__not_contains=python` |
| `startswith`      | Starts with | `?name__startswith=Jo` |
| `not_startswith`  | Does not start with | `?name__not_startswith=Jo` |
| `istartswith`     | Case-insensitive starts with | `?name__istartswith=jo` |
| `not_istartswith` | Case-insensitive does not start with | `?name__not_istartswith=jo` |
| `endswith`        | Ends with | `?name__endswith=son` |
| `not_endswith`    | Does not end with | `?name__not_endswith=son` |
| `iendswith`       | Case-insensitive ends with | `?name__iendswith=son` |
| `not_iendswith`   | Case-insensitive does not end with | `?name__not_iendswith=son` |
| `in`              | Value in a list | `?id__in=1,2,3` |
| `not_in`          | Value not in a list | `?id__not_in=1,2,3` |
| `isnull`          | Check for `NULL` | `?deleted_at__isnull=true` |
| `overlap`         | PostgreSQL overlap | `?tags__overlap=python,django` |
| `not_overlap`     | Negated PostgreSQL overlap | `?tags__not_overlap=python,django` |
| `range`           | Between two values | `?age__range=18,30` |
| `date`            | Match the date part of a datetime | `?created_at__date=2026-07-14` |
| `year`            | Match year | `?created_at__year=2026` |
| `month`           | Match month | `?created_at__month=7` |
| `day`             | Match day | `?created_at__day=14` |
| `hour`            | Match hour | `?created_at__hour=10` |
| `minute`          | Match minute | `?created_at__minute=30` |
| `second`          | Match second | `?created_at__second=15` |
| `time`            | Match the time part of a datetime | `?created_at__time=10:30:00` |

> **Note**
>
> - `icontains` is implemented internally using SQLAlchemy's `ilike()` and performs a case-insensitive substring search (`ILIKE '%value%'`).
> - `contains` uses SQLAlchemy's native `contains()` operator, which works with strings as well as database types such as PostgreSQL `ARRAY` and `JSON`.
> - `like` supports SQL wildcard characters such as `%` and `_`.