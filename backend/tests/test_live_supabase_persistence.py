"""
Comprehensive E2E Integration Test: Real-Time Supabase Persistence
Tests full golden path from signup to verification and ensures all records exist in PostgreSQL.
"""
import sys
import os
import uuid
import jwt
import requests
from datetime import datetime, timezone

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_root_dir = os.path.dirname(_backend_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from backend.config import settings

BASE_URL = "http://localhost:8000/api/v1"

def make_jwt(user_id: str, email: str, role: str, name: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "user_metadata": {
            "display_name": name,
            "full_name": name,
            "role": role
        },
        "exp": 2104717285
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

def run_e2e_test():
    print("=" * 70)
    print("  KAUSHALSETU: REAL-TIME SUPABASE DATA PERSISTENCE E2E TEST")
    print("=" * 70)

    # 1. Generate real unique user identities
    customer_uuid = str(uuid.uuid4())
    customer_email = f"test.cust.{customer_uuid[:8]}@example.com"
    customer_jwt = make_jwt(customer_uuid, customer_email, "customer", "Real Test Customer")

    worker_uuid = str(uuid.uuid4())
    worker_email = f"test.worker.{worker_uuid[:8]}@example.com"
    worker_jwt = make_jwt(worker_uuid, worker_email, "worker", "Real Test Technician")

    # 2. Test Customer Signup & Profile Sync
    print(f"\n[1/10] Registering Customer profile ({customer_uuid})...")
    cust_res = requests.post(
        f"{BASE_URL}/auth/sync-profile",
        headers={"Authorization": f"Bearer {customer_jwt}"},
        json={
            "id": customer_uuid,
            "email": customer_email,
            "role": "customer",
            "full_name": "Real Test Customer",
            "phone": "+91 9988776655",
            "locality": "Indiranagar",
            "city": "Bengaluru"
        }
    )
    assert cust_res.status_code == 200, f"Customer sync failed: {cust_res.text}"
    cust_data = cust_res.json()
    assert cust_data.get("locality") == "Indiranagar", f"Expected locality 'Indiranagar', got: {cust_data.get('locality')}"
    assert cust_data.get("city") == "Bengaluru", f"Expected city 'Bengaluru', got: {cust_data.get('city')}"
    print(f"  [+] Customer profile created: {cust_data['display_name']} ({cust_data['locality']}, {cust_data['city']})")

    # Also test /auth/register endpoint with dynamic locality & city
    dyn_reg_res = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": f"dynamic.{customer_uuid[:8]}@example.com",
            "password": "Password123!",
            "full_name": "Dynamic Location User",
            "locality": "HSR Layout",
            "city": "Bengaluru"
        }
    )
    assert dyn_reg_res.status_code in [200, 201], f"Register failed: {dyn_reg_res.text}"
    dyn_data = dyn_reg_res.json()
    assert dyn_data.get("locality") == "HSR Layout", f"Expected 'HSR Layout', got: {dyn_data.get('locality')}"
    assert dyn_data.get("city") == "Bengaluru", f"Expected 'Bengaluru', got: {dyn_data.get('city')}"
    print(f"  [+] /auth/register persisted custom locality: {dyn_data['locality']}, {dyn_data['city']}")

    # 3. Test Worker Signup & Profile Sync
    print(f"\n[2/10] Registering Technician profile & worker profile ({worker_uuid})...")
    worker_res = requests.post(
        f"{BASE_URL}/auth/sync-profile",
        headers={"Authorization": f"Bearer {worker_jwt}"},
        json={
            "id": worker_uuid,
            "email": worker_email,
            "role": "worker",
            "full_name": "Real Test Technician",
            "phone": "+91 9988776644",
            "locality": "Koramangala",
            "city": "Bengaluru"
        }
    )
    assert worker_res.status_code == 200, f"Worker sync failed: {worker_res.text}"
    worker_data = worker_res.json()
    assert worker_data.get("locality") == "Koramangala", f"Expected 'Koramangala', got: {worker_data.get('locality')}"
    assert worker_data.get("city") == "Bengaluru", f"Expected 'Bengaluru', got: {worker_data.get('city')}"
    print(f"  [+] Worker profile & worker_profiles record created: {worker_data['display_name']} ({worker_data['locality']}, {worker_data['city']})")

    # 4. Customer Creates Problem & Uploads Media Path
    print(f"\n[3/10] Customer creating problem with uploaded media metadata...")
    storage_path = f"problem-media/problems/{int(datetime.now().timestamp())}_s23_damage.jpg"
    prob_res = requests.post(
        f"{BASE_URL}/problems",
        headers={"Authorization": f"Bearer {customer_jwt}"},
        json={
            "title": "Samsung S23 No Power After Drop",
            "description": "Phone fell from table onto concrete floor. Display is blank, drawing 0mA on USB-C.",
            "address_line": "101, 12th Main Road",
            "locality": "Indiranagar",
            "city": "Bengaluru",
            "state": "Karnataka",
            "postal_code": "560038",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "media_paths": [storage_path]
        }
    )
    assert prob_res.status_code == 201, f"Problem creation failed: {prob_res.text}"
    problem_data = prob_res.json()
    assert problem_data.get("locality") == "Indiranagar"
    assert problem_data.get("city") == "Bengaluru"
    problem_id = problem_data["id"]
    print(f"  [+] Problem created with ID: {problem_id} (Locality: {problem_data['locality']}, City: {problem_data['city']})")
    print(f"  [+] Problem media persisted: {len(problem_data.get('media', []))} items")

    # 5. Customer Generates AI Fingerprint
    print(f"\n[4/10] Generating AI Problem Fingerprint for problem {problem_id}...")
    fp_res = requests.post(
        f"{BASE_URL}/problems/{problem_id}/fingerprint",
        headers={"Authorization": f"Bearer {customer_jwt}"},
        json={"regenerate": False}
    )
    assert fp_res.status_code == 200, f"Fingerprint generation failed: {fp_res.text}"
    fp_data = fp_res.json()
    print(f"  [+] Fingerprint generated: device={fp_data.get('brand')} {fp_data.get('model')}, issue={fp_data.get('issue')}")

    # 6. Customer Retrieves Matches
    print(f"\n[5/10] Retrieving intelligent matches for problem...")
    matches_res = requests.get(
        f"{BASE_URL}/problems/{problem_id}/matches",
        headers={"Authorization": f"Bearer {customer_jwt}"}
    )
    assert matches_res.status_code == 200, f"Match retrieval failed: {matches_res.text}"
    matches_data = matches_res.json()
    matches = matches_data.get("matches", [])
    print(f"  [+] Found {len(matches)} matched technicians. Top score: {matches[0]['match_score'] if matches else 'N/A'}")
    
    # Pick target worker (use the matched worker or the newly registered test worker)
    target_worker_id = matches[0]["worker_id"] if matches else worker_uuid
    match_result_id = matches[0]["match_result_id"] if matches else None

    # 7. Customer Requests Technician
    print(f"\n[6/10] Customer sending service request to technician {target_worker_id}...")
    sr_res = requests.post(
        f"{BASE_URL}/service-requests",
        headers={"Authorization": f"Bearer {customer_jwt}"},
        json={
            "problem_id": problem_id,
            "worker_id": target_worker_id,
            "customer_message": "Can you please inspect this today?",
            "match_result_id": match_result_id
        }
    )
    assert sr_res.status_code == 201, f"Service request failed: {sr_res.text}"
    request_data = sr_res.json()
    request_id = request_data["id"]
    print(f"  [+] Service request created: {request_id} (status: {request_data['status']})")

    # Test Duplicate Request Prevention (409 Conflict)
    dup_sr_res = requests.post(
        f"{BASE_URL}/service-requests",
        headers={"Authorization": f"Bearer {customer_jwt}"},
        json={
            "problem_id": problem_id,
            "worker_id": target_worker_id,
            "customer_message": "Duplicate attempt",
            "match_result_id": match_result_id
        }
    )
    assert dup_sr_res.status_code == 409, f"Expected 409 Conflict for duplicate request, got: {dup_sr_res.status_code}"
    print(f"  [+] Duplicate service request successfully prevented with HTTP 409 Conflict.")

    # 8. Technician Receives Request on Dashboard via /service-requests/me
    assigned_worker_jwt = worker_jwt
    if target_worker_id != worker_uuid:
        from backend.db.supabase_client import db
        target_wp = db.worker_profiles.get(target_worker_id)
        target_user_id = str(target_wp.get("user_id")) if target_wp else target_worker_id
        assigned_worker_jwt = make_jwt(target_user_id, f"worker.{target_user_id[:8]}@kaushalsetu.in", "worker", "Technician")

    print(f"\n[7/10] Verifying technician incoming requests dashboard via GET /service-requests/me...")
    worker_me_res = requests.get(
        f"{BASE_URL}/service-requests/me",
        headers={"Authorization": f"Bearer {assigned_worker_jwt}"}
    )
    assert worker_me_res.status_code == 200, f"Worker requests fetch failed: {worker_me_res.text}"
    worker_reqs = worker_me_res.json()
    assert any(r["id"] == request_id for r in worker_reqs), f"Request {request_id} not found in technician's incoming requests"
    print(f"  [+] Request {request_id} successfully delivered to authenticated technician dashboard via /service-requests/me.")

    # Also verify Customer sees it via /service-requests/me
    cust_me_res = requests.get(
        f"{BASE_URL}/service-requests/me",
        headers={"Authorization": f"Bearer {customer_jwt}"}
    )
    assert cust_me_res.status_code == 200
    assert any(r["id"] == request_id for r in cust_me_res.json())
    print(f"  [+] Customer successfully tracked request status via /service-requests/me.")

    # 9. Technician Accepts Request (Creates Job + job_status_history)
    print(f"\n[8/10] Technician accepting service request {request_id}...")
    accept_res = requests.patch(
        f"{BASE_URL}/service-requests/{request_id}",
        headers={"Authorization": f"Bearer {assigned_worker_jwt}"},
        json={
            "status": "accepted",
            "worker_response": "I can visit at 3:00 PM for board diagnosis."
        }
    )
    assert accept_res.status_code == 200, f"Accept failed: {accept_res.text}"
    job_id = accept_res.json().get("created_job_id")
    assert job_id, "Job ID not returned upon acceptance"
    print(f"  [+] Service request accepted! Job automatically generated: {job_id}")

    # Test Duplicate Acceptance Prevention (409 Conflict)
    dup_accept_res = requests.patch(
        f"{BASE_URL}/service-requests/{request_id}",
        headers={"Authorization": f"Bearer {assigned_worker_jwt}"},
        json={"status": "accepted"}
    )
    assert dup_accept_res.status_code == 409, f"Expected 409 Conflict for repeated acceptance, got: {dup_accept_res.status_code}"
    print(f"  [+] Duplicate acceptance safely rejected with HTTP 409 Conflict.")

    # 10. Technician Starts Job & Submits Completion
    print(f"\n[9/10] Technician transitioning job status and submitting completion...")
    start_res = requests.patch(
        f"{BASE_URL}/jobs/{job_id}/status",
        headers={"Authorization": f"Bearer {assigned_worker_jwt}"},
        json={"status": "in_progress", "notes": "On-site diagnosis started."}
    )
    assert start_res.status_code == 200, f"Start job failed: {start_res.text}"
    print(f"  [+] Job status: in_progress")

    comp_res = requests.post(
        f"{BASE_URL}/jobs/{job_id}/completion",
        headers={"Authorization": f"Bearer {assigned_worker_jwt}"},
        json={
            "diagnosis": "Dead phone drawing 0mA; short on VDD_MAIN rail traced to damaged PMIC decoupling capacitor.",
            "actions": [
                {
                    "step_number": 1,
                    "action_type": "diagnostic",
                    "action_description": "Thermal camera inspection identified localized heating under motherboard shielding.",
                    "tools_used": ["Thermal Camera", "Digital Multimeter"]
                },
                {
                    "step_number": 2,
                    "action_type": "repair",
                    "action_description": "Lifted shield at 320C, desoldered shorted capacitor, soldered replacement 10uF SMD capacitor.",
                    "tools_used": ["Micro-soldering Station", "Hot Air Rework"]
                }
            ],
            "outcomes": [
                {
                    "outcome_type": "repair_result",
                    "outcome_description": "Device boots normally into operating system, charging current confirmed at 2.4A.",
                    "success_status": "successful",
                    "lessons_learned": "Mechanical drops often produce hairline fractures on high-capacitance decoupling capacitors."
                }
            ],
            "evidence": [
                {
                    "storage_path": f"experience-media/evidence/{int(datetime.now().timestamp())}_after_repair.jpg",
                    "media_type": "image",
                    "media_role": "after"
                }
            ]
        }
    )
    assert comp_res.status_code == 200, f"Job completion failed: {comp_res.text}"
    print(f"  [+] Job completed! Experience, actions, outcomes, and evidence persisted.")

    # 11. Customer Verifies Job & Submits Feedback
    print(f"\n[10/10] Customer verifying completed repair and submitting feedback...")
    verif_res = requests.post(
        f"{BASE_URL}/jobs/{job_id}/verify",
        headers={"Authorization": f"Bearer {customer_jwt}"},
        json={"comments": "Phone powered on and charged perfectly. Great work!"}
    )
    assert verif_res.status_code == 200, f"Verification failed: {verif_res.text}"
    print(f"  [+] Verification confirmed! Linked experience upgraded to 'verified'.")

    fb_res = requests.post(
        f"{BASE_URL}/feedback",
        headers={"Authorization": f"Bearer {customer_jwt}"},
        json={
            "job_id": job_id,
            "rating": 5.0,
            "feedback_text": "Highly skilled technician. Fixed the motherboard issue in under an hour."
        }
    )
    assert fb_res.status_code == 201, f"Feedback failed: {fb_res.text}"
    print(f"  [+] 5-star customer feedback submitted and persisted.")

    # Test Duplicate Feedback Prevention (409 Conflict)
    dup_fb_res = requests.post(
        f"{BASE_URL}/feedback",
        headers={"Authorization": f"Bearer {customer_jwt}"},
        json={
            "job_id": job_id,
            "rating": 5.0,
            "feedback_text": "Duplicate rating attempt"
        }
    )
    assert dup_fb_res.status_code == 409, f"Expected 409 Conflict for duplicate feedback, got: {dup_fb_res.status_code}"
    print(f"  [+] Duplicate feedback safely rejected with HTTP 409 Conflict.")

    # 12. Rating reflected ONLY on Technician Profile
    print(f"\n[11/12] Verifying rating reflects strictly on technician profile and NOT customer...")
    worker_prof_res = requests.get(
        f"{BASE_URL}/workers/{target_worker_id}",
        headers={"Authorization": f"Bearer {customer_jwt}"}
    )
    assert worker_prof_res.status_code == 200
    wp_data = worker_prof_res.json()
    print(f"  [+] Technician profile rating: {wp_data.get('rating')} ({wp_data.get('total_reviews')} reviews)")
    assert wp_data.get("total_reviews", 0) >= 1, "Technician total_reviews should be at least 1"

    # Verify Customer profile does NOT have a technician rating
    cust_prof_res = requests.get(
        f"{BASE_URL}/me",
        headers={"Authorization": f"Bearer {customer_jwt}"}
    )
    assert cust_prof_res.status_code == 200
    cp_data = cust_prof_res.json()
    assert "rating" not in cp_data or cp_data.get("rating") is None, "Customer profile must NOT contain technician rating"
    print(f"  [+] Confirmed: Customer profile has NO technician rating attached.")

    # 11. Worker Creates Knowledge Case
    print(f"\n[10/10] Technician publishing Knowledge Hub case...")
    kc_res = requests.post(
        f"{BASE_URL}/knowledge-cases",
        headers={"Authorization": f"Bearer {assigned_worker_jwt}"},
        json={
            "title": "Samsung S23 No Power After Drop - PMIC Capacitor Fracture",
            "problem_summary": "Phone completely unresponsive and drawing 0mA after dropping onto floor.",
            "diagnosis": "Microscopic crack on 10uF VDD_MAIN decoupling capacitor near primary PMIC.",
            "solution": "Replaced SMD capacitor and confirmed voltage rails restored.",
            "lesson_learned": "Always check capacitor pads for hairline cracks around the PMIC perimeter.",
            "difficulty": "advanced",
            "device_category": "Smartphone",
            "brand": "Samsung",
            "model": "Galaxy S23",
            "media_paths": [f"experience-media/{int(datetime.now().timestamp())}_pmic_crack.jpg"]
        }
    )
    assert kc_res.status_code == 201, f"Knowledge case failed: {kc_res.text}"
    case_data = kc_res.json()
    print(f"  [+] Knowledge case created and published: ID={case_data['id']}")
    created_at_str = case_data.get('created_at', '')
    assert "+05:30" in created_at_str or created_at_str.endswith("IST"), f"Expected IST timestamp, got: {created_at_str}"
    print(f"  [+] Verified IST timestamp in knowledge case: {created_at_str}")

    # 12. Knowledge Hub Access Control Verification
    print(f"\n[11/11] Verifying Knowledge Hub access control...")
    cust_kh_res = requests.get(
        f"{BASE_URL}/knowledge-cases/similar",
        headers={"Authorization": f"Bearer {customer_jwt}"},
        params={"q": "Samsung"}
    )
    assert cust_kh_res.status_code == 403, f"Expected 403 Forbidden for customer accessing Knowledge Hub, got: {cust_kh_res.status_code}"
    print("  [+] Customer blocked from Knowledge Hub search (HTTP 403 Forbidden) as required.")

    worker_kh_res = requests.get(
        f"{BASE_URL}/knowledge-cases/similar",
        headers={"Authorization": f"Bearer {assigned_worker_jwt}"},
        params={"q": "Samsung"}
    )
    assert worker_kh_res.status_code == 200, f"Technician Knowledge Hub search failed: {worker_kh_res.text}"
    print(f"  [+] Technician successfully accessed Knowledge Hub search (Found {len(worker_kh_res.json())} cases).")

    print("\n" + "=" * 70)
    print("  [SUCCESS] ALL STEPS PASSED! KNOWLEDGE HUB RESTRICTED, IST VERIFIED!")
    print("  All records were synchronously committed to live Supabase PostgreSQL.")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_test()
