"""Authorization and the error contract.

RLS is off and the backend holds the service-role key, so FastAPI is the only thing
between a caller and the data. These tests are the check on that claim.
"""
from __future__ import annotations

import pytest

from backend.tests.conftest import auth

API = "/api/v1"


def _problem(client, world, **overrides):
    body = {"title": "S23 dead", "description": "Samsung S23 fell and won't turn on.",
            "latitude": 18.5204, "longitude": 73.8567}
    body.update(overrides)
    return client.post(f"{API}/problems", headers=auth(world.customer), json=body).json()


# --------------------------------------------------------------- authentication


PROTECTED = [
    ("get", f"{API}/me"),
    ("patch", f"{API}/me"),
    ("get", f"{API}/problems"),
    ("post", f"{API}/problems"),
    ("get", f"{API}/notifications"),
    ("get", f"{API}/skills"),
    ("get", f"{API}/jobs"),
    ("get", f"{API}/service-requests"),
    ("post", f"{API}/feedback"),
    ("post", f"{API}/knowledge-cases"),
    ("get", f"{API}/experiences/similar?q=test"),
    ("get", f"{API}/knowledge-cases/similar?q=test"),
]


@pytest.mark.parametrize("method,path", PROTECTED)
def test_every_protected_endpoint_rejects_anonymous_calls(client, method, path):
    kwargs = {} if method == "get" else {"json": {}}
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "AUTH_REQUIRED"
    assert body["request_id"]


def test_malformed_authorization_header_is_rejected(client, world):
    for header in [{"Authorization": "Basic abc"}, {"Authorization": "Bearer"},
                   {"Authorization": "Bearer   "}, {"Authorization": ""}]:
        response = client.get(f"{API}/me", headers=header)
        assert response.status_code == 401, header


def test_token_for_a_user_without_a_profile_is_rejected(client, world):
    response = client.get(f"{API}/me", headers=auth("00000000-0000-0000-0000-000000000000"))
    assert response.status_code == 404


def test_deactivated_accounts_are_refused(client, world, store):
    profile = next(p for p in store.all("profiles") if p["id"] == world.customer)
    profile["is_active"] = False
    response = client.get(f"{API}/me", headers=auth(world.customer))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_every_response_carries_a_request_id_header(client, world):
    response = client.get(f"{API}/me", headers=auth(world.customer))
    assert response.headers["X-Request-ID"]


# ------------------------------------------------------------------ role checks


def test_only_customers_create_problems(client, world):
    response = client.post(f"{API}/problems", headers=auth(world.worker_a),
                           json={"title": "x", "description": "y"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_only_workers_create_experiences(client, world):
    response = client.post(f"{API}/experiences", headers=auth(world.customer),
                           json={"title": "x", "problem_description": "y"})
    assert response.status_code == 403


def test_only_workers_publish_knowledge_cases(client, world):
    response = client.post(f"{API}/knowledge-cases", headers=auth(world.customer),
                           json={"title": "x", "problem_summary": "y"})
    assert response.status_code == 403


def test_only_workers_add_certificates(client, world):
    response = client.post(f"{API}/workers/me/certificates", headers=auth(world.customer),
                           json={"certificate_name": "Electrician Level 2"})
    assert response.status_code == 403


def test_admin_may_act_across_roles(client, world):
    problem = _problem(client, world)
    response = client.get(f"{API}/problems/{problem['id']}", headers=auth(world.admin))
    assert response.status_code == 200


# ------------------------------------------------------------- ownership checks


def test_a_customer_cannot_read_another_customers_problem(client, world):
    problem = _problem(client, world)
    response = client.get(f"{API}/problems/{problem['id']}",
                          headers=auth(world.other_customer))
    assert response.status_code == 403


def test_a_worker_cannot_read_an_unrelated_problem(client, world):
    problem = _problem(client, world)
    response = client.get(f"{API}/problems/{problem['id']}", headers=auth(world.worker_b))
    assert response.status_code == 403


def test_a_customer_cannot_fingerprint_another_customers_problem(client, world):
    problem = _problem(client, world)
    response = client.post(f"{API}/problems/{problem['id']}/fingerprint",
                           headers=auth(world.other_customer), json={})
    assert response.status_code == 403


def test_a_customer_cannot_request_a_worker_for_someone_elses_problem(client, world):
    problem = _problem(client, world)
    response = client.post(f"{API}/service-requests", headers=auth(world.other_customer),
                           json={"problem_id": problem["id"], "worker_id": world.worker_a})
    assert response.status_code == 403


def test_the_customer_id_in_a_body_is_ignored(client, world, store):
    """Identity comes from the token; a spoofed owner in the body must not take effect."""
    response = client.post(
        f"{API}/problems", headers=auth(world.customer),
        json={"title": "x", "description": "y", "customer_id": world.other_customer},
    )
    # The field is not part of the request schema, so it is rejected outright.
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_a_worker_cannot_edit_another_workers_experience(client, world):
    experience_id = world.add_experience(world.worker_a, "A case", "Some description.")
    response = client.patch(f"{API}/experiences/{experience_id}",
                            headers=auth(world.worker_b), json={"title": "hijacked"})
    assert response.status_code == 403


def test_a_worker_cannot_edit_another_workers_knowledge_case(client, world, store):
    case_id = client.post(
        f"{API}/knowledge-cases", headers=auth(world.worker_a),
        json={"title": "Case", "problem_summary": "Summary"},
    ).json()["id"]
    response = client.patch(f"{API}/knowledge-cases/{case_id}", headers=auth(world.worker_b),
                            json={"title": "hijacked"})
    assert response.status_code == 403


def test_draft_knowledge_cases_are_hidden_from_other_workers(client, world):
    case_id = client.post(
        f"{API}/knowledge-cases", headers=auth(world.worker_a),
        json={"title": "Draft case", "problem_summary": "Summary"},
    ).json()["id"]
    assert client.get(f"{API}/knowledge-cases/{case_id}",
                      headers=auth(world.worker_b)).status_code == 404
    assert client.get(f"{API}/knowledge-cases/{case_id}",
                      headers=auth(world.worker_a)).status_code == 200


def test_a_user_cannot_mark_another_users_notification_read(client, world, store):
    store.seed("notifications", [{
        "id": "n1", "user_id": world.worker_a, "notification_type": "test",
        "title": "t", "message": "m", "is_read": False,
    }])
    response = client.patch(f"{API}/notifications/n1/read", headers=auth(world.worker_b))
    assert response.status_code == 403


def test_a_user_only_sees_their_own_notifications(client, world, store):
    store.seed("notifications", [
        {"id": "n1", "user_id": world.worker_a, "notification_type": "t",
         "title": "mine", "message": "m", "is_read": False},
        {"id": "n2", "user_id": world.worker_b, "notification_type": "t",
         "title": "theirs", "message": "m", "is_read": False},
    ])
    titles = [n["title"] for n in
              client.get(f"{API}/notifications", headers=auth(world.worker_a)).json()]
    assert titles == ["mine"]


# ------------------------------------------------------- job-scoped authorization


@pytest.fixture
def job(client, world):
    world.add_experience(world.worker_a, "S23 no power after drop",
                         "Galaxy S23 no power after physical drop, motherboard repair")
    problem = _problem(client, world)
    client.post(f"{API}/problems/{problem['id']}/fingerprint",
                headers=auth(world.customer), json={})
    request_id = client.post(f"{API}/service-requests", headers=auth(world.customer),
                             json={"problem_id": problem["id"],
                                   "worker_id": world.worker_a}).json()["id"]
    job_id = client.patch(f"{API}/service-requests/{request_id}", headers=auth(world.worker_a),
                          json={"status": "accepted"}).json()["job_id"]
    return {"problem_id": problem["id"], "request_id": request_id, "job_id": job_id}


def test_only_the_requested_worker_may_accept(client, world):
    problem = _problem(client, world)
    request_id = client.post(f"{API}/service-requests", headers=auth(world.customer),
                             json={"problem_id": problem["id"],
                                   "worker_id": world.worker_a}).json()["id"]
    response = client.patch(f"{API}/service-requests/{request_id}",
                            headers=auth(world.worker_b), json={"status": "accepted"})
    assert response.status_code == 403


def test_a_worker_cannot_cancel_a_request(client, world):
    problem = _problem(client, world)
    request_id = client.post(f"{API}/service-requests", headers=auth(world.customer),
                             json={"problem_id": problem["id"],
                                   "worker_id": world.worker_a}).json()["id"]
    response = client.patch(f"{API}/service-requests/{request_id}",
                            headers=auth(world.worker_a), json={"status": "cancelled"})
    assert response.status_code == 403


def test_a_non_participant_cannot_read_a_job(client, world, job):
    assert client.get(f"{API}/jobs/{job['job_id']}",
                      headers=auth(world.worker_b)).status_code == 403
    assert client.get(f"{API}/jobs/{job['job_id']}",
                      headers=auth(world.other_customer)).status_code == 403


def test_only_the_assigned_worker_submits_completion(client, world, job):
    response = client.post(
        f"{API}/jobs/{job['job_id']}/completion", headers=auth(world.customer),
        json={"diagnosis": "d",
              "actions": [{"step_number": 1, "action_type": "repair",
                           "action_description": "a"}],
              "outcomes": [{"outcome_description": "o"}]},
    )
    assert response.status_code == 403


def test_a_worker_cannot_verify_their_own_job(client, world, job):
    """The central trust rule: a worker can never confirm their own outcome."""
    client.post(f"{API}/jobs/{job['job_id']}/completion", headers=auth(world.worker_a),
                json={"diagnosis": "d",
                      "actions": [{"step_number": 1, "action_type": "repair",
                                   "action_description": "a"}],
                      "outcomes": [{"outcome_description": "o"}]})
    response = client.post(f"{API}/jobs/{job['job_id']}/verify", headers=auth(world.worker_a),
                           json={"verification_status": "verified"})
    assert response.status_code == 403


def test_only_the_job_customer_leaves_feedback(client, world, job):
    client.post(f"{API}/jobs/{job['job_id']}/completion", headers=auth(world.worker_a),
                json={"diagnosis": "d",
                      "actions": [{"step_number": 1, "action_type": "repair",
                                   "action_description": "a"}],
                      "outcomes": [{"outcome_description": "o"}]})
    response = client.post(f"{API}/feedback", headers=auth(world.other_customer),
                           json={"job_id": job["job_id"], "rating": 5})
    assert response.status_code == 403


# ----------------------------------------------------------- state-machine guards


def test_a_job_cannot_be_completed_through_the_status_endpoint(client, world, job):
    """Completion must carry outcome and evidence, so the shortcut is closed."""
    response = client.patch(f"{API}/jobs/{job['job_id']}/status", headers=auth(world.worker_a),
                            json={"status": "completed"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_an_invalid_job_transition_is_rejected(client, world, job):
    client.patch(f"{API}/jobs/{job['job_id']}/status", headers=auth(world.worker_a),
                 json={"status": "cancelled"})
    response = client.patch(f"{API}/jobs/{job['job_id']}/status", headers=auth(world.worker_a),
                            json={"status": "in_progress"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_a_request_cannot_be_accepted_twice(client, world, job):
    response = client.patch(f"{API}/service-requests/{job['request_id']}",
                            headers=auth(world.worker_a), json={"status": "accepted"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_duplicate_open_requests_to_one_worker_are_refused(client, world):
    problem = _problem(client, world)
    client.post(f"{API}/service-requests", headers=auth(world.customer),
                json={"problem_id": problem["id"], "worker_id": world.worker_a})
    response = client.post(f"{API}/service-requests", headers=auth(world.customer),
                           json={"problem_id": problem["id"], "worker_id": world.worker_a})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_offline_workers_cannot_be_requested(client, world, store):
    worker = next(w for w in store.all("worker_profiles") if w["user_id"] == world.worker_a)
    worker["availability_status"] = "offline"
    problem = _problem(client, world)
    response = client.post(f"{API}/service-requests", headers=auth(world.customer),
                           json={"problem_id": problem["id"], "worker_id": world.worker_a})
    assert response.status_code == 409


def test_completion_cannot_be_submitted_twice(client, world, job):
    body = {"diagnosis": "d",
            "actions": [{"step_number": 1, "action_type": "repair",
                         "action_description": "a"}],
            "outcomes": [{"outcome_description": "o"}]}
    assert client.post(f"{API}/jobs/{job['job_id']}/completion",
                       headers=auth(world.worker_a), json=body).status_code == 201
    response = client.post(f"{API}/jobs/{job['job_id']}/completion",
                           headers=auth(world.worker_a), json=body)
    assert response.status_code == 409


def test_a_job_cannot_be_verified_twice(client, world, job):
    client.post(f"{API}/jobs/{job['job_id']}/completion", headers=auth(world.worker_a),
                json={"diagnosis": "d",
                      "actions": [{"step_number": 1, "action_type": "repair",
                                   "action_description": "a"}],
                      "outcomes": [{"outcome_description": "o"}]})
    client.post(f"{API}/jobs/{job['job_id']}/verify", headers=auth(world.customer),
                json={"verification_status": "verified"})
    response = client.post(f"{API}/jobs/{job['job_id']}/verify", headers=auth(world.customer),
                           json={"verification_status": "verified"})
    assert response.status_code == 409


def test_feedback_cannot_be_submitted_twice(client, world, job):
    client.post(f"{API}/jobs/{job['job_id']}/completion", headers=auth(world.worker_a),
                json={"diagnosis": "d",
                      "actions": [{"step_number": 1, "action_type": "repair",
                                   "action_description": "a"}],
                      "outcomes": [{"outcome_description": "o"}]})
    client.post(f"{API}/feedback", headers=auth(world.customer),
                json={"job_id": job["job_id"], "rating": 5})
    response = client.post(f"{API}/feedback", headers=auth(world.customer),
                           json={"job_id": job["job_id"], "rating": 4})
    assert response.status_code == 409


def test_feedback_before_completion_is_refused(client, world, job):
    response = client.post(f"{API}/feedback", headers=auth(world.customer),
                           json={"job_id": job["job_id"], "rating": 5})
    assert response.status_code == 409


def test_a_problem_under_way_can_no_longer_be_edited(client, world, job):
    response = client.patch(f"{API}/problems/{job['problem_id']}", headers=auth(world.customer),
                            json={"title": "changed", "description": "changed"})
    assert response.status_code == 409


# ---------------------------------------------------------------- error contract


def test_unknown_resources_use_the_standard_error_shape(client, world):
    response = client.get(f"{API}/problems/11111111-1111-1111-1111-111111111111",
                          headers=auth(world.customer))
    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"error", "request_id"}
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_validation_errors_use_the_standard_error_shape(client, world):
    response = client.post(f"{API}/problems", headers=auth(world.customer),
                           json={"title": "", "description": ""})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]["errors"]


@pytest.mark.parametrize("payload", [
    {"job_id": "x", "rating": 0},
    {"job_id": "x", "rating": 6},
])
def test_rating_is_bounded_to_one_through_five(client, world, payload):
    response = client.post(f"{API}/feedback", headers=auth(world.customer), json=payload)
    assert response.status_code == 422


def test_coordinates_are_range_checked(client, world):
    response = client.post(f"{API}/problems", headers=auth(world.customer),
                           json={"title": "t", "description": "d",
                                 "latitude": 200, "longitude": 0})
    assert response.status_code == 422


def test_unknown_skill_ids_are_refused(client, world):
    response = client.put(f"{API}/workers/me/skills", headers=auth(world.worker_a),
                          json={"skills": [{"skill_id": "11111111-1111-1111-1111-111111111111"}]})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
