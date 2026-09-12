import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from fastapi import HTTPException

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)

class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class AppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.request_id = str(uuid.uuid4())
        super().__init__(status_code=status_code, detail=message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
            "request_id": self.request_id,
        }
