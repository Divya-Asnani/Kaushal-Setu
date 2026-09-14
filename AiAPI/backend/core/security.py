"""Supabase JWT validation.

Supabase projects sign access tokens either with the legacy shared HS256 secret or,
on newer projects, with an asymmetric key published via JWKS. Both are supported so
the team does not have to care which their project uses.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

import jwt
from jwt import PyJWKClient

from backend.core.config import settings
from backend.core.errors import APIError, AUTH_REQUIRED

log = logging.getLogger(__name__)

_jwks_client: PyJWKClient | None = None
_jwks_lock = threading.Lock()
_JWKS_TTL = 600
_jwks_created_at = 0.0


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client, _jwks_created_at
    with _jwks_lock:
        expired = time.time() - _jwks_created_at > _JWKS_TTL
        if _jwks_client is None or expired:
            url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
            _jwks_client = PyJWKClient(url, cache_keys=True)
            _jwks_created_at = time.time()
        return _jwks_client


def decode_access_token(token: str) -> dict[str, Any]:
    """Return the token claims, or raise AUTH_REQUIRED."""
    options = {"verify_aud": False}
    try:
        if settings.supabase_jwt_secret:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                options=options,
            )
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            options=options,
        )
    except jwt.ExpiredSignatureError as exc:
        raise APIError(AUTH_REQUIRED, "Access token has expired.") from exc
    except jwt.PyJWTError as exc:
        # Deliberately not echoing the token or the library message to the client.
        log.info("JWT rejected: %s", type(exc).__name__)
        raise APIError(AUTH_REQUIRED, "Invalid access token.") from exc
    except APIError:
        raise
    except Exception as exc:  # pragma: no cover - network/JWKS failures
        log.exception("JWT validation failed unexpectedly")
        raise APIError(AUTH_REQUIRED, "Could not validate access token.") from exc
