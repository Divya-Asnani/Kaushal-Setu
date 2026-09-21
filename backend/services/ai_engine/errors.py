"""Engine-local error type.

Kept separate from the application's AppException on purpose: nothing in this package
should raise an error the application's handlers have to know about. The adapters catch
EngineError and fall back to the built-in heuristics, so an AI failure degrades the
result rather than failing the request.
"""
from __future__ import annotations

from typing import Any

AI_ERROR = "AI_ERROR"
VECTOR_SEARCH_ERROR = "VECTOR_SEARCH_ERROR"


class APIError(Exception):
    """Named APIError so the modules copied from the standalone service work unchanged."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


EngineError = APIError
