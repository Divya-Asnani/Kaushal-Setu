"""Shared Gemini client.

The frozen spec named OpenAI. The team runs on Gemini instead, so this module is the
single place that knows about the provider. Dimensionality stays 1536, which is what
matters: the pgvector columns and HNSW indexes are unchanged.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from backend.core.config import settings
from backend.core.errors import AI_ERROR, APIError

log = logging.getLogger(__name__)


@lru_cache
def get_client():
    if not settings.gemini_api_key:
        raise APIError(AI_ERROR, "GEMINI_API_KEY is not configured.")
    from google import genai

    return genai.Client(api_key=settings.gemini_api_key)


def is_quota_error(exc: Exception) -> bool:
    """True for 429 RESOURCE_EXHAUSTED, the API's rate-limit signal."""
    text = f"{type(exc).__name__} {exc}".lower()
    return any(k in text for k in ("429", "resource_exhausted", "quota", "rate limit"))


def is_transient_server_error(exc: Exception) -> bool:
    """True for 500/503-class faults on Google's side.

    These are worth retrying, unlike a quota error: the same request often succeeds a
    moment later. Gemma in particular returns 500 INTERNAL intermittently.
    """
    text = f"{type(exc).__name__} {exc}".lower()
    return any(
        k in text
        for k in ("500", "503", "internal", "unavailable", "overloaded", "deadline")
    )
