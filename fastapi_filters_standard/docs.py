from fastapi import FastAPI
from typing import Any


def _fix_openapi_schema(openapi_schema: dict[str, Any]) -> None:
    """Fix explode parameter in OpenAPI schema."""
    for endpoints in openapi_schema.get("paths", {}).values():
        for endpoint in endpoints.values():
            for parameter in endpoint.get("parameters", ()):
                if "explode" in parameter.get("schema", {}):
                    parameter["explode"] = parameter["schema"].pop("explode")


# Global flag to track if we've already patched
_patched = False


def _auto_fix_docs() -> None:
    """Automatically patch FastAPI to fix explode parameter."""
    global _patched
    
    if _patched:
        return
    
    try:
        import fastapi
        
        # Patch FastAPI.openapi method
        original_openapi = fastapi.FastAPI.openapi
        
        def patched_openapi(self: FastAPI) -> dict[str, Any]:
            """Patched openapi method that fixes explode parameter."""
            schema = original_openapi(self)
            _fix_openapi_schema(schema)
            return schema
        
        # Replace the method
        fastapi.FastAPI.openapi = patched_openapi  # type: ignore[assignment]
        _patched = True
    except (ImportError, AttributeError):
        # FastAPI not installed or already patched
        pass


def fix_docs(app: FastAPI) -> None:
    """Manually fix docs for a specific app (legacy function, auto-patch is enabled by default)."""
    def _fix_docs() -> None:
        openapi = app.openapi()
        _fix_openapi_schema(openapi)

    app.add_event_handler("startup", _fix_docs)


__all__ = [
    "fix_docs",
    "_auto_fix_docs",
]
