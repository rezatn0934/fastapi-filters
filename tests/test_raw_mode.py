import pytest
from fastapi import Depends, status
from pydantic import BaseModel

from fastapi_filters_standard import create_filters_from_model, RawFilterValues


@pytest.mark.asyncio
async def test_raw_mode(app, client):
    class UserModel(BaseModel):
        username: str
        age: int

    @app.get("/")
    async def route(
        filters: RawFilterValues = Depends(
            create_filters_from_model(UserModel, raw_mode=True)
        ),
    ) -> RawFilterValues:
        return filters

    res = await client.get(
        "/",
        params={"username__contains": "09001", "age__gte": "18"},
    )

    assert res.status_code == status.HTTP_200_OK
    # Should return raw query parameters without conversion
    assert res.json() == {
        "username__contains": "09001",
        "age__gte": "18",
    }

