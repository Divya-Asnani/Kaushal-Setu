"""pgvector candidate retrieval.

Cosine distance is used via the ``<=>`` operator, which is what the HNSW indexes were
built for. Similarity is reported as ``1 - distance`` so callers always work with
"higher is better" on a 0..1 scale.

Queries are written against DATABASE_URL rather than the Supabase REST client because
PostgREST cannot express a vector ordering. Only these searches use the direct path.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from backend.core.config import settings
from backend.db.pg import query, to_vector_literal

log = logging.getLogger(__name__)


@dataclass
class ExperienceCandidate:
    experience_id: str
    worker_id: str
    similarity: float
    title: str
    problem_description: str
    diagnosis: str | None
    outcome_summary: str | None
    experience_status: str
    verification_confidence: float
    source_text: str


_EXPERIENCE_SQL = """
SELECT
    e.id                       AS experience_id,
    e.worker_id                AS worker_id,
    1 - (ee.embedding <=> %s::vector) AS similarity,
    e.title                    AS title,
    e.problem_description      AS problem_description,
    e.diagnosis                AS diagnosis,
    e.outcome_summary          AS outcome_summary,
    e.experience_status        AS experience_status,
    e.verification_confidence  AS verification_confidence,
    ee.source_text             AS source_text
FROM experience_embeddings ee
JOIN experiences e ON e.id = ee.experience_id
WHERE e.experience_status <> 'archived'
ORDER BY ee.embedding <=> %s::vector
LIMIT %s
"""


def search_experiences(
    query_vector: list[float], limit: int | None = None
) -> list[ExperienceCandidate]:
    """Return the nearest solved experiences to a query vector."""
    limit = limit or settings.match_candidate_pool
    literal = to_vector_literal(query_vector)
    results = query(_EXPERIENCE_SQL, (literal, literal, limit))
    return [
        ExperienceCandidate(
            experience_id=str(r["experience_id"]),
            worker_id=str(r["worker_id"]),
            similarity=float(r["similarity"]),
            title=r.get("title") or "",
            problem_description=r.get("problem_description") or "",
            diagnosis=r.get("diagnosis"),
            outcome_summary=r.get("outcome_summary"),
            experience_status=r.get("experience_status") or "draft",
            verification_confidence=float(r.get("verification_confidence") or 0),
            source_text=r.get("source_text") or "",
        )
        for r in results
    ]


_KNOWLEDGE_SQL = """
SELECT
    kc.id           AS knowledge_case_id,
    1 - (kce.embedding <=> %s::vector) AS similarity,
    kc.title        AS title,
    kc.worker_id    AS worker_id,
    kc.is_verified  AS is_verified,
    kc.difficulty_level AS difficulty_level
FROM knowledge_case_embeddings kce
JOIN knowledge_cases kc ON kc.id = kce.knowledge_case_id
WHERE kc.visibility_status = 'published'
ORDER BY kce.embedding <=> %s::vector
LIMIT %s
"""


def search_knowledge_cases(query_vector: list[float], limit: int = 5) -> list[dict[str, Any]]:
    """Knowledge Hub search. Only published cases are visible."""
    literal = to_vector_literal(query_vector)
    results = query(_KNOWLEDGE_SQL, (literal, literal, limit))
    return [
        {
            "knowledge_case_id": str(r["knowledge_case_id"]),
            "similarity": round(float(r["similarity"]), 4),
            "title": r.get("title") or "",
            "worker_id": str(r["worker_id"]),
            "verification_state": "verified" if r.get("is_verified") else "unverified",
            "difficulty_level": r.get("difficulty_level"),
        }
        for r in results
    ]


_SIMILAR_EXPERIENCE_SQL = """
SELECT
    e.id        AS experience_id,
    e.worker_id AS worker_id,
    e.title     AS title,
    e.experience_status AS experience_status,
    1 - (ee.embedding <=> %s::vector) AS similarity
FROM experience_embeddings ee
JOIN experiences e ON e.id = ee.experience_id
WHERE e.experience_status <> 'archived'
ORDER BY
    -- verified cases first among near-equal matches, per the spec for this endpoint
    (CASE WHEN e.experience_status = 'verified' THEN 0 ELSE 1 END),
    ee.embedding <=> %s::vector
LIMIT %s
"""


def search_similar_experiences(query_vector: list[float], limit: int = 5) -> list[dict[str, Any]]:
    literal = to_vector_literal(query_vector)
    results = query(_SIMILAR_EXPERIENCE_SQL, (literal, literal, limit))
    return [
        {
            "experience_id": str(r["experience_id"]),
            "similarity": round(float(r["similarity"]), 4),
            "worker_id": str(r["worker_id"]),
            "title": r.get("title") or "",
            "verification_status": r.get("experience_status") or "draft",
        }
        for r in results
    ]
