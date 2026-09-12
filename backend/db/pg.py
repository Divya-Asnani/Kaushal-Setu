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


IPV6_HINT = (
    "Supabase's direct database host (db.<ref>.supabase.co) resolves to IPv6 only. "
    "That works from a machine with IPv6, but not from inside a Docker container on a "
    "default bridge network. Use the Session pooler connection string from "
    "Supabase -> Settings -> Database, which is reachable over IPv4."
)


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
            settings.database_url,
            min_size=0,
            max_size=5,
            # Fail fast rather than hanging a request for half a minute. An
            # unreachable database is a configuration problem, not a slow query.
            timeout=settings.db_pool_timeout_seconds,
            kwargs={
                "autocommit": True,
                "connect_timeout": settings.db_connect_timeout_seconds,
            },
            # Opening lazily keeps a misconfigured DATABASE_URL from blocking startup;
            # the rest of the API does not need this connection.
            open=True,
            check=None,
        )
    return _pool


@contextmanager
def cursor() -> Iterator[Any]:
    from psycopg.rows import dict_row

    with _get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            yield cur


def _is_unreachable(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return any(
        k in text
        for k in ("network is unreachable", "timeout", "could not connect",
                  "connection refused", "name or service not known", "temporary failure")
    )


def query(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    try:
        with cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    except APIError:
        raise
    except Exception as exc:  # pragma: no cover - depends on live database
        if _is_unreachable(exc):
            # By far the most common cause, and the least obvious from the raw error.
            log.error("Database unreachable for vector search. %s", IPV6_HINT)
            raise APIError(
                VECTOR_SEARCH_ERROR,
                "The database is unreachable, so semantic search is unavailable.",
                {"hint": IPV6_HINT},
            ) from exc
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
