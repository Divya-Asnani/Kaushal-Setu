"""Embedding generation.

`gemini-embedding-001` is used with output_dimensionality=1536 so vectors drop
straight into the existing `vector(1536)` columns. Google only pre-normalises the
full 3072-dimension output, so truncated outputs are normalised here — without that,
cosine distance in pgvector would be computed over unnormalised vectors and the
similarity scores would not be comparable between rows.
"""
from __future__ import annotations

import logging
import math

from backend.services.ai_engine.config import settings
from backend.services.ai_engine.errors import AI_ERROR, APIError
from backend.services.ai_engine.client import get_client

log = logging.getLogger(__name__)

DOCUMENT = "RETRIEVAL_DOCUMENT"
QUERY = "RETRIEVAL_QUERY"


def _normalise(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0:
        return values
    return [v / norm for v in values]


def embed_texts(texts: list[str], task_type: str = DOCUMENT) -> list[list[float]]:
    if not texts:
        return []
    from google.genai import types

    try:
        response = get_client().models.embed_content(
            model=settings.gemini_embedding_model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.embedding_dim,
            ),
        )
    except APIError:
        raise
    except Exception as exc:
        log.exception("Embedding request failed")
        raise APIError(AI_ERROR, "Could not generate embeddings.") from exc

    vectors = [_normalise(list(e.values)) for e in response.embeddings]
    for vector in vectors:
        if len(vector) != settings.embedding_dim:
            raise APIError(
                AI_ERROR,
                f"Embedding model returned {len(vector)} dimensions, "
                f"expected {settings.embedding_dim}.",
            )
    return vectors


def embed_text(text: str, task_type: str = DOCUMENT) -> list[float]:
    return embed_texts([text], task_type)[0]


def embed_query(text: str) -> list[float]:
    return embed_text(text, QUERY)


def model_name() -> str:
    return settings.gemini_embedding_model
