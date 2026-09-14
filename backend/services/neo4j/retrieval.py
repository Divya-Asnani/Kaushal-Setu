"""
Graph-based Candidate Retrieval Service for Kaushal Setu.

Uses Neo4j graph relationships to find technicians (Workers) who have solved
experiences or possess skills matching a problem fingerprint.

Source of truth remains PostgreSQL/Supabase.
Graph candidate retrieval provides evidence-backed graph scores to feed into
the hybrid matching engine.
"""

import logging
from typing import Any, Dict, List, Optional
from .client import Neo4jClient, neo4j_client


logger = logging.getLogger("kaushalsetu.neo4j.retrieval")


def _normalize(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip().lower()


class GraphCandidateRetriever:
    """Retrieves worker candidates from Neo4j graph with detailed evidence and scoring."""

    def __init__(self, client: Optional[Neo4jClient] = None) -> None:
        self.client = client or neo4j_client

    def retrieve_candidates(
        self,
        problem_id: Optional[str] = None,
        device_type: Optional[str] = None,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        issue: Optional[str] = None,
        context: Optional[Any] = None,
        suspected_component: Optional[str] = None,
        repair_type: Optional[str] = None,
        extracted_skills: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve candidate workers matching a problem fingerprint from Neo4j.

        Returns a list of candidate dictionaries containing:
        - worker_id (str)
        - worker_name (str)
        - experience_id (str | None)
        - experience_title (str | None)
        - verification_status (str | None)
        - matched_device (dict | None)
        - matched_issue (str | None)
        - matched_context (list[str])
        - matched_skills (list[str])
        - graph_score (float)
        - explanations (list[str])
        """
        # Parse context items robustly
        context_items: List[str] = []
        if isinstance(context, dict):
            raw_c = context.get("items") or []
            if isinstance(raw_c, list):
                context_items = [str(x).strip() for x in raw_c if x and str(x).strip()]
            elif isinstance(raw_c, str) and raw_c.strip():
                context_items = [raw_c.strip()]
        elif isinstance(context, list):
            context_items = [str(x).strip() for x in context if x and str(x).strip()]
        elif isinstance(context, str) and context.strip():
            context_items = [context.strip()]

        # Parse extracted skills robustly
        skills_list: List[str] = []
        if isinstance(extracted_skills, list):
            skills_list = [str(s).strip() for s in extracted_skills if s and str(s).strip()]
        elif isinstance(extracted_skills, str) and extracted_skills.strip():
            skills_list = [extracted_skills.strip()]

        params = {
            "problem_id": problem_id or "",
            "canonical_problem_id": f"problem_{problem_id}" if problem_id and not str(problem_id).startswith("problem_") else (problem_id or ""),
            "device_type": device_type or "",
            "brand": brand or "",
            "model": model or "",
            "issue": issue or "",
            "context_items": context_items,
            "skills": skills_list,
        }

        query = """
        MATCH (w:Worker)
        OPTIONAL MATCH (w)-[:SOLVED]->(e:Experience)
        OPTIONAL MATCH (e)-[:INVOLVES]->(ed:Device)
        OPTIONAL MATCH (e)-[:HAS_ISSUE]->(ei:Issue)
        OPTIONAL MATCH (e)-[:OCCURRED_IN]->(ec:Context)
        OPTIONAL MATCH (e)-[:REQUIRED_SKILL]->(es:Skill)
        OPTIONAL MATCH (w)-[:HAS_SKILL]->(ws:Skill)

        RETURN
            w.id AS worker_id,
            w.user_id AS user_id,
            w.name AS worker_name,
            w.rating AS rating,
            w.is_verified AS worker_verified,
            e.id AS experience_id,
            e.title AS experience_title,
            e.verification_status AS verification_status,
            e.brand AS exp_brand,
            e.model AS exp_model,
            e.device_category AS exp_device_type,
            ed.brand AS dev_brand,
            ed.model AS dev_model,
            ed.category AS dev_category,
            ei.canonical_name AS issue_name,
            COLLECT(DISTINCT ec.name) AS context_names,
            COLLECT(DISTINCT es.name) + COLLECT(DISTINCT ws.name) AS skill_names
        """

        try:
            raw_response = self.client.execute(query, params)
            rows = self._parse_cypher_response(raw_response)
        except Exception as err:
            logger.warning("Neo4j candidate retrieval query failed: %s", err)
            return []

        if not rows:
            return []

        return self._evaluate_candidates(
            rows=rows,
            target_brand=brand,
            target_model=model,
            target_device_type=device_type,
            target_issue=issue,
            target_contexts=context_items,
            target_skills=skills_list,
        )

    def _parse_cypher_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse raw HTTPS Query API response into a list of row dicts."""
        if not response or not isinstance(response, dict):
            return []

        # Standard Cypher REST API format with 'data' -> 'keys'/'columns' and 'values'
        data_block = response.get("data") or {}
        columns = data_block.get("keys") or response.get("columns") or []
        values = data_block.get("values") or response.get("data") or []

        parsed_rows = []
        if columns and values and isinstance(values, list):
            for row_vals in values:
                if isinstance(row_vals, list) and len(row_vals) == len(columns):
                    parsed_rows.append(dict(zip(columns, row_vals)))

        return parsed_rows

    def _evaluate_candidates(
        self,
        rows: List[Dict[str, Any]],
        target_brand: Optional[str],
        target_model: Optional[str],
        target_device_type: Optional[str],
        target_issue: Optional[str],
        target_contexts: List[str],
        target_skills: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Group rows by worker, score matches deterministically, and format evidence.

        Scoring Rules:
        - +40 for exact model match
        - +20 for brand/device match
        - +20 for issue match
        - +10 for context match (if any matched)
        - +10 for skill overlap (if any matched)
        """
        norm_brand = _normalize(target_brand)
        norm_model = _normalize(target_model)
        norm_issue = _normalize(target_issue)
        norm_contexts = {_normalize(c) for c in target_contexts if c}
        norm_skills = {_normalize(s) for s in target_skills if s}

        # Group by worker_id
        candidates_by_worker: Dict[str, Dict[str, Any]] = {}

        for r in rows:
            worker_id = r.get("worker_id")
            if not worker_id:
                continue

            if worker_id not in candidates_by_worker:
                candidates_by_worker[worker_id] = {
                    "worker_id": str(worker_id),
                    "worker_name": r.get("worker_name") or "Specialist Technician",
                    "best_score": 0.0,
                    "best_experience_id": None,
                    "best_experience_title": None,
                    "verification_status": "unverified",
                    "matched_device": None,
                    "matched_issue": None,
                    "matched_context": [],
                    "matched_skills": [],
                    "explanations": [],
                }

            cand = candidates_by_worker[worker_id]

            exp_id = r.get("experience_id")
            exp_title = r.get("experience_title")
            ver_status = r.get("verification_status") or ("verified" if r.get("worker_verified") else "unverified")

            dev_brand = _normalize(r.get("dev_brand") or r.get("exp_brand"))
            dev_model = _normalize(r.get("dev_model") or r.get("exp_model"))
            issue_name = _normalize(r.get("issue_name"))

            row_contexts = [_normalize(c) for c in (r.get("context_names") or []) if c]
            row_skills = [_normalize(s) for s in (r.get("skill_names") or []) if s]

            score = 0.0
            reasons = []
            matched_device_info = None

            # 1. Model match (+40)
            if norm_model and dev_model and norm_model == dev_model:
                score += 40.0
                reasons.append(f"Exact model match: {r.get('dev_model') or r.get('exp_model')}")
                matched_device_info = {
                    "brand": r.get("dev_brand") or r.get("exp_brand"),
                    "model": r.get("dev_model") or r.get("exp_model"),
                }

            # 2. Brand / device match (+20)
            if norm_brand and dev_brand and norm_brand == dev_brand:
                score += 20.0
                if not matched_device_info:
                    reasons.append(f"Brand match: {r.get('dev_brand') or r.get('exp_brand')}")
                    matched_device_info = {
                        "brand": r.get("dev_brand") or r.get("exp_brand"),
                        "model": r.get("dev_model") or r.get("exp_model"),
                    }

            # 3. Issue match (+20)
            matched_issue_val = None
            if norm_issue and issue_name and (norm_issue in issue_name or issue_name in norm_issue):
                score += 20.0
                matched_issue_val = r.get("issue_name")
                reasons.append(f"Matched issue: {matched_issue_val}")

            # 4. Context match (+10)
            ctx_overlap = norm_contexts & set(row_contexts)
            matched_ctx_list = []
            if ctx_overlap:
                score += 10.0
                matched_ctx_list = [c for c in (r.get("context_names") or []) if _normalize(c) in ctx_overlap]
                reasons.append(f"Matched context: {', '.join(matched_ctx_list)}")

            # 5. Skill overlap (+10)
            skill_overlap = norm_skills & set(row_skills)
            matched_sk_list = []
            if skill_overlap:
                score += 10.0
                matched_sk_list = [s for s in (r.get("skill_names") or []) if _normalize(s) in skill_overlap]
                reasons.append(f"Matched skills: {', '.join(matched_sk_list)}")

            # Update best matching experience/score for this candidate worker
            if score > cand["best_score"] or (cand["best_score"] == 0 and exp_id):
                cand["best_score"] = float(score)
                cand["best_experience_id"] = exp_id
                cand["best_experience_title"] = exp_title
                cand["verification_status"] = ver_status
                if matched_device_info:
                    cand["matched_device"] = matched_device_info
                if matched_issue_val:
                    cand["matched_issue"] = matched_issue_val
                if matched_ctx_list:
                    cand["matched_context"] = matched_ctx_list
                if matched_sk_list:
                    cand["matched_skills"] = matched_sk_list
                cand["explanations"] = reasons

        results = []
        for cand in candidates_by_worker.values():
            if cand["best_score"] > 0 or cand["best_experience_id"]:
                results.append({
                    "worker_id": cand["worker_id"],
                    "worker_name": cand["worker_name"],
                    "experience_id": cand["best_experience_id"],
                    "experience_title": cand["best_experience_title"],
                    "verification_status": cand["verification_status"],
                    "matched_device": cand["matched_device"],
                    "matched_issue": cand["matched_issue"],
                    "matched_context": cand["matched_context"],
                    "matched_skills": cand["matched_skills"],
                    "graph_score": cand["best_score"],
                    "explanations": cand["explanations"] or ["Relevant specialty in graph"],
                })

        results.sort(key=lambda item: item["graph_score"], reverse=True)
        return results
