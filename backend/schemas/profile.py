import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class ProfileBase(BaseModel):
    full_name: str
    phone: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    avatar_url: Optional[str] = None

class ProfileRead(ProfileBase):
    id: uuid.UUID
    email: str
    role: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    avatar_url: Optional[str] = None

class BecomeWorkerRequest(BaseModel):
    service_category: str = "electronics"
    headline: Optional[str] = "Certified Service Technician"
    locality: Optional[str] = None
    city: Optional[str] = None
    experience_years: int = 3
    hourly_rate: float = 450.0
    service_radius_km: float = 15.0

