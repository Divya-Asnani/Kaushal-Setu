import os
from datetime import datetime, timezone, timedelta
from pydantic_settings import BaseSettings

# Indian Standard Time (IST, UTC+05:30)
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

def get_indian_time() -> datetime:
    """Returns current datetime in Indian Standard Time (IST, UTC+05:30)."""
    return datetime.now(IST)


class Settings(BaseSettings):
    PROJECT_NAME: str = "KaushalSetu"
    API_V1_STR: str = "/api/v1"
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://xyzcompany.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_anon_key")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "dummy_service_role_key")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "super-secret-jwt-token-with-at-least-32-chars-long!")
    
    # Storage Buckets (as defined in single source of truth)
    STORAGE_BUCKET_PROBLEM: str = "problem-media"
    STORAGE_BUCKET_EXPERIENCE: str = "experience-media"
    
    # Matching Algorithm Weights (Frozen Section 8)
    WEIGHT_PROBLEM_SIMILARITY: float = 0.40
    WEIGHT_CONTEXT_SIMILARITY: float = 0.30
    WEIGHT_VERIFIED_EXP_CONFIDENCE: float = 0.20
    WEIGHT_PROXIMITY: float = 0.10

    model_config = {
        "case_sensitive": True,
        "env_file": [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
            ".env"
        ],
        "extra": "ignore"
    }

settings = Settings()
