"""Application settings, loaded once from the environment."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "iBolt API"
    api_prefix: str = "/api/v1"
    debug: bool = False

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    database_url: str = ""
    supabase_jwt_secret: str = ""

    # Gemini
    gemini_api_key: str = ""
    gemini_embedding_model: str = "gemini-embedding-2"
    embedding_dim: int = 1536
    gemini_fingerprint_model: str = "gemma-4-31b-it"
    # Gemma has no structured-output mode, so a malformed JSON reply is retried on
    # the same model with a stricter instruction; a transient 5xx is retried after a
    # backoff. Once these attempts are spent the backup model takes over.
    fingerprint_max_attempts: int = 1
    # Gemini backup. Supports real structured output and is far more reliable, so it
    # needs fewer attempts. Set blank to disable and run on Gemma alone.
    gemini_fingerprint_fallback_model: str = "gemini-3.5-flash-lite"
    fingerprint_fallback_attempts: int = 2
    # A single call is cut off after this long; Gemma can otherwise run past a minute.
    fingerprint_timeout_seconds: int = 20

    # Neo4j
    neo4j_uri: str = ""
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""

    # Storage
    storage_problem_bucket: str = "problem-media"
    storage_experience_bucket: str = "experience-media"
    storage_knowledge_bucket: str = "knowledge-case-media"
    storage_certificate_bucket: str = "certificates"
    knowledge_video_max_bytes: int = 52_428_800

    # Matching — prototype weights, deliberately configurable (PRD §14).
    match_weight_problem: float = 0.40
    match_weight_context: float = 0.30
    match_weight_verified: float = 0.20
    match_weight_proximity: float = 0.10
    match_candidate_pool: int = 50
    service_request_ttl_hours: int = 48

    @property
    def match_weights(self) -> dict[str, float]:
        return {
            "problem": self.match_weight_problem,
            "context": self.match_weight_context,
            "verified": self.match_weight_verified,
            "proximity": self.match_weight_proximity,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
