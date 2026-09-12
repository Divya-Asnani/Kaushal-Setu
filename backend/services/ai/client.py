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
    text = f"{type(exc).__name__} {exc}".lower()
    return any(k in text for k in ("429", "resource_exhausted", "quota", "rate limit"))
