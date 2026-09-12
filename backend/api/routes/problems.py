"""/problems — customer problems, media metadata and Problem Fingerprint generation."""
from __future__ import annotations

import base64
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query

from backend.api.deps import CurrentUser, get_current_user, require_customer
from backend.core.config import settings
from backend.core.errors import APIError, CONFLICT, forbidden, not_found
from backend.db.supabase import one_or_none, rows, table
from backend.schemas.common import clean
from backend.schemas.models import (
    FingerprintConfirm,
    FingerprintOut,
    FingerprintRequest,
    ProblemIn,
    ProblemMediaIn,
    ProblemOut,
)
from backend.services.ai import fingerprint as fp_service

log = logging.getLogger(__name__)
router = APIRouter(tags=["problems"])

# A problem may not be re-edited once work is under way.
_EDITABLE_STATUSES = {"open", "matched", "requested"}
_MAX_IMAGE_BYTES = 8 * 1024 * 1024


def load_problem(problem_id: str) -> dict[str, Any]:
    problem = one_or_none(
        table("problems").select("*").eq("id", problem_id).limit(1).execute()
    )
    if problem is None:
        raise not_found("Problem")
    return problem


def assert_problem_access(problem: dict[str, Any], user: CurrentUser) -> None:
    if user.is_admin or user.owns(str(problem["customer_id"])):
        return
    raise forbidden("This problem belongs to another customer.")


def _fingerprint_out(row: dict[str, Any]) -> FingerprintOut:
    context = row.get("context") or {}
    if isinstance(context, list):
        context = {"items": context}
    return FingerprintOut(
        id=str(row["id"]) if row.get("id") else None,
        problem_id=str(row["problem_id"]),
        device_type=row.get("device_type"),
        brand=row.get("brand"),
        model=row.get("model"),
        category=row.get("category"),
        issue=row.get("issue"),
        symptoms=list(row.get("symptoms") or []),
        context=context,
        suspected_component=row.get("suspected_component"),
        suspected_component_source=context.get("suspected_component_source"),
        repair_type=row.get("repair_type"),
        urgency=context.get("urgency"),
        extracted_skills=list(row.get("extracted_skills") or []),
        ai_summary=row.get("ai_summary") or "",
        embedding_status=row.get("embedding_status") or "pending",
        fingerprint_version=row.get("fingerprint_version") or "v1",
        safety_warning=context.get("safety_warning"),
    )


@router.post("/problems", response_model=ProblemOut, status_code=201)
def create_problem(
    payload: ProblemIn,
    user: CurrentUser = Depends(require_customer),
) -> ProblemOut:
    row = clean(payload.model_dump(exclude_unset=True))
    # customer_id comes from the token, never the request body.
    row["customer_id"] = user.id
    row["status"] = "open"
    created = rows(table("problems").insert(row).execute())[0]
    return ProblemOut(**{**created, "id": str(created["id"]),
                         "customer_id": str(created["customer_id"])})


@router.get("/problems", response_model=list[ProblemOut])
def list_my_problems(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
) -> list[ProblemOut]:
    result = rows(
        table("problems")
        .select("*")
        .eq("customer_id", user.id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return [
        ProblemOut(**{**r, "id": str(r["id"]), "customer_id": str(r["customer_id"])})
        for r in result
    ]


@router.get("/problems/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: str, user: CurrentUser = Depends(get_current_user)) -> ProblemOut:
    problem = load_problem(problem_id)
    assert_problem_access(problem, user)

    media = rows(table("problem_media").select("*").eq("problem_id", problem_id).execute())
    fingerprint = one_or_none(
        table("problem_fingerprints").select("*").eq("problem_id", problem_id).limit(1).execute()
    )
    return ProblemOut(
        **{
            **problem,
            "id": str(problem["id"]),
            "customer_id": str(problem["customer_id"]),
            "media": [{**m, "id": str(m["id"])} for m in media],
            "fingerprint": _fingerprint_out(fingerprint).model_dump() if fingerprint else None,
        }
    )


@router.patch("/problems/{problem_id}", response_model=ProblemOut)
def update_problem(
    problem_id: str,
    payload: ProblemIn,
    user: CurrentUser = Depends(get_current_user),
) -> ProblemOut:
    problem = load_problem(problem_id)
    assert_problem_access(problem, user)
    if problem.get("status") not in _EDITABLE_STATUSES:
        raise APIError(
            CONFLICT,
            "This problem can no longer be edited because work has started.",
            {"status": problem.get("status")},
        )

    updates = clean(payload.model_dump(exclude_unset=True))
    if not updates:
        return get_problem(problem_id, user)
    updated = rows(table("problems").update(updates).eq("id", problem_id).execute())[0]
    return ProblemOut(**{**updated, "id": str(updated["id"]),
                         "customer_id": str(updated["customer_id"])})


@router.post("/problems/{problem_id}/media", status_code=201)
def add_problem_media(
    problem_id: str,
    payload: ProblemMediaIn,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Register a file already uploaded to the problem-media bucket."""
    problem = load_problem(problem_id)
    assert_problem_access(problem, user)

    # media_type defaults here and backs a NOT NULL column, so unset fields are kept.
    row = clean(payload.model_dump())
    row["problem_id"] = problem_id
    created = rows(table("problem_media").insert(row).execute())[0]
    return {**created, "id": str(created["id"])}


def _download_images(media: list[dict[str, Any]]) -> list[tuple[bytes, str]]:
    """Fetch problem images so the fingerprint model can actually see them.

    Buckets are public in the prototype, so a plain GET is enough. Failures are skipped:
    a missing image degrades the fingerprint to text-only rather than failing the call.
    """
    images: list[tuple[bytes, str]] = []
    base = settings.supabase_url.rstrip("/")
    bucket = settings.storage_problem_bucket

    for item in media:
        if item.get("media_type") != "image":
            continue
        path = str(item.get("storage_path") or "").lstrip("/")
        if not path:
            continue
        if path.startswith(f"{bucket}/"):
            path = path[len(bucket) + 1 :]
        url = f"{base}/storage/v1/object/public/{bucket}/{path}"
        try:
            response = httpx.get(url, timeout=15, follow_redirects=True)
            response.raise_for_status()
            data = response.content
            if len(data) > _MAX_IMAGE_BYTES:
                log.info("Skipping oversized problem image %s", path)
                continue
            mime = item.get("mime_type") or response.headers.get("content-type") or "image/jpeg"
            images.append((data, mime.split(";")[0].strip()))
        except Exception:
            log.warning("Could not fetch problem image %s; continuing text-only", path)
    return images[:4]


@router.post("/problems/{problem_id}/fingerprint", response_model=FingerprintOut)
def generate_fingerprint(
    problem_id: str,
    payload: FingerprintRequest | None = None,
    user: CurrentUser = Depends(get_current_user),
) -> FingerprintOut:
    """Generate or refresh the multimodal Problem Fingerprint."""
    problem = load_problem(problem_id)
    assert_problem_access(problem, user)
    payload = payload or FingerprintRequest()

    existing = one_or_none(
        table("problem_fingerprints").select("*").eq("problem_id", problem_id).limit(1).execute()
    )
    if existing and not payload.regenerate:
        return _fingerprint_out(existing)

    media = rows(
        table("problem_media")
        .select("storage_path, media_type, mime_type")
        .eq("problem_id", problem_id)
        .execute()
    )
    result = fp_service.generate_fingerprint(
        title=problem.get("title") or "",
        description=problem.get("description") or "",
        images=_download_images(media),
    )

    row = result.to_row(problem_id)
    row["embedding_status"] = "pending"
    saved = rows(
        table("problem_fingerprints").upsert(row, on_conflict="problem_id").execute()
    )[0]
    return _fingerprint_out(saved)


@router.patch("/problems/{problem_id}/fingerprint", response_model=FingerprintOut)
def confirm_fingerprint(
    problem_id: str,
    payload: FingerprintConfirm,
    user: CurrentUser = Depends(get_current_user),
) -> FingerprintOut:
    """Apply the customer's corrections to the extracted fingerprint.

    A corrected field is customer-stated, which is stronger evidence than anything the
    model inferred — so correcting the component also upgrades its provenance marker.
    """
    problem = load_problem(problem_id)
    assert_problem_access(problem, user)

    existing = one_or_none(
        table("problem_fingerprints").select("*").eq("problem_id", problem_id).limit(1).execute()
    )
    if existing is None:
        raise not_found("Fingerprint")

    updates = payload.model_dump(exclude_unset=True)
    context = existing.get("context") or {}
    if isinstance(context, list):
        context = {"items": context}

    if "context" in updates:
        context["items"] = updates.pop("context") or []
    if "urgency" in updates:
        context["urgency"] = updates.pop("urgency")
    if "suspected_component" in updates:
        context["suspected_component_source"] = (
            fp_service.STATED if updates["suspected_component"] else None
        )

    row = {k: v for k, v in updates.items() if v is not None or k == "suspected_component"}
    row["context"] = context
    # The searchable content changed, so any embedding built from it is now stale.
    row["embedding_status"] = "pending"

    saved = rows(
        table("problem_fingerprints").update(row).eq("problem_id", problem_id).execute()
    )[0]
    return _fingerprint_out(saved)
