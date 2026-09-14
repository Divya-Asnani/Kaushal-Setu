"""The matching pipeline (PRD section 13, FastAPI spec section 8).

    fingerprint -> canonical text -> embedding -> pgvector -> graph enrichment
                -> radius/structured filters -> ranking -> match_results

Persisting match_results is not bookkeeping: a service request points at the match that
produced it, so the reason a customer chose a worker stays auditable after the fact.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.core.config import settings
from backend.db.supabase import rows, table
from backend.services.ai import canonical, embeddings
from backend.services.ai.fingerprint import Fingerprint
from backend.services.graph import neo4j_client
from backend.services.matching import retrieval
from backend.services.matching.ranking import ScoredWorker, WorkerCandidate, rank

log = logging.getLogger(__name__)


def _group_by_worker(
    candidates: list[retrieval.ExperienceCandidate],
) -> dict[str, list[retrieval.ExperienceCandidate]]:
    grouped: dict[str, list[retrieval.ExperienceCandidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.worker_id, []).append(candidate)
    return grouped


def _load_worker_profiles(worker_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not worker_ids:
        return {}
    result = rows(
        table("worker_profiles")
        .select(
            "user_id, professional_title, latitude, longitude, service_radius_km, "
            "availability_status, is_verified, locality, city, state, years_experience"
        )
        .in_("user_id", worker_ids)
        .execute()
    )
    return {str(r["user_id"]): r for r in result}


def _load_experience_context(experience_ids: list[str]):
    """Structured context and skills for the retrieved experiences, in two queries."""
    if not experience_ids:
        return {}, {}

    contexts: dict[str, list[dict[str, Any]]] = {}
    for row in rows(
        table("experience_contexts")
        .select("experience_id, context_type, context_value")
        .in_("experience_id", experience_ids)
        .execute()
    ):
        contexts.setdefault(str(row["experience_id"]), []).append(row)

    skills: dict[str, list[str]] = {}
    for row in rows(
        table("experience_skills")
        .select("experience_id, skills(name)")
        .in_("experience_id", experience_ids)
        .execute()
    ):
        name = (row.get("skills") or {}).get("name")
        if name:
            skills.setdefault(str(row["experience_id"]), []).append(name)

    return contexts, skills


def build_candidates(
    experience_candidates: list[retrieval.ExperienceCandidate],
) -> list[WorkerCandidate]:
    grouped = _group_by_worker(experience_candidates)
    worker_ids = list(grouped)
    profiles = _load_worker_profiles(worker_ids)
    experience_ids = [c.experience_id for c in experience_candidates]
    contexts, skills = _load_experience_context(experience_ids)
    graph = neo4j_client.enrich_workers(worker_ids)

    candidates = []
    for worker_id, experiences in grouped.items():
        profile = profiles.get(worker_id)
        if profile is None:
            # An experience whose worker profile has gone; not a rankable candidate.
            continue
        candidates.append(
            WorkerCandidate(
                worker_id=worker_id,
                experiences=experiences,
                profile=profile,
                graph=graph.get(worker_id, {}),
                contexts_by_experience={
                    e.experience_id: contexts.get(e.experience_id, []) for e in experiences
                },
                skills_by_experience={
                    e.experience_id: skills.get(e.experience_id, []) for e in experiences
                },
            )
        )
    return candidates


def persist_match_results(problem_id: str, ranked: list[ScoredWorker]) -> list[dict[str, Any]]:
    """Replace this problem's match results with the current ranking."""
    table("match_results").delete().eq("problem_id", problem_id).execute()
    if not ranked:
        return []

    payload = [
        {
            "problem_id": problem_id,
            "worker_id": worker.worker_id,
            "problem_similarity": worker.problem_similarity,
            "context_similarity": worker.context_similarity,
            "verified_experience_confidence": worker.verified_experience_confidence,
            "proximity_score": worker.proximity_score,
            "match_score": worker.match_score,
            "rank_position": position,
            "explanation": worker.explanation,
            "matching_metadata": worker.metadata,
        }
        for position, worker in enumerate(ranked, start=1)
    ]
    return rows(table("match_results").insert(payload).execute())


def run_matching(
    problem: dict[str, Any],
    fingerprint: Fingerprint,
    limit: int = 5,
) -> dict[str, Any]:
    """Full pipeline for one problem. Returns the API-shaped match payload."""
    source_text = canonical.fingerprint_text(fingerprint)
    query_vector = embeddings.embed_text(source_text, embeddings.QUERY)

    experience_candidates = retrieval.search_experiences(
        query_vector, settings.match_candidate_pool
    )
    candidates = build_candidates(experience_candidates)

    latitude = problem.get("latitude")
    longitude = problem.get("longitude")
    ranked = rank(
        candidates,
        fingerprint,
        float(latitude) if latitude is not None else None,
        float(longitude) if longitude is not None else None,
        limit=limit,
    )

    # A radius that excludes everyone is worse than an honest "these are further away".
    relaxed = False
    if not ranked and candidates:
        relaxed = True
        ranked = rank(
            candidates,
            fingerprint,
            float(latitude) if latitude is not None else None,
            float(longitude) if longitude is not None else None,
            limit=limit,
            include_out_of_radius=True,
        )

    stored = persist_match_results(problem["id"], ranked)
    ids_by_worker = {str(r["worker_id"]): str(r["id"]) for r in stored}

    return {
        "problem_id": str(problem["id"]),
        "items": [
            {
                "match_result_id": ids_by_worker.get(worker.worker_id),
                "worker_id": worker.worker_id,
                "rank_position": position,
                "match_score": worker.match_score,
                "problem_similarity": worker.problem_similarity,
                "context_similarity": worker.context_similarity,
                "verified_experience_confidence": worker.verified_experience_confidence,
                "proximity_score": worker.proximity_score,
                "explanation": worker.explanation,
                "distance_km": worker.metadata.get("distance_km"),
                "within_service_radius": worker.metadata.get("within_service_radius"),
            }
            for position, worker in enumerate(ranked, start=1)
        ],
        "candidate_pool_size": len(experience_candidates),
        "graph_enriched": neo4j_client.is_available(),
        "radius_relaxed": relaxed,
        "safety_warning": fingerprint.safety_warning,
        "weights": settings.match_weights,
    }
