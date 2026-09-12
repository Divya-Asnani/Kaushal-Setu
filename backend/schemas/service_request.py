import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class ServiceRequestCreate(BaseModel):
    problem_id: uuid.UUID
    worker_id: uuid.UUID
    match_result_id: Optional[uuid.UUID] = None
    customer_message: Optional[str] = None

class ServiceRequestUpdate(BaseModel):
    status: str  # "accepted" or "rejected" or "cancelled"
    worker_response: Optional[str] = None

class ServiceRequestRead(BaseModel):
    id: uuid.UUID
    problem_id: uuid.UUID
    worker_id: uuid.UUID
    match_result_id: Optional[uuid.UUID] = None
    customer_message: Optional[str] = None
    worker_response: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    
    # Nested preview details
    problem_title: Optional[str] = None
    problem_description: Optional[str] = None
    problem_category: Optional[str] = None
    customer_name: Optional[str] = None
    worker_name: Optional[str] = None
    locality: Optional[str] = None
    created_job_id: Optional[uuid.UUID] = None
