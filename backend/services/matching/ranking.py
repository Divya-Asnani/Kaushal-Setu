"""Hybrid ranking (PRD section 14).

    match_score = 0.40*problem + 0.30*context + 0.20*verified_confidence + 0.10*proximity

Every weight is configurable. These are prototype parameters chosen by the team, not
coefficients fitted to data, and nothing in this module should imply otherwise.

The four signals are deliberately different in kind, because vector similarity alone
cannot tell a Galaxy S23 from an S22, or a post-drop failure from an unrelated charging
fault. Structured agreement and verified evidence are what separate those cases.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from backend.core.config import settings
from backend.services.ai.canonical import normalise_skill
from backend.services.ai.fingerprint import Fingerprint
from backend.services.matching.retrieval import ExperienceCandidate

EARTH_RADIUS_KM = 6371.0


@dataclass
class WorkerCandidate:
    worker_id: str
    experiences: list[ExperienceCandidate] = field(default_factory=list)
    profile: dict[str, Any] = field(default_factory=dict)
    graph: dict[str, Any] = field(default_factory=dict)
    contexts_by_experience: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    skills_by_experience: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class ScoredWorker:
    worker_id: str
    match_score: float
    problem_similarity: float
    context_similarity: float
    verified_experience_confidence: float
    proximity_score: float
    explanation: list[str]
    metadata: dict[str, Any]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _pct(value: float) -> float:
    """Clamp to 0..100 and round, matching the numeric(5,2) match_results columns."""
    return round(max(0.0, min(100.0, value)) * 1.0, 2)


def _problem_similarity(candidate: WorkerCandidate) -> tuple[float, int]:
    """Best semantic match, nudged up when several experiences agree.

    A worker with one strong case and a worker with four strong cases should not score
    identically, but depth must not overtake relevance either, so the bonus is capped.
    """
    if not candidate.experiences:
        return 0.0, 0
    sims = sorted((e.similarity for e in candidate.experiences), reverse=True)
    best = sims[0]
    supporting = sum(1 for s in sims[1:] if s >= best - 0.05)
    depth_bonus = min(supporting, 3) * 0.02
    return _pct(min(1.0, best + depth_bonus) * 100), supporting


def _context_similarity(candidate: WorkerCandidate, fp: Fingerprint) -> tuple[float, dict[str, Any]]:
    """Structured agreement: model, brand, device, component, context, skills.

    This is the signal that keeps embeddings honest. Model agreement is weighted most
    heavily because it is the field customers care about and the one embeddings blur.
    """
    fp_brand = (fp.brand or "").strip().lower()
    fp_model = (fp.model or "").strip().lower()
    fp_device = (fp.device_type or "").strip().lower()
    fp_component = (fp.suspected_component or "").strip().lower()
    fp_contexts = {normalise_skill(c) for c in fp.context if c}
    fp_skills = {normalise_skill(s) for s in fp.extracted_skills if s}

    best = 0.0
    hits = {
        "model_matches": 0,
        "brand_matches": 0,
        "device_matches": 0,
        "component_matches": 0,
        "context_matches": 0,
    }

    for exp in candidate.experiences:
        blob = " ".join(
            [exp.source_text, exp.title, exp.problem_description, exp.diagnosis or ""]
        ).lower()
        exp_contexts = {
            normalise_skill(str(c.get("context_value") or ""))
            for c in candidate.contexts_by_experience.get(exp.experience_id, [])
        }
        exp_contexts |= {
            normalise_skill(str(c.get("context_type") or ""))
            for c in candidate.contexts_by_experience.get(exp.experience_id, [])
        }
        exp_skills = {
            normalise_skill(s) for s in candidate.skills_by_experience.get(exp.experience_id, [])
        }

        score = 0.0
        if fp_model and fp_model in blob:
            score += 0.40
            hits["model_matches"] += 1
        if fp_brand and fp_brand in blob:
            score += 0.15
            hits["brand_matches"] += 1
        if fp_device and fp_device in blob:
            score += 0.10
            hits["device_matches"] += 1
        if fp_component and fp_component in blob:
            score += 0.15
            hits["component_matches"] += 1

        shared_context = fp_contexts & (exp_contexts or set())
        if not shared_context and fp_contexts:
            shared_context = {c for c in fp_contexts if c and c in blob}
        if shared_context:
            score += min(0.15, 0.075 * len(shared_context))
            hits["context_matches"] += 1

        shared_skills = fp_skills & (exp_skills or set())
        if not shared_skills and fp_skills:
            shared_skills = {s for s in fp_skills if s and s in blob}
        if shared_skills:
            score += min(0.05, 0.025 * len(shared_skills))

        best = max(best, score)

    graph_contexts = {normalise_skill(c) for c in candidate.graph.get("contexts", [])}
    if fp_contexts and graph_contexts & fp_contexts:
        best = min(1.0, best + 0.05)
        hits["context_matches"] += 1

    return _pct(best * 100), hits


def _verified_confidence(candidate: WorkerCandidate) -> tuple[float, int]:
    """Confidence built from customer-verified outcomes only.

    Self-reported experience contributes a small amount and can never on its own reach
    a high score, which is the PRD trust rule (section 15) expressed numerically.
    """
    verified = [e for e in candidate.experiences if e.experience_status == "verified"]
    disputed = [e for e in candidate.experiences if e.experience_status == "disputed"]
    self_reported = [
        e for e in candidate.experiences if e.experience_status in {"draft", "submitted"}
    ]

    score = 0.0
    if verified:
        avg_confidence = sum(e.verification_confidence for e in verified) / len(verified)
        # Depth of verified history saturates rather than growing without bound.
        depth = 1 - math.exp(-len(verified) / 2.0)
        score = 0.65 * (avg_confidence / 100.0) + 0.35 * depth
    # Unverified work is worth something, but is capped well below a verified record.
    score = max(score, min(0.25, 0.08 * len(self_reported)))
    if disputed:
        score *= 0.6

    if candidate.profile.get("is_verified"):
        score = min(1.0, score + 0.05)

    return _pct(score * 100), len(verified)


def _proximity(candidate: WorkerCandidate, lat: float | None, lon: float | None):
    """Distance score plus a hard service-radius eligibility flag.

    Returns (score, distance_km, within_radius). When either side has no coordinates
    the worker is not excluded -- they simply receive a neutral proximity score, since
    absent location is not evidence of being far away.
    """
    profile = candidate.profile
    wlat, wlon = profile.get("latitude"), profile.get("longitude")
    if lat is None or lon is None or wlat is None or wlon is None:
        return _pct(50.0), None, True

    distance = haversine_km(float(lat), float(lon), float(wlat), float(wlon))
    radius = float(profile.get("service_radius_km") or 10)
    within = distance <= radius
    # Full marks at the doorstep, decaying to zero at the edge of the service radius.
    score = max(0.0, 1 - (distance / radius)) if radius > 0 else 0.0
    return _pct(score * 100), round(distance, 2), within


def _explain(
    candidate: WorkerCandidate,
    fp: Fingerprint,
    hits: dict[str, Any],
    supporting: int,
    verified_count: int,
    distance_km: float | None,
    within_radius: bool,
) -> list[str]:
    """Human-readable reasons. Every Top-K result must carry these (PRD section 27)."""
    reasons: list[str] = []
    total = len(candidate.experiences)

    descriptor = " ".join(x for x in [fp.brand, fp.repair_type] if x) or "similar"
    if total:
        reasons.append(f"Solved {total} similar {descriptor} case{'s' if total != 1 else ''}.")

    if hits.get("model_matches") and fp.model:
        n = hits["model_matches"]
        context_label = fp.context[0] if fp.context else None
        detail = f"{fp.model} + {fp.issue}" if fp.issue else fp.model
        if context_label:
            detail += f" after {context_label}"
        reasons.append(f"{n} case{'s' if n != 1 else ''} match {detail}.")
    elif hits.get("brand_matches") and fp.brand:
        reasons.append(f"Experience with {fp.brand} devices.")

    if hits.get("component_matches") and fp.suspected_component:
        reasons.append(
            f"Has worked on the {fp.suspected_component} area the customer suspects."
        )

    if verified_count:
        reasons.append(
            f"{verified_count} customer-verified outcome{'s' if verified_count != 1 else ''}."
        )
    else:
        reasons.append("Experience is self-reported and not yet customer-verified.")

    if distance_km is not None:
        radius = candidate.profile.get("service_radius_km")
        if within_radius and radius:
            reasons.append(f"{distance_km} km away, within the {radius} km service radius.")
        elif within_radius:
            reasons.append(f"{distance_km} km away.")
        else:
            reasons.append(f"{distance_km} km away, outside the usual service radius.")

    if candidate.graph:
        solved = candidate.graph.get("solved_count")
        if solved:
            reasons.append(f"Experience graph links {solved} related solved problems.")

    if supporting:
        reasons.append(f"{supporting} further closely-related case{'s' if supporting != 1 else ''}.")

    return reasons


def rank(
    candidates: list[WorkerCandidate],
    fingerprint: Fingerprint,
    latitude: float | None,
    longitude: float | None,
    limit: int = 5,
    include_out_of_radius: bool = False,
) -> list[ScoredWorker]:
    """Score and order workers. Highest match_score first."""
    weights = settings.match_weights
    scored: list[ScoredWorker] = []

    for candidate in candidates:
        problem, supporting = _problem_similarity(candidate)
        context, hits = _context_similarity(candidate, fingerprint)
        verified, verified_count = _verified_confidence(candidate)
        proximity, distance_km, within_radius = _proximity(candidate, latitude, longitude)

        if not within_radius and not include_out_of_radius:
            continue
        if candidate.profile.get("availability_status") == "offline":
            continue

        total = (
            weights["problem"] * problem
            + weights["context"] * context
            + weights["verified"] * verified
            + weights["proximity"] * proximity
        )

        scored.append(
            ScoredWorker(
                worker_id=candidate.worker_id,
                match_score=_pct(total),
                problem_similarity=problem,
                context_similarity=context,
                verified_experience_confidence=verified,
                proximity_score=proximity,
                explanation=_explain(
                    candidate, fingerprint, hits, supporting,
                    verified_count, distance_km, within_radius,
                ),
                metadata={
                    "weights": weights,
                    "weights_note": (
                        "Prototype weights from PRD section 14; not trained coefficients."
                    ),
                    "distance_km": distance_km,
                    "within_service_radius": within_radius,
                    "candidate_experience_ids": [
                        e.experience_id for e in candidate.experiences[:10]
                    ],
                    "verified_experience_count": verified_count,
                    "structured_hits": hits,
                    "graph_enriched": bool(candidate.graph),
                },
            )
        )

    scored.sort(key=lambda s: s.match_score, reverse=True)
    return scored[:limit]
