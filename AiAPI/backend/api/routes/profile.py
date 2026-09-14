"""/me — the caller's own profile."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.deps import CurrentUser, get_current_user
from backend.db.supabase import one_or_none, rows, table
from backend.schemas.common import clean
from backend.schemas.models import ProfileOut, ProfileUpdate

router = APIRouter(tags=["profile"])


def _to_out(row: dict) -> ProfileOut:
    return ProfileOut(
        id=str(row["id"]),
        role=row.get("role") or "customer",
        display_name=row.get("display_name") or "",
        phone=row.get("phone"),
        avatar_url=row.get("avatar_url"),
        is_active=bool(row.get("is_active", True)),
    )


@router.get("/me", response_model=ProfileOut)
def get_me(user: CurrentUser = Depends(get_current_user)) -> ProfileOut:
    row = one_or_none(table("profiles").select("*").eq("id", user.id).limit(1).execute())
    return _to_out(row or {"id": user.id, "role": user.role, "display_name": user.display_name})


@router.patch("/me", response_model=ProfileOut)
def update_me(
    payload: ProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> ProfileOut:
    # role and is_active are deliberately absent: a user cannot promote themselves.
    updates = clean(payload.model_dump(exclude_unset=True))
    if not updates:
        row = one_or_none(table("profiles").select("*").eq("id", user.id).limit(1).execute())
        return _to_out(row or {})
    updated = rows(table("profiles").update(updates).eq("id", user.id).execute())
    return _to_out(updated[0])
