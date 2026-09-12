"""iBolt / Kaushal Setu API.

FastAPI is the application and orchestration layer. PostgreSQL via Supabase is the
transactional source of truth; pgvector and Neo4j are derived, and either can be
rebuilt without data loss.
"""
from __future__ import annotations

import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(find_dotenv())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("ibolt")

from backend.core.config import settings  # noqa: E402
from backend.core.errors import register_exception_handlers  # noqa: E402
from backend.api.routes import (  # noqa: E402
    experiences,
    feedback,
    jobs,
    knowledge,
    matching,
    notifications,
    problems,
    profile,
    service_requests,
    workers,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    from backend.db.pg import close_pool
    from backend.services.graph import neo4j_client

    close_pool()
    neo4j_client.close()


app = FastAPI(
    title="iBolt API",
    description=(
        "AI-driven experience mapping and intelligent opportunity matching for "
        "electricians and repair technicians."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Prototype only; restrict before any real deployment.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Attach a request id and log latency.

    Deliberately logs only method, path and timing — never bodies, addresses or tokens.
    """
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    log.info(
        "%s %s -> %s in %.0fms", request.method, request.url.path, response.status_code, elapsed_ms
    )
    return response


for router in (
    profile.router,
    workers.router,
    problems.router,
    matching.router,
    experiences.router,
    service_requests.router,
    jobs.router,
    feedback.router,
    knowledge.router,
    notifications.router,
):
    app.include_router(router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "service": "iBolt API",
        "docs": "/docs",
        "api": settings.api_prefix,
    }


@app.get("/health", tags=["health"])
def health() -> dict[str, object]:
    """Configuration presence check. Deliberately reports no secret values."""
    from backend.services.graph import neo4j_client

    return {
        "status": "ok",
        "supabase_configured": bool(settings.supabase_url and settings.supabase_service_role_key),
        "database_url_configured": bool(settings.database_url),
        "gemini_configured": bool(settings.gemini_api_key),
        "jwt_mode": "hs256_secret" if settings.supabase_jwt_secret else "jwks",
        "embedding_model": settings.gemini_embedding_model,
        "embedding_dim": settings.embedding_dim,
        "fingerprint_model": settings.gemini_fingerprint_model,
        "fingerprint_fallback_model": settings.gemini_fingerprint_fallback_model,
        "neo4j_available": neo4j_client.is_available(),
        "match_weights": settings.match_weights,
    }
