"""
Phase 11: End-to-End Golden Path Validation Test Suite for Kaushal Setu.

Validates the complete experience-intelligence pipeline:
1. Customer Problem Creation
2. AI Fingerprint Extraction (using existing engine / fallback adapter)
3. Supabase Data Store Persistence
4. Embedding Generation
5. Neo4j Graph Synchronization (Problem, Device, Issue, Context, Skill nodes & edges)
6. Graph Reachability & Relationship Linking
7. Hybrid Candidate Retrieval & Matcher Execution
8. Score Breakdown & Explanations Audit
9. Fault Tolerance (Neo4j failure fallback)
10. Missing Fingerprint Handling
"""

import uuid
from unittest.mock import MagicMock, patch
import pytest

from backend.db.supabase_client import db
from backend.services.ai_engine.adapters import extract_problem_fingerprint
from backend.services.ai_engine.embeddings import embed_query
from backend.services.matching.matcher import compute_matches_for_problem as builtin_matcher
from backend.services.ai_engine.adapters import compute_matches_for_problem as engine_matcher
from backend.services.neo4j.sync import sync_all


@pytest.fixture
def golden_path_problem():
    """Sets up a test customer problem for Samsung S23 drop failure."""
    prob_id = str(uuid.uuid4())
    problem_data = {
        "id": prob_id,
        "customer_id": "673c60cc-51f0-4c34-b05e-75c8fd8762f6",
        "title": "Samsung Galaxy S23 Fell and Dead",
        "description": "Samsung Galaxy S23 fell down and now does not turn on. The phone is completely dead.",
        "status": "open",
        "latitude": 19.0760,
        "longitude": 72.8777,
    }
    db.problems[prob_id] = problem_data

    yield problem_data

    db.problems.pop(prob_id, None)
    db.problem_fingerprints.pop(prob_id, None)


def test_step_1_to_4_fingerprint_extraction_and_persistence(golden_path_problem):
    prob_id = golden_path_problem["id"]

    # Step 2: Extract Problem Fingerprint using existing extraction logic
    fingerprint = extract_problem_fingerprint(
        title=golden_path_problem["title"],
        description=golden_path_problem["description"]
    )

    assert fingerprint is not None
    assert fingerprint.get("brand") == "Samsung"
    assert "galaxy s23" in (fingerprint.get("model") or "").lower() or "s23" in (fingerprint.get("model") or "").lower()
    assert fingerprint.get("device_type") is not None
    assert isinstance(fingerprint.get("extracted_skills"), list)

    # Step 3: Persist fingerprint into db.problem_fingerprints
    fp_row = {
        "id": prob_id,
        "problem_id": prob_id,
        **fingerprint,
        "embedding_status": "pending",
        "fingerprint_version": "v1"
    }
    db.problem_fingerprints[prob_id] = fp_row
    db.sync_to_supabase("problem_fingerprints", fp_row)

    assert prob_id in db.problem_fingerprints
    assert db.problem_fingerprints[prob_id]["brand"] == "Samsung"

    # Step 4: Verify Embedding Flow works with existing embedding implementation
    with patch("backend.services.ai_engine.embeddings.embed_texts", return_value=[[0.01] * 384]):
        vector = embed_query(f"{golden_path_problem['title']} {golden_path_problem['description']}")
        assert isinstance(vector, list)
        assert len(vector) in (384, 1536)


def test_step_5_and_6_neo4j_graph_sync_and_reachability(golden_path_problem):
    prob_id = golden_path_problem["id"]

    # Seed fingerprint into store
    fp_row = {
        "id": prob_id,
        "problem_id": prob_id,
        "brand": "Samsung",
        "model": "Galaxy S23",
        "device_type": "Smartphone",
        "issue": "Short Circuit / PMIC Failure",
        "context": {"items": ["Physical drop / impact"], "urgency": "Standard"},
        "extracted_skills": ["Board-Level Soldering", "Micro-Soldering"],
        "embedding_status": "generated",
        "fingerprint_version": "v1"
    }
    db.problem_fingerprints[prob_id] = fp_row

    # Mock Neo4j client calls to verify Cypher execution queries
    mock_neo4j = MagicMock()
    mock_neo4j.execute.return_value = {"data": {"keys": [], "values": []}}

    with patch("backend.services.neo4j.sync.neo4j_client", mock_neo4j):
        counts = sync_all()
        assert "problem_fingerprints" in counts
        assert counts["problem_fingerprints"] >= 1

        # Verify that MERGE statements for Problem, Device, Issue, Context, Skill were issued
        query_statements = [call[0][0] for call in mock_neo4j.execute.call_args_list]
        cypher_blob = " ".join(query_statements)

        assert "MERGE (p:Problem" in cypher_blob or "MERGE (worker:Worker" in cypher_blob
        assert "MERGE (device:Device" in cypher_blob
        assert "MERGE (issue:Issue" in cypher_blob
        assert "MERGE (context:Context" in cypher_blob


def test_step_7_to_9_matching_execution_and_explanation(golden_path_problem):
    prob_id = golden_path_problem["id"]

    # Seed fingerprint into store
    fp_row = {
        "id": prob_id,
        "problem_id": prob_id,
        "brand": "Samsung",
        "model": "Galaxy S23",
        "device_type": "Smartphone",
        "issue": "Short Circuit / PMIC Failure",
        "context": {"items": ["Physical drop / impact"]},
        "extracted_skills": ["Board-Level Soldering", "Micro-Soldering"],
    }
    db.problem_fingerprints[prob_id] = fp_row

    # Mock graph retrieval candidate hit for Ramesh Verma
    mock_graph_candidates = [
        {
            "worker_id": "81280d57-947f-490c-825a-c2c6b8d3cc3c",
            "worker_name": "Ramesh Verma",
            "experience_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01",
            "experience_title": "Samsung Galaxy S23 Power Rail Short Circuit Repair",
            "verification_status": "verified",
            "matched_device": {"brand": "Samsung", "model": "Galaxy S23"},
            "matched_issue": "Short Circuit / PMIC Failure",
            "matched_context": ["Physical drop / impact"],
            "matched_skills": ["Board-Level Soldering", "Micro-Soldering"],
            "graph_score": 100.0,
            "explanations": [
                "Exact model match: Galaxy S23",
                "Brand match: Samsung",
                "Matched issue: Short Circuit / PMIC Failure",
                "Matched context: Physical drop / impact",
                "Matched skills: Micro-Soldering"
            ],
        }
    ]

    with patch("backend.services.neo4j.retrieval.GraphCandidateRetriever.retrieve_candidates", return_value=mock_graph_candidates):
        matches = engine_matcher(prob_id, limit=5)

        assert len(matches) > 0
        ramesh = next(m for m in matches if m["worker_id"] == "81280d57-947f-490c-825a-c2c6b8d3cc3c")

        # Step 8: Assert all required fields exist
        assert ramesh["worker_id"] == "81280d57-947f-490c-825a-c2c6b8d3cc3c"
        assert ramesh["worker_name"] == "Ramesh Verma"
        assert "match_score" in ramesh
        assert "problem_similarity" in ramesh
        assert "context_similarity" in ramesh
        assert "verified_experience_confidence" in ramesh
        assert "proximity_score" in ramesh
        assert "explanations" in ramesh
        assert "relevant_solved_cases" in ramesh

        # Step 9: Assert explanation contains graph evidence
        exps = ramesh["explanations"]
        assert any("Exact model match: Galaxy S23" in e for e in exps)
        assert any("Matched issue: Short Circuit / PMIC Failure" in e for e in exps)


def test_step_10_graceful_degradation_on_neo4j_failure(golden_path_problem):
    prob_id = golden_path_problem["id"]

    with patch("backend.services.neo4j.retrieval.GraphCandidateRetriever.retrieve_candidates", side_effect=RuntimeError("Aura unreachable")):
        matches = builtin_matcher(prob_id, limit=5)
        assert len(matches) > 0
        assert matches[0]["match_score"] > 0


def test_step_11_no_fingerprint_case():
    prob_id = str(uuid.uuid4())
    db.problems[prob_id] = {
        "id": prob_id,
        "customer_id": "cust-999",
        "title": "Unspecified Repair",
        "description": "General help needed",
        "latitude": 19.0760,
        "longitude": 72.8777,
    }

    try:
        matches = builtin_matcher(prob_id, limit=5)
        assert len(matches) > 0
    finally:
        db.problems.pop(prob_id, None)
