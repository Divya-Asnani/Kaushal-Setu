import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class JobVerificationRequest(BaseModel):
    verification_status: str = "verified"  # "verified"
    comments: Optional[str] = None

class JobDisputeRequest(BaseModel):
    comments: str

class VerificationRead(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    customer_id: uuid.UUID
    verification_status: str
    comments: Optional[str] = None
    verified_at: datetime
    created_at: datetime
