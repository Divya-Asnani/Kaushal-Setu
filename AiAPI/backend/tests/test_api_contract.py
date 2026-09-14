"""The exposed API surface, checked against the documented contract.

Section 6 of the FastAPI specification lists an exact endpoint inventory. These tests
assert the app actually publishes it, with the documented response fields, so drift
between the doc and the code is caught rather than discovered during integration.
"""
from __future__ import annotations

import pytest

from backend.main import app
from backend.tests.conftest import auth

API = "/api/v1"

# (method, path) exactly as the specification's endpoint inventory lists them.
DOCUMENTED = [
    ("get", "/me"),
    ("patch", "/me"),
    ("get", "/workers/{worker_id}"),
    ("patch", "/workers/me"),
    ("put", "/workers/me/skills"),
    ("post", "/workers/me/certificates"),
    ("get", "/workers/{worker_id}/experiences"),
    ("post", "/problems"),
    ("get", "/problems/{problem_id}"),
    ("patch", "/problems/{problem_id}"),
    ("post", "/problems/{problem_id}/fingerprint"),
    ("get", "/problems/{problem_id}/matches"),
    ("post", "/experiences"),
    ("get", "/experiences/{experience_id}"),
    ("patch", "/experiences/{experience_id}"),
    ("get", "/experiences/similar"),
    ("post", "/service-requests"),
    ("get", "/service-requests/{request_id}"),
    ("patch", "/service-requests/{request_id}"),
    ("get", "/jobs/{job_id}"),
    ("patch", "/jobs/{job_id}/status"),
    ("post", "/jobs/{job_id}/completion"),
    ("post", "/jobs/{job_id}/verify"),
    ("post", "/jobs/{job_id}/dispute"),
    ("post", "/feedback"),
    ("get", "/jobs/{job_id}/feedback"),
    ("post", "/knowledge-cases"),
    ("get", "/knowledge-cases/{case_id}"),
    ("patch", "/knowledge-cases/{case_id}"),
    ("get", "/knowledge-cases/similar"),
    ("get", "/notifications"),
    ("patch", "/notifications/{id}/read"),
]

# Routes this backend adds beyond the inventory, each with a reason to exist.
ADDITIONS = [
    ("get", "/problems"),                        # a customer listing their own problems
    ("post", "/problems/{problem_id}/media"),    # register an uploaded file
    ("patch", "/problems/{problem_id}/fingerprint"),  # customer confirms/corrects (C-05)
    ("get", "/problems/{problem_id}/matches/stored"),  # re-read without re-running AI
    ("get", "/skills"),                          # canonical list for skill pickers
    ("get", "/service-requests"),                # a worker's inbox
    ("get", "/jobs"),                            # a participant's job list
    ("get", "/knowledge-cases"),                 # Knowledge Hub browsing
]


def _published() -> set[tuple[str, str]]:
    published = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path.startswith(API):
            continue
        for method in getattr(route, "methods", set()):
            if method in {"HEAD", "OPTIONS"}:
                continue
            published.add((method.lower(), path[len(API):]))
    return published


def _normalise(pair: tuple[str, str]) -> tuple[str, str]:
    """Path parameter names are an implementation detail; compare positionally."""
    method, path = pair
    segments = [
        "{p}" if segment.startswith("{") else segment
        for segment in path.split("/")
    ]
    return method, "/".join(segments)


@pytest.mark.parametrize("method,path", DOCUMENTED)
def test_every_documented_endpoint_is_published(method, path):
    published = {_normalise(p) for p in _published()}
    assert _normalise((method, path)) in published, f"{method.upper()} {path} is missing"


def test_no_undocumented_endpoints_are_exposed():
    """Anything published beyond the contract must be a deliberate, listed addition."""
    published = {_normalise(p) for p in _published()}
    expected = {_normalise(p) for p in DOCUMENTED} | {_normalise(p) for p in ADDITIONS}
    assert published - expected == set()


def test_openapi_document_builds():
    schema = app.openapi()
    assert schema["info"]["title"] == "iBolt API"
    assert schema["paths"]


def test_health_is_public_and_leaks_no_secrets(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["match_weights"] == {
        "problem": 0.4, "context": 0.3, "verified": 0.2, "proximity": 0.1
    }
    # Configuration presence is reported as booleans, never as values.
    serialised = str(body)
    assert "key" not in serialised.lower() or "api_key" not in serialised.lower()
    for field in ("supabase_configured", "gemini_configured", "database_url_configured"):
        assert isinstance(body[field], bool)


def test_root_is_public(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["api"] == API


# ------------------------------------------------------------- response shapes


def test_me_matches_the_documented_shape(client, world):
    body = client.get(f"{API}/me", headers=auth(world.customer)).json()
    assert set(body) == {"id", "role", "display_name", "phone", "avatar_url", "is_active"}


def test_worker_profile_matches_the_documented_shape(client, world):
    body = client.get(f"{API}/workers/{world.worker_a}", headers=auth(world.customer)).json()
    assert set(body) == {
        "user_id", "professional_title", "bio", "years_experience", "service_radius_km",
        "locality", "city", "state", "latitude", "longitude", "availability_status",
        "is_verified", "skills",
    }


def test_worker_profile_does_not_leak_a_street_address(client, world, store):
    """Exact location is disclosed later in the workflow, not during matching."""
    worker = next(w for w in store.all("worker_profiles") if w["user_id"] == world.worker_a)
    worker["address_line"] = "12 Private Lane"
    worker["postal_code"] = "411001"
    body = client.get(f"{API}/workers/{world.worker_a}", headers=auth(world.customer)).json()
    assert "address_line" not in body
    assert "postal_code" not in body
    assert "12 Private Lane" not in str(body)


def test_fingerprint_matches_the_documented_shape(client, world):
    problem_id = client.post(
        f"{API}/problems", headers=auth(world.customer),
        json={"title": "S23 dead", "description": "Samsung S23 fell, motherboard maybe."},
    ).json()["id"]
    body = client.post(f"{API}/problems/{problem_id}/fingerprint",
                       headers=auth(world.customer), json={}).json()
    for field in ("problem_id", "device_type", "brand", "model", "category", "issue",
                  "symptoms", "context", "suspected_component", "repair_type",
                  "extracted_skills", "ai_summary", "embedding_status",
                  "fingerprint_version"):
        assert field in body, field


def test_match_item_matches_the_documented_shape(client, world):
    world.add_experience(world.worker_a, "S23 no power after drop",
                         "Galaxy S23 no power after physical drop motherboard repair")
    problem_id = client.post(
        f"{API}/problems", headers=auth(world.customer),
        json={"title": "S23 dead", "description": "Samsung S23 fell and won't turn on.",
              "latitude": 18.5204, "longitude": 73.8567},
    ).json()["id"]
    client.post(f"{API}/problems/{problem_id}/fingerprint",
                headers=auth(world.customer), json={})

    body = client.get(f"{API}/problems/{problem_id}/matches", headers=auth(world.customer)).json()
    assert {"problem_id", "items"} <= set(body)
    item = body["items"][0]
    for field in ("worker_id", "rank_position", "match_score", "problem_similarity",
                  "context_similarity", "verified_experience_confidence",
                  "proximity_score", "explanation"):
        assert field in item, field
    assert isinstance(item["explanation"], list)


def test_similar_experiences_match_the_documented_shape(client, world):
    world.add_experience(world.worker_a, "S23 no power", "Galaxy S23 no power after drop")
    body = client.get(f"{API}/experiences/similar?q=Samsung+S23+no+power&limit=5",
                      headers=auth(world.worker_a)).json()
    assert body
    assert set(body[0]) == {"experience_id", "similarity", "worker_id", "title",
                            "verification_status"}


def test_similar_knowledge_cases_match_the_documented_shape(client, world):
    client.post(f"{API}/knowledge-cases", headers=auth(world.worker_a),
                json={"title": "No power after impact",
                      "problem_summary": "Samsung phone no power after a drop",
                      "visibility_status": "published"})
    body = client.get(f"{API}/knowledge-cases/similar?q=samsung+no+power&limit=5",
                      headers=auth(world.worker_a)).json()
    assert body
    assert {"knowledge_case_id", "similarity", "title", "verification_state"} <= set(body[0])


def test_notification_matches_the_documented_shape(client, world, store):
    store.seed("notifications", [{
        "id": "n1", "user_id": world.customer, "notification_type": "test",
        "title": "t", "message": "m", "is_read": False,
    }])
    body = client.patch(f"{API}/notifications/n1/read", headers=auth(world.customer)).json()
    assert body["is_read"] is True
    assert body["read_at"]


def test_stored_matches_replay_without_rerunning_the_pipeline(client, world):
    world.add_experience(world.worker_a, "S23 no power after drop",
                         "Galaxy S23 no power after physical drop motherboard")
    problem_id = client.post(
        f"{API}/problems", headers=auth(world.customer),
        json={"title": "S23 dead", "description": "Samsung S23 fell and won't turn on.",
              "latitude": 18.5204, "longitude": 73.8567},
    ).json()["id"]
    client.post(f"{API}/problems/{problem_id}/fingerprint",
                headers=auth(world.customer), json={})
    live = client.get(f"{API}/problems/{problem_id}/matches",
                      headers=auth(world.customer)).json()
    stored = client.get(f"{API}/problems/{problem_id}/matches/stored",
                        headers=auth(world.customer)).json()

    assert [i["worker_id"] for i in stored["items"]] == [i["worker_id"] for i in live["items"]]
    assert [i["match_score"] for i in stored["items"]] == [i["match_score"] for i in live["items"]]
    assert stored["items"][0]["explanation"] == live["items"][0]["explanation"]


def test_unhandled_errors_stay_inside_the_error_contract(client, world, monkeypatch):
    """A crash must not escape as a bare 500 with no request id."""
    from backend.api.routes import profile

    def explode(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(profile, "one_or_none", explode)

    # A separate client that returns the 500 instead of re-raising it, so the response
    # body can be inspected. The `client` fixture's patches are still in effect.
    from fastapi.testclient import TestClient

    from backend.main import app as real_app

    with TestClient(real_app, raise_server_exceptions=False) as quiet:
        response = quiet.get(f"{API}/me", headers=auth(world.customer))

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["request_id"]
    # The internal message must not reach the client.
    assert "boom" not in str(body)


def test_unknown_routes_use_the_error_contract(client):
    response = client.get(f"{API}/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert body["request_id"]


def test_wrong_method_uses_the_error_contract(client, world):
    response = client.delete(f"{API}/me", headers=auth(world.customer))
    assert response.status_code == 405
    assert "error" in response.json()
