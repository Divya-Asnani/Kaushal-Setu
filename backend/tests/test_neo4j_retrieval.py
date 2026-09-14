from unittest.mock import MagicMock
import pytest
from backend.services.neo4j.retrieval import GraphCandidateRetriever


def build_mock_response(keys, values):
    return {
        "data": {
            "keys": keys,
            "values": values,
        }
    }


@pytest.fixture
def mock_client():
    return MagicMock()


def test_exact_model_issue_context_match(mock_client):
    keys = [
        "worker_id", "user_id", "worker_name", "rating", "worker_verified",
        "experience_id", "experience_title", "verification_status",
        "exp_brand", "exp_model", "exp_device_type", "dev_brand", "dev_model",
        "dev_category", "issue_name", "context_names", "skill_names"
    ]
    values = [
        [
            "w-001", "u-001", "Ramesh Verma", 4.9, True,
            "exp-101", "Samsung S23 PMIC Repair", "verified",
            "Samsung", "Galaxy S23", "Smartphone", "Samsung", "Galaxy S23",
            "Smartphone", "Short Circuit / PMIC Failure",
            ["Physical drop / impact"], ["Board-Level Soldering", "Micro-Soldering"]
        ]
    ]

    mock_client.execute.return_value = build_mock_response(keys, values)
    retriever = GraphCandidateRetriever(client=mock_client)

    results = retriever.retrieve_candidates(
        brand="Samsung",
        model="Galaxy S23",
        issue="Short Circuit / PMIC Failure",
        context={"items": ["Physical drop / impact"]},
        extracted_skills=["Micro-Soldering"]
    )

    assert len(results) == 1
    cand = results[0]
    assert cand["worker_id"] == "w-001"
    assert cand["worker_name"] == "Ramesh Verma"
    assert cand["verification_status"] == "verified"
    # Score calculation: 40 (model) + 20 (brand) + 20 (issue) + 10 (context) + 10 (skill) = 100.0
    assert cand["graph_score"] == 100.0
    assert "Exact model match: Galaxy S23" in cand["explanations"]


def test_partial_match(mock_client):
    keys = [
        "worker_id", "user_id", "worker_name", "rating", "worker_verified",
        "experience_id", "experience_title", "verification_status",
        "exp_brand", "exp_model", "exp_device_type", "dev_brand", "dev_model",
        "dev_category", "issue_name", "context_names", "skill_names"
    ]
    values = [
        [
            "w-002", "u-002", "Suresh Kumar", 4.7, False,
            "exp-202", "Generic Inverter Repair", "submitted",
            "Luminous", "Zelio 1100", "Inverter", "Luminous", "Zelio 1100",
            "Inverter", "Overload Alarm",
            ["Overload condition"], ["Home Appliance Wiring"]
        ]
    ]

    mock_client.execute.return_value = build_mock_response(keys, values)
    retriever = GraphCandidateRetriever(client=mock_client)

    # Search for different model (Zelio 1500) but matching brand (Luminous) and issue
    results = retriever.retrieve_candidates(
        brand="Luminous",
        model="Zelio 1500",
        issue="Overload Alarm",
        context=None,
        extracted_skills=None
    )

    assert len(results) == 1
    cand = results[0]
    assert cand["worker_id"] == "w-002"
    # Score calculation: 0 (model mismatch) + 20 (brand) + 20 (issue) = 40.0
    assert cand["graph_score"] == 40.0


def test_missing_fingerprint_fields(mock_client):
    keys = [
        "worker_id", "user_id", "worker_name", "rating", "worker_verified",
        "experience_id", "experience_title", "verification_status",
        "exp_brand", "exp_model", "exp_device_type", "dev_brand", "dev_model",
        "dev_category", "issue_name", "context_names", "skill_names"
    ]
    values = [
        [
            "w-001", "u-001", "Ramesh Verma", 4.9, True,
            "exp-101", "General Repair", "verified",
            None, None, None, None, None,
            None, None,
            [], ["Board-Level Soldering"]
        ]
    ]

    mock_client.execute.return_value = build_mock_response(keys, values)
    retriever = GraphCandidateRetriever(client=mock_client)

    # All search parameters are None / missing
    results = retriever.retrieve_candidates(
        problem_id="p-123",
        brand=None,
        model=None,
        issue=None,
        context=None,
        extracted_skills=None
    )

    assert len(results) == 1
    cand = results[0]
    assert cand["graph_score"] == 0.0
    assert cand["worker_id"] == "w-001"


def test_verified_vs_unverified_experience(mock_client):
    keys = [
        "worker_id", "user_id", "worker_name", "rating", "worker_verified",
        "experience_id", "experience_title", "verification_status",
        "exp_brand", "exp_model", "exp_device_type", "dev_brand", "dev_model",
        "dev_category", "issue_name", "context_names", "skill_names"
    ]
    values = [
        [
            "w-001", "u-001", "Ramesh Verma", 4.9, True,
            "exp-101", "Verified Samsung Repair", "verified",
            "Samsung", "Galaxy S23", "Smartphone", "Samsung", "Galaxy S23",
            "Smartphone", "PMIC Failure", [], []
        ],
        [
            "w-002", "u-002", "Suresh Kumar", 4.5, False,
            "exp-102", "Unverified Repair", "submitted",
            "Samsung", "Galaxy S23", "Smartphone", "Samsung", "Galaxy S23",
            "Smartphone", "PMIC Failure", [], []
        ]
    ]

    mock_client.execute.return_value = build_mock_response(keys, values)
    retriever = GraphCandidateRetriever(client=mock_client)

    results = retriever.retrieve_candidates(
        brand="Samsung",
        model="Galaxy S23",
        issue="PMIC Failure"
    )

    assert len(results) == 2
    # Both get graph score 60.0 (40 model + 20 brand), but verification_status remains accurate
    cand_verified = next(c for c in results if c["worker_id"] == "w-001")
    cand_unverified = next(c for c in results if c["worker_id"] == "w-002")

    assert cand_verified["verification_status"] == "verified"
    assert cand_unverified["verification_status"] == "submitted"
    assert cand_verified["graph_score"] == cand_unverified["graph_score"]


def test_no_candidates(mock_client):
    mock_client.execute.return_value = build_mock_response([], [])
    retriever = GraphCandidateRetriever(client=mock_client)

    results = retriever.retrieve_candidates(
        brand="NonExistentBrand",
        model="UnknownModel"
    )

    assert results == []
