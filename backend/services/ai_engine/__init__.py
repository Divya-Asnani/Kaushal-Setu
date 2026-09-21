"""AI engine: real Problem Fingerprint extraction and semantic matching.

The application ships heuristic implementations of both (keyword matching for
fingerprints, skill-set overlap for matching). This package provides model-backed
versions and exposes them through `adapters`, which keep the exact signatures and
return shapes the application's routes already expect.

Every adapter falls back to the built-in heuristic when the engine is unconfigured or
a call fails, so adding this package cannot take the application down.
"""
from backend.services.ai_engine.config import settings, status  # noqa: F401
