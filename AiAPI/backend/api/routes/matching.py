"""/problems/{id}/matches — the ranked Top-K workers."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from backend.api.deps import CurrentUser, get_current_user
from backend.api.routes.problems import assert_problem_access, load_problem
from backend.core.errors import APIError, CONFLICT
from backend.db.supabase import one_or_none, rows, table
from backend.schemas.models import MatchesOut
from backend.services.ai import fingerprint as fp_service
from backend.services.matching import pipeline

log = logging.getLogger(__name__)
router = APIRouter(tags=["matching"])


@router.get("/problems/{problem_id}/matches", response_model=MatchesOut)
def get_matches(
    problem_id: str,
    limit: int = Query(default=5, ge=1, le=20),
    user: CurrentUser = Depends(get_current_user),
) -> MatchesOut:
    problem = load_problem(problem_id)
    assert_problem_access(problem, user)

    fingerprint_row = one_or_none(
        table("problem_fingerprints").select("*").eq("problem_id", problem_id).limit(1).execute()
    )
    if fingerprint_row is None:
        raise APIError(
            CONFLICT,
            "Generate a Problem Fingerprint before requesting matches.",
            {"next": f"POST /problems/{problem_id}/fingerprint"},
        )

    fingerprint = fp_service.from_row(fingerprint_row)
    result = pipeline.run_matching(problem, fingerprint, limit=limit)

    # The embedding is built from the confirmed fingerprint, so a successful match run
    # is the point at which it is known to be current.
    if fingerprint_row.get("embedding_status") != "generated":
        table("problem_fingerprints").update({"embedding_status": "generated"}).eq(
            "problem_id", problem_id
        ).execute()

    if result["items"] and problem.get("status") == "open":
        table("problems").update({"status": "matched"}).eq("id", problem_id).execute()

    return MatchesOut(**result)


@router.get("/problems/{problem_id}/matches/stored", response_model=MatchesOut)
def get_stored_matches(
    problem_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> MatchesOut:
    """Re-read the last ranking without re-running the AI pipeline.

    Useful for a client returning to a results screen, and for demoing the exact
    ranking a service request was created from.
    """
    problem = load_problem(problem_id)
    assert_problem_access(problem, user)

    stored = rows(
        table("match_results")
        .select("*")
        .eq("problem_id", problem_id)
        .order("rank_position")
        .execute()
    )
    return MatchesOut(
        problem_id=str(problem_id),
        items=[
            {
                "match_result_id": str(r["id"]),
                "worker_id": str(r["worker_id"]),
                "rank_position": r["rank_position"],
                "match_score": float(r["match_score"]),
                "problem_similarity": float(r["problem_similarity"]),
                "context_similarity": float(r["context_similarity"]),
                "verified_experience_confidence": float(r["verified_experience_confidence"]),
                "proximity_score": float(r["proximity_score"]),
                "explanation": r.get("explanation") or [],
                "distance_km": (r.get("matching_metadata") or {}).get("distance_km"),
                "within_service_radius": (r.get("matching_metadata") or {}).get(
                    "within_service_radius", True
                ),
            }
            for r in stored
        ],
        candidate_pool_size=len(stored),
    )
