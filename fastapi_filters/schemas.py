from typing import Annotated, Any, TypeAlias, TypeVar

from pydantic import BeforeValidator, GetPydanticSchema

T = TypeVar("T")


def csv_list_validator(v: Any) -> Any:
    match v:
        case str():
            return v.split(",")
        case list() if all(isinstance(item, str) for item in v):
            # If FastAPI receives multiple query parameters, join them with comma
            # This prevents duplicate parameters like ?param=1&param=2&param=3
            # Example: ["1", "2", "3"] -> "1,2,3" -> ["1", "2", "3"]
            return ",".join(v).split(",")
        case list():
            # If it's already a list of non-strings (from multiple query params), join and split
            return ",".join(str(item) for item in v).split(",")
        case _:
            return v


CSVList: TypeAlias = Annotated[
    list[T],
    BeforeValidator(csv_list_validator),
    GetPydanticSchema(
        get_pydantic_json_schema=lambda core_schema, handler: {
            **handler.resolve_ref_schema(handler(core_schema)),
            "explode": False,
        },
    ),
]

__all__ = [
    "CSVList",
]
