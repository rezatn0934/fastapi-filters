import pytest
from fastapi import Depends, status
from pydantic import BaseModel

from fastapi_filters_standard.sorters import create_sorting, create_sorting_from_model
from fastapi_filters_standard.types import SortingValues


@pytest.mark.asyncio
async def test_filters_as_dep(app, client):
    @app.get("/")
    async def route(
        sorting: SortingValues = Depends(create_sorting("name", "age", "created_at")),
    ) -> SortingValues:
        return sorting

    res = await client.get("/")

    assert res.status_code == status.HTTP_200_OK
    assert res.json() == []

    res = await client.get("/", params={"sort": "+name,-age"})

    assert res.status_code == status.HTTP_200_OK
    assert res.json() == [["name", "asc", None], ["age", "desc", None]]


@pytest.mark.asyncio
async def test_sorting_with_comma_separated_values(app, client):
    @app.get("/")
    async def route(
        sorting: SortingValues = Depends(create_sorting("name", "age", "created_at")),
    ) -> SortingValues:
        return sorting

    # Correct: comma-separated values in single parameter
    res = await client.get("/", params={"sort": "+name,-age,+created_at"})

    assert res.status_code == status.HTTP_200_OK
    assert res.json() == [["name", "asc", None], ["age", "desc", None], ["created_at", "asc", None]]

    # Test that repeated parameters are handled correctly
    # FastAPI may receive multiple values as a list, validator should handle it
    res = await client.get("/", params=[("sort", "+name"), ("sort", "-age"), ("sort", "+created_at")])

    # The validator should join multiple values and split them
    assert res.status_code == status.HTTP_200_OK
    assert res.json() == [["name", "asc", None], ["age", "desc", None], ["created_at", "asc", None]]


def test_create_sorting():
    model = create_sorting("name", "age", "created_at")

    assert model.__defs__ == {
        "+age": ("age", "asc", None),
        "-age": ("age", "desc", None),
        "+name": ("name", "asc", None),
        "-name": ("name", "desc", None),
        "+created_at": ("created_at", "asc", None),
        "-created_at": ("created_at", "desc", None),
    }


def test_create_sorting_from_model():
    class Group(BaseModel):
        name: str

    class User(BaseModel):
        name: str
        age: int
        created_at: str
        group: Group
        languages: list[str]

    model = create_sorting_from_model(User)

    assert model.__defs__ == {
        "+age": ("age", "asc", None),
        "-age": ("age", "desc", None),
        "+name": ("name", "asc", None),
        "-name": ("name", "desc", None),
        "+created_at": ("created_at", "asc", None),
        "-created_at": ("created_at", "desc", None),
    }


def test_create_sorting_invalid_default():
    with pytest.raises(ValueError, match=r"^Default sort field invalid is not in .*$"):
        create_sorting("name", "age", "created_at", default="invalid")
