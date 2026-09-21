from unittest.mock import MagicMock, patch
import pytest
from backend.db.supabase_client import db
from backend.services.matching.matcher import compute_matches_for_problem as builtin_matcher
from backend.services.ai_engine.adapters import compute_matches_for_problem as engine_matcher


@pytest.fixture(autouse=True)
def setup_seed_data():
    """Ensure standard seed problem exists in db for testing."""
    prob_id = "test-prob-p10"
    db.problems[prob_id] = {
        "id": prob_id,
        "customer_id": "cust-001",
        "title": "Samsung Galaxy S23 No Power",
        "description": "Phone dropped, completely dead, 0mA current",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "status": "open",
    }
    db.problem_fingerprints[prob_id] = {
        "id": prob_id,
        "problem_id": prob_id,
        "brand": "Samsung",
        "model": "Galaxy S23",
        "device_type": "Smartphone",
        "issue": "Short Circuit / PMIC Failure",
        "context": {"items": ["Physical drop / impact"]},
        "extracted_skills": ["Board-Level Soldering", "Micro-Soldering"],
    }
    yield
    db.problems.pop(prob_id, None)
    db.problem_fingerprints.pop(prob_id, None)


# -----------------------------------------------------------------------------
# A. Normal hybrid matching with Neo4j candidates
# -----------------------------------------------------------------------------
def test_normal_hybrid_matching_with_neo4j_candidates(monkeypatch):
    mock_retriever = MagicMock()
    mock_retriever.retrieve_candidates.return_value = [
        {
            "worker_id": "81280d57-947f-490c-825a-c2c6b8d3cc3c",
            "worker_name": "Ramesh Verma",
            "experience_id": "exp-101",
            "experience_title": "Samsung Galaxy S23 Power Rail Short Circuit Repair",
            "verification_status": "verified",
            "matched_device": {"brand": "Samsung", "model": "Galaxy S23"},
            "matched_issue": "Short Circuit / PMIC Failure",
            "matched_context": ["Physical drop / impact"],
            "matched_skills": ["Micro-Soldering"],
            "graph_score": 100.0,
            "explanations": ["Exact model match: Galaxy S23", "Matched issue: Short Circuit / PMIC Failure"],
        }
    ]

    with patch("backend.services.neo4j.retrieval.GraphCandidateRetriever", return_value=mock_retriever):
        matches = builtin_matcher("test-prob-p10", limit=5)
        assert len(matches) > 0
        top = matches[0]
        assert top["worker_id"] == "81280d57-947f-490c-825a-c2c6b8d3cc3c"
        assert any("Exact model match: Galaxy S23" in exp for exp in top["explanations"])


# -----------------------------------------------------------------------------
# B. Neo4j candidate overlaps with pgvector candidate
# -----------------------------------------------------------------------------
def test_neo4j_candidate_overlaps_with_pgvector(monkeypatch):
    mock_retriever = MagicMock()
    mock_retriever.retrieve_candidates.return_value = [
        {
            "worker_id": "81280d57-947f-490c-825a-c2c6b8d3cc3c",
            "worker_name": "Ramesh Verma",
            "verification_status": "verified",
            "graph_score": 90.0,
            "explanations": ["Matched issue: Short Circuit / PMIC Failure"],
        }
    ]

    with patch("backend.services.neo4j.retrieval.GraphCandidateRetriever", return_value=mock_retriever):
        matches = engine_matcher("test-prob-p10", limit=5)
        # Ensure worker is returned ONCE without duplication
        worker_ids = [m["worker_id"] for m in matches]
        assert len(worker_ids) == len(set(worker_ids))
        assert "81280d57-947f-490c-825a-c2c6b8d3cc3c" in worker_ids


# -----------------------------------------------------------------------------
# C. Neo4j returns a worker not returned by pgvector / local top hit
# -----------------------------------------------------------------------------
def test_neo4j_returns_additional_worker(monkeypatch):
    mock_retriever = MagicMock()
    mock_retriever.retrieve_candidates.return_value = [
        {
            "worker_id": "9bfe05be-8fe9-463f-862e-a3b7c44563c1",
            "worker_name": "Suresh Kumar",
            "verification_status": "submitted",
            "graph_score": 80.0,
            "explanations": ["Matched skills: Home Appliance Wiring"],
        }
    ]

    with patch("backend.services.neo4j.retrieval.GraphCandidateRetriever", return_value=mock_retriever):
        matches = engine_matcher("test-prob-p10", limit=5)
        worker_ids = [m["worker_id"] for m in matches]
        assert "9bfe05be-8fe9-463f-862e-a3b7c44563c1" in worker_ids


# -----------------------------------------------------------------------------
# D. Neo4j unavailable -> existing matcher still works
# -----------------------------------------------------------------------------
def test_neo4j_unavailable_fallback(monkeypatch):
    mock_retriever = MagicMock()
    mock_retriever.retrieve_candidates.side_effect = RuntimeError("Neo4j Aura connection timeout")

    with patch("backend.services.neo4j.retrieval.GraphCandidateRetriever", return_value=mock_retriever):
        matches = builtin_matcher("test-prob-p10", limit=5)
        assert len(matches) > 0
        assert matches[0]["match_score"] > 0


# -----------------------------------------------------------------------------
# E. No Neo4j candidates -> existing matcher still works
# -----------------------------------------------------------------------------
def test_no_neo4j_candidates(monkeypatch):
    mock_retriever = MagicMock()
    mock_retriever.retrieve_candidates.return_value = []

    with patch("backend.services.neo4j.retrieval.GraphCandidateRetriever", return_value=mock_retriever):
        matches = engine_matcher("test-prob-p10", limit=5)
        assert len(matches) > 0


# -----------------------------------------------------------------------------
# F. Missing / partial fingerprint
# -----------------------------------------------------------------------------
def test_missing_or_partial_fingerprint(monkeypatch):
    prob_no_fp = "test-prob-no-fp"
    db.problems[prob_no_fp] = {
        "id": prob_no_fp,
        "customer_id": "cust-001",
        "title": "Basic Electrical Repair",
        "description": "Switchboard sparking",
        "latitude": 19.0760,
        "longitude": 72.8777,
    }
    try:
        mock_retriever = MagicMock()
        mock_retriever.retrieve_candidates.return_value = []

        with patch("backend.services.neo4j.retrieval.GraphCandidateRetriever", return_value=mock_retriever):
            matches = builtin_matcher(prob_no_fp, limit=5)
            assert len(matches) > 0
    finally:
        db.problems.pop(prob_no_fp, None)


# -----------------------------------------------------------------------------
# G. Verified experience contributes to the correct trust signal
# -----------------------------------------------------------------------------
def test_verified_experience_contributes_to_trust_signal(monkeypatch):
    mock_retriever = MagicMock()
    mock_retriever.retrieve_candidates.return_value = [
        {
            "worker_id": "81280d57-947f-490c-825a-c2c6b8d3cc3c",
            "worker_name": "Ramesh Verma",
            "verification_status": "verified",
            "graph_score": 60.0,
            "explanations": ["Verified experience in graph"],
        }
    ]

    with patch("backend.services.neo4j.retrieval.GraphCandidateRetriever", return_value=mock_retriever):
        matches = builtin_matcher("test-prob-p10", limit=5)
        target = next(m for m in matches if m["worker_id"] == "81280d57-947f-490c-825a-c2c6b8d3cc3c")
        assert target["verified_experience_confidence"] >= 0.88


# -----------------------------------------------------------------------------
# H. Match explanations contain graph evidence when available
# -----------------------------------------------------------------------------
def test_match_explanations_contain_graph_evidence(monkeypatch):
    mock_retriever = MagicMock()
    mock_retriever.retrieve_candidates.return_value = [
        {
            "worker_id": "81280d57-947f-490c-825a-c2c6b8d3cc3c",
            "worker_name": "Ramesh Verma",
            "verification_status": "verified",
            "graph_score": 100.0,
            "explanations": ["Exact model match: Galaxy S23", "Matched context: Physical drop / impact"],
        }
    ]

    with patch("backend.services.neo4j.retrieval.GraphCandidateRetriever", return_value=mock_retriever):
        matches = engine_matcher("test-prob-p10", limit=5)
        target = next(m for m in matches if m["worker_id"] == "81280d57-947f-490c-825a-c2c6b8d3cc3c")
        assert "Exact model match: Galaxy S23" in target["explanations"]
        assert "Matched context: Physical drop / impact" in target["explanations"]
