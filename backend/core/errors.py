"""Standard error contract (FastAPI spec section 5)."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

AUTH_REQUIRED = "AUTH_REQUIRED"
FORBIDDEN = "FORBIDDEN"
VALIDATION_ERROR = "VALIDATION_ERROR"
RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
CONFLICT = "CONFLICT"
INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
AI_ERROR = "AI_ERROR"
VECTOR_SEARCH_ERROR = "VECTOR_SEARCH_ERROR"
GRAPH_ERROR = "GRAPH_ERROR"
STORAGE_ERROR = "STORAGE_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"

_STATUS = {
    AUTH_REQUIRED: 401,
    FORBIDDEN: 403,
    VALIDATION_ERROR: 422,
    RESOURCE_NOT_FOUND: 404,
    CONFLICT: 409,
    INVALID_STATE_TRANSITION: 409,
    AI_ERROR: 502,
    VECTOR_SEARCH_ERROR: 502,
    GRAPH_ERROR: 502,
    STORAGE_ERROR: 502,
    INTERNAL_ERROR: 500,
}


class APIError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = _STATUS.get(code, 400)
        super().__init__(message)


def not_found(what: str) -> APIError:
    return APIError(RESOURCE_NOT_FOUND, f"{what} not found.")


def forbidden(message: str = "You are not allowed to perform this action.") -> APIError:
    return APIError(FORBIDDEN, message)


def invalid_transition(current: str, requested: str) -> APIError:
    return APIError(
        INVALID_STATE_TRANSITION,
        f"Cannot move from '{current}' to '{requested}'.",
        {"current": current, "requested": requested},
    )


def _body(code: str, message: str, details: dict[str, Any], request: Request) -> dict[str, Any]:
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    return {
        "error": {"code": code, "message": message, "details": details},
        "request_id": request_id,
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def _api_error(request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(exc.code, exc.message, exc.details, request),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_body(
                VALIDATION_ERROR,
                "Request validation failed.",
                {"errors": exc.errors()},
                request,
            ),
        )
