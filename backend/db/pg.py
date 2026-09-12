"""Direct PostgreSQL access, used only where the REST client cannot express the query.

That is pgvector similarity search. Everything else goes through db.supabase so the
project keeps a single obvious CRUD path.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from backend.core.config import settings
from backend.core.errors import APIError, VECTOR_SEARCH_ERROR

log = logging.getLogger(__name__)

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        if not settings.database_url:
            raise APIError(
                VECTOR_SEARCH_ERROR,
                "DATABASE_URL is not configured; semantic search is unavailable.",
            )
        from psycopg_pool import ConnectionPool

        _pool = ConnectionPool(
            settings.database_url, min_size=1, max_size=5, kwargs={"autocommit": True}
        )
    return _pool


@contextmanager
def cursor() -> Iterator[Any]:
    from psycopg.rows import dict_row

    with _get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            yield cur


def query(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    try:
        with cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    except APIError:
        raise
    except Exception as exc:  # pragma: no cover - depends on live database
        log.exception("pgvector query failed")
        raise APIError(VECTOR_SEARCH_ERROR, "Semantic search failed.") from exc


def to_vector_literal(values: list[float]) -> str:
    """pgvector accepts its own text form: '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
