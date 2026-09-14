"""pgvector candidate retrieval.

Cosine distance via the ``<=>`` operator, which is what the HNSW indexes on
``experience_embeddings`` and ``knowledge_case_embeddings`` were built for. Similarity
is reported as ``1 - distance`` so callers always work with "higher is better" on 0..1.

This is the one place that needs a direct Postgres connection: PostgREST cannot express
a vector ordering, so the Supabase REST client cannot run these queries.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from backend.services.ai_engine.config import settings
from backend.services.ai_engine.errors import APIError, VECTOR_SEARCH_ERROR

log = logging.getLogger("kaushalsetu.ai_engine.retrieval")

_pool = None

IPV6_HINT = (
    "Supabase's direct database host (db.<ref>.supabase.co) resolves to IPv6 only and "
    "is unreachable from Docker and most hosting networks. Use the Session pooler "
    "connection string from Supabase -> Settings -> Database."
)


def _get_pool():
    global _pool
    if _pool is None:
        if not settings.database_url:
            raise APIError(VECTOR_SEARCH_ERROR, "DATABASE_URL is not configured.")
        from psycopg_pool import ConnectionPool

        _pool = ConnectionPool(
            settings.database_url,
            min_size=0,
            max_size=5,
            timeout=settings.db_pool_timeout_seconds,
            kwargs={
                "autocommit": True,
                "connect_timeout": settings.db_connect_timeout_seconds,
            },
            open=True,
            check=None,
        )
    return _pool


def _is_unreachable(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return any(
        k in text
        for k in ("network is unreachable", "timeout", "could not connect",
                  "connection refused", "name or service not known", "temporary failure")
    )


def query(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    from psycopg.rows import dict_row

    try:
        with _get_pool().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                return cur.fetchall()
    except APIError:
        raise
    except Exception as exc:
        if _is_unreachable(exc):
            log.error("Vector database unreachable. %s", IPV6_HINT)
            raise APIError(
                VECTOR_SEARCH_ERROR, "The vector database is unreachable.",
                {"hint": IPV6_HINT},
            ) from exc
        log.exception("pgvector query failed")
        raise APIError(VECTOR_SEARCH_ERROR, "Semantic search failed.") from exc


def to_vector_literal(values: list[float]) -> str:
    """pgvector accepts its own text form: '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


@dataclass
class ExperienceCandidate:
    experience_id: str
    worker_id: str
    similarity: float
    title: str
    problem_description: str
    diagnosis: str | None
    outcome_summary: str | None
    source_text: str


_EXPERIENCE_SQL = """
SELECT
    e.id                              AS experience_id,
    e.worker_id                       AS worker_id,
    1 - (ee.embedding <=> %s::vector) AS similarity,
    e.title                           AS title,
    e.problem_description             AS problem_description,
    e.diagnosis                       AS diagnosis,
    e.outcome_summary                 AS outcome_summary,
    ee.source_text                    AS source_text
FROM experience_embeddings ee
JOIN experiences e ON e.id = ee.experience_id
ORDER BY ee.embedding <=> %s::vector
LIMIT %s
"""


def search_experiences(
    query_vector: list[float], limit: int | None = None
) -> list[ExperienceCandidate]:
    """Nearest solved experiences to a query vector."""
    limit = limit or settings.match_candidate_pool
    literal = to_vector_literal(query_vector)
    return [
        ExperienceCandidate(
            experience_id=str(r["experience_id"]),
            worker_id=str(r["worker_id"]),
            similarity=float(r["similarity"]),
            title=r.get("title") or "",
            problem_description=r.get("problem_description") or "",
            diagnosis=r.get("diagnosis"),
            outcome_summary=r.get("outcome_summary"),
            source_text=r.get("source_text") or "",
        )
        for r in query(_EXPERIENCE_SQL, (literal, literal, limit))
    ]


def is_available() -> bool:
    """Cheap probe used by the adapters before committing to the semantic path."""
    if not settings.database_url:
        return False
    try:
        query("SELECT 1 AS ok")
        return True
    except Exception:
        return False
