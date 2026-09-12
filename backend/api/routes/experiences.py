"""/experiences — worker-recorded solved cases and semantic search over them."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from backend.api.deps import CurrentUser, get_current_user, require_worker
from backend.core.errors import forbidden, not_found
from backend.db.supabase import one_or_none, rows, table
from backend.schemas.common import clean
from backend.schemas.models import (
    ExperienceIn,
    ExperienceOut,
    ExperienceUpdate,
    SimilarExperience,
)
from backend.services.ai import embeddings, indexing
from backend.services.matching import retrieval

log = logging.getLogger(__name__)
router = APIRouter(tags=["experiences"])


def write_experience_children(
    experience_id: str,
    contexts: list[Any],
    actions: list[Any],
    outcomes: list[Any],
    skill_ids: list[str],
) -> None:
    """Insert the normalised child rows for an experience."""
    if contexts:
        table("experience_contexts").insert(
            [{**c.model_dump(exclude_unset=True), "experience_id": experience_id} for c in contexts]
        ).execute()
    if actions:
        table("experience_actions").insert(
            [{**a.model_dump(exclude_unset=True), "experience_id": experience_id} for a in actions]
        ).execute()
    if outcomes:
        table("experience_outcomes").insert(
            [
                {
                    **o.model_dump(exclude_unset=True),
                    "experience_id": experience_id,
                    # Only a customer verification may set this; never the author.
                    "customer_confirmed": False,
                }
                for o in outcomes
            ]
        ).execute()
    if skill_ids:
        known = {
            str(r["id"])
            for r in rows(table("skills").select("id").in_("id", list(set(skill_ids))).execute())
        }
        if known:
            table("experience_skills").insert(
                [{"experience_id": experience_id, "skill_id": s} for s in known]
            ).execute()


def load_experience_detail(experience_id: str) -> ExperienceOut:
    experience = one_or_none(
        table("experiences").select("*").eq("id", experience_id).limit(1).execute()
    )
    if experience is None:
        raise not_found("Experience")

    contexts = rows(
        table("experience_contexts").select("*").eq("experience_id", experience_id).execute()
    )
    actions = rows(
        table("experience_actions")
        .select("*")
        .eq("experience_id", experience_id)
        .order("step_number")
        .execute()
    )
    outcomes = rows(
        table("experience_outcomes").select("*").eq("experience_id", experience_id).execute()
    )
    media = rows(
        table("experience_media").select("*").eq("experience_id", experience_id).execute()
    )
    skill_links = rows(
        table("experience_skills")
        .select("skills(name)")
        .eq("experience_id", experience_id)
        .execute()
    )

    return ExperienceOut(
        id=str(experience["id"]),
        worker_id=str(experience["worker_id"]),
        title=experience.get("title") or "",
        problem_description=experience.get("problem_description"),
        diagnosis=experience.get("diagnosis"),
        outcome_summary=experience.get("outcome_summary"),
        experience_status=experience.get("experience_status") or "draft",
        verification_confidence=float(experience.get("verification_confidence") or 0),
        contexts=[{**c, "id": str(c["id"])} for c in contexts],
        actions=[{**a, "id": str(a["id"])} for a in actions],
        outcomes=[{**o, "id": str(o["id"])} for o in outcomes],
        media=[{**m, "id": str(m["id"])} for m in media],
        skills=[(s.get("skills") or {}).get("name") for s in skill_links if s.get("skills")],
    )


@router.post("/experiences", response_model=ExperienceOut, status_code=201)
def create_experience(
    payload: ExperienceIn,
    user: CurrentUser = Depends(require_worker),
) -> ExperienceOut:
    """Record a historical solved case.

    Self-reported history is stored with zero verification confidence. Only a customer
    verification on a real job can raise it (PRD section 15).
    """
    row = clean(
        payload.model_dump(exclude_unset=True, exclude={"contexts", "actions", "outcomes", "skill_ids"})
    )
    row["worker_id"] = user.id
    row["verification_confidence"] = 0
    created = rows(table("experiences").insert(row).execute())[0]

    write_experience_children(
        str(created["id"]), payload.contexts, payload.actions, payload.outcomes, payload.skill_ids
    )
    indexing.index_experience(str(created["id"]))
    return load_experience_detail(str(created["id"]))


@router.get("/experiences/similar", response_model=list[SimilarExperience])
def similar_experiences(
    q: str = Query(min_length=3, max_length=1000),
    limit: int = Query(default=5, ge=1, le=20),
    user: CurrentUser = Depends(get_current_user),
) -> list[SimilarExperience]:
    """Semantic search over solved experiences.

    Declared before the /{experience_id} route so the literal path is not captured
    as an id.
    """
    vector = embeddings.embed_query(q)
    return [SimilarExperience(**item) for item in retrieval.search_similar_experiences(vector, limit)]


@router.get("/experiences/{experience_id}", response_model=ExperienceOut)
def get_experience(
    experience_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> ExperienceOut:
    return load_experience_detail(experience_id)


@router.patch("/experiences/{experience_id}", response_model=ExperienceOut)
def update_experience(
    experience_id: str,
    payload: ExperienceUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> ExperienceOut:
    experience = one_or_none(
        table("experiences").select("*").eq("id", experience_id).limit(1).execute()
    )
    if experience is None:
        raise not_found("Experience")
    if not user.is_admin and not user.owns(str(experience["worker_id"])):
        raise forbidden("This experience belongs to another worker.")

    updates = clean(payload.model_dump(exclude_unset=True))
    if updates:
        table("experiences").update(updates).eq("id", experience_id).execute()
        # Searchable content may have changed, so the vector must be rebuilt.
        indexing.index_experience(experience_id)
    return load_experience_detail(experience_id)
