import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from backend.config import IST
from backend.api.deps import CurrentUser, get_current_user, require_customer, check_problem_owner
from backend.db.supabase_client import db
from backend.schemas.problem import (
    ProblemCreate, ProblemRead, ProblemFingerprintRequest, ProblemFingerprintRead
)
from backend.services.ai.fingerprint import extract_problem_fingerprint
from backend.schemas.common import AppException

router = APIRouter(prefix="/problems", tags=["Problems"])

def _hydrate_problem(problem_id_str: str) -> dict:
    problem = db.problems.get(problem_id_str)
    if not problem:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Problem not found."
        )
    
    # Hydrate media
    media_list = [m for m in db.problem_media.values() if str(m.get("problem_id")) == problem_id_str]
    
    # Hydrate fingerprint
    fp = db.problem_fingerprints.get(problem_id_str)
    
    return {
        **problem,
        "media": media_list,
        "fingerprint": fp
    }

@router.post("", response_model=ProblemRead, status_code=status.HTTP_201_CREATED)
def create_problem(payload: ProblemCreate, current_user: CurrentUser = Depends(require_customer)):
    """
    Creates customer problem. The authenticated customer identity comes strictly from JWT.
    Stores media in problem_media.
    """
    problem_id = str(uuid.uuid4())
    now = datetime.now(IST)
    
    new_problem = {
        "id": problem_id,
        "customer_id": str(current_user.id),
        "title": payload.title,
        "description": payload.description,
        "address_line": payload.address_line,
        "locality": payload.locality,
        "city": payload.city,
        "state": payload.state,
        "postal_code": payload.postal_code,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "status": "open",
        "created_at": now,
        "updated_at": now
    }
    db.problems[problem_id] = new_problem
    db.sync_to_supabase("problems", new_problem)

    # Record media in problem_media table
    for path in (payload.media_paths or []):
        media_id = str(uuid.uuid4())
        media_rec = {
            "id": media_id,
            "problem_id": problem_id,
            "storage_path": path,
            "media_type": "image",
            "file_size_bytes": None,
            "created_at": now
        }
        db.problem_media[media_id] = media_rec
        db.sync_to_supabase("problem_media", media_rec)

    return _hydrate_problem(problem_id)

@router.get("", response_model=List[ProblemRead])
def list_problems(current_user: CurrentUser = Depends(get_current_user)):
    user_id_str = str(current_user.id)
    if current_user.role == "admin":
        probs = list(db.problems.values())
    else:
        probs = [p for p in db.problems.values() if str(p.get("customer_id")) == user_id_str]
        
    probs.sort(key=lambda x: x.get("created_at"), reverse=True)
    return [_hydrate_problem(str(p["id"])) for p in probs]

@router.get("/{problem_id}", response_model=ProblemRead)
def get_problem(problem_id: uuid.UUID, current_user: CurrentUser = Depends(get_current_user)):
    return _hydrate_problem(str(problem_id))

@router.post("/{problem_id}/fingerprint", response_model=ProblemFingerprintRead)
def generate_problem_fingerprint(
    problem_id: uuid.UUID,
    payload: ProblemFingerprintRequest,
    current_user: CurrentUser = Depends(require_customer)
):
    """
    Generates or retrieves problem fingerprint.
    Extracts device specs, symptoms, hypothetical suspected component, and required skills.
    """
    prob_str = str(problem_id)
    problem = check_problem_owner(prob_str, current_user)
    
    existing_fp = db.problem_fingerprints.get(prob_str)
    if existing_fp and not payload.regenerate:
        return existing_fp
        
    now = datetime.now(IST)
    extracted = extract_problem_fingerprint(problem["title"], problem["description"])
    
    fp_id = existing_fp["id"] if existing_fp else str(uuid.uuid4())
    version = (existing_fp.get("fingerprint_version", 1) + 1) if existing_fp else 1
    
    fp_record = {
        "id": fp_id,
        "problem_id": prob_str,
        **extracted,
        "fingerprint_version": version,
        "created_at": existing_fp["created_at"] if existing_fp else now,
        "updated_at": now
    }
    db.problem_fingerprints[prob_str] = fp_record
    db.sync_to_supabase("problem_fingerprints", fp_record)
    return fp_record
