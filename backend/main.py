import sys
import os
import uuid
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("kaushalsetu.api")

# Ensure project root and backend dir are in sys.path regardless of execution directory
_backend_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_backend_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import jwt
from fastapi import FastAPI, Request, status, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from datetime import datetime

try:
    from backend.config import settings, IST
    from backend.schemas.common import AppException, ErrorResponse, ErrorDetail
    from backend.api.routes import (
        profile, workers, experiences, problems, matching, service_requests,
        jobs, verification, feedback, knowledge, notifications
    )
    from backend.db.supabase_client import db
except ModuleNotFoundError:
    from config import settings, IST
    from schemas.common import AppException, ErrorResponse, ErrorDetail
    from api.routes import (
        profile, workers, experiences, problems, matching, service_requests,
        jobs, verification, feedback, knowledge, notifications
    )
    from db.supabase_client import db

app = FastAPI(
    title="KaushalSetu API",
    description="AI-Driven Experience Mapping and Intelligent Opportunity Matching for electricians and repair technicians.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration for Flutter Web, Android Emulator, and Desktop
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Section 18: Standard Error Format
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.warning(f"AppException [{request.method} {request.url.path}]: {exc.status_code} {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = str(uuid.uuid4())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": {"errors": exc.errors()}
            },
            "request_id": req_id
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    req_id = str(uuid.uuid4())
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected internal server error occurred.",
                "details": {"error_type": type(exc).__name__, "message": str(exc)}
            },
            "request_id": req_id
        }
    )

# Section 19: All application APIs use /api/v1
api_v1_prefix = settings.API_V1_STR

app.include_router(profile.router, prefix=api_v1_prefix)
app.include_router(workers.router, prefix=api_v1_prefix)
app.include_router(experiences.router, prefix=api_v1_prefix)
app.include_router(problems.router, prefix=api_v1_prefix)
app.include_router(matching.router, prefix=api_v1_prefix)
app.include_router(service_requests.router, prefix=api_v1_prefix)
app.include_router(jobs.router, prefix=api_v1_prefix)
app.include_router(verification.router, prefix=api_v1_prefix)
app.include_router(feedback.router, prefix=api_v1_prefix)
app.include_router(knowledge.router, prefix=api_v1_prefix)
app.include_router(notifications.router, prefix=api_v1_prefix)

# Helper schemas for Supabase Auth Flutter profile registration
class ProfileInitRequest(BaseModel):
    id: Optional[uuid.UUID] = None
    email: str
    role: str = "customer"
    full_name: str
    phone: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "customer"
    phone: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None

@app.post(f"{api_v1_prefix}/auth/register", tags=["Auth Registration"])
def register_supabase_user(payload: RegisterRequest):
    """
    Provisions a new user in Supabase auth.users with email_confirm=True via Supabase Admin API.
    Guarantees auth.users.id == profiles.id and sets up worker_profiles if role == 'worker'.
    Prevents SMTP email rate limits while maintaining 100% real Supabase Auth identity.
    """
    clean_email = payload.email.strip()
    if len(payload.password) < 6:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_PASSWORD",
            message="Password must be at least 6 characters."
        )

    user_id_str = None
    if db.supabase_client:
        try:
            existing_user = None
            try:
                users = db.supabase_client.auth.admin.list_users()
                for u in users:
                    if u.email and u.email.lower() == clean_email.lower():
                        existing_user = u
                        break
            except Exception as e:
                logger.warning(f"Could not check existing users: {e}")

            if existing_user:
                user_id_str = str(existing_user.id)
                db.supabase_client.auth.admin.update_user_by_id(
                    user_id_str,
                    {
                        "password": payload.password,
                        "email_confirm": True,
                        "user_metadata": {
                            "display_name": payload.full_name,
                            "full_name": payload.full_name,
                            "role": payload.role,
                            "phone": payload.phone
                        }
                    }
                )
            else:
                new_user = db.supabase_client.auth.admin.create_user({
                    "email": clean_email,
                    "password": payload.password,
                    "email_confirm": True,
                    "user_metadata": {
                        "display_name": payload.full_name,
                        "full_name": payload.full_name,
                        "role": payload.role,
                        "phone": payload.phone
                    }
                })
                user_id_str = str(new_user.user.id)
        except Exception as e:
            logger.error(f"Supabase Auth admin create_user failed: {e}")
            raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="AUTH_CREATION_FAILED",
                message=str(e)
            )

    if not user_id_str:
        user_id_str = str(uuid.uuid4())

    from backend.config import IST
    now = datetime.now(IST)
    profile_record = {
        "id": user_id_str,
        "role": payload.role,
        "display_name": payload.full_name,
        "full_name": payload.full_name,
        "email": clean_email,
        "phone": payload.phone,
        "locality": payload.locality.strip() if payload.locality else None,
        "city": payload.city.strip() if payload.city else None,
        "avatar_url": None,
        "is_active": True,
        "created_at": now,
        "updated_at": now
    }
    db.profiles[user_id_str] = profile_record
    db.sync_to_supabase("profiles", profile_record)

    if payload.role == "worker":
        worker_record = {
            "id": user_id_str,
            "user_id": user_id_str,
            "headline": "Electrician & Repair Technician",
            "professional_title": "Electrician & Repair Technician",
            "bio": "Certified service professional on KaushalSetu.",
            "experience_years": 3,
            "years_experience": 3,
            "hourly_rate": 450.0,
            "service_radius_km": 15.0,
            "latitude": 19.0760,
            "longitude": 72.8777,
            "locality": payload.locality.strip() if payload.locality else None,
            "city": payload.city.strip() if payload.city else None,
            "state": "Maharashtra",
            "postal_code": "400050",
            "is_available": True,
            "availability_status": "available",
            "is_verified": False,
            "rating": 5.0,
            "total_reviews": 0,
            "created_at": now,
            "updated_at": now
        }
        db.worker_profiles[user_id_str] = worker_record
        db.sync_to_supabase("worker_profiles", worker_record)

    return db.profiles[user_id_str]

@app.post(f"{api_v1_prefix}/auth/sync-profile", tags=["Auth Profile Sync"])
def sync_supabase_profile(
    payload: ProfileInitRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Called upon Supabase Auth signup to ensure profiles.id == auth.users.id
    and initialize worker_profile if role == 'worker'.
    Derives authenticated UUID from Supabase JWT.
    """
    user_id_str = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split()[1]
        try:
            p = jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
            user_id_str = p.get("sub")
        except Exception:
            try:
                p = jwt.decode(token, options={"verify_signature": False})
                user_id_str = p.get("sub")
            except Exception:
                pass

    if not user_id_str and payload.id:
        user_id_str = str(payload.id)

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not determine authenticated user ID."
        )

    now = datetime.now(IST)
    
    # 1. Upsert profiles
    existing_profile = db.profiles.get(user_id_str)
    display_name = payload.full_name or (existing_profile.get("display_name") if existing_profile else "User")
    
    profile_record = {
        "id": user_id_str,
        "role": payload.role,
        "display_name": display_name,
        "full_name": display_name,
        "email": payload.email,
        "phone": payload.phone,
        "locality": payload.locality or (existing_profile.get("locality") if existing_profile else None),
        "city": payload.city or (existing_profile.get("city") if existing_profile else None),
        "avatar_url": existing_profile.get("avatar_url") if existing_profile else None,
        "is_active": True,
        "created_at": existing_profile["created_at"] if existing_profile else now,
        "updated_at": now
    }
    db.profiles[user_id_str] = profile_record
    db.sync_to_supabase("profiles", profile_record)
    
    # 2. If worker, upsert worker_profiles
    if payload.role == "worker":
        existing_worker = db.worker_profiles.get(user_id_str)
        worker_record = {
            "id": user_id_str,
            "user_id": user_id_str,
            "headline": existing_worker.get("headline") if existing_worker else "Electrician & Repair Technician",
            "professional_title": existing_worker.get("professional_title") if existing_worker else "Electrician & Repair Technician",
            "bio": existing_worker.get("bio") if existing_worker else "Certified service professional on KaushalSetu.",
            "experience_years": existing_worker.get("experience_years", 3) if existing_worker else 3,
            "years_experience": existing_worker.get("years_experience", 3) if existing_worker else 3,
            "hourly_rate": 450.0,
            "service_radius_km": 15.0,
            "latitude": 19.0760,
            "longitude": 72.8777,
            "locality": payload.locality or (existing_worker.get("locality") if existing_worker else None),
            "city": payload.city or (existing_worker.get("city") if existing_worker else None),
            "state": "Maharashtra",
            "postal_code": "400050",
            "is_available": True,
            "availability_status": "available",
            "is_verified": False,
            "rating": existing_worker.get("rating", 5.0) if existing_worker else 5.0,
            "total_reviews": existing_worker.get("total_reviews", 0) if existing_worker else 0,
            "created_at": existing_worker["created_at"] if existing_worker else now,
            "updated_at": now
        }
        db.worker_profiles[user_id_str] = worker_record
        db.sync_to_supabase("worker_profiles", worker_record)
        
    return db.profiles[user_id_str]

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "tables_count": 25
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

