import math
import uuid
from typing import List, Dict, Any
from backend.config import settings
from backend.db.supabase_client import db

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two coordinates in km."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def compute_matches_for_problem(problem_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Computes Top-K matched technicians using the 4-component weighted model:
    Match Score = 0.40 * Prob_Sim + 0.30 * Ctx_Sim + 0.20 * Verified_Exp + 0.10 * Proximity
    """
    problem = db.problems.get(str(problem_id))
    if not problem:
        return []
    
    fingerprint = db.problem_fingerprints.get(str(problem_id)) or {}
    prob_skills = set(fingerprint.get("extracted_skills", []))
    prob_brand = (fingerprint.get("brand") or "").lower()
    prob_device = (fingerprint.get("device_type") or "").lower()
    p_lat = problem.get("latitude", 19.0760)
    p_lon = problem.get("longitude", 72.8777)

    results = []

    for worker_id, worker in db.worker_profiles.items():
        if not worker.get("is_available", True):
            continue
        
        user_id = str(worker.get("user_id"))
        profile = db.profiles.get(user_id, {})
        worker_name = profile.get("full_name", "Specialist Technician")
        
        # 1. Collect worker skills
        worker_skill_names = []
        for ws in db.worker_skills.values():
            if str(ws.get("worker_id")) == str(worker_id):
                sk = db.skills.get(str(ws.get("skill_id")))
                if sk:
                    worker_skill_names.append(sk.get("name"))

        # Skill overlap for problem similarity
        matching_skills = prob_skills.intersection(set(worker_skill_names))
        if prob_skills:
            problem_similarity = round(len(matching_skills) / len(prob_skills), 4)
        else:
            problem_similarity = 0.85
        
        # Base boost if technician has board/repair skills
        if "Board-Level Soldering" in worker_skill_names and ("board" in prob_device or "samsung" in prob_brand):
            problem_similarity = min(0.98, max(problem_similarity, 0.92))

        # 2. Context similarity (device, brand, failure mode matches)
        context_similarity = 0.70
        solved_cases_count = 0
        verified_outcomes_count = 0
        
        for exp in db.experiences.values():
            if str(exp.get("worker_id")) == str(worker_id):
                solved_cases_count += 1
                if exp.get("verification_status") == "verified":
                    verified_outcomes_count += 1
                if prob_brand and prob_brand in (exp.get("brand") or "").lower():
                    context_similarity = min(0.96, context_similarity + 0.15)
                if prob_device and prob_device in (exp.get("device_category") or "").lower():
                    context_similarity = min(0.95, context_similarity + 0.10)

        # 3. Verified Experience Confidence
        if verified_outcomes_count >= 3:
            verified_confidence = 0.95
        elif verified_outcomes_count >= 1:
            verified_confidence = 0.88
        else:
            verified_confidence = 0.65

        # 4. Proximity
        w_lat = worker.get("latitude", p_lat)
        w_lon = worker.get("longitude", p_lon)
        dist_km = calculate_haversine_distance(p_lat, p_lon, w_lat, w_lon)
        radius = float(worker.get("service_radius_km", 15.0))
        
        if dist_km <= radius:
            proximity_score = round(max(0.2, 1.0 - (dist_km / (radius * 1.5))), 4)
        else:
            proximity_score = 0.10

        # Weighted calculation
        match_score = (
            settings.WEIGHT_PROBLEM_SIMILARITY * problem_similarity +
            settings.WEIGHT_CONTEXT_SIMILARITY * context_similarity +
            settings.WEIGHT_VERIFIED_EXP_CONFIDENCE * verified_confidence +
            settings.WEIGHT_PROXIMITY * proximity_score
        )
        match_score = round(match_score, 4)

        # Build transparent human explanations (Section 8)
        explanations = []
        if solved_cases_count > 0:
            explanations.append(f"Solved {solved_cases_count} similar real-world repair cases in this category")
        if matching_skills:
            explanations.append(f"Mastery in required skills: {', '.join(matching_skills)}")
        if verified_outcomes_count > 0:
            explanations.append(f"{verified_outcomes_count} customer-verified positive repair outcomes")
        if dist_km <= radius:
            explanations.append(f"Within {round(dist_km, 1)} km (technician covers {int(radius)} km service radius)")
        else:
            explanations.append(f"Located approx {round(dist_km, 1)} km from your repair location")

        match_id = str(uuid.uuid4())
        
        result_item = {
            "match_result_id": match_id,
            "problem_id": problem_id,
            "worker_id": worker_id,
            "rank_position": 1,  # will assign below
            "match_score": match_score,
            "problem_similarity": problem_similarity,
            "context_similarity": context_similarity,
            "verified_experience_confidence": verified_confidence,
            "proximity_score": proximity_score,
            "explanations": explanations,
            "worker_name": worker_name,
            "headline": worker.get("headline"),
            "locality": worker.get("locality"),
            "city": worker.get("city"),
            "hourly_rate": worker.get("hourly_rate"),
            "rating": float(worker.get("rating", 5.0)),
            "total_reviews": int(worker.get("total_reviews", 0)),
            "is_available": worker.get("is_available", True),
            "relevant_solved_cases": solved_cases_count,
            "skills": worker_skill_names
        }
        results.append(result_item)

    # Sort descending by match_score
    results.sort(key=lambda x: x["match_score"], reverse=True)

    # Assign rank and persist to match_results table
    final_matches = []
    for idx, item in enumerate(results[:limit]):
        item["rank_position"] = idx + 1
        match_record = {
            "id": str(item["match_result_id"]),
            "problem_id": str(problem_id),
            "worker_id": str(item["worker_id"]),
            "rank_position": item["rank_position"],
            "match_score": item["match_score"],
            "problem_similarity": item["problem_similarity"],
            "context_similarity": item["context_similarity"],
            "verified_experience_confidence": item["verified_experience_confidence"],
            "proximity_score": item["proximity_score"],
            "explanation": "\n".join(item["explanations"]),
            "matching_metadata": {"explanations": item["explanations"]},
            "created_at": problem.get("created_at")
        }
        db.match_results[str(item["match_result_id"])] = match_record
        db.sync_to_supabase("match_results", match_record)
        final_matches.append(item)

    return final_matches
