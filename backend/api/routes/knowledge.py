"""/knowledge-cases — the Knowledge Hub.

Reuses the same embedding model and retrieval path as matching, which is the point:
one semantic foundation, two products.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from backend.api.deps import CurrentUser, get_current_user, require_worker
from backend.core.errors import forbidden, not_found
from backend.db.supabase import one_or_none, rows, table
from backend.schemas.common import clean
from backend.schemas.models import (
    KnowledgeCaseIn,
    KnowledgeCaseOut,
    KnowledgeCaseUpdate,
    SimilarKnowledgeCase,
)
from backend.services.ai import embeddings, indexing
from backend.services.jobs import lifecycle
from backend.services.matching import retrieval

log = logging.getLogger(__name__)
router = APIRouter(tags=["knowledge"])


def _to_out(row: dict[str, Any], media: list[dict[str, Any]] | None = None) -> KnowledgeCaseOut:
    return KnowledgeCaseOut(
        id=str(row["id"]),
        worker_id=str(row["worker_id"]),
        experience_id=str(row["experience_id"]) if row.get("experience_id") else None,
        title=row.get("title") or "",
        problem_summary=row.get("problem_summary"),
        diagnosis_summary=row.get("diagnosis_summary"),
        solution_summary=row.get("solution_summary"),
        lesson_learned=row.get("lesson_learned"),
        difficulty_level=row.get("difficulty_level") or "intermediate",
        visibility_status=row.get("visibility_status") or "draft",
        is_verified=bool(row.get("is_verified")),
        published_at=row.get("published_at"),
        media=[{**m, "id": str(m["id"])} for m in (media or [])],
    )


@router.post("/knowledge-cases", response_model=KnowledgeCaseOut, status_code=201)
def create_knowledge_case(
    payload: KnowledgeCaseIn,
    user: CurrentUser = Depends(require_worker),
) -> KnowledgeCaseOut:
    row = clean(payload.model_dump(exclude_unset=True))
    row["worker_id"] = user.id

    if payload.experience_id:
        experience = one_or_none(
            table("experiences")
            .select("worker_id, experience_status")
            .eq("id", payload.experience_id)
            .limit(1)
            .execute()
        )
        if experience is None:
            raise not_found("Experience")
        if not user.owns(str(experience["worker_id"])):
            raise forbidden("You can only publish cases from your own experience.")
        # A case inherits verification from the experience behind it, never from the author.
        row["is_verified"] = experience.get("experience_status") == "verified"
    else:
        row["is_verified"] = False

    if payload.visibility_status == "published":
        row["published_at"] = lifecycle.iso()

    created = rows(table("knowledge_cases").insert(row).execute())[0]
    indexing.index_knowledge_case(str(created["id"]))
    return _to_out(created)


@router.get("/knowledge-cases/similar", response_model=list[SimilarKnowledgeCase])
def similar_knowledge_cases(
    q: str = Query(min_length=3, max_length=1000),
    limit: int = Query(default=5, ge=1, le=20),
    user: CurrentUser = Depends(get_current_user),
) -> list[SimilarKnowledgeCase]:
    """Semantic Knowledge Hub search. Declared before /{case_id} so the path is not
    swallowed as an id."""
    vector = embeddings.embed_query(q)
    return [
        SimilarKnowledgeCase(**item) for item in retrieval.search_knowledge_cases(vector, limit)
    ]


@router.get("/knowledge-cases", response_model=list[KnowledgeCaseOut])
def list_knowledge_cases(
    mine: bool = Query(default=False, description="Only the caller's own cases"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
) -> list[KnowledgeCaseOut]:
    builder = table("knowledge_cases").select("*")
    if mine:
        builder = builder.eq("worker_id", user.id)
    else:
        builder = builder.eq("visibility_status", "published")
    result = rows(
        builder.order("published_at", desc=True).range(offset, offset + limit - 1).execute()
    )
    return [_to_out(r) for r in result]


@router.get("/knowledge-cases/{case_id}", response_model=KnowledgeCaseOut)
def get_knowledge_case(
    case_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> KnowledgeCaseOut:
    row = one_or_none(table("knowledge_cases").select("*").eq("id", case_id).limit(1).execute())
    if row is None:
        raise not_found("Knowledge case")
    if row.get("visibility_status") != "published":
        if not user.owns(str(row["worker_id"])) and not user.is_admin:
            raise not_found("Knowledge case")

    media = rows(
        table("knowledge_case_media").select("*").eq("knowledge_case_id", case_id).execute()
    )
    return _to_out(row, media)


@router.patch("/knowledge-cases/{case_id}", response_model=KnowledgeCaseOut)
def update_knowledge_case(
    case_id: str,
    payload: KnowledgeCaseUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> KnowledgeCaseOut:
    row = one_or_none(table("knowledge_cases").select("*").eq("id", case_id).limit(1).execute())
    if row is None:
        raise not_found("Knowledge case")
    if not user.owns(str(row["worker_id"])) and not user.is_admin:
        raise forbidden("This case belongs to another worker.")

    updates = clean(payload.model_dump(exclude_unset=True))
    if payload.visibility_status == "published" and not row.get("published_at"):
        updates["published_at"] = lifecycle.iso()

    if updates:
        row = rows(table("knowledge_cases").update(updates).eq("id", case_id).execute())[0]
        # Content changes make the stored vector stale.
        indexing.index_knowledge_case(case_id)
    return _to_out(row)
