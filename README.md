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

* Multiple values can be passed as comma-separated list:

  ```
  GET /places?main_industry=1,2,3
  ```
* No need to use `[in]` or other operator suffixes in URL.

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

# import from the forked package
from fastapi_filters__standard import create_filters, create_filters_from_model, FilterValues

app = FastAPI()


class UserOut(BaseModel):
    name: str = Field(..., example="Steve")
    surname: str = Field(..., example="Rogers")
    age: int = Field(..., example=102)


@app.get("/users")
async def get_users_manual_filters(
    filters: FilterValues = Depends(create_filters(name=str, surname=str, age=int)),
) -> List[UserOut]:
    pass


@app.get("/users")
async def get_users_auto_filters(
    filters: FilterValues = Depends(create_filters_from_model(UserOut)),
) -> List[UserOut]:
    pass
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

### Features of this fork

* Standardized query parameter syntax (comma-separated, multi-value)
* Full support for filtering and sorting
* Compatible with FastAPI and SQLAlchemy async
* Backwards compatible with most `fastapi-filters` features
