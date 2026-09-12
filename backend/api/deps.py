"""Request dependencies: identity, role and ownership.

Caller identity always comes from the validated JWT. A user_id in a request body is
never trusted for authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Request

from backend.core.errors import APIError, AUTH_REQUIRED, forbidden, not_found
from backend.core.security import decode_access_token
from backend.db.supabase import one_or_none, table

CUSTOMER = "customer"
WORKER = "worker"
ADMIN = "admin"


@dataclass(frozen=True)
class CurrentUser:
    id: str
    role: str
    display_name: str
    is_active: bool
    claims: dict[str, Any]

    @property
    def is_admin(self) -> bool:
        return self.role == ADMIN

    def owns(self, user_id: str | None) -> bool:
        return user_id is not None and str(user_id) == self.id


def _bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise APIError(AUTH_REQUIRED, "Authorization: Bearer <token> is required.")
    return token.strip()


def get_current_user(request: Request) -> CurrentUser:
    claims = decode_access_token(_bearer_token(request))
    user_id = claims.get("sub")
    if not user_id:
        raise APIError(AUTH_REQUIRED, "Token is missing a subject claim.")

    profile = one_or_none(
        table("profiles").select("id, role, display_name, is_active").eq("id", user_id).limit(1).execute()
    )
    if profile is None:
        # Authenticated with Supabase but no application profile row yet.
        raise not_found("Profile")
    if not profile.get("is_active", True):
        raise forbidden("This account is deactivated.")

    return CurrentUser(
        id=str(profile["id"]),
        role=profile.get("role") or CUSTOMER,
        display_name=profile.get("display_name") or "",
        is_active=bool(profile.get("is_active", True)),
        claims=claims,
    )


def require_roles(*roles: str):
    """Dependency factory: allow only the listed roles (admin always allowed)."""

    def _dep(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles and not user.is_admin:
            raise forbidden(f"This action requires one of: {', '.join(roles)}.")
        return user

    return _dep


require_customer = require_roles(CUSTOMER)
require_worker = require_roles(WORKER)
require_admin = require_roles(ADMIN)
