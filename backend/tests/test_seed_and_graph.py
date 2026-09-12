"""The demo seed fixture, and the matching path when Neo4j is available.

The default test run exercises the degraded path with no graph, because that is what
the PRD requires to keep working. These tests cover the other side.
"""
from __future__ import annotations

from backend.services.graph import neo4j_client
from backend.tests.conftest import auth

API = "/api/v1"


# ---------------------------------------------------------------- seed fixture


def test_seed_data_is_internally_consistent():
    """Every skill a seeded worker or experience refers to must be defined."""
    from backend.scripts import seed_demo

    defined = {name for name, _ in seed_demo.SKILLS}
    worker_keys = {w[0] for w in seed_demo.WORKERS}

    for _, _, _, _, _, _, _, skills in seed_demo.WORKERS:
        unknown = set(skills) - defined
        assert not unknown, f"worker refers to undefined skills: {unknown}"

    for entry in seed_demo.EXPERIENCES:
        key, skills = entry[0], entry[8]
        assert key in worker_keys, f"experience refers to unknown worker '{key}'"
        unknown = set(skills) - defined
        assert not unknown, f"experience refers to undefined skills: {unknown}"

    for case in seed_demo.KNOWLEDGE_CASES:
        assert case[0] in worker_keys


def test_seeded_experience_statuses_are_valid():
    """Seeded rows must satisfy the documented CHECK constraints."""
    from backend.scripts import seed_demo
    from backend.tests.fakes import ENUMS, RANGES

    allowed = ENUMS[("experiences", "experience_status")]
    low, high = RANGES[("experiences", "verification_confidence")]
    for entry in seed_demo.EXPERIENCES:
        status, confidence = entry[5], entry[6]
        assert status in allowed, status
        assert low <= confidence <= high

    difficulties = ENUMS[("knowledge_cases", "difficulty_level")]
    for case in seed_demo.KNOWLEDGE_CASES:
        assert case[6] in difficulties


def test_seed_accounts_are_marked_as_demo_data():
    """Prototype data must be distinguishable from real user data (PRD section 28)."""
    from backend.scripts import seed_demo

    assert seed_demo.DEMO_DOMAIN.endswith(".local")
    assert seed_demo._email("ravi").endswith(f"@{seed_demo.DEMO_DOMAIN}")


def test_the_seed_fixture_covers_the_prd_ranking_scenario():
    """Ravi, Meena and Arjun must differ in the way the PRD scenario requires."""
    from backend.scripts import seed_demo

    by_worker: dict[str, list[str]] = {}
    for entry in seed_demo.EXPERIENCES:
        by_worker.setdefault(entry[0], []).append(f"{entry[1]} {entry[2]}".lower())

    ravi = " ".join(by_worker["ravi"])
    meena = " ".join(by_worker["meena"])
    arjun = " ".join(by_worker["arjun"])

    assert "s23" in ravi and "drop" in ravi, "Ravi: same model, same context"
    assert "s23" in meena and "charg" in meena, "Meena: same model, different fault"
    assert "s22" in arjun, "Arjun: different model"


# ------------------------------------------------------------- graph enrichment


def test_matching_reports_when_the_graph_enriched_it(client, world, monkeypatch):
    world.add_experience(world.worker_a, "S23 no power after drop",
                         "Galaxy S23 no power after physical drop motherboard repair",
                         contexts=[("damage", "physical drop")])

    monkeypatch.setattr(neo4j_client, "is_available", lambda: True)
    monkeypatch.setattr(
        neo4j_client, "enrich_workers",
        lambda ids: {
            world.worker_a: {
                "contexts": ["physical drop"],
                "skills": ["board-level repair"],
                "solved_count": 7,
                "evidence_count": 4,
                "verified_outcomes": 5,
            }
        },
    )

    problem_id = client.post(
        f"{API}/problems", headers=auth(world.customer),
        json={"title": "S23 dead", "description": "Samsung S23 fell and won't turn on.",
              "latitude": 18.5204, "longitude": 73.8567},
    ).json()["id"]
    client.post(f"{API}/problems/{problem_id}/fingerprint",
                headers=auth(world.customer), json={})

    body = client.get(f"{API}/problems/{problem_id}/matches",
                      headers=auth(world.customer)).json()
    assert body["graph_enriched"] is True
    explanation = " ".join(body["items"][0]["explanation"])
    assert "7 related solved problems" in explanation


def test_a_graph_failure_does_not_break_matching(client, world, monkeypatch):
    """Neo4j is a projection; losing it must not take the product down."""
    world.add_experience(world.worker_a, "S23 no power after drop",
                         "Galaxy S23 no power after physical drop motherboard repair")

    def explode(ids):
        raise RuntimeError("graph is down")

    # enrich_workers swallows its own errors, so the pipeline sees an empty result.
    monkeypatch.setattr(neo4j_client, "enrich_workers", lambda ids: {})
    monkeypatch.setattr(neo4j_client, "is_available", lambda: False)

    problem_id = client.post(
        f"{API}/problems", headers=auth(world.customer),
        json={"title": "S23 dead", "description": "Samsung S23 fell and won't turn on.",
              "latitude": 18.5204, "longitude": 73.8567},
    ).json()["id"]
    client.post(f"{API}/problems/{problem_id}/fingerprint",
                headers=auth(world.customer), json={})

    response = client.get(f"{API}/problems/{problem_id}/matches", headers=auth(world.customer))
    assert response.status_code == 200
    assert response.json()["items"], "matching still returns candidates without the graph"
    assert response.json()["graph_enriched"] is False


def test_neo4j_helpers_are_inert_when_unconfigured(monkeypatch):
    """With no NEO4J_URI the client must no-op rather than raise."""
    from backend.core.config import settings

    monkeypatch.setattr(settings, "neo4j_uri", "")
    monkeypatch.setattr(neo4j_client, "_driver", None)
    monkeypatch.setattr(neo4j_client, "_unavailable", False)

    assert neo4j_client.is_available() is False
    assert neo4j_client.enrich_workers(["a"]) == {}
    assert neo4j_client.project_experience(
        experience_id="e", worker_id="w", title="t",
        problem_description="d", contexts=[], skills=[], verified=True,
    ) is False


# ------------------------------------------------------- indexing failure isolation


def test_an_embedding_failure_does_not_roll_back_a_completed_job(client, world, monkeypatch):
    """PostgreSQL is the source of truth; a derived-store failure must not undo it."""
    from backend.services.ai import embeddings, indexing

    world.add_experience(world.worker_a, "S23 no power", "Galaxy S23 no power after drop")
    problem_id = client.post(
        f"{API}/problems", headers=auth(world.customer),
        json={"title": "S23 dead", "description": "Samsung S23 fell and won't turn on.",
              "latitude": 18.5204, "longitude": 73.8567},
    ).json()["id"]
    request_id = client.post(f"{API}/service-requests", headers=auth(world.customer),
                             json={"problem_id": problem_id,
                                   "worker_id": world.worker_a}).json()["id"]
    job_id = client.patch(f"{API}/service-requests/{request_id}", headers=auth(world.worker_a),
                          json={"status": "accepted"}).json()["job_id"]

    def explode(*args, **kwargs):
        raise RuntimeError("embedding service is down")

    monkeypatch.setattr(indexing.embeddings, "embed_text", explode)

    response = client.post(
        f"{API}/jobs/{job_id}/completion", headers=auth(world.worker_a),
        json={"diagnosis": "Board fault.",
              "actions": [{"step_number": 1, "action_type": "repair",
                           "action_description": "Repaired."}],
              "outcomes": [{"outcome_description": "Powers on"}]},
    )
    assert response.status_code == 201, "the job still completes"
    assert response.json()["status"] == "completed"
