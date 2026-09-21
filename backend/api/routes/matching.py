import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from backend.api.deps import CurrentUser, get_current_user, check_problem_owner
from backend.schemas.matching import MatchResponse
# AI engine: pgvector semantic retrieval, falling back to the skill-overlap
# matcher in backend/services/matching/matcher.py when unconfigured or on failure.
from backend.services.ai_engine.adapters import compute_matches_for_problem
from backend.schemas.common import AppException

router = APIRouter(prefix="/problems", tags=["Matching"])

@router.get("/{problem_id}/matches", response_model=MatchResponse)
def get_problem_matches(
    problem_id: uuid.UUID,
    limit: int = Query(5, ge=1, le=20),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Retrieves Top-K matched technicians for a problem.
    Validates ownership or access permission.
    """
    prob_str = str(problem_id)
    # Check problem ownership or allow worker viewing if authorized
    check_problem_owner(prob_str, current_user)
    
    matches = compute_matches_for_problem(prob_str, limit=limit)
    return MatchResponse(
        problem_id=problem_id,
        total_matches=len(matches),
        matches=matches
    )
