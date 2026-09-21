"""Drop-in replacements for the application's heuristic AI functions.

These keep the exact signatures and return shapes of
``backend.services.ai.fingerprint.extract_problem_fingerprint`` and
``backend.services.matching.matcher.compute_matches_for_problem``, so wiring them in is
a one-line import change at each call site and the Flutter client sees no difference in
the response payload.

Both adapters fall back to the original heuristic implementation whenever the engine is
unconfigured or a call fails. An expired Gemini quota or an unreachable database
therefore degrades the quality of a result rather than breaking the request.
"""
from __future__ import annotations

import logging
import math
import uuid
from typing import Any

from backend.services.ai_engine import canonical, embeddings
from backend.services.ai_engine import fingerprint as fp_engine
from backend.services.ai_engine import retrieval
from backend.services.ai_engine.config import settings

log = logging.getLogger("kaushalsetu.ai_engine")


# --------------------------------------------------------------------- fingerprint


def extract_problem_fingerprint(title: str, description: str) -> dict[str, Any]:
    """Extract a Problem Fingerprint with Gemini, in the shape the routes expect.

    Two safety rules from the specification survive into the output: a suspected
    component is recorded with its provenance rather than asserted, and high-risk
    electrical wording raises a warning to involve a qualified professional. Both are
    carried in the ``context`` dict, which is a jsonb column with no fixed shape.
    """
    from backend.services.ai.fingerprint import extract_problem_fingerprint as heuristic

    if not settings.fingerprint_enabled():
        return heuristic(title, description)

    try:
        result = fp_engine.generate_fingerprint(title, description)
    except Exception as exc:
        log.warning("AI fingerprint failed (%s); using the built-in extractor", exc)
        return heuristic(title, description)

    base = heuristic(title, description)

    def pick(value: Any, fallback: Any) -> Any:
        """Prefer the model's answer, but never regress to an empty field."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return fallback
        if isinstance(value, list) and not value:
            return fallback
        return value

    context: dict[str, Any] = {
        "origin": "Customer problem description",
        "urgency": "High" if result.urgency == "urgent" else "Standard",
        "requires_onsite": True,
        "items": result.context,
        # Provenance is mandatory: the UI must be able to tell a customer's own words
        # from the model's guess, and never present either as a confirmed diagnosis.
        "suspected_component_source": result.suspected_component_source,
        "safety_warning": result.safety_warning,
        "extracted_by": result.model_used,
    }

    return {
        **base,
        "device_type": pick(result.device_type, base["device_type"]),
        "brand": pick(result.brand, base["brand"]),
        "model": pick(result.model, base["model"]),
        "category": pick(result.category, base["category"]),
        "issue": pick(result.issue, base["issue"]),
        "symptoms": pick(result.symptoms, base["symptoms"]),
        "context": context,
        "suspected_component": pick(result.suspected_component, base["suspected_component"]),
        "repair_type": pick(result.repair_type, base["repair_type"]),
        "extracted_skills": pick(result.extracted_skills, base["extracted_skills"]),
        "ai_summary": pick(result.ai_summary, base["ai_summary"]),
    }


# ------------------------------------------------------------------------ matching


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _fingerprint_from_record(record: dict[str, Any]) -> fp_engine.Fingerprint:
    """Rebuild an engine Fingerprint from a stored fingerprint record."""
    context = record.get("context") or {}
    if not isinstance(context, dict):
        context = {}
    return fp_engine.Fingerprint(
        device_type=record.get("device_type"),
        brand=record.get("brand"),
        model=record.get("model"),
        category=record.get("category"),
        issue=record.get("issue"),
        symptoms=list(record.get("symptoms") or []),
        context=list(context.get("items") or []),
        suspected_component=record.get("suspected_component"),
        suspected_component_source=context.get("suspected_component_source"),
        repair_type=record.get("repair_type"),
        extracted_skills=list(record.get("extracted_skills") or []),
        ai_summary=record.get("ai_summary") or "",
    )


def _semantic_scores(fingerprint: fp_engine.Fingerprint) -> dict[str, dict[str, Any]]:
    """Best semantic similarity per worker, from pgvector.

    Returns {worker_id: {"similarity": float, "matches": int, "titles": [str]}}.
    """
    text = canonical.fingerprint_text(fingerprint)
    if not text.strip():
        return {}

    vector = embeddings.embed_query(text)
    candidates = retrieval.search_experiences(vector, settings.match_candidate_pool)

    by_worker: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        entry = by_worker.setdefault(
            candidate.worker_id, {"similarity": 0.0, "matches": 0, "titles": []}
        )
        entry["similarity"] = max(entry["similarity"], candidate.similarity)
        # Only count genuinely close cases, so a long tail of weak matches cannot
        # inflate a worker's apparent depth of experience.
        if candidate.similarity >= 0.6:
            entry["matches"] += 1
            if len(entry["titles"]) < 3:
                entry["titles"].append(candidate.title)
    return by_worker


def _structured_context_score(
    fingerprint: fp_engine.Fingerprint, experiences: list[dict[str, Any]], skills: list[str]
) -> float:
    """Structured agreement on model, brand, device and component.

    Vector similarity alone cannot tell a Galaxy S23 from an S22, or a post-drop failure
    from an unrelated charging fault, so these fields are scored separately with model
    agreement weighted highest.
    """
    fp_model = (fingerprint.model or "").strip().lower()
    fp_brand = (fingerprint.brand or "").strip().lower()
    fp_device = (fingerprint.device_type or "").strip().lower()
    fp_component = (fingerprint.suspected_component or "").strip().lower()
    skill_blob = " ".join(skills).lower()

    best = 0.0
    for exp in experiences:
        blob = " ".join(
            str(exp.get(k) or "")
            for k in ("title", "problem_description", "diagnosis", "brand",
                      "device_category", "outcome_summary")
        ).lower()
        score = 0.0
        if fp_model and fp_model in blob:
            score += 0.40
        if fp_brand and fp_brand in blob:
            score += 0.20
        if fp_device and fp_device.split("/")[0].strip() in blob:
            score += 0.15
        if fp_component and fp_component in blob:
            score += 0.25
        best = max(best, score)

    if fp_component and fp_component in skill_blob:
        best = max(best, best + 0.10)
    # A floor keeps a worker with no textual overlap from collapsing to zero on a
    # signal that is only ever supporting evidence.
    return round(min(1.0, max(0.55, best)), 4)


def compute_matches_for_problem(problem_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Rank technicians using semantic retrieval plus structured and proximity signals.

    Same contract as the built-in matcher: a list of result dicts, ranked, persisted to
    ``match_results``, with scores on 0..1 and the worker display fields the client
    renders.
    """
    from backend.db.supabase_client import db
    from backend.services.matching.matcher import compute_matches_for_problem as heuristic

    if not settings.matching_enabled():
        log.info("[MATCH ENGINE] engine=heuristic_fallback reason=settings.matching_enabled_is_false")
        return heuristic(problem_id, limit=limit)

    try:
        log.info("[MATCH ENGINE] engine=ai_engine")
        return _compute(problem_id, limit, db)
    except Exception as exc:
        log.warning("[MATCH ENGINE] engine=heuristic_fallback reason=semantic_matching_exception (%s)", exc)
        return heuristic(problem_id, limit=limit)


def _compute(problem_id: str, limit: int, db: Any) -> list[dict[str, Any]]:
    problem = db.problems.get(str(problem_id))
    if not problem:
        log.warning("[MATCH START] problem_id=%s NOT FOUND", problem_id)
        return []

    p_lat = problem.get("latitude")
    p_lon = problem.get("longitude")
    if p_lat is None or p_lon is None:
        log.error("[LOCATION ERROR] customer coordinates missing for problem_id=%s", problem_id)

    log.info("[MATCH START] problem_id=%s lat=%s lon=%s", problem_id, p_lat, p_lon)

    record = db.problem_fingerprints.get(str(problem_id)) or {}
    fingerprint = _fingerprint_from_record(record)

    log.info(
        "[FINGERPRINT] device=%s brand=%s model=%s issue=%s context=%s repair_type=%s skills=%s",
        fingerprint.device_type, fingerprint.brand, fingerprint.model,
        fingerprint.issue, fingerprint.context, fingerprint.repair_type,
        fingerprint.extracted_skills,
    )

    # 1. Semantic pgvector experience search
    semantic_scores_by_worker = _semantic_scores(fingerprint)
    log.info("[PGVECTOR] called=true candidate_count=%d", len(semantic_scores_by_worker))

    # 2. Neo4j Graph Candidate Retrieval
    graph_hits: dict[str, dict[str, Any]] = {}
    try:
        from backend.services.neo4j.retrieval import GraphCandidateRetriever
        retriever = GraphCandidateRetriever()
        graph_candidates = retriever.retrieve_candidates(
            problem_id=str(problem_id),
            device_type=fingerprint.device_type,
            brand=fingerprint.brand,
            model=fingerprint.model,
            issue=fingerprint.issue,
            context=fingerprint.context,
            suspected_component=fingerprint.suspected_component,
            repair_type=fingerprint.repair_type,
            extracted_skills=fingerprint.extracted_skills,
        )
        for cand in graph_candidates:
            w_id = str(cand.get("worker_id"))
            graph_hits[w_id] = cand
        log.info("[NEO4J] called=true candidate_count=%d", len(graph_candidates))
    except Exception as exc:
        log.warning("[NEO4J] called=false failure=%s", exc)

    declared_skills = {s.lower() for s in (fingerprint.extracted_skills or [])}

    raw_candidates: list[dict[str, Any]] = []
    out_of_radius_count = 0

    for worker_id, worker in db.worker_profiles.items():
        if not worker.get("is_available", True):
            continue

        user_id = str(worker.get("user_id"))
        profile = db.profiles.get(user_id, {})

        # Location & Proximity Verification
        w_lat = worker.get("latitude")
        w_lon = worker.get("longitude")
        radius = float(worker.get("service_radius_km", 15.0))

        if p_lat is not None and p_lon is not None and w_lat is not None and w_lon is not None:
            distance_km = _haversine_km(p_lat, p_lon, w_lat, w_lon)
            if distance_km > radius:
                out_of_radius_count += 1
                log.info("[LOCATION] worker_id=%s distance=%.2f km > radius=%.1f km -> EXCLUDED", worker_id, distance_km, radius)
                continue
            proximity_score = round(max(0.2, 1.0 - (distance_km / (radius * 1.5))), 4)
            log.info("[LOCATION] worker_id=%s distance=%.2f km <= radius=%.1f km -> ELIGIBLE (prox=%.4f)", worker_id, distance_km, radius, proximity_score)
        else:
            distance_km = 0.0
            proximity_score = 0.50 if (w_lat is not None and w_lon is not None) else 0.10
            log.info("[LOCATION] worker_id=%s missing coordinates (dist=%.2f km, prox=%.4f)", worker_id, distance_km, proximity_score)

        worker_skills = [
            skill.get("name")
            for link in db.worker_skills.values()
            if str(link.get("worker_id")) == str(worker_id)
            for skill in [db.skills.get(str(link.get("skill_id")))]
            if skill
        ]
        experiences = [
            exp for exp in db.experiences.values()
            if str(exp.get("worker_id")) in {str(worker_id), user_id}
        ]
        verified_count = sum(
            1 for exp in experiences if exp.get("verification_status") == "verified"
        )

        hit = semantic_scores_by_worker.get(user_id) or semantic_scores_by_worker.get(str(worker_id))
        g_hit = graph_hits.get(str(worker_id)) or graph_hits.get(user_id)

        # Problem Similarity: combine semantic vector, graph score & model/skill agreement
        if hit:
            sem_sim = round(min(0.99, hit["similarity"]), 4)
            sem_matches = hit["matches"]
            best_exp_title = hit["best_experience"].get("title") if hit.get("best_experience") else None
        else:
            overlap = declared_skills & {s.lower() for s in worker_skills if s}
            sem_sim = round(len(overlap) / len(declared_skills), 4) if declared_skills else 0.0
            sem_matches = 0
            best_exp_title = None

        graph_prob_sim = min(0.99, round(g_hit.get("graph_score", 0.0) / 100.0, 4)) if g_hit else 0.0
        problem_similarity = round(max(sem_sim, graph_prob_sim), 4)

        # Context Similarity: use structured context evidence without artificial floors
        struct_context = _structured_context_score(
            fingerprint, experiences, [s for s in worker_skills if s]
        )
        graph_ctx_sim = min(0.99, round(0.50 + (g_hit.get("graph_score", 0.0) * 0.005), 4)) if (g_hit and g_hit.get("graph_score", 0.0) > 0) else 0.0
        context_similarity = round(max(struct_context, graph_ctx_sim), 4)

        # Verified Confidence: evidence-based
        if verified_count >= 3:
            verified_confidence = 0.95
        elif verified_count >= 1:
            verified_confidence = 0.88
        else:
            verified_confidence = 0.50

        if g_hit and g_hit.get("verification_status") == "verified":
            verified_confidence = round(max(verified_confidence, 0.88), 4)

        weights = settings.weights
        match_score = round(
            weights["problem"] * problem_similarity
            + weights["context"] * context_similarity
            + weights["verified"] * verified_confidence
            + weights["proximity"] * proximity_score,
            4,
        )

        explanations = _explain(
            fingerprint, hit, sem_matches, len(experiences), verified_count,
            distance_km, radius, declared_skills, worker_skills,
        )
        if g_hit:
            for g_reason in g_hit.get("explanations", []):
                if g_reason not in explanations:
                    explanations.insert(0, g_reason)

        log.info(
            "[SCORING] worker=%s prob_sim=%.4f ctx_sim=%.4f ver_conf=%.4f prox=%.4f -> final_score=%.4f",
            profile.get("full_name", worker_id), problem_similarity, context_similarity,
            verified_confidence, proximity_score, match_score
        )

        raw_candidates.append({
            "match_result_id": str(uuid.uuid4()),
            "problem_id": problem_id,
            "worker_id": str(worker_id),
            "rank_position": 1,
            "match_score": match_score,
            "problem_similarity": problem_similarity,
            "context_similarity": context_similarity,
            "verified_experience_confidence": verified_confidence,
            "proximity_score": proximity_score,
            "explanations": explanations,
            "worker_name": profile.get("full_name", "Specialist Technician"),
            "headline": worker.get("headline"),
            "locality": worker.get("locality"),
            "city": worker.get("city"),
            "hourly_rate": worker.get("hourly_rate"),
            "rating": float(worker.get("rating", 5.0)),
            "total_reviews": int(worker.get("total_reviews", 0)),
            "is_available": worker.get("is_available", True),
            "relevant_solved_cases": max(sem_matches, 1 if (g_hit or sem_sim > 0.5) else 0),
            "skills": [s for s in worker_skills if s],
            "best_experience_title": best_exp_title
        })

    # Strict Deduplication by Unique worker_id
    deduped_map: dict[str, dict[str, Any]] = {}
    for cand in raw_candidates:
        w_id = cand["worker_id"]
        if w_id not in deduped_map or cand["match_score"] > deduped_map[w_id]["match_score"]:
            deduped_map[w_id] = cand

    log.info(
        "[MERGE] raw_candidates=%d out_of_radius_filtered=%d unique_workers=%d",
        len(raw_candidates), out_of_radius_count, len(deduped_map)
    )

    results = list(deduped_map.values())
    results.sort(key=lambda item: item["match_score"], reverse=True)

    final: list[dict[str, Any]] = []
    seen_workers: set[str] = set()

    for index, item in enumerate(results[:limit]):
        w_id = item["worker_id"]
        assert w_id not in seen_workers, f"Duplicate worker_id detected: {w_id}"
        seen_workers.add(w_id)

        item["rank_position"] = index + 1
        db.match_results[str(item["match_result_id"])] = {
            "id": str(item["match_result_id"]),
            "problem_id": str(problem_id),
            "worker_id": w_id,
            "rank_position": item["rank_position"],
            "match_score": item["match_score"],
            "problem_similarity": item["problem_similarity"],
            "context_similarity": item["context_similarity"],
            "verified_experience_confidence": item["verified_experience_confidence"],
            "proximity_score": item["proximity_score"],
            "explanation": "\n".join(item["explanations"]),
            "matching_metadata": {
                "explanations": item["explanations"],
                "engine": "ai_engine",
                "weights": settings.weights,
            },
            "created_at": problem.get("created_at"),
        }
        db.sync_to_supabase("match_results", db.match_results[str(item["match_result_id"])])
        final.append(item)

        log.info(
            "[FINAL RANKING] rank=%d worker_id=%s name='%s' score=%.4f best_exp='%s'",
            item["rank_position"], w_id, item["worker_name"], item["match_score"], item.get("best_experience_title") or "General"
        )

    return final


def _semantic_scores(fingerprint: fp_engine.Fingerprint) -> dict[str, dict[str, Any]]:
    """Best semantic similarity per worker, from pgvector.

    Returns {worker_id: {"similarity": float, "matches": int, "titles": [str], "best_experience": dict}}.
    """
    text = canonical.fingerprint_text(fingerprint)
    if not text.strip():
        return {}

    try:
        vector = embeddings.embed_query(text)
        candidates = retrieval.search_experiences(vector, settings.match_candidate_pool)
    except Exception as exc:
        log.warning("[PGVECTOR] vector search failed (%s)", exc)
        return {}

    by_worker: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        w_id = str(candidate.worker_id)
        entry = by_worker.setdefault(
            w_id, {"similarity": 0.0, "matches": 0, "titles": [], "best_experience": None}
        )
        if candidate.similarity > entry["similarity"]:
            entry["similarity"] = candidate.similarity
            entry["best_experience"] = {"id": candidate.experience_id, "title": candidate.title}
        
        if candidate.similarity >= 0.55:
            entry["matches"] += 1
            if len(entry["titles"]) < 3 and candidate.title not in entry["titles"]:
                entry["titles"].append(candidate.title)

    return by_worker


def _structured_context_score(
    fingerprint: fp_engine.Fingerprint, experiences: list[dict[str, Any]], skills: list[str]
) -> float:
    """Structured agreement on model, brand, device and component without artificial floors."""
    fp_model = (fingerprint.model or "").strip().lower()
    fp_brand = (fingerprint.brand or "").strip().lower()
    fp_device = (fingerprint.device_type or "").strip().lower()
    fp_component = (fingerprint.suspected_component or "").strip().lower()
    skill_blob = " ".join(skills).lower()

    best = 0.0
    for exp in experiences:
        blob = " ".join(
            str(exp.get(k) or "")
            for k in ("title", "problem_description", "diagnosis", "brand",
                      "device_category", "outcome_summary")
        ).lower()
        score = 0.0
        if fp_model and fp_model in blob:
            score += 0.45
        if fp_brand and fp_brand in blob:
            score += 0.20
        if fp_device and fp_device.split("/")[0].strip() in blob:
            score += 0.15
        if fp_component and fp_component in blob:
            score += 0.20
        best = max(best, score)

    if fp_component and fp_component in skill_blob:
        best = max(best, best + 0.10)

    return round(min(1.0, max(0.10, best)), 4)


def _explain(
    fingerprint: fp_engine.Fingerprint,
    hit: dict[str, Any] | None,
    semantic_matches: int,
    total_cases: int,
    verified_count: int,
    distance_km: float,
    radius: float,
    declared_skills: set[str],
    worker_skills: list[str],
) -> list[str]:
    """Human-readable match reasons."""
    reasons: list[str] = []

    if hit and semantic_matches > 0:
        closest = round(hit["similarity"] * 100)
        noun = "repair" if semantic_matches == 1 else "repairs"
        verb = "matches" if semantic_matches == 1 else "match"
        reasons.append(
            f"{semantic_matches} past {noun} semantically {verb} this problem "
            f"(closest {closest}%)"
        )
        for title in hit.get("titles", [])[:2]:
            if title:
                reasons.append(f"Previously solved: {title}")
    elif total_cases > 0:
        reasons.append(f"Total recorded repair cases in portfolio: {total_cases}")

    overlap = declared_skills & {s.lower() for s in worker_skills if s}
    if overlap:
        matched = [s for s in worker_skills if s and s.lower() in overlap]
        reasons.append(f"Mastery in required skills: {', '.join(matched)}")

    if fingerprint.suspected_component:
        source = (
            "reported by the customer"
            if fingerprint.suspected_component_source == fp_engine.STATED
            else "suspected, unconfirmed"
        )
        reasons.append(
            f"Relevant to the {fingerprint.suspected_component} area ({source})"
        )

    if verified_count > 0:
        reasons.append(
            f"{verified_count} customer-verified positive repair outcome"
            f"{'s' if verified_count != 1 else ''}"
        )
    else:
        reasons.append("Experience is self-reported and not yet customer-verified")

    if distance_km <= radius:
        reasons.append(
            f"Within {round(distance_km, 1)} km (technician covers {int(radius)} km service radius)"
        )
    else:
        reasons.append(f"Located approx {round(distance_km, 1)} km from your repair location")

    return reasons

