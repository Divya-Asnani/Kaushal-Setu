import os
import uuid
import logging
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional
from backend.config import settings, IST

logger = logging.getLogger("kaushalsetu.db")

# Frozen 25 PostgreSQL Schema Valid Columns
TABLE_COLUMNS = {
    "profiles": {'id', 'role', 'display_name', 'phone', 'avatar_url', 'is_active', 'created_at', 'updated_at'},
    "worker_profiles": {'user_id', 'professional_title', 'bio', 'years_experience', 'service_radius_km', 'address_line', 'locality', 'city', 'state', 'postal_code', 'latitude', 'longitude', 'availability_status', 'is_verified', 'created_at', 'updated_at'},
    "skills": {'id', 'name', 'category', 'description', 'is_active', 'created_at', 'updated_at'},
    "worker_skills": {'worker_id', 'skill_id', 'proficiency_level', 'years_experience', 'is_primary', 'created_at', 'updated_at'},
    "certificates": {'id', 'worker_id', 'certificate_name', 'issuing_organization', 'certificate_number', 'issue_date', 'expiry_date', 'certificate_url', 'verification_status', 'verified_at', 'created_at', 'updated_at'},
    "problems": {'id', 'customer_id', 'title', 'description', 'status', 'address_line', 'locality', 'city', 'state', 'postal_code', 'latitude', 'longitude', 'created_at', 'updated_at'},
    "problem_media": {'id', 'problem_id', 'storage_path', 'media_type', 'mime_type', 'file_name', 'file_size_bytes', 'caption', 'created_at'},
    "problem_fingerprints": {'id', 'problem_id', 'device_type', 'brand', 'model', 'category', 'issue', 'symptoms', 'context', 'suspected_component', 'repair_type', 'extracted_skills', 'ai_summary', 'raw_ai_output', 'embedding_status', 'fingerprint_version', 'created_at', 'updated_at'},
    "experiences": {'id', 'worker_id', 'title', 'problem_description', 'diagnosis', 'outcome_summary', 'experience_status', 'verification_confidence', 'solved_at', 'created_at', 'updated_at'},
    "experience_contexts": {'id', 'experience_id', 'context_type', 'context_value', 'context_details', 'importance_score', 'created_at', 'updated_at'},
    "experience_actions": {'id', 'experience_id', 'step_number', 'action_type', 'action_description', 'tools_used', 'components_involved', 'result', 'created_at', 'updated_at'},
    "experience_outcomes": {'id', 'experience_id', 'outcome_type', 'outcome_description', 'success_status', 'customer_confirmed', 'follow_up_required', 'created_at', 'updated_at'},
    "experience_skills": {'experience_id', 'skill_id', 'proficiency_demonstrated', 'is_primary_skill', 'created_at', 'updated_at'},
    "experience_media": {'id', 'experience_id', 'storage_path', 'media_type', 'mime_type', 'file_name', 'file_size_bytes', 'media_role', 'caption', 'is_verified', 'created_at'},
    "experience_embeddings": {'id', 'experience_id', 'embedding', 'embedding_model', 'embedding_version', 'source_text', 'created_at', 'updated_at'},
    "service_requests": {'id', 'problem_id', 'worker_id', 'status', 'customer_message', 'worker_response', 'requested_at', 'responded_at', 'accepted_at', 'expires_at', 'created_at', 'updated_at', 'match_result_id'},
    "jobs": {'id', 'service_request_id', 'status', 'scheduled_at', 'started_at', 'completed_at', 'created_at', 'updated_at'},
    "job_status_history": {'id', 'job_id', 'status', 'changed_by', 'notes', 'changed_at', 'created_at'},
    "verifications": {'id', 'job_id', 'experience_id', 'verifier_id', 'verification_type', 'verification_status', 'verification_score', 'comments', 'verified_at', 'created_at', 'updated_at'},
    "feedback": {'id', 'job_id', 'customer_id', 'worker_id', 'rating', 'feedback_text', 'created_at', 'updated_at'},
    "knowledge_cases": {'id', 'worker_id', 'experience_id', 'title', 'problem_summary', 'diagnosis_summary', 'solution_summary', 'lesson_learned', 'difficulty_level', 'visibility_status', 'is_verified', 'published_at', 'created_at', 'updated_at'},
    "knowledge_case_media": {'id', 'knowledge_case_id', 'storage_path', 'media_type', 'mime_type', 'file_name', 'file_size_bytes', 'media_role', 'caption', 'created_at'},
    "knowledge_case_embeddings": {'id', 'knowledge_case_id', 'embedding', 'embedding_model', 'embedding_version', 'source_text', 'created_at', 'updated_at'},
    "match_results": {'id', 'problem_id', 'worker_id', 'problem_similarity', 'context_similarity', 'verified_experience_confidence', 'proximity_score', 'match_score', 'rank_position', 'explanation', 'matching_metadata', 'created_at', 'updated_at'},
    "notifications": {'id', 'user_id', 'notification_type', 'title', 'message', 'related_entity_type', 'related_entity_id', 'is_read', 'read_at', 'created_at'}
}

def adapt_record_for_table(table_name: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Adapts internal dictionary to strictly match frozen Supabase columns."""
    adapted = dict(record)
    if table_name == "profiles":
        if "display_name" not in adapted:
            adapted["display_name"] = adapted.get("full_name") or "User"
        if "is_active" not in adapted:
            adapted["is_active"] = True
    elif table_name == "worker_profiles":
        if "user_id" not in adapted and "id" in adapted:
            adapted["user_id"] = adapted["id"]
        if "professional_title" not in adapted and "headline" in adapted:
            adapted["professional_title"] = adapted["headline"]
        if "years_experience" not in adapted and "experience_years" in adapted:
            adapted["years_experience"] = adapted["experience_years"]
        if "availability_status" not in adapted:
            is_avail = adapted.get("is_available", True)
            adapted["availability_status"] = "available" if is_avail else "unavailable"
    elif table_name == "worker_skills":
        adapted.pop("id", None)
        adapted.pop("verified", None)
        if "years_experience" not in adapted:
            adapted["years_experience"] = 3
        if "is_primary" not in adapted:
            adapted["is_primary"] = True
    elif table_name == "certificates":
        if "certificate_name" not in adapted and "title" in adapted:
            adapted["certificate_name"] = adapted["title"]
        if "certificate_url" not in adapted and "credential_url" in adapted:
            adapted["certificate_url"] = adapted["credential_url"]
        if "verification_status" not in adapted:
            is_ver = adapted.get("is_verified", False)
            adapted["verification_status"] = "verified" if is_ver else "pending"
    elif table_name == "experiences":
        if "problem_description" not in adapted:
            adapted["problem_description"] = adapted.get("diagnosis", "Repair case")
        if "outcome_summary" not in adapted:
            adapted["outcome_summary"] = "Repair completed and verified successfully"
        status_val = adapted.get("experience_status", "submitted")
        if status_val not in {"draft", "submitted", "verified", "disputed"}:
            status_val = "submitted"
        adapted["experience_status"] = status_val
        if status_val == "verified":
            if not adapted.get("verification_confidence") or adapted.get("verification_confidence") == 0:
                adapted["verification_confidence"] = 0.95
        else:
            if "verification_confidence" not in adapted:
                adapted["verification_confidence"] = 0.0
    elif table_name == "knowledge_cases":
        if "diagnosis_summary" not in adapted and "diagnosis" in adapted:
            adapted["diagnosis_summary"] = adapted["diagnosis"]
        if "solution_summary" not in adapted and "solution" in adapted:
            adapted["solution_summary"] = adapted["solution"]
        if "difficulty_level" not in adapted and "difficulty" in adapted:
            adapted["difficulty_level"] = adapted["difficulty"]
        if "visibility_status" not in adapted:
            is_pub = adapted.get("is_published", True)
            adapted["visibility_status"] = "published" if is_pub else "draft"
        if adapted.get("visibility_status") == "published" and not adapted.get("published_at"):
            adapted["published_at"] = datetime.now(IST).isoformat()
    elif table_name == "jobs":
        if "service_request_id" not in adapted and "request_id" in adapted:
            adapted["service_request_id"] = adapted["request_id"]
    elif table_name == "job_status_history":
        if "status" not in adapted and "to_status" in adapted:
            adapted["status"] = adapted["to_status"]
        if "changed_at" not in adapted:
            adapted["changed_at"] = adapted.get("created_at") or datetime.now(IST).isoformat()
    elif table_name == "verifications":
        if not adapted.get("verification_type"):
            adapted["verification_type"] = "customer_confirmation"
        if not adapted.get("verification_status"):
            adapted["verification_status"] = adapted.get("status") or "verified"
    elif table_name == "problem_fingerprints":
        if "embedding_status" not in adapted or adapted.get("embedding_status") == "completed":
            adapted["embedding_status"] = "pending"
    elif table_name == "match_results":
        wid = str(adapted.get("worker_id", ""))
        if wid in ("cccccccc-cccc-cccc-cccc-cccccccccc01", "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb01"):
            adapted["worker_id"] = "81280d57-947f-490c-825a-c2c6b8d3cc3c"
        elif wid in ("cccccccc-cccc-cccc-cccc-cccccccccc02", "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb02"):
            adapted["worker_id"] = "9bfe05be-8fe9-463f-862e-a3b7c44563c1"
    elif table_name == "notifications":
        type_mapping = {
            "new_request": "service_request_received",
            "request_accepted": "service_request_accepted",
            "request_rejected": "service_request_rejected",
            "verification_required": "verification_requested",
            "job_disputed": "service_request_rejected",
        }
        raw_type = adapted.get("notification_type") or adapted.get("type", "match_found")
        adapted["notification_type"] = type_mapping.get(raw_type, raw_type)
        if adapted["notification_type"] not in {
            'job_started', 'job_completed', 'service_request_received', 
            'service_request_accepted', 'service_request_rejected', 
            'verification_requested', 'verification_completed', 'match_found'
        }:
            adapted["notification_type"] = "match_found"

    valid_cols = TABLE_COLUMNS.get(table_name)
    clean = {}
    for k, v in adapted.items():
        if valid_cols and k not in valid_cols:
            continue
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            clean[k] = v.astimezone(IST).isoformat()
        elif isinstance(v, date):
            clean[k] = v.isoformat()
        elif isinstance(v, uuid.UUID):
            clean[k] = str(v)
        else:
            clean[k] = v
    return clean

class SupabaseDataStore:
    """
    Transactional dual-mode store mirroring the exact 25 PostgreSQL tables.
    When live Supabase credentials are provided, writes/reads sync directly with Supabase.
    """
    def __init__(self):
        # Exactly 25 Tables
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self.worker_profiles: Dict[str, Dict[str, Any]] = {}
        self.skills: Dict[str, Dict[str, Any]] = {}
        self.worker_skills: Dict[str, Dict[str, Any]] = {}
        self.certificates: Dict[str, Dict[str, Any]] = {}
        self.problems: Dict[str, Dict[str, Any]] = {}
        self.problem_media: Dict[str, Dict[str, Any]] = {}
        self.problem_fingerprints: Dict[str, Dict[str, Any]] = {}
        self.experiences: Dict[str, Dict[str, Any]] = {}
        self.experience_contexts: Dict[str, Dict[str, Any]] = {}
        self.experience_actions: Dict[str, Dict[str, Any]] = {}
        self.experience_outcomes: Dict[str, Dict[str, Any]] = {}
        self.experience_skills: Dict[str, Dict[str, Any]] = {}
        self.experience_media: Dict[str, Dict[str, Any]] = {}
        self.experience_embeddings: Dict[str, Dict[str, Any]] = {}
        self.service_requests: Dict[str, Dict[str, Any]] = {}
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.job_status_history: Dict[str, Dict[str, Any]] = {}
        self.verifications: Dict[str, Dict[str, Any]] = {}
        self.feedback: Dict[str, Dict[str, Any]] = {}
        self.knowledge_cases: Dict[str, Dict[str, Any]] = {}
        self.knowledge_case_media: Dict[str, Dict[str, Any]] = {}
        self.knowledge_case_embeddings: Dict[str, Dict[str, Any]] = {}
        self.match_results: Dict[str, Dict[str, Any]] = {}
        self.notifications: Dict[str, Dict[str, Any]] = {}

        self.supabase_client = None
        self._init_supabase_client()
        self.seed_defaults()
        self._fetch_from_supabase_if_available()

    def _init_supabase_client(self):
        url = settings.SUPABASE_URL
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
        if url and not url.startswith("https://your-project") and not url.startswith("https://xyzcompany"):
            try:
                from supabase import create_client
                self.supabase_client = create_client(url, key)
                logger.info(f"Connected to live Supabase project: {url}")
            except Exception as e:
                logger.warning(f"Could not connect to live Supabase ({e}). Using local store.")

    def sync_to_supabase(self, table_name: str, record: Dict[str, Any]):
        """Asynchronously or safely writes the record to live Supabase."""
        if not self.supabase_client:
            return
        try:
            clean_record = adapt_record_for_table(table_name, record)
            self.supabase_client.table(table_name).upsert(clean_record).execute()
        except Exception as e:
            logger.warning(f"Supabase sync warning for {table_name}: {e}")

    def _fetch_from_supabase_if_available(self):
        """Hydrates state from live Supabase if connected."""
        if not self.supabase_client:
            return
        try:
            # 1. Profiles
            res = self.supabase_client.table("profiles").select("*").execute()
            if res.data:
                for row in res.data:
                    row_id = str(row["id"])
                    email = f"{row.get('display_name', 'user').lower().replace(' ', '.')}@kaushalsetu.in"
                    if row_id == "673c60cc-51f0-4c34-b05e-75c8fd8762f6":
                        email = "customer@kaushalsetu.in"
                    elif row_id == "81280d57-947f-490c-825a-c2c6b8d3cc3c":
                        email = "ramesh.verma@kaushalsetu.in"
                    elif row_id == "9bfe05be-8fe9-463f-862e-a3b7c44563c1":
                        email = "suresh.kumar@kaushalsetu.in"
                    self.profiles[row_id] = {
                        **row,
                        "full_name": row.get("display_name") or "User",
                        "email": email
                    }
            
            # 2. Worker Profiles
            res_wp = self.supabase_client.table("worker_profiles").select("*").execute()
            if res_wp.data:
                for row in res_wp.data:
                    wid = str(row["user_id"])
                    self.worker_profiles[wid] = {
                        **row,
                        "id": wid,
                        "user_id": wid,
                        "headline": row.get("professional_title") or "Repair Specialist",
                        "experience_years": row.get("years_experience") or 5,
                        "is_available": row.get("availability_status") == "available",
                        "hourly_rate": 450.0,
                        "rating": 4.9,
                        "total_reviews": 42
                    }

            # 3. Problems
            res_p = self.supabase_client.table("problems").select("*").execute()
            if res_p.data:
                for row in res_p.data:
                    self.problems[str(row["id"])] = row

            # Problem Fingerprints
            res_pf = self.supabase_client.table("problem_fingerprints").select("*").execute()
            if res_pf.data:
                for row in res_pf.data:
                    self.problem_fingerprints[str(row["id"])] = row

            # 4. Service Requests
            res_sr = self.supabase_client.table("service_requests").select("*").execute()
            if res_sr.data:
                for row in res_sr.data:
                    self.service_requests[str(row["id"])] = row

            # 5. Jobs
            res_j = self.supabase_client.table("jobs").select("*").execute()
            if res_j.data:
                for row in res_j.data:
                    sr = self.service_requests.get(str(row.get("service_request_id")), {})
                    prob = self.problems.get(str(sr.get("problem_id")), {})
                    self.jobs[str(row["id"])] = {
                        **row,
                        "customer_id": prob.get("customer_id") or row.get("customer_id"),
                        "worker_id": sr.get("worker_id") or row.get("worker_id"),
                        "problem_id": sr.get("problem_id") or row.get("problem_id")
                    }

            # 6. Knowledge Cases
            res_kc = self.supabase_client.table("knowledge_cases").select("*").execute()
            if res_kc.data:
                for row in res_kc.data:
                    self.knowledge_cases[str(row["id"])] = row

            # 7. Worker Skills
            res_ws = self.supabase_client.table("worker_skills").select("*").execute()
            if res_ws.data:
                for row in res_ws.data:
                    ws_id = str(row.get("id") or uuid.uuid5(uuid.NAMESPACE_DNS, f"{row['worker_id']}_{row['skill_id']}"))
                    self.worker_skills[ws_id] = {
                        "id": ws_id,
                        "worker_id": str(row["worker_id"]),
                        "skill_id": str(row["skill_id"]),
                        "proficiency_level": row.get("proficiency_level") or "intermediate",
                        "verified": row.get("verified", False),
                        "created_at": row.get("created_at") or datetime.now(IST)
                    }

            # 8. Certificates
            res_cert = self.supabase_client.table("certificates").select("*").execute()
            if res_cert.data:
                for row in res_cert.data:
                    cid = str(row["id"])
                    self.certificates[cid] = {
                        "id": cid,
                        "worker_id": str(row["worker_id"]),
                        "title": row.get("title") or row.get("certificate_name") or "Certificate",
                        "certificate_name": row.get("certificate_name") or row.get("title") or "Certificate",
                        "issuing_organization": row.get("issuing_organization") or "Organization",
                        "issue_date": row.get("issue_date"),
                        "expiry_date": row.get("expiry_date"),
                        "credential_url": row.get("credential_url") or row.get("certificate_url"),
                        "storage_path": row.get("storage_path"),
                        "is_verified": row.get("is_verified", False) or (row.get("verification_status") == "verified"),
                        "created_at": row.get("created_at") or datetime.now(IST)
                    }

            # 9. Feedback
            res_fb = self.supabase_client.table("feedback").select("*").execute()
            if res_fb.data:
                for row in res_fb.data:
                    self.feedback[str(row["id"])] = row

            # 10. Notifications
            res_notif = self.supabase_client.table("notifications").select("*").execute()
            if res_notif.data:
                for row in res_notif.data:
                    self.notifications[str(row["id"])] = row

            logger.info(f"Hydrated {len(self.profiles)} profiles, {len(self.worker_skills)} worker skills, and {len(self.certificates)} certificates from Supabase.")
        except Exception as e:
            logger.warning(f"Notice: Supabase hydration warning: {e}")

    def seed_defaults(self):
        now = datetime.now(IST)
        
        # 1. Skills
        skill1_id = "11111111-1111-1111-1111-111111110001"
        skill2_id = "11111111-1111-1111-1111-111111110002"
        skill3_id = "11111111-1111-1111-1111-111111110003"
        skill4_id = "11111111-1111-1111-1111-111111110004"
        skill5_id = "11111111-1111-1111-1111-111111110005"
        
        self.skills[skill1_id] = {
            "id": skill1_id, "name": "Board-Level Soldering", "category": "Electronics",
            "description": "SMD component rework, micro-soldering, BGA rework", "is_active": True, "created_at": now
        }
        self.skills[skill2_id] = {
            "id": skill2_id, "name": "Power Supply Diagnostics", "category": "Electronics",
            "description": "SMPS testing, capacitor replacements, rail voltage analysis", "is_active": True, "created_at": now
        }
        self.skills[skill3_id] = {
            "id": skill3_id, "name": "Short Circuit Tracing", "category": "Electrical",
            "description": "Thermal camera inspection, multimeter diode mode tracing", "is_active": True, "created_at": now
        }
        self.skills[skill4_id] = {
            "id": skill4_id, "name": "Inverter & UPS Repair", "category": "Power Systems",
            "description": "Pure sine wave inverter fault analysis, MOSFET replacement", "is_active": True, "created_at": now
        }
        self.skills[skill5_id] = {
            "id": skill5_id, "name": "Home Appliance Wiring", "category": "Electrical",
            "description": "Distribution board installation, MCB tripping diagnosis", "is_active": True, "created_at": now
        }

        # 2. Demo Customer (Live Supabase ID)
        cust_id = "673c60cc-51f0-4c34-b05e-75c8fd8762f6"
        self.profiles[cust_id] = {
            "id": cust_id, "role": "customer", "full_name": "Rahul Sharma", "display_name": "Rahul Sharma",
            "email": "customer@kaushalsetu.in", "phone": "+91 9876543210",
            "avatar_url": None, "created_at": now, "updated_at": now
        }
        # Backward-compatibility alias for local tests
        self.profiles["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"] = self.profiles[cust_id]

        # 3. Demo Worker 1 - Ramesh Verma (Live Supabase ID)
        w1_user_id = "81280d57-947f-490c-825a-c2c6b8d3cc3c"
        w1_worker_id = w1_user_id
        self.profiles[w1_user_id] = {
            "id": w1_user_id, "role": "worker", "full_name": "Ramesh Verma", "display_name": "Ramesh Verma",
            "email": "ramesh.verma@kaushalsetu.in", "phone": "+91 9876500001",
            "avatar_url": None, "created_at": now, "updated_at": now
        }
        self.worker_profiles[w1_worker_id] = {
            "id": w1_worker_id, "user_id": w1_user_id,
            "headline": "Senior Board Repair Specialist & Electrician",
            "professional_title": "Senior Board Repair Specialist & Electrician",
            "bio": "12+ years experience in PCB board-level diagnosis, micro-soldering, and home inverter circuitry.",
            "experience_years": 12, "years_experience": 12, "hourly_rate": 550.0, "service_radius_km": 15.0,
            "latitude": 19.0760, "longitude": 72.8777, "locality": "Bandra West",
            "city": "Mumbai", "state": "Maharashtra", "postal_code": "400050",
            "is_available": True, "availability_status": "available", "is_verified": True, "rating": 4.90, "total_reviews": 48,
            "created_at": now, "updated_at": now
        }
        self.profiles["bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb01"] = self.profiles[w1_user_id]
        self.worker_profiles["cccccccc-cccc-cccc-cccc-cccccccccc01"] = self.worker_profiles[w1_worker_id]
        
        ws1_id = str(uuid.uuid4())
        self.worker_skills[ws1_id] = {
            "id": ws1_id, "worker_id": w1_worker_id, "skill_id": skill1_id,
            "proficiency_level": "expert", "verified": True, "created_at": now
        }
        ws2_id = str(uuid.uuid4())
        self.worker_skills[ws2_id] = {
            "id": ws2_id, "worker_id": w1_worker_id, "skill_id": skill2_id,
            "proficiency_level": "expert", "verified": True, "created_at": now
        }
        ws3_id = str(uuid.uuid4())
        self.worker_skills[ws3_id] = {
            "id": ws3_id, "worker_id": w1_worker_id, "skill_id": skill3_id,
            "proficiency_level": "expert", "verified": True, "created_at": now
        }

        cert1_id = str(uuid.uuid4())
        self.certificates[cert1_id] = {
            "id": cert1_id, "worker_id": w1_worker_id,
            "title": "Advanced Micro-Soldering Certification (IPC-7711/7721)",
            "certificate_name": "Advanced Micro-Soldering Certification (IPC-7711/7721)",
            "issuing_organization": "National Electronics Association",
            "issue_date": "2021-06-15", "expiry_date": None,
            "credential_url": "https://credentials.example.org/ipc-7711-rv",
            "certificate_url": "https://credentials.example.org/ipc-7711-rv",
            "storage_path": None, "is_verified": True, "created_at": now
        }

        # 4. Demo Worker 2 - Suresh Kumar (Live Supabase ID)
        w2_user_id = "9bfe05be-8fe9-463f-862e-a3b7c44563c1"
        w2_worker_id = w2_user_id
        self.profiles[w2_user_id] = {
            "id": w2_user_id, "role": "worker", "full_name": "Suresh Kumar", "display_name": "Suresh Kumar",
            "email": "suresh.kumar@kaushalsetu.in", "phone": "+91 9876500002",
            "avatar_url": None, "created_at": now, "updated_at": now
        }
        self.worker_profiles[w2_worker_id] = {
            "id": w2_worker_id, "user_id": w2_user_id,
            "headline": "Certified Electrical & Inverter Specialist",
            "professional_title": "Certified Electrical & Inverter Specialist",
            "bio": "ITI certified electrician specializing in household wiring, tripping faults, and motor rewinding.",
            "experience_years": 8, "years_experience": 8, "hourly_rate": 400.0, "service_radius_km": 12.0,
            "latitude": 19.0800, "longitude": 72.8800, "locality": "Kurla",
            "city": "Mumbai", "state": "Maharashtra", "postal_code": "400070",
            "is_available": True, "availability_status": "available", "is_verified": True, "rating": 4.75, "total_reviews": 31,
            "created_at": now, "updated_at": now
        }
        self.profiles["bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb02"] = self.profiles[w2_user_id]
        self.worker_profiles["cccccccc-cccc-cccc-cccc-cccccccccc02"] = self.worker_profiles[w2_worker_id]

        ws4_id = str(uuid.uuid4())
        self.worker_skills[ws4_id] = {
            "id": ws4_id, "worker_id": w2_worker_id, "skill_id": skill4_id,
            "proficiency_level": "expert", "verified": True, "created_at": now
        }
        ws5_id = str(uuid.uuid4())
        self.worker_skills[ws5_id] = {
            "id": ws5_id, "worker_id": w2_worker_id, "skill_id": skill5_id,
            "proficiency_level": "advanced", "verified": True, "created_at": now
        }

        # 5. Verified Experience for Worker 1
        exp1_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01"
        self.experiences[exp1_id] = {
            "id": exp1_id, "worker_id": w1_worker_id,
            "title": "Samsung Galaxy S23 Power Rail Short Circuit Repair",
            "problem_description": "Dead phone drawing 0mA after drop; short on VDD_MAIN rail traced to damaged PMIC decoupling capacitor.",
            "diagnosis": "Dead phone drawing 0mA after drop; short on VDD_MAIN rail traced to damaged PMIC decoupling capacitor.",
            "repair_type": "board-level component replacement", "device_category": "Smartphone / Electronics",
            "brand": "Samsung", "model": "Galaxy S23", "difficulty": "advanced",
            "verification_status": "verified", "experience_status": "verified", "created_at": now, "updated_at": now
        }

        # 6. Knowledge Hub Seed Cases
        kc1_id = "dddddddd-dddd-dddd-dddd-dddddddddd01"
        self.knowledge_cases[kc1_id] = {
            "id": kc1_id, "worker_id": w1_worker_id, "experience_id": exp1_id,
            "title": "Samsung S23 No Power After Physical Drop",
            "problem_summary": "Device completely dead following a drop, drawing 0mA on DC power supply.",
            "diagnosis_summary": "Primary power management IC (PMIC) cracked under shielding bracket, VBAT rail shorted to ground.",
            "solution_summary": "Carefully lifted the shield with hot air at 320C, replaced damaged PMIC and decoupling capacitor C4021.",
            "lesson_learned": "Always inspect the inductor pads next to PMIC for trace hairline fractures after drop impact.",
            "difficulty_level": "advanced", "difficulty": "advanced",
            "device_category": "Smartphone / PCB",
            "brand": "Samsung", "model": "Galaxy S23",
            "visibility_status": "published", "is_published": True, "is_verified": True, "view_count": 142,
            "created_at": now, "updated_at": now
        }

        kc2_id = "dddddddd-dddd-dddd-dddd-dddddddddd02"
        self.knowledge_cases[kc2_id] = {
            "id": kc2_id, "worker_id": w2_worker_id, "experience_id": None,
            "title": "Luminous 1100VA Inverter Continuous Overload Alarm",
            "problem_summary": "Inverter beeps continuously indicating overload even with zero connected load on backup.",
            "diagnosis_summary": "Damaged MOSFET pair on the primary H-bridge stage causing feedback loop sensing anomaly.",
            "solution_summary": "Replaced IRF3205 MOSFETs and 10 ohm gate resistors. Tested inverter under 600W resistive load.",
            "lesson_learned": "Always replace gate driver resistors in pairs whenever MOSFETs fail in an inverter circuit.",
            "difficulty_level": "intermediate", "difficulty": "intermediate",
            "device_category": "Power Inverter",
            "brand": "Luminous", "model": "Zelio 1100",
            "visibility_status": "published", "is_published": True, "is_verified": True, "view_count": 89,
            "created_at": now, "updated_at": now
        }

db = SupabaseDataStore()
