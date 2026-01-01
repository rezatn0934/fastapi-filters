from typing import Annotated

import pytest
from fastapi import Query

from fastapi_filters_standard.schemas import CSVList


@pytest.fixture
def app(app):
    @app.get("/")
    def route(
        q1: Annotated[CSVList[int], Query()],
        q2: Annotated[list[int], Query()],
    ):
        return []

    # Auto-patch is enabled by default, no need to call fix_docs
    return app


def test_fix_docs(app, client):
    assert app.openapi()["paths"]["/"]["get"]["parameters"] == [
        {
            "in": "query",
            "name": "q1",
            "required": True,
            "schema": {"items": {"type": "integer"}, "title": "Q1", "type": "array"},
            "explode": False,
        },
        {
            "in": "query",
            "name": "q2",
            "required": True,
            "schema": {"items": {"type": "integer"}, "title": "Q2", "type": "array"},
        },
    ]
