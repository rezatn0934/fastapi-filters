<h1 align="center">
<img alt="logo" src="https://raw.githubusercontent.com/uriyyo/fastapi-filters/main/logo.png">
</h1>

<div align="center">
<img alt="license" src="https://img.shields.io/badge/License-MIT-lightgrey">
<img alt="test" src="https://github.com/rezatn0934/fastapi-filters/workflows/Test/badge.svg">
<img alt="codecov" src="https://codecov.io/gh/rezatn0934/fastapi-filters/branch/main/graph/badge.svg">
<a href="https://pepy.tech/project/fastapi_filters__standard"><img alt="downloads" src="https://pepy.tech/badge/fastapi_filters__standard"></a>
<a href="https://pypi.org/project/fastapi_filters__standard"><img alt="pypi" src="https://img.shields.io/pypi/v/fastapi_filters__standard"></a>
<img alt="black" src="https://img.shields.io/badge/code%20style-black-000000.svg">
</div>

## Introduction

`fastapi_filters__standard` is a **fork of [fastapi-filters](https://github.com/uriyyo/fastapi-filters)** providing filtering and sorting features for [FastAPI](https://fastapi.tiangolo.com/) applications.

This fork introduces **standard query parameter syntax** for filters:

* Field operations are now standardized:

  ```
  field__operation
  ```

  Instead of the old syntax:

  ```
  field[operation]
  ```
* Operations are standardized across the package, independent of SQLAlchemy naming.
* For filters requiring lists, values are **comma-separated in a single parameter**:

  ```
  GET /places?main_industry=1,2,3
  ```
* Optionally, **Raw Mode** can be used to receive filters exactly as sent in query parameters.

---

## Installation

```bash
pip install fastapi_filters__standard
```

---

## Quickstart

Filters can be defined either **manually** or **automatically from Pydantic models**.

```python
from typing import List

from fastapi import FastAPI, Depends
from pydantic import BaseModel, Field

from fastapi_filters_standard import create_filters, create_filters_from_model, FilterValues, RawFilterValues

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
        filters: RawFilterValues = Depends(create_filters_from_model(UserOut, raw_mode=True)),
) -> RawFilterValues:
    return filters
```

---

## SQLAlchemy Integration

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_filters__standard.ext.sqlalchemy import apply_filters

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
* **Raw Mode**: receive filters exactly as sent, for forwarding to external services
* Compatible with FastAPI and SQLAlchemy async
* Backwards compatible with most `fastapi-filters` features
