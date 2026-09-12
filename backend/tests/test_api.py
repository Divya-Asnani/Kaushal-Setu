import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

CUSTOMER_AUTH = {"Authorization": "Bearer demo-customer"}
WORKER_AUTH = {"Authorization": "Bearer demo-worker-1"}

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_unauthenticated_request_rejected():
    res = client.get("/api/v1/me")
    assert res.status_code == 401
    data = res.json()
    assert data["error"]["code"] == "AUTH_REQUIRED"

def test_customer_profile():
    res = client.get("/api/v1/me", headers=CUSTOMER_AUTH)
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "customer"
    assert data["email"] == "customer@kaushalsetu.in"

def test_worker_profile():
    res = client.get("/api/v1/workers/me", headers=WORKER_AUTH)
    assert res.status_code == 200
    data = res.json()
    assert data["full_name"] == "Ramesh Verma"
    assert len(data["skills"]) > 0

def test_customer_cannot_access_worker_endpoints():
    res = client.get("/api/v1/workers/me", headers=CUSTOMER_AUTH)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

def test_full_golden_path_e2e():
    # 1. Customer creates a repair problem
    prob_res = client.post(
        "/api/v1/problems",
        headers=CUSTOMER_AUTH,
        json={
            "title": "Samsung Galaxy S23 Dead After Dropping",
            "description": "Phone fell from table onto floor. Screen has no cracks but phone will not turn on at all, completely dead.",
            "address_line": "Flat 402, Sea View Apartments",
            "locality": "Bandra West",
            "city": "Mumbai",
            "state": "Maharashtra",
            "postal_code": "400050",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "media_paths": ["problem-media/sample-dead-phone.jpg"]
        }
    )
    assert prob_res.status_code == 201
    prob_data = prob_res.json()
    prob_id = prob_data["id"]
    assert prob_data["title"] == "Samsung Galaxy S23 Dead After Dropping"
    assert len(prob_data["media"]) == 1

    # 2. Customer generates / reviews problem fingerprint
    fp_res = client.post(
        f"/api/v1/problems/{prob_id}/fingerprint",
        headers=CUSTOMER_AUTH,
        json={"regenerate": False}
    )
    assert fp_res.status_code == 200
    fp_data = fp_res.json()
    assert fp_data["brand"] == "Samsung"
    assert "Possible" in fp_data["suspected_component"] or "motherboard" in fp_data["suspected_component"].lower()
    assert len(fp_data["extracted_skills"]) > 0

    # 3. Customer gets Top-K worker matches
    match_res = client.get(
        f"/api/v1/problems/{prob_id}/matches?limit=5",
        headers=CUSTOMER_AUTH
    )
    assert match_res.status_code == 200
    match_data = match_res.json()
    assert match_data["total_matches"] >= 1
    top_match = match_data["matches"][0]
    assert top_match["rank_position"] == 1
    assert top_match["match_score"] > 0
    assert len(top_match["explanations"]) > 0
    matched_worker_id = top_match["worker_id"]

    # 4. Customer sends service request
    req_res = client.post(
        "/api/v1/service-requests",
        headers=CUSTOMER_AUTH,
        json={
            "problem_id": prob_id,
            "worker_id": matched_worker_id,
            "match_result_id": top_match.get("match_result_id"),
            "customer_message": "Need urgent diagnosis today please."
        }
    )
    assert req_res.status_code == 201
    req_data = req_res.json()
    req_id = req_data["id"]
    assert req_data["status"] == "pending"

    # 5. Worker accepts service request -> Exactly 1 job created
    accept_res = client.patch(
        f"/api/v1/service-requests/{req_id}",
        headers=WORKER_AUTH,
        json={
            "status": "accepted",
            "worker_response": "I can visit within 1 hour."
        }
    )
    assert accept_res.status_code == 200
    accept_data = accept_res.json()
    assert accept_data["status"] == "accepted"
    created_job_id = accept_data["created_job_id"]
    assert created_job_id is not None

    # 6. Worker starts job (status -> in_progress)
    start_res = client.patch(
        f"/api/v1/jobs/{created_job_id}/status",
        headers=WORKER_AUTH,
        json={
            "status": "in_progress",
            "notes": "Arrived on-site, opening shielding to inspect PMIC."
        }
    )
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "in_progress"

    # 7. Worker completes job with diagnosis, actions, outcomes, and evidence
    complete_res = client.post(
        f"/api/v1/jobs/{created_job_id}/completion",
        headers=WORKER_AUTH,
        json={
            "diagnosis": "Short-circuit on VDD_MAIN rail caused by cracked decoupling capacitor near PMIC.",
            "actions": [
                {
                    "step_number": 1,
                    "action_type": "diagnostic",
                    "action_description": "Traced short using thermal camera and multimeter diode check.",
                    "tools_used": ["Thermal Camera", "Digital Multimeter"]
                },
                {
                    "step_number": 2,
                    "action_type": "repair",
                    "action_description": "Desoldered cracked capacitor C4021 and replaced with 10uF 0402 SMD capacitor.",
                    "tools_used": ["Micro-soldering Station", "Stereo Microscope"]
                }
            ],
            "outcomes": [
                {
                    "outcome_type": "repair_result",
                    "outcome_description": "Device boots into OS, charges properly at 15W.",
                    "success_status": "successful",
                    "lessons_learned": "Drop impact cracked capacitor right along shielding solder boundary."
                }
            ],
            "evidence": [
                {
                    "storage_path": f"{created_job_id}/before.jpg",
                    "media_type": "image",
                    "media_role": "before",
                    "is_verified": False
                },
                {
                    "storage_path": f"{created_job_id}/after.jpg",
                    "media_type": "image",
                    "media_role": "after",
                    "is_verified": False
                }
            ]
        }
    )
    assert complete_res.status_code == 200
    complete_data = complete_res.json()
    assert complete_data["status"] == "completed"
    assert complete_data["diagnosis"] is not None
    assert len(complete_data["actions"]) == 2
    assert len(complete_data["evidence"]) == 2

    # 8. Customer reviews and verifies job
    verify_res = client.post(
        f"/api/v1/jobs/{created_job_id}/verify",
        headers=CUSTOMER_AUTH,
        json={
            "verification_status": "verified",
            "comments": "Phone working perfectly now. Excellent work!"
        }
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["verification_status"] == "verified"

    # 9. Customer submits feedback rating
    fb_res = client.post(
        "/api/v1/feedback",
        headers=CUSTOMER_AUTH,
        json={
            "job_id": created_job_id,
            "rating": 5.0,
            "feedback_text": "Ramesh solved the issue in under an hour. Outstanding diagnosis."
        }
    )
    assert fb_res.status_code == 201
    assert fb_res.json()["rating"] == 5.0

    # 10. Worker searches Knowledge Hub
    search_res = client.get(
        "/api/v1/knowledge-cases/similar?q=samsung+s23+power",
        headers=WORKER_AUTH
    )
    assert search_res.status_code == 200
    cases = search_res.json()
    assert len(cases) > 0
    assert "Samsung" in cases[0]["title"]

    # 11. Customer & Worker check notifications
    notifs_res = client.get("/api/v1/notifications", headers=CUSTOMER_AUTH)
    assert notifs_res.status_code == 200
    assert len(notifs_res.json()) > 0

def test_worker_can_submit_problem_in_customer_mode():
    """Verify that a technician/worker switching to Customer Mode can report issues without 403 Forbidden."""
    prob_res = client.post(
        "/api/v1/problems",
        headers=WORKER_AUTH,
        json={
            "title": "Air Conditioner Leaking Water Inside Room",
            "description": "Split AC indoor unit is dripping water down the wall after 20 minutes of cooling.",
            "address_line": "12 Pali Hill",
            "locality": "Bandra West",
            "city": "Mumbai",
            "state": "Maharashtra",
            "postal_code": "400050",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "media_paths": []
        }
    )
    assert prob_res.status_code == 201
    prob = prob_res.json()
    assert prob["title"] == "Air Conditioner Leaking Water Inside Room"

    # Worker can also extract AI fingerprint for their problem
    fp_res = client.post(
        f"/api/v1/problems/{prob['id']}/fingerprint",
        headers=WORKER_AUTH,
        json={"regenerate": False}
    )
    assert fp_res.status_code == 200
    fp = fp_res.json()
    assert fp["problem_id"] == prob["id"]

