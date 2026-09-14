"""/workers — worker profiles, declared skills, certificates and experience summaries."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.api.deps import CurrentUser, get_current_user, require_worker
from backend.core.errors import APIError, CONFLICT, not_found
from backend.db.supabase import one_or_none, rows, table
from backend.schemas.common import clean
from backend.schemas.models import (
    CertificateIn,
    CertificateOut,
    SkillOut,
    WorkerOut,
    WorkerSkillsReplace,
    WorkerUpdate,
)

router = APIRouter(tags=["workers"])

# Fields safe to show to any authenticated user. Street address is deliberately absent:
# exact location is only disclosed later in the workflow.
_PUBLIC_WORKER_FIELDS = (
    "user_id, professional_title, bio, years_experience, service_radius_km, "
    "locality, city, state, latitude, longitude, availability_status, is_verified"
)


def _load_skills(worker_id: str) -> list[SkillOut]:
    links = rows(
        table("worker_skills")
        .select("skill_id, proficiency_level, is_primary, skills(id, name, category)")
        .eq("worker_id", worker_id)
        .execute()
    )
    out = []
    for link in links:
        skill = link.get("skills") or {}
        if not skill.get("id"):
            continue
        out.append(
            SkillOut(
                id=str(skill["id"]),
                name=skill.get("name") or "",
                category=skill.get("category"),
                proficiency_level=link.get("proficiency_level"),
                is_primary=link.get("is_primary"),
            )
        )
    return out


def _to_out(row: dict) -> WorkerOut:
    return WorkerOut(
        user_id=str(row["user_id"]),
        professional_title=row.get("professional_title") or "",
        bio=row.get("bio"),
        years_experience=int(row.get("years_experience") or 0),
        service_radius_km=float(row.get("service_radius_km") or 10),
        locality=row.get("locality"),
        city=row.get("city"),
        state=row.get("state"),
        latitude=float(row["latitude"]) if row.get("latitude") is not None else None,
        longitude=float(row["longitude"]) if row.get("longitude") is not None else None,
        availability_status=row.get("availability_status") or "available",
        is_verified=bool(row.get("is_verified")),
        skills=_load_skills(str(row["user_id"])),
    )


@router.get("/workers/{worker_id}", response_model=WorkerOut)
def get_worker(worker_id: str, user: CurrentUser = Depends(get_current_user)) -> WorkerOut:
    row = one_or_none(
        table("worker_profiles")
        .select(_PUBLIC_WORKER_FIELDS)
        .eq("user_id", worker_id)
        .limit(1)
        .execute()
    )
    if row is None:
        raise not_found("Worker")
    return _to_out(row)


@router.patch("/workers/me", response_model=WorkerOut)
def update_my_worker_profile(
    payload: WorkerUpdate,
    user: CurrentUser = Depends(require_worker),
) -> WorkerOut:
    updates = clean(payload.model_dump(exclude_unset=True))
    existing = one_or_none(
        table("worker_profiles").select("user_id").eq("user_id", user.id).limit(1).execute()
    )

    if existing is None:
        # First save creates the row; professional_title is NOT NULL in the schema.
        updates.setdefault("professional_title", user.display_name or "Technician")
        updates["user_id"] = user.id
        created = rows(table("worker_profiles").insert(updates).execute())
        return _to_out(created[0])

    if not updates:
        row = one_or_none(
            table("worker_profiles").select("*").eq("user_id", user.id).limit(1).execute()
        )
        return _to_out(row or {"user_id": user.id})

    updated = rows(table("worker_profiles").update(updates).eq("user_id", user.id).execute())
    return _to_out(updated[0])


@router.put("/workers/me/skills", response_model=list[SkillOut])
def replace_my_skills(
    payload: WorkerSkillsReplace,
    user: CurrentUser = Depends(require_worker),
) -> list[SkillOut]:
    """Replace the worker's declared skills.

    A declared skill is a claim, not verified experience — matching treats it as such.
    """
    skill_ids = [s.skill_id for s in payload.skills]
    if skill_ids:
        known = {
            str(r["id"])
            for r in rows(table("skills").select("id").in_("id", skill_ids).execute())
        }
        unknown = [s for s in skill_ids if s not in known]
        if unknown:
            raise APIError(CONFLICT, "Unknown skill ids.", {"skill_ids": unknown})
        if len(set(skill_ids)) != len(skill_ids):
            raise APIError(CONFLICT, "The same skill was listed more than once.")

    table("worker_skills").delete().eq("worker_id", user.id).execute()
    if payload.skills:
        table("worker_skills").insert(
            [
                {
                    "worker_id": user.id,
                    "skill_id": s.skill_id,
                    "proficiency_level": s.proficiency_level,
                    "years_experience": s.years_experience,
                    "is_primary": s.is_primary,
                }
                for s in payload.skills
            ]
        ).execute()
    return _load_skills(user.id)


@router.get("/skills", response_model=list[SkillOut])
def list_skills(
    q: str | None = Query(default=None, description="Filter by name"),
    user: CurrentUser = Depends(get_current_user),
) -> list[SkillOut]:
    """Canonical skill list, needed by any client that lets a worker pick skills."""
    builder = table("skills").select("id, name, category").eq("is_active", True)
    if q:
        builder = builder.ilike("name", f"%{q}%")
    return [
        SkillOut(id=str(r["id"]), name=r.get("name") or "", category=r.get("category"))
        for r in rows(builder.order("name").limit(200).execute())
    ]


@router.post("/workers/me/certificates", response_model=CertificateOut, status_code=201)
def add_certificate(
    payload: CertificateIn,
    user: CurrentUser = Depends(require_worker),
) -> CertificateOut:
    """Record certificate metadata after the file itself was uploaded to Storage."""
    row = payload.model_dump(exclude_unset=True)
    for key in ("issue_date", "expiry_date"):
        if row.get(key) is not None:
            row[key] = row[key].isoformat()
    row["worker_id"] = user.id
    # Claimed qualifications start unverified; nothing here may set them otherwise.
    row["verification_status"] = "pending"
    created = rows(table("certificates").insert(row).execute())[0]
    return CertificateOut(**{**created, "id": str(created["id"])})


@router.get("/workers/{worker_id}/experiences")
def worker_experiences(
    worker_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Experience summaries for a worker, used to justify a match."""
    items = rows(
        table("experiences")
        .select("id, title, experience_status, verification_confidence, diagnosis, outcome_summary")
        .eq("worker_id", worker_id)
        .neq("experience_status", "archived")
        .order("verification_confidence", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return {
        "items": [{**i, "id": str(i["id"])} for i in items],
        "total": len(items),
    }
 