import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from backend.config import IST
from backend.api.deps import CurrentUser, get_current_user, require_worker
from backend.db.supabase_client import db
from backend.schemas.knowledge import (
    KnowledgeCaseCreate, KnowledgeCaseUpdate, KnowledgeCaseRead
)
from backend.schemas.common import AppException

router = APIRouter(prefix="/knowledge-cases", tags=["Knowledge Hub"])

def _hydrate_case(case_id_str: str) -> dict:
    kc = db.knowledge_cases.get(case_id_str)
    if not kc:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Knowledge case not found."
        )
    
    worker = db.worker_profiles.get(str(kc.get("worker_id")), {})
    worker_user = db.profiles.get(str(worker.get("user_id")), {})
    
    media = [m for m in db.knowledge_case_media.values() if str(m.get("knowledge_case_id")) == case_id_str]
    
    return {
        **kc,
        "diagnosis": kc.get("diagnosis") or kc.get("diagnosis_summary") or "",
        "solution": kc.get("solution") or kc.get("solution_summary") or "",
        "difficulty": kc.get("difficulty") or kc.get("difficulty_level") or "intermediate",
        "is_published": kc.get("is_published", True) if "is_published" in kc else (kc.get("visibility_status") == "published"),
        "worker_name": worker_user.get("full_name") or worker_user.get("display_name") or "Specialist Technician",
        "media": media
    }

@router.get("/similar", response_model=List[KnowledgeCaseRead])
def search_similar_cases(
    q: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=20),
    current_user: CurrentUser = Depends(require_worker)
):
    """
    Worker-facing Knowledge Hub semantic search (Technicians only).
    Searches across published cases matching symptoms, device type, brand, diagnosis, and solutions.
    """
    terms = q.lower().split()
    matched = []

    for c_id, c in db.knowledge_cases.items():
        if not c.get("is_published", True):
            continue
            
        text = f"{c.get('title', '')} {c.get('problem_summary', '')} {c.get('diagnosis', '')} {c.get('solution', '')} {c.get('brand', '')} {c.get('model', '')} {c.get('device_category', '')}".lower()
        score = sum(1 for t in terms if t in text)
        if score > 0 or len(terms) == 0:
            matched.append((score, c_id))

    # Sort descending by match relevance
    matched.sort(key=lambda x: x[0], reverse=True)
    
    # If generic search or empty match, return top published cases
    if not matched:
        results = [c_id for c_id, c in db.knowledge_cases.items() if c.get("is_published", True)][:limit]
    else:
        results = [item[1] for item in matched[:limit]]

    return [_hydrate_case(cid) for cid in results]

@router.get("/{case_id}", response_model=KnowledgeCaseRead)
def get_knowledge_case(case_id: uuid.UUID, current_user: CurrentUser = Depends(require_worker)):
    case_id_str = str(case_id)
    case = _hydrate_case(case_id_str)
    # Increment view count
    if case_id_str in db.knowledge_cases:
        db.knowledge_cases[case_id_str]["view_count"] = db.knowledge_cases[case_id_str].get("view_count", 0) + 1
    return case

@router.post("", response_model=KnowledgeCaseRead, status_code=status.HTTP_201_CREATED)
def create_knowledge_case(payload: KnowledgeCaseCreate, current_user: CurrentUser = Depends(require_worker)):
    worker_id_str = str(current_user.worker_id)
    case_id = str(uuid.uuid4())
    now = datetime.now(IST)

    new_case = {
        "id": case_id,
        "worker_id": worker_id_str,
        "experience_id": str(payload.experience_id) if payload.experience_id else None,
        "title": payload.title,
        "problem_summary": payload.problem_summary,
        "diagnosis": payload.diagnosis,
        "solution": payload.solution,
        "lesson_learned": payload.lesson_learned,
        "difficulty": payload.difficulty,
        "device_category": payload.device_category,
        "brand": payload.brand,
        "model": payload.model,
        "is_published": True,
        "is_verified": False,
        "view_count": 0,
        "created_at": now,
        "updated_at": now
    }
    db.knowledge_cases[case_id] = new_case
    db.sync_to_supabase("knowledge_cases", new_case)

    for path in (payload.media_paths or []):
        media_id = str(uuid.uuid4())
        media_record = {
            "id": media_id,
            "knowledge_case_id": case_id,
            "storage_path": path,
            "media_type": "image",
            "caption": None,
            "created_at": now
        }
        db.knowledge_case_media[media_id] = media_record
        db.sync_to_supabase("knowledge_case_media", media_record)

    return _hydrate_case(case_id)

@router.patch("/{case_id}", response_model=KnowledgeCaseRead)
def update_knowledge_case(
    case_id: uuid.UUID,
    payload: KnowledgeCaseUpdate,
    current_user: CurrentUser = Depends(require_worker)
):
    case_id_str = str(case_id)
    case = db.knowledge_cases.get(case_id_str)
    if not case:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Knowledge case not found."
        )

    if current_user.role != "admin" and str(case.get("worker_id")) != str(current_user.worker_id):
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message="Only the authoring technician can modify this knowledge case."
        )

    update_data = payload.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if val is not None:
            case[key] = val
    case["updated_at"] = datetime.now(IST)
    db.sync_to_supabase("knowledge_cases", case)

    return _hydrate_case(case_id_str)
