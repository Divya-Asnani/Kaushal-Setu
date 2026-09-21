import uuid
from typing import Optional, List
from pydantic import BaseModel, Field

class MatchResultItem(BaseModel):
    match_result_id: Optional[uuid.UUID] = None
    problem_id: uuid.UUID
    worker_id: uuid.UUID
    rank_position: int
    match_score: float
    problem_similarity: float
    context_similarity: float
    verified_experience_confidence: float
    proximity_score: float
    explanations: List[str] = Field(default_factory=list)
    
    # Worker preview details for UI cards
    worker_name: str
    headline: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    hourly_rate: Optional[float] = None
    rating: float = 5.0
    total_reviews: int = 0
    is_available: bool = True
    relevant_solved_cases: int = 0
    skills: List[str] = Field(default_factory=list)

class MatchResponse(BaseModel):
    problem_id: uuid.UUID
    total_matches: int
    matches: List[MatchResultItem]
