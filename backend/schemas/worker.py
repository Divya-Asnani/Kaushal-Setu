import uuid
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field

class SkillRead(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    description: Optional[str] = None

class WorkerSkillRead(BaseModel):
    id: uuid.UUID
    skill_id: uuid.UUID
    skill_name: str
    category: str
    proficiency_level: str
    verified: bool

class WorkerSkillCreate(BaseModel):
    skill_id: uuid.UUID
    proficiency_level: str = "intermediate"

class CertificateCreate(BaseModel):
    title: str
    issuing_organization: str
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    credential_url: Optional[str] = None
    storage_path: Optional[str] = None

class CertificateRead(CertificateCreate):
    id: uuid.UUID
    worker_id: uuid.UUID
    is_verified: bool
    created_at: datetime

class WorkerProfileRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: str
    phone: Optional[str] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    experience_years: int = 0
    hourly_rate: Optional[float] = None
    service_radius_km: float = 15.0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    is_available: bool = True
    is_verified: bool = False
    rating: float = 5.0
    total_reviews: int = 0
    skills: List[WorkerSkillRead] = Field(default_factory=list)
    certificates: List[CertificateRead] = Field(default_factory=list)

class WorkerProfileUpdate(BaseModel):
    headline: Optional[str] = None
    bio: Optional[str] = None
    experience_years: Optional[int] = None
    hourly_rate: Optional[float] = None
    service_radius_km: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address_line: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    is_available: Optional[bool] = None
