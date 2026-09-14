"""The golden path, end to end through the real API.

Problem -> fingerprint -> matches -> request -> accept -> job -> completion ->
verification -> verified experience -> re-index -> knowledge case. This is the flow
the MVP Definition of Done describes, so it is asserted as one continuous test as well
as in pieces.
"""
from __future__ import annotations

from backend.tests.conftest import World, auth

API = "/api/v1"


def _seed_experiences(world: World) -> None:
    """Three workers with different amounts of overlap with the S23 problem."""
    world.add_experience(
        world.worker_a,
        "Samsung Galaxy S23 no power after drop",
        "Galaxy S23 stopped powering on with no display after a physical drop; "
        "motherboard power section repaired",
        status="verified", confidence=95,
        contexts=[("damage", "physical drop")],
        skills=[world.skill_samsung, world.skill_board],
    )
    world.add_experience(
        world.worker_a,
        "Galaxy S23 dead after fall",
        "Galaxy S23 no power after fall, motherboard fault",
        status="verified", confidence=92,
        contexts=[("damage", "physical drop")],
        skills=[world.skill_samsung],
    )
    world.add_experience(
        world.worker_c,
        "Samsung Galaxy S23 charging failure",
        "Galaxy S23 would not charge, motherboard charging circuit repaired",
        status="verified", confidence=93,
        skills=[world.skill_samsung],
    )
    world.add_experience(
        world.worker_b,
        "Samsung Galaxy S22 no power",
        "Galaxy S22 no power, motherboard repaired",
        status="verified", confidence=85,
        skills=[world.skill_samsung],
    )


def test_full_golden_path(client, world, store):
    _seed_experiences(world)
    customer = auth(world.customer)

    # 1. Create the problem ------------------------------------------------
    response = client.post(
        f"{API}/problems",
        headers=customer,
        json={
            "title": "Phone fell and will not turn on",
            "description": "My Samsung S23 fell and now it won't turn on. No display. "
                           "I think there may be a motherboard issue.",
            "city": "Pune",
            "latitude": 18.5204,
            "longitude": 73.8567,
        },
    )
    assert response.status_code == 201, response.text
    problem = response.json()
    problem_id = problem["id"]
    assert problem["status"] == "open"
    # The owner comes from the token, not the body.
    assert problem["customer_id"] == world.customer

    # 2. Fingerprint -------------------------------------------------------
    response = client.post(f"{API}/problems/{problem_id}/fingerprint",
                           headers=customer, json={"regenerate": False})
    assert response.status_code == 200, response.text
    fingerprint = response.json()
    assert fingerprint["model"] == "Galaxy S23"
    assert fingerprint["suspected_component"] == "motherboard"
    # The customer said "I think" — provenance must record that, not assert a fault.
    assert fingerprint["suspected_component_source"] == "customer_stated"
    assert fingerprint["embedding_status"] == "pending"

    # 3. Matches -----------------------------------------------------------
    response = client.get(f"{API}/problems/{problem_id}/matches?limit=5", headers=customer)
    assert response.status_code == 200, response.text
    matches = response.json()
    assert matches["items"], "seeded experiences should produce matches"

    ranked = [m["worker_id"] for m in matches["items"]]
    assert ranked[0] == world.worker_a, "same model + same context + verified ranks first"
    assert world.worker_far not in ranked, "out-of-radius workers are excluded"

    top = matches["items"][0]
    assert top["rank_position"] == 1
    assert top["explanation"], "every result must carry human-readable reasons"
    assert top["match_result_id"], "the ranking must be persisted for auditability"
    assert matches["weights"] == {
        "problem": 0.4, "context": 0.3, "verified": 0.2, "proximity": 0.1
    }

    # Running matches marks the fingerprint embedded and the problem matched.
    assert store.all("problem_fingerprints")[0]["embedding_status"] == "generated"
    assert store.all("problems")[0]["status"] == "matched"
    assert store.count("match_results") == len(matches["items"])

    # 4. Service request ---------------------------------------------------
    response = client.post(
        f"{API}/service-requests",
        headers=customer,
        json={
            "problem_id": problem_id,
            "worker_id": world.worker_a,
            "match_result_id": top["match_result_id"],
            "customer_message": "Please inspect the device.",
        },
    )
    assert response.status_code == 201, response.text
    request_id = response.json()["id"]
    assert response.json()["status"] == "pending"
    assert response.json()["expires_at"], "requests get a TTL"

    # The worker is notified.
    notifications = client.get(f"{API}/notifications", headers=auth(world.worker_a)).json()
    assert any(n["notification_type"] == "service_request" for n in notifications)

    # 5. Worker accepts ----------------------------------------------------
    response = client.patch(
        f"{API}/service-requests/{request_id}",
        headers=auth(world.worker_a),
        json={"status": "accepted", "worker_response": "I can look at it today."},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "accepted"
    job_id = response.json()["job_id"]
    assert job_id, "accepting creates exactly one job"
    assert store.count("jobs") == 1

    # 6. Job progresses ----------------------------------------------------
    response = client.patch(f"{API}/jobs/{job_id}/status", headers=auth(world.worker_a),
                            json={"status": "in_progress", "notes": "Started diagnosis."})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "in_progress"
    assert response.json()["started_at"]

    # 7. Completion with evidence ------------------------------------------
    response = client.post(
        f"{API}/jobs/{job_id}/completion",
        headers=auth(world.worker_a),
        json={
            "diagnosis": "Power section fault identified on the mainboard.",
            "outcome_summary": "Device powers on normally.",
            "actions": [
                {"step_number": 1, "action_type": "diagnostic",
                 "action_description": "Checked power rails."},
                {"step_number": 2, "action_type": "repair",
                 "action_description": "Repaired the affected board section."},
            ],
            "outcomes": [{"outcome_description": "Device powers on"}],
            "evidence": [{"storage_path": "experience-media/x/after.jpg",
                          "media_role": "after"}],
            "contexts": [{"context_type": "damage", "context_value": "physical drop"}],
        },
    )
    assert response.status_code == 201, response.text
    completion = response.json()
    experience_id = completion["experience_id"]
    assert completion["status"] == "completed"
    assert completion["evidence_count"] == 1

    # Evidence alone must not make the experience verified.
    experience = next(e for e in store.all("experiences") if e["id"] == experience_id)
    assert experience["experience_status"] == "submitted"
    assert experience["verification_confidence"] == 0
    outcome = next(o for o in store.all("experience_outcomes")
                   if o["experience_id"] == experience_id)
    assert outcome["customer_confirmed"] is False
    media = next(m for m in store.all("experience_media")
                 if m["experience_id"] == experience_id)
    assert media["is_verified"] is False

    # 8. Customer verifies -------------------------------------------------
    response = client.post(f"{API}/jobs/{job_id}/verify", headers=customer,
                           json={"verification_status": "verified",
                                 "comments": "Repair confirmed working."})
    assert response.status_code == 200, response.text
    assert response.json()["verification_status"] == "verified"
    assert response.json()["verification_score"] == 100

    experience = next(e for e in store.all("experiences") if e["id"] == experience_id)
    assert experience["experience_status"] == "verified"
    assert experience["verification_confidence"] == 100
    outcome = next(o for o in store.all("experience_outcomes")
                   if o["experience_id"] == experience_id)
    assert outcome["customer_confirmed"] is True
    assert store.all("problems")[0]["status"] == "resolved"

    # The verified experience is re-indexed and retrievable for future matching.
    assert any(e["experience_id"] == experience_id
               for e in store.all("experience_embeddings"))

    # 9. Feedback ----------------------------------------------------------
    response = client.post(f"{API}/feedback", headers=customer,
                           json={"job_id": job_id, "rating": 4.5,
                                 "feedback_text": "Good diagnosis."})
    assert response.status_code == 201, response.text
    assert response.json()["rating"] == 4.5

    # 10. Knowledge case ---------------------------------------------------
    response = client.post(
        f"{API}/knowledge-cases",
        headers=auth(world.worker_a),
        json={
            "experience_id": experience_id,
            "title": "Diagnosing no-power Samsung phones after impact",
            "problem_summary": "Samsung phone has no power after a drop.",
            "solution_summary": "Inspect the power rails before replacing the board.",
            "visibility_status": "published",
        },
    )
    assert response.status_code == 201, response.text
    case = response.json()
    assert case["visibility_status"] == "published"
    # Verification is inherited from the experience, never claimed by the author.
    assert case["is_verified"] is True

    response = client.get(
        f"{API}/knowledge-cases/similar?q=Samsung%20no%20power%20after%20falling&limit=5",
        headers=auth(world.worker_a),
    )
    assert response.status_code == 200, response.text
    assert any(item["knowledge_case_id"] == case["id"] for item in response.json())


def test_matches_require_a_fingerprint_first(client, world):
    response = client.post(f"{API}/problems", headers=auth(world.customer),
                           json={"title": "Fan issue", "description": "Fan not spinning."})
    problem_id = response.json()["id"]

    response = client.get(f"{API}/problems/{problem_id}/matches", headers=auth(world.customer))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_fingerprint_is_reused_unless_regenerate_is_requested(client, world, store):
    problem_id = client.post(
        f"{API}/problems", headers=auth(world.customer),
        json={"title": "S23 dead", "description": "Samsung S23 will not turn on."},
    ).json()["id"]

    first = client.post(f"{API}/problems/{problem_id}/fingerprint",
                        headers=auth(world.customer), json={"regenerate": False}).json()
    second = client.post(f"{API}/problems/{problem_id}/fingerprint",
                         headers=auth(world.customer), json={"regenerate": False}).json()
    assert first["id"] == second["id"]
    assert store.count("problem_fingerprints") == 1


def test_customer_correction_upgrades_component_provenance(client, world):
    problem_id = client.post(
        f"{API}/problems", headers=auth(world.customer),
        json={"title": "Fan issue", "description": "Ceiling fan hums but does not spin."},
    ).json()["id"]
    client.post(f"{API}/problems/{problem_id}/fingerprint",
                headers=auth(world.customer), json={})

    response = client.patch(
        f"{API}/problems/{problem_id}/fingerprint",
        headers=auth(world.customer),
        json={"suspected_component": "starting capacitor", "urgency": "urgent"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["suspected_component"] == "starting capacitor"
    assert body["suspected_component_source"] == "customer_stated"
    assert body["urgency"] == "urgent"
    # Changing searchable content invalidates the stored embedding.
    assert body["embedding_status"] == "pending"


def test_safety_warning_reaches_the_client(client, world):
    problem_id = client.post(
        f"{API}/problems", headers=auth(world.customer),
        json={"title": "Sparks", "description": "Sparks and burning smell from the switchboard."},
    ).json()["id"]

    response = client.post(f"{API}/problems/{problem_id}/fingerprint",
                           headers=auth(world.customer), json={})
    assert response.status_code == 200
    assert response.json()["safety_warning"], "high-risk wording must warn the user"


def test_accepting_one_request_expires_the_others(client, world, store):
    _seed_experiences(world)
    problem_id = client.post(
        f"{API}/problems", headers=auth(world.customer),
        json={"title": "S23 dead", "description": "Samsung S23 fell and won't turn on.",
              "latitude": 18.5204, "longitude": 73.8567},
    ).json()["id"]

    for worker in (world.worker_a, world.worker_c):
        client.post(f"{API}/service-requests", headers=auth(world.customer),
                    json={"problem_id": problem_id, "worker_id": worker})

    first = next(r for r in store.all("service_requests") if r["worker_id"] == world.worker_a)
    client.patch(f"{API}/service-requests/{first['id']}", headers=auth(world.worker_a),
                 json={"status": "accepted"})

    other = next(r for r in store.all("service_requests") if r["worker_id"] == world.worker_c)
    assert other["status"] == "expired"
    assert store.count("jobs") == 1


def test_dispute_prevents_verified_experience(client, world, store):
    _seed_experiences(world)
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
    experience_id = client.post(
        f"{API}/jobs/{job_id}/completion", headers=auth(world.worker_a),
        json={"diagnosis": "Board fault.",
              "actions": [{"step_number": 1, "action_type": "repair",
                           "action_description": "Repaired board."}],
              "outcomes": [{"outcome_description": "Powers on"}]},
    ).json()["experience_id"]

    response = client.post(f"{API}/jobs/{job_id}/dispute", headers=auth(world.customer),
                           json={"comments": "Device still shuts down."})
    assert response.status_code == 200, response.text
    assert response.json()["verification_status"] == "disputed"

    experience = next(e for e in store.all("experiences") if e["id"] == experience_id)
    assert experience["experience_status"] == "disputed"
    assert experience["verification_confidence"] == 0
    job = next(j for j in store.all("jobs") if j["id"] == job_id)
    assert job["status"] == "disputed"


def test_job_status_history_records_every_transition(client, world, store):
    _seed_experiences(world)
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
    client.patch(f"{API}/jobs/{job_id}/status", headers=auth(world.worker_a),
                 json={"status": "in_progress"})
    client.post(f"{API}/jobs/{job_id}/completion", headers=auth(world.worker_a),
                json={"diagnosis": "Board fault.",
                      "actions": [{"step_number": 1, "action_type": "repair",
                                   "action_description": "Repaired."}],
                      "outcomes": [{"outcome_description": "Powers on"}]})

    history = [h["status"] for h in store.all("job_status_history")]
    assert history == ["confirmed", "in_progress", "completed"]

    response = client.get(f"{API}/jobs/{job_id}", headers=auth(world.customer))
    assert [h["status"] for h in response.json()["status_history"]] == history
