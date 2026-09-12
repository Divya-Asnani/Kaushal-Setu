"""Request and response schemas for every endpoint in the API contract."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import Field

from backend.schemas.common import Address, Out, Schema

# --------------------------------------------------------------------------- profile


class ProfileOut(Out):
    id: str
    role: str
    display_name: str
    phone: str | None = None
    avatar_url: str | None = None
    is_active: bool = True


class ProfileUpdate(Schema):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = None
    avatar_url: str | None = None


# --------------------------------------------------------------------------- workers


class SkillOut(Out):
    id: str
    name: str
    category: str | None = None
    proficiency_level: str | None = None
    is_primary: bool | None = None


class WorkerOut(Out):
    user_id: str
    professional_title: str
    bio: str | None = None
    years_experience: int = 0
    service_radius_km: float = 10
    locality: str | None = None
    city: str | None = None
    state: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    availability_status: str = "available"
    is_verified: bool = False
    skills: list[SkillOut] = []


class WorkerUpdate(Address):
    professional_title: str | None = Field(default=None, min_length=1, max_length=160)
    bio: str | None = None
    years_experience: int | None = Field(default=None, ge=0, le=80)
    service_radius_km: float | None = Field(default=None, gt=0, le=500)
    availability_status: Literal["available", "busy", "offline"] | None = None


class WorkerSkillIn(Schema):
    skill_id: str
    proficiency_level: Literal["beginner", "intermediate", "advanced", "expert"] = "intermediate"
    years_experience: int = Field(default=0, ge=0, le=80)
    is_primary: bool = False


class WorkerSkillsReplace(Schema):
    skills: list[WorkerSkillIn] = Field(default_factory=list, max_length=100)


class CertificateIn(Schema):
    certificate_name: str = Field(min_length=1, max_length=200)
    issuing_organization: str | None = None
    certificate_number: str | None = None
    issue_date: date | None = None
    expiry_date: date | None = None
    certificate_url: str | None = None


class CertificateOut(Out):
    id: str
    certificate_name: str
    issuing_organization: str | None = None
    certificate_number: str | None = None
    issue_date: date | None = None
    expiry_date: date | None = None
    certificate_url: str | None = None
    verification_status: str = "pending"


# -------------------------------------------------------------------------- problems


class ProblemIn(Address):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)


class ProblemUpdate(Address):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=5000)


class ProblemMediaIn(Schema):
    storage_path: str = Field(min_length=1)
    media_type: Literal["image", "video", "document"] = "image"
    mime_type: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = Field(default=None, ge=0)
    caption: str | None = None


class ProblemOut(Out):
    id: str
    customer_id: str | None = None
    title: str
    description: str | None = None
    status: str = "open"
    address_line: str | None = None
    locality: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime | None = None
    media: list[dict[str, Any]] = []
    fingerprint: dict[str, Any] | None = None


# ---------------------------------------------------------------------- fingerprints


class FingerprintRequest(Schema):
    regenerate: bool = False


class FingerprintOut(Out):
    id: str | None = None
    problem_id: str
    device_type: str | None = None
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    issue: str | None = None
    symptoms: list[str] = []
    context: dict[str, Any] = {}
    suspected_component: str | None = None
    suspected_component_source: str | None = None
    repair_type: str | None = None
    urgency: str | None = None
    extracted_skills: list[str] = []
    ai_summary: str = ""
    embedding_status: str = "pending"
    fingerprint_version: str = "v1"
    safety_warning: str | None = None


class FingerprintConfirm(Schema):
    """Customer corrections to the extracted fingerprint (PRD requirement C-05)."""

    device_type: str | None = None
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    issue: str | None = None
    symptoms: list[str] | None = None
    context: list[str] | None = None
    suspected_component: str | None = None
    repair_type: str | None = None
    urgency: Literal["normal", "urgent"] | None = None
    extracted_skills: list[str] | None = None


# --------------------------------------------------------------------------- matching


class MatchItem(Out):
    match_result_id: str | None = None
    worker_id: str
    rank_position: int
    match_score: float
    problem_similarity: float
    context_similarity: float
    verified_experience_confidence: float
    proximity_score: float
    explanation: list[str] = []
    distance_km: float | None = None
    within_service_radius: bool = True


class MatchesOut(Out):
    problem_id: str
    items: list[MatchItem] = []
    candidate_pool_size: int = 0
    graph_enriched: bool = False
    radius_relaxed: bool = False
    safety_warning: str | None = None
    weights: dict[str, float] = {}


# ------------------------------------------------------------------------ experiences


class ContextIn(Schema):
    context_type: str = Field(min_length=1, max_length=80)
    context_value: str = Field(min_length=1, max_length=300)
    context_details: dict[str, Any] | None = None
    importance_score: float = Field(default=0.5, ge=0, le=1)


class ActionIn(Schema):
    step_number: int = Field(ge=1)
    action_type: str = Field(min_length=1, max_length=80)
    action_description: str = Field(min_length=1, max_length=2000)
    tools_used: list[str] | None = None
    components_involved: list[str] | None = None
    result: str | None = None


class OutcomeIn(Schema):
    outcome_type: str = Field(default="repair_result", max_length=80)
    outcome_description: str = Field(min_length=1, max_length=2000)
    success_status: Literal[
        "successful", "partially_successful", "unsuccessful", "unknown"
    ] = "successful"
    follow_up_required: bool = False


class EvidenceIn(Schema):
    storage_path: str = Field(min_length=1)
    media_type: Literal["image", "video", "document"] = "image"
    media_role: Literal["evidence", "before", "during", "after", "diagnostic", "other"] = "evidence"
    mime_type: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = Field(default=None, ge=0)
    caption: str | None = None


class ExperienceIn(Schema):
    title: str = Field(min_length=1, max_length=200)
    problem_description: str = Field(min_length=1, max_length=5000)
    diagnosis: str | None = None
    outcome_summary: str | None = None
    experience_status: Literal["draft", "submitted"] = "draft"
    contexts: list[ContextIn] = []
    actions: list[ActionIn] = []
    outcomes: list[OutcomeIn] = []
    skill_ids: list[str] = []


class ExperienceUpdate(Schema):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    problem_description: str | None = None
    diagnosis: str | None = None
    outcome_summary: str | None = None
    experience_status: Literal["draft", "submitted", "archived"] | None = None


class ExperienceOut(Out):
    id: str
    worker_id: str | None = None
    title: str
    problem_description: str | None = None
    diagnosis: str | None = None
    outcome_summary: str | None = None
    experience_status: str = "draft"
    verification_confidence: float = 0
    contexts: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    media: list[dict[str, Any]] = []
    skills: list[str] = []


class SimilarExperience(Out):
    experience_id: str
    similarity: float
    worker_id: str
    title: str
    verification_status: str


# -------------------------------------------------------------------- service requests


class ServiceRequestIn(Schema):
    problem_id: str
    worker_id: str
    match_result_id: str | None = None
    customer_message: str | None = Field(default=None, max_length=1000)


class ServiceRequestPatch(Schema):
    status: Literal["accepted", "rejected", "cancelled", "expired"]
    worker_response: str | None = Field(default=None, max_length=1000)


class ServiceRequestOut(Out):
    id: str
    problem_id: str | None = None
    worker_id: str | None = None
    status: str
    customer_message: str | None = None
    worker_response: str | None = None
    requested_at: datetime | None = None
    responded_at: datetime | None = None
    accepted_at: datetime | None = None
    expires_at: datetime | None = None
    job_id: str | None = None


# ------------------------------------------------------------------------------ jobs


class JobStatusPatch(Schema):
    status: Literal["in_progress", "completed", "cancelled", "disputed"]
    notes: str | None = Field(default=None, max_length=1000)


class JobOut(Out):
    id: str
    service_request_id: str | None = None
    status: str
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status_history: list[dict[str, Any]] = []


class CompletionIn(Schema):
    diagnosis: str = Field(min_length=1, max_length=5000)
    outcome_summary: str | None = None
    actions: list[ActionIn] = Field(min_length=1)
    outcomes: list[OutcomeIn] = Field(min_length=1)
    evidence: list[EvidenceIn] = []
    contexts: list[ContextIn] = []
    skill_ids: list[str] = []


class CompletionOut(Out):
    job_id: str
    status: str
    experience_id: str
    evidence_count: int = 0


class VerifyIn(Schema):
    verification_status: Literal["verified", "rejected"] = "verified"
    comments: str | None = Field(default=None, max_length=2000)


class DisputeIn(Schema):
    comments: str = Field(min_length=1, max_length=2000)


class VerificationOut(Out):
    verification_id: str
    verification_status: str
    verification_score: float | None = None
    verified_at: datetime | None = None
    experience_id: str | None = None


class FeedbackIn(Schema):
    job_id: str
    rating: float = Field(ge=1, le=5)
    feedback_text: str | None = Field(default=None, max_length=2000)


class FeedbackOut(Out):
    id: str
    job_id: str
    customer_id: str | None = None
    worker_id: str | None = None
    rating: float
    feedback_text: str | None = None


# ------------------------------------------------------------------- knowledge cases


class KnowledgeCaseIn(Schema):
    experience_id: str | None = None
    title: str = Field(min_length=1, max_length=200)
    problem_summary: str = Field(min_length=1, max_length=5000)
    diagnosis_summary: str | None = None
    solution_summary: str | None = None
    lesson_learned: str | None = None
    difficulty_level: Literal["beginner", "intermediate", "advanced", "expert"] = "intermediate"
    visibility_status: Literal["draft", "published"] = "draft"


class KnowledgeCaseUpdate(Schema):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    problem_summary: str | None = None
    diagnosis_summary: str | None = None
    solution_summary: str | None = None
    lesson_learned: str | None = None
    difficulty_level: Literal["beginner", "intermediate", "advanced", "expert"] | None = None
    visibility_status: Literal["draft", "published", "archived"] | None = None


class KnowledgeCaseOut(Out):
    id: str
    worker_id: str | None = None
    experience_id: str | None = None
    title: str
    problem_summary: str | None = None
    diagnosis_summary: str | None = None
    solution_summary: str | None = None
    lesson_learned: str | None = None
    difficulty_level: str = "intermediate"
    visibility_status: str = "draft"
    is_verified: bool = False
    published_at: datetime | None = None
    media: list[dict[str, Any]] = []


class SimilarKnowledgeCase(Out):
    knowledge_case_id: str
    similarity: float
    title: str
    worker_id: str | None = None
    verification_state: str = "unverified"
    difficulty_level: str | None = None


# ------------------------------------------------------------------------ notifications


class NotificationOut(Out):
    id: str
    notification_type: str
    title: str
    message: str
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    is_read: bool = False
    read_at: datetime | None = None
    created_at: datetime | None = None
