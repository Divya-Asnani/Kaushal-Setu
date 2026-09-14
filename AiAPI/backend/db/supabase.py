"""Supabase client used for all ordinary CRUD.

The service-role key bypasses RLS, which is exactly what the frozen prototype
architecture expects: RLS is off and authorization lives in FastAPI. That makes
it critical that every route resolves identity from the validated JWT and never
from client-supplied fields.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from backend.core.config import settings
from backend.core.errors import APIError, INTERNAL_ERROR


@lru_cache
def get_supabase() -> Client:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise APIError(
            INTERNAL_ERROR,
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def table(name: str):
    return get_supabase().table(name)


def one_or_none(response: Any) -> dict[str, Any] | None:
    data = getattr(response, "data", None) or []
    return data[0] if data else None


def rows(response: Any) -> list[dict[str, Any]]:
    return getattr(response, "data", None) or []
