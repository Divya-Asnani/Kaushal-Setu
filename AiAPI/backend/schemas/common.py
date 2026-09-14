"""Shared schema pieces and the enumerated values the database CHECK constraints allow."""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

ROLES = ("customer", "worker", "admin")
AVAILABILITY = ("available", "busy", "offline")
PROFICIENCY = ("beginner", "intermediate", "advanced", "expert")
PROBLEM_STATUS = ("open", "matched", "requested", "in_progress", "resolved", "cancelled")
EXPERIENCE_STATUS = ("draft", "submitted", "verified", "disputed", "archived")
SUCCESS_STATUS = ("successful", "partially_successful", "unsuccessful", "unknown")
REQUEST_STATUS = ("pending", "accepted", "rejected", "cancelled", "expired")
JOB_STATUS = ("confirmed", "in_progress", "completed", "cancelled", "disputed")
VERIFICATION_TYPE = ("customer_confirmation", "evidence_review", "admin_review", "dispute")
VERIFICATION_STATUS = ("pending", "verified", "rejected", "disputed")
MEDIA_TYPE = ("image", "video", "document")
MEDIA_ROLE = ("evidence", "before", "during", "after", "diagnostic", "other")
DIFFICULTY = ("beginner", "intermediate", "advanced", "expert")
VISIBILITY = ("draft", "published", "archived")


class Schema(BaseModel):
    """Base for request bodies. Unknown fields are rejected so typos surface early."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Out(BaseModel):
    """Base for responses.

    Responses are frequently built by splatting a database row, which carries columns
    the schema does not publish (``updated_at``, internal ids). Ignoring extras keeps
    a new column from turning into a 500, while the declared fields still define
    exactly what is serialised back to the client.
    """

    model_config = ConfigDict(extra="ignore")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int = 0


class Coordinates(Schema):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class Address(Coordinates):
    address_line: str | None = None
    locality: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None


def clean(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop keys the caller did not send, so PATCH never nulls untouched columns."""
    return {k: v for k, v in payload.items() if v is not None}
