"""Settings for the AI engine.

Deliberately self-contained rather than an addition to ``backend/config.py``. The
engine needs credentials the rest of the application has never needed (Gemini, and a
direct Postgres URL for pgvector), and keeping them here means the engine can be added
or removed without touching the application's own configuration.

Everything has a default, so importing this module never fails. Whether the engine can
actually run is reported by ``is_configured()`` and checked by the adapters, which fall
back to the application's built-in heuristics when it cannot.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name) or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name) or default)
    except ValueError:
        return default


@dataclass
class EngineSettings:
    # --- Gemini ---
    gemini_api_key: str = field(default_factory=lambda: _env("GEMINI_API_KEY"))
    gemini_embedding_model: str = field(
        default_factory=lambda: _env("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
    )
    embedding_dim: int = field(default_factory=lambda: _env_int("EMBEDDING_DIM", 1536))
    gemini_fingerprint_model: str = field(
        default_factory=lambda: _env("GEMINI_FINGERPRINT_MODEL", "gemma-4-31b-it")
    )
    gemini_fingerprint_fallback_model: str = field(
        default_factory=lambda: _env("GEMINI_FINGERPRINT_FALLBACK_MODEL", "gemini-3.5-flash-lite")
    )
    fingerprint_max_attempts: int = field(
        default_factory=lambda: _env_int("FINGERPRINT_MAX_ATTEMPTS", 1)
    )
    fingerprint_fallback_attempts: int = field(
        default_factory=lambda: _env_int("FINGERPRINT_FALLBACK_ATTEMPTS", 2)
    )
    fingerprint_timeout_seconds: int = field(
        default_factory=lambda: _env_int("FINGERPRINT_TIMEOUT_SECONDS", 20)
    )

    # --- pgvector ---
    # Prefer the Supabase Session pooler string: the direct host is IPv6-only and is
    # unreachable from Docker and most PaaS networks.
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL"))
    db_connect_timeout_seconds: int = field(
        default_factory=lambda: _env_int("DB_CONNECT_TIMEOUT_SECONDS", 8)
    )
    db_pool_timeout_seconds: int = field(
        default_factory=lambda: _env_int("DB_POOL_TIMEOUT_SECONDS", 10)
    )
    match_candidate_pool: int = field(
        default_factory=lambda: _env_int("MATCH_CANDIDATE_POOL", 50)
    )

    # --- Relevance filtering ---
    # A technician with no evidence of relevance should not be offered at all. These
    # control how much evidence is enough; set MATCH_MIN_SCORE to 0 to rank everyone.
    match_min_score: float = field(
        default_factory=lambda: _env_float("MATCH_MIN_SCORE", 0.45)
    )
    # Below this cosine similarity a retrieved case is not treated as real evidence.
    match_min_similarity: float = field(
        default_factory=lambda: _env_float("MATCH_MIN_SIMILARITY", 0.60)
    )
    # Workers outside their own stated service radius are excluded, unless that would
    # leave the customer with nothing.
    match_enforce_radius: bool = field(
        default_factory=lambda: _env("MATCH_ENFORCE_RADIUS", "true") != "false"
    )

    # --- Ranking weights ---
    # Named to match the application's own settings so the two cannot drift apart.
    weight_problem: float = field(
        default_factory=lambda: _env_float("WEIGHT_PROBLEM_SIMILARITY", 0.40)
    )
    weight_context: float = field(
        default_factory=lambda: _env_float("WEIGHT_CONTEXT_SIMILARITY", 0.30)
    )
    weight_verified: float = field(
        default_factory=lambda: _env_float("WEIGHT_VERIFIED_EXP_CONFIDENCE", 0.20)
    )
    weight_proximity: float = field(
        default_factory=lambda: _env_float("WEIGHT_PROXIMITY", 0.10)
    )

    # --- Feature switches ---
    def fingerprint_enabled(self) -> bool:
        """Real extraction needs only a Gemini key."""
        return bool(self.gemini_api_key) and _env("AI_ENGINE_FINGERPRINT", "true") != "false"

    def matching_enabled(self) -> bool:
        """Semantic matching needs a Gemini key *and* a Postgres URL for pgvector."""
        return (
            bool(self.gemini_api_key)
            and bool(self.database_url)
            and _env("AI_ENGINE_MATCHING", "true") != "false"
        )

    @property
    def weights(self) -> dict[str, float]:
        return {
            "problem": self.weight_problem,
            "context": self.weight_context,
            "verified": self.weight_verified,
            "proximity": self.weight_proximity,
        }


settings = EngineSettings()


def status() -> dict[str, object]:
    """Configuration presence, for logging and health output. Never returns values."""
    return {
        "gemini_configured": bool(settings.gemini_api_key),
        "database_url_configured": bool(settings.database_url),
        "fingerprint_enabled": settings.fingerprint_enabled(),
        "matching_enabled": settings.matching_enabled(),
        "fingerprint_model": settings.gemini_fingerprint_model,
        "fingerprint_fallback_model": settings.gemini_fingerprint_fallback_model,
        "embedding_model": settings.gemini_embedding_model,
        "embedding_dim": settings.embedding_dim,
        "weights": settings.weights,
    }
