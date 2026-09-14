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
        
        # 1. Skills (6 canonical skills)
        skill1_id = "11111111-1111-1111-1111-111111110001"
        skill2_id = "11111111-1111-1111-1111-111111110002"
        skill3_id = "11111111-1111-1111-1111-111111110003"
        skill4_id = "11111111-1111-1111-1111-111111110004"
        skill5_id = "11111111-1111-1111-1111-111111110005"
        skill6_id = "11111111-1111-1111-1111-111111110006"
        
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
        self.skills[skill6_id] = {
            "id": skill6_id, "name": "Smart TV Panel & T-Con Repair", "category": "Consumer Electronics",
            "description": "T-Con board diagnostics, COF bonding, LED backlight strip replacement", "is_active": True, "created_at": now
        }

        # 2. Demo Customer (Live Supabase ID + Alias)
        cust_id = "673c60cc-51f0-4c34-b05e-75c8fd8762f6"
        self.profiles[cust_id] = {
            "id": cust_id, "role": "customer", "full_name": "Rahul Sharma", "display_name": "Rahul Sharma",
            "email": "customer@kaushalsetu.in", "phone": "+91 9876543210",
            "avatar_url": None, "created_at": now, "updated_at": now
        }
        self.profiles["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"] = self.profiles[cust_id]

        # --------------------------------------------------------------------
        # 3. WORKER A — Ramesh Verma (Tier 1 - Master Board Repair Specialist)
        # --------------------------------------------------------------------
        w1_id = "81280d57-947f-490c-825a-c2c6b8d3cc3c"
        self.profiles[w1_id] = {
            "id": w1_id, "role": "worker", "full_name": "Ramesh Verma", "display_name": "Ramesh Verma",
            "email": "ramesh.verma@kaushalsetu.in", "phone": "+91 9876500001",
            "avatar_url": None, "created_at": now, "updated_at": now
        }
        self.worker_profiles[w1_id] = {
            "id": w1_id, "user_id": w1_id,
            "headline": "Senior Board Repair Specialist & Mobile Diagnostics",
            "professional_title": "Senior Board Repair Specialist & Mobile Diagnostics",
            "bio": "12+ years experience in PCB board-level diagnosis, micro-soldering, and smartphone power rail troubleshooting.",
            "experience_years": 12, "years_experience": 12, "hourly_rate": 550.0, "service_radius_km": 15.0,
            "latitude": 19.0760, "longitude": 72.8777, "locality": "Bandra West",
            "city": "Mumbai", "state": "Maharashtra", "postal_code": "400050",
            "is_available": True, "availability_status": "available", "is_verified": True, "rating": 4.90, "total_reviews": 48,
            "created_at": now, "updated_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w1_id}_{skill1_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w1_id}_{skill1_id}")), "worker_id": w1_id, "skill_id": skill1_id,
            "proficiency_level": "expert", "verified": True, "created_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w1_id}_{skill2_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w1_id}_{skill2_id}")), "worker_id": w1_id, "skill_id": skill2_id,
            "proficiency_level": "expert", "verified": True, "created_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w1_id}_{skill3_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w1_id}_{skill3_id}")), "worker_id": w1_id, "skill_id": skill3_id,
            "proficiency_level": "expert", "verified": True, "created_at": now
        }
        cert1_id = "f1111111-1111-1111-1111-111111110001"
        self.certificates[cert1_id] = {
            "id": cert1_id, "worker_id": w1_id, "title": "Advanced Micro-Soldering Certification (IPC-7711/7721)",
            "certificate_name": "Advanced Micro-Soldering Certification (IPC-7711/7721)", "issuing_organization": "National Electronics Association",
            "issue_date": "2021-06-15", "expiry_date": None, "credential_url": "https://credentials.example.org/ipc-7711-rv",
            "certificate_url": "https://credentials.example.org/ipc-7711-rv", "storage_path": None, "is_verified": True, "created_at": now
        }

        # --------------------------------------------------------------------
        # 4. WORKER B — Suresh Kumar (Tier 4 - Power Systems & Inverter Specialist)
        # --------------------------------------------------------------------
        w2_id = "9bfe05be-8fe9-463f-862e-a3b7c44563c1"
        self.profiles[w2_id] = {
            "id": w2_id, "role": "worker", "full_name": "Suresh Kumar", "display_name": "Suresh Kumar",
            "email": "suresh.kumar@kaushalsetu.in", "phone": "+91 9876500002",
            "avatar_url": None, "created_at": now, "updated_at": now
        }
        self.worker_profiles[w2_id] = {
            "id": w2_id, "user_id": w2_id,
            "headline": "Certified Electrical & Inverter Specialist",
            "professional_title": "Certified Electrical & Inverter Specialist",
            "bio": "ITI certified electrician specializing in household wiring, inverter PCB power overload, and motor rewinding.",
            "experience_years": 8, "years_experience": 8, "hourly_rate": 400.0, "service_radius_km": 12.0,
            "latitude": 19.0800, "longitude": 72.8800, "locality": "Kurla",
            "city": "Mumbai", "state": "Maharashtra", "postal_code": "400070",
            "is_available": True, "availability_status": "available", "is_verified": True, "rating": 4.75, "total_reviews": 31,
            "created_at": now, "updated_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w2_id}_{skill4_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w2_id}_{skill4_id}")), "worker_id": w2_id, "skill_id": skill4_id,
            "proficiency_level": "expert", "verified": True, "created_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w2_id}_{skill5_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w2_id}_{skill5_id}")), "worker_id": w2_id, "skill_id": skill5_id,
            "proficiency_level": "advanced", "verified": True, "created_at": now
        }
        cert2_id = "f1111111-1111-1111-1111-111111110002"
        self.certificates[cert2_id] = {
            "id": cert2_id, "worker_id": w2_id, "title": "National Trade Certificate (NTC) Electrician",
            "certificate_name": "National Trade Certificate (NTC) Electrician", "issuing_organization": "National Council for Vocational Training",
            "issue_date": "2018-08-20", "expiry_date": None, "credential_url": "https://credentials.example.org/ntc-sk",
            "certificate_url": "https://credentials.example.org/ntc-sk", "storage_path": None, "is_verified": True, "created_at": now
        }

        # --------------------------------------------------------------------
        # 5. WORKER C — Vikram Singh (Tier 5 - General Electrician)
        # --------------------------------------------------------------------
        w3_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb03"
        self.profiles[w3_id] = {
            "id": w3_id, "role": "worker", "full_name": "Vikram Singh", "display_name": "Vikram Singh",
            "email": "vikram.singh@kaushalsetu.in", "phone": "+91 9876500003",
            "avatar_url": None, "created_at": now, "updated_at": now
        }
        self.worker_profiles[w3_id] = {
            "id": w3_id, "user_id": w3_id,
            "headline": "General House Electrician & Wiring Technician",
            "professional_title": "General House Electrician & Wiring Technician",
            "bio": "Specialized in residential wiring installation, switchboard repair, MCB replacement, and house earthing.",
            "experience_years": 6, "years_experience": 6, "hourly_rate": 350.0, "service_radius_km": 10.0,
            "latitude": 19.0400, "longitude": 72.8500, "locality": "Dharavi",
            "city": "Mumbai", "state": "Maharashtra", "postal_code": "400017",
            "is_available": True, "availability_status": "available", "is_verified": False, "rating": 4.50, "total_reviews": 18,
            "created_at": now, "updated_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w3_id}_{skill5_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w3_id}_{skill5_id}")), "worker_id": w3_id, "skill_id": skill5_id,
            "proficiency_level": "intermediate", "verified": False, "created_at": now
        }

        # --------------------------------------------------------------------
        # 6. WORKER D — Amit Shah (Tier 2 - Smartphone Repair Specialist)
        # --------------------------------------------------------------------
        w4_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb04"
        self.profiles[w4_id] = {
            "id": w4_id, "role": "worker", "full_name": "Amit Shah", "display_name": "Amit Shah",
            "email": "amit.shah@kaushalsetu.in", "phone": "+91 9876500004",
            "avatar_url": None, "created_at": now, "updated_at": now
        }
        self.worker_profiles[w4_id] = {
            "id": w4_id, "user_id": w4_id,
            "headline": "Smartphone Motherboard & Power Fault Specialist",
            "professional_title": "Smartphone Motherboard & Power Fault Specialist",
            "bio": "Expert in Samsung & Android device troubleshooting, board-level power diagnostics, and drop damage repairs.",
            "experience_years": 9, "years_experience": 9, "hourly_rate": 500.0, "service_radius_km": 14.0,
            "latitude": 19.1190, "longitude": 72.8470, "locality": "Andheri West",
            "city": "Mumbai", "state": "Maharashtra", "postal_code": "400058",
            "is_available": True, "availability_status": "available", "is_verified": True, "rating": 4.85, "total_reviews": 39,
            "created_at": now, "updated_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w4_id}_{skill1_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w4_id}_{skill1_id}")), "worker_id": w4_id, "skill_id": skill1_id,
            "proficiency_level": "expert", "verified": True, "created_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w4_id}_{skill2_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w4_id}_{skill2_id}")), "worker_id": w4_id, "skill_id": skill2_id,
            "proficiency_level": "advanced", "verified": True, "created_at": now
        }

        # --------------------------------------------------------------------
        # 7. WORKER E — Neha Patel (Tier 2 - Electronics / PCB Repair Specialist)
        # --------------------------------------------------------------------
        w5_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb05"
        self.profiles[w5_id] = {
            "id": w5_id, "role": "worker", "full_name": "Neha Patel", "display_name": "Neha Patel",
            "email": "neha.patel@kaushalsetu.in", "phone": "+91 9876500005",
            "avatar_url": None, "created_at": now, "updated_at": now
        }
        self.worker_profiles[w5_id] = {
            "id": w5_id, "user_id": w5_id,
            "headline": "PCB Power Circuit & Micro-Electronics Engineer",
            "professional_title": "PCB Power Circuit & Micro-Electronics Engineer",
            "bio": "Specialized in micro-soldering, short circuit tracing, and electronic board power fault rectification.",
            "experience_years": 7, "years_experience": 7, "hourly_rate": 480.0, "service_radius_km": 12.0,
            "latitude": 19.1170, "longitude": 72.9050, "locality": "Powai",
            "city": "Mumbai", "state": "Maharashtra", "postal_code": "400076",
            "is_available": True, "availability_status": "available", "is_verified": True, "rating": 4.80, "total_reviews": 27,
            "created_at": now, "updated_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w5_id}_{skill1_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w5_id}_{skill1_id}")), "worker_id": w5_id, "skill_id": skill1_id,
            "proficiency_level": "advanced", "verified": True, "created_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w5_id}_{skill3_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w5_id}_{skill3_id}")), "worker_id": w5_id, "skill_id": skill3_id,
            "proficiency_level": "expert", "verified": True, "created_at": now
        }

        # --------------------------------------------------------------------
        # 8. WORKER F — Arjun Rao (Tier 3 - Mobile Display & Charging Technician)
        # --------------------------------------------------------------------
        w6_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb06"
        self.profiles[w6_id] = {
            "id": w6_id, "role": "worker", "full_name": "Arjun Rao", "display_name": "Arjun Rao",
            "email": "arjun.rao@kaushalsetu.in", "phone": "+91 9876500006",
            "avatar_url": None, "created_at": now, "updated_at": now
        }
        self.worker_profiles[w6_id] = {
            "id": w6_id, "user_id": w6_id,
            "headline": "Mobile Display & Charging Port Repair Technician",
            "professional_title": "Mobile Display & Charging Port Repair Technician",
            "bio": "Focused on smartphone screen replacements, USB-C charging IC replacements, and battery servicing.",
            "experience_years": 5, "years_experience": 5, "hourly_rate": 380.0, "service_radius_km": 10.0,
            "latitude": 19.0180, "longitude": 72.8430, "locality": "Dadar",
            "city": "Mumbai", "state": "Maharashtra", "postal_code": "400028",
            "is_available": True, "availability_status": "available", "is_verified": False, "rating": 4.60, "total_reviews": 22,
            "created_at": now, "updated_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w6_id}_{skill2_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w6_id}_{skill2_id}")), "worker_id": w6_id, "skill_id": skill2_id,
            "proficiency_level": "intermediate", "verified": False, "created_at": now
        }

        # --------------------------------------------------------------------
        # 9. WORKER G — Priya Nair (Tier 3 - TV & Consumer Electronics Specialist)
        # --------------------------------------------------------------------
        w7_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb07"
        self.profiles[w7_id] = {
            "id": w7_id, "role": "worker", "full_name": "Priya Nair", "display_name": "Priya Nair",
            "email": "priya.nair@kaushalsetu.in", "phone": "+91 9876500007",
            "avatar_url": None, "created_at": now, "updated_at": now
        }
        self.worker_profiles[w7_id] = {
            "id": w7_id, "user_id": w7_id,
            "headline": "Smart TV & Consumer Electronics Board Specialist",
            "professional_title": "Smart TV & Consumer Electronics Board Specialist",
            "bio": "Expert in Samsung Smart TV power boards, T-Con panels, and home media electronics troubleshooting.",
            "experience_years": 8, "years_experience": 8, "hourly_rate": 450.0, "service_radius_km": 15.0,
            "latitude": 19.2180, "longitude": 72.9780, "locality": "Thane West",
            "city": "Mumbai", "state": "Maharashtra", "postal_code": "400601",
            "is_available": True, "availability_status": "available", "is_verified": True, "rating": 4.75, "total_reviews": 33,
            "created_at": now, "updated_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w7_id}_{skill2_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w7_id}_{skill2_id}")), "worker_id": w7_id, "skill_id": skill2_id,
            "proficiency_level": "advanced", "verified": True, "created_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w7_id}_{skill6_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w7_id}_{skill6_id}")), "worker_id": w7_id, "skill_id": skill6_id,
            "proficiency_level": "expert", "verified": True, "created_at": now
        }

        # --------------------------------------------------------------------
        # 10. WORKER H — Mehul Chhabra (Tier 4 - Inverter & UPS Power Systems)
        # --------------------------------------------------------------------
        w8_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb08"
        self.profiles[w8_id] = {
            "id": w8_id, "role": "worker", "full_name": "Mehul Chhabra", "display_name": "Mehul Chhabra",
            "email": "mehul.chhabra@kaushalsetu.in", "phone": "+91 9876500008",
            "avatar_url": None, "created_at": now, "updated_at": now
        }
        self.worker_profiles[w8_id] = {
            "id": w8_id, "user_id": w8_id,
            "headline": "Industrial Inverter & Heavy UPS Systems Engineer",
            "professional_title": "Industrial Inverter & Heavy UPS Systems Engineer",
            "bio": "Specialized in high-voltage power backups, commercial inverters, battery bank maintenance, and overload circuits.",
            "experience_years": 10, "years_experience": 10, "hourly_rate": 520.0, "service_radius_km": 18.0,
            "latitude": 19.0330, "longitude": 73.0290, "locality": "Vashi",
            "city": "Navi Mumbai", "state": "Maharashtra", "postal_code": "400703",
            "is_available": True, "availability_status": "available", "is_verified": True, "rating": 4.88, "total_reviews": 41,
            "created_at": now, "updated_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w8_id}_{skill4_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w8_id}_{skill4_id}")), "worker_id": w8_id, "skill_id": skill4_id,
            "proficiency_level": "expert", "verified": True, "created_at": now
        }

        # --------------------------------------------------------------------
        # 11. WORKER I — Karan Joshi (Tier 5 - Electrical Diagnostics & Tracing)
        # --------------------------------------------------------------------
        w9_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb09"
        self.profiles[w9_id] = {
            "id": w9_id, "role": "worker", "full_name": "Karan Joshi", "display_name": "Karan Joshi",
            "email": "karan.joshi@kaushalsetu.in", "phone": "+91 9876500009",
            "avatar_url": None, "created_at": now, "updated_at": now
        }
        self.worker_profiles[w9_id] = {
            "id": w9_id, "user_id": w9_id,
            "headline": "Household Electrical Fault & Short Circuit Specialist",
            "professional_title": "Household Electrical Fault & Short Circuit Specialist",
            "bio": "Expert in home electrical wiring short circuit detection, MCB/ELCB tripping, and phase imbalance troubleshooting.",
            "experience_years": 7, "years_experience": 7, "hourly_rate": 420.0, "service_radius_km": 12.0,
            "latitude": 19.2300, "longitude": 72.8560, "locality": "Borivali West",
            "city": "Mumbai", "state": "Maharashtra", "postal_code": "400092",
            "is_available": True, "availability_status": "available", "is_verified": True, "rating": 4.70, "total_reviews": 29,
            "created_at": now, "updated_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w9_id}_{skill3_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w9_id}_{skill3_id}")), "worker_id": w9_id, "skill_id": skill3_id,
            "proficiency_level": "advanced", "verified": True, "created_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w9_id}_{skill5_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w9_id}_{skill5_id}")), "worker_id": w9_id, "skill_id": skill5_id,
            "proficiency_level": "advanced", "verified": True, "created_at": now
        }

        # --------------------------------------------------------------------
        # 12. WORKER J — Sneha Kulkarni (Tier 5 - Home Electrical Wiring)
        # --------------------------------------------------------------------
        w10_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb10"
        self.profiles[w10_id] = {
            "id": w10_id, "role": "worker", "full_name": "Sneha Kulkarni", "display_name": "Sneha Kulkarni",
            "email": "sneha.kulkarni@kaushalsetu.in", "phone": "+91 9876500010",
            "avatar_url": None, "created_at": now, "updated_at": now
        }
        self.worker_profiles[w10_id] = {
            "id": w10_id, "user_id": w10_id,
            "headline": "Residential Wiring & Switchboard Repair Technician",
            "professional_title": "Residential Wiring & Switchboard Repair Technician",
            "bio": "Certified electrician focusing on residential switchboard installations, light fixtures, and basic appliance wiring.",
            "experience_years": 4, "years_experience": 4, "hourly_rate": 320.0, "service_radius_km": 10.0,
            "latitude": 19.0620, "longitude": 72.8970, "locality": "Chembur",
            "city": "Mumbai", "state": "Maharashtra", "postal_code": "400071",
            "is_available": True, "availability_status": "available", "is_verified": False, "rating": 4.55, "total_reviews": 15,
            "created_at": now, "updated_at": now
        }
        self.worker_skills[str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w10_id}_{skill5_id}"))] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{w10_id}_{skill5_id}")), "worker_id": w10_id, "skill_id": skill5_id,
            "proficiency_level": "intermediate", "verified": False, "created_at": now
        }

        # --------------------------------------------------------------------
        # 13. EXPERIENCES (21 Total Experiences, 10 Verified)
        # --------------------------------------------------------------------
        
        # --- Worker A (Ramesh Verma) --- 3 Experiences (2 Verified)
        exp1_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01"
        self.experiences[exp1_id] = {
            "id": exp1_id, "worker_id": w1_id,
            "title": "Samsung Galaxy S23 Power Rail Short Circuit Repair",
            "problem_description": "Samsung Galaxy S23 fell down and now does not turn on. Device completely dead drawing 0mA; short on VDD_MAIN rail traced to damaged PMIC decoupling capacitor after drop.",
            "diagnosis": "Dead phone drawing 0mA after drop; short on VDD_MAIN rail traced to damaged PMIC decoupling capacitor.",
            "outcome_summary": "Replaced PMIC C4021 decoupling capacitor and restored full power boot.",
            "repair_type": "board-level component replacement", "device_category": "Smartphone / Electronics",
            "brand": "Samsung", "model": "Galaxy S23", "difficulty": "advanced",
            "verification_status": "verified", "experience_status": "verified", "verification_confidence": 0.95, "created_at": now, "updated_at": now
        }
        exp2_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee02"
        self.experiences[exp2_id] = {
            "id": exp2_id, "worker_id": w1_id,
            "title": "Samsung Galaxy S22 Ultra No Booting Post Impact",
            "problem_description": "Galaxy S22 Ultra dropped on hard surface. Screen black, motherboard short circuit detected.",
            "diagnosis": "Sub-PMIC short circuit due to hairline solder crack under power IC.",
            "outcome_summary": "Reballing Sub-PMIC IC chip restored device functionality and fast charging.",
            "repair_type": "micro-soldering & BGA reballing", "device_category": "Smartphone / Electronics",
            "brand": "Samsung", "model": "Galaxy S22 Ultra", "difficulty": "advanced",
            "verification_status": "verified", "experience_status": "verified", "verification_confidence": 0.92, "created_at": now, "updated_at": now
        }
        exp3_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee03"
        self.experiences[exp3_id] = {
            "id": exp3_id, "worker_id": w1_id,
            "title": "OnePlus 11 5G Dead Motherboard Recovery",
            "problem_description": "OnePlus 11 shut down suddenly after water splash, short circuit on charging line.",
            "diagnosis": "Corroded diode and shorted input capacitor on charging controller circuit.",
            "outcome_summary": "Cleaned corrosion, replaced Schottky diode and capacitor.",
            "repair_type": "SMD component rework", "device_category": "Smartphone / Electronics",
            "brand": "OnePlus", "model": "11 5G", "difficulty": "intermediate",
            "verification_status": "unverified", "experience_status": "submitted", "verification_confidence": 0.0, "created_at": now, "updated_at": now
        }

        # --- Worker B (Suresh Kumar) --- 2 Experiences (1 Verified)
        exp4_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee04"
        self.experiences[exp4_id] = {
            "id": exp4_id, "worker_id": w2_id,
            "title": "Luminous 1100VA Inverter Continuous Overload Repair",
            "problem_description": "Inverter beeps continuously indicating overload even with zero connected load on backup.",
            "diagnosis": "Damaged MOSFET pair on the primary H-bridge stage causing feedback loop sensing anomaly.",
            "outcome_summary": "Replaced IRF3205 MOSFETs and gate driver resistors; load test passed.",
            "repair_type": "power electronics PCB repair", "device_category": "Power Systems",
            "brand": "Luminous", "model": "Zelio 1100", "difficulty": "intermediate",
            "verification_status": "verified", "experience_status": "verified", "verification_confidence": 0.88, "created_at": now, "updated_at": now
        }
        exp5_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee05"
        self.experiences[exp5_id] = {
            "id": exp5_id, "worker_id": w2_id,
            "title": "Microtek UPS Battery Charging Board Repair",
            "problem_description": "UPS failing to charge battery during mains power availability.",
            "diagnosis": "Blown rectifier diode and failed relay on charging control section.",
            "outcome_summary": "Replaced 12V relay and power diode.",
            "repair_type": "component replacement", "device_category": "Power Systems",
            "brand": "Microtek", "model": "Heritage 1000", "difficulty": "intermediate",
            "verification_status": "unverified", "experience_status": "submitted", "verification_confidence": 0.0, "created_at": now, "updated_at": now
        }

        # --- Worker C (Vikram Singh) --- 2 Experiences (0 Verified)
        exp6_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee06"
        self.experiences[exp6_id] = {
            "id": exp6_id, "worker_id": w3_id,
            "title": "Residential Apartment Main Distribution Board Rewiring",
            "problem_description": "Frequent power tripping across kitchen power points under high load.",
            "diagnosis": "Loose neutral connection and overloaded 16A single-pole MCB.",
            "outcome_summary": "Upgraded MCB to 25A C-curve and rebalanced load across 3 phases.",
            "repair_type": "household electrical wiring", "device_category": "Home Electrical",
            "brand": "Havells", "model": "DB-12Way", "difficulty": "intermediate",
            "verification_status": "unverified", "experience_status": "submitted", "verification_confidence": 0.0, "created_at": now, "updated_at": now
        }
        exp7_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee07"
        self.experiences[exp7_id] = {
            "id": exp7_id, "worker_id": w3_id,
            "title": "Modular Switchboard Installation and Earthing Fix",
            "problem_description": "Light shocks felt on metallic casing of water heater switchboard.",
            "diagnosis": "Improper earthing resistance (>15 ohms) and corroded earthing wire connection.",
            "outcome_summary": "Replaced copper earthing wire and installed modular 6-gang switchboard.",
            "repair_type": "switchboard installation", "device_category": "Home Electrical",
            "brand": "Anchor", "model": "Roma Classic", "difficulty": "basic",
            "verification_status": "unverified", "experience_status": "submitted", "verification_confidence": 0.0, "created_at": now, "updated_at": now
        }

        # --- Worker D (Amit Shah) --- 2 Experiences (2 Verified)
        exp8_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee08"
        self.experiences[exp8_id] = {
            "id": exp8_id, "worker_id": w4_id,
            "title": "Samsung Galaxy S22 No Power After Hard Drop",
            "problem_description": "Samsung Galaxy S22 dropped down and became completely dead with no screen response.",
            "diagnosis": "Main power rail capacitor shorted due to physical impact near PM8350 IC.",
            "outcome_summary": "Removed shorted SMD capacitor and replaced PMIC power rail line.",
            "repair_type": "smartphone board repair", "device_category": "Smartphone / Electronics",
            "brand": "Samsung", "model": "Galaxy S22", "difficulty": "advanced",
            "verification_status": "verified", "experience_status": "verified", "verification_confidence": 0.94, "created_at": now, "updated_at": now
        }
        exp9_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee09"
        self.experiences[exp9_id] = {
            "id": exp9_id, "worker_id": w4_id,
            "title": "Samsung Galaxy A54 Charging Failure & Boot Loop",
            "problem_description": "Galaxy A54 stuck on charging logo and refusing to power on completely.",
            "diagnosis": "Damaged USB charging controller IC (OVP IC tripped).",
            "outcome_summary": "Replaced OVP IC and restored normal battery charging curve.",
            "repair_type": "board-level IC replacement", "device_category": "Smartphone / Electronics",
            "brand": "Samsung", "model": "Galaxy A54", "difficulty": "intermediate",
            "verification_status": "verified", "experience_status": "verified", "verification_confidence": 0.90, "created_at": now, "updated_at": now
        }

        # --- Worker E (Neha Patel) --- 2 Experiences (1 Verified)
        exp10_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee10"
        self.experiences[exp10_id] = {
            "id": exp10_id, "worker_id": w5_id,
            "title": "Smartphone Board-Level Power Fault & Short Rectification",
            "problem_description": "Android mobile device drawing excessive standby current, getting hot near CPU.",
            "diagnosis": "Short circuit on secondary power line VBAT_SENSE caused by cracked decoupling cap.",
            "outcome_summary": "Thermal imaging located shorted cap; replaced and restored normal current draw.",
            "repair_type": "short circuit tracing & cap replacement", "device_category": "Smartphone / Electronics",
            "brand": "Xiaomi", "model": "Redmi Note 12", "difficulty": "advanced",
            "verification_status": "verified", "experience_status": "verified", "verification_confidence": 0.91, "created_at": now, "updated_at": now
        }
        exp11_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee11"
        self.experiences[exp11_id] = {
            "id": exp11_id, "worker_id": w5_id,
            "title": "Damaged PCB Power Circuit Component Rework",
            "problem_description": "Tablet motherboard dead after non-genuine charger connected.",
            "diagnosis": "Burnt charging MOSFET and blown input fuse diode.",
            "outcome_summary": "Replaced protection diode and power MOSFET with SMD rework station.",
            "repair_type": "PCB power circuit rework", "device_category": "Electronics / PCB",
            "brand": "Lenovo", "model": "Tab M10", "difficulty": "intermediate",
            "verification_status": "unverified", "experience_status": "submitted", "verification_confidence": 0.0, "created_at": now, "updated_at": now
        }

        # --- Worker F (Arjun Rao) --- 2 Experiences (1 Verified)
        exp12_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee12"
        self.experiences[exp12_id] = {
            "id": exp12_id, "worker_id": w6_id,
            "title": "Samsung Galaxy S21 Ultra Cracked Display Replacement",
            "problem_description": "Samsung Galaxy S21 screen shattered after drop, touchscreen unresponsive.",
            "diagnosis": "FHD AMOLED panel glass fracture and digitizer ribbon tear.",
            "outcome_summary": "Installed original Samsung display assembly and recalibrated fingerprint sensor.",
            "repair_type": "display assembly replacement", "device_category": "Smartphone / Electronics",
            "brand": "Samsung", "model": "Galaxy S21 Ultra", "difficulty": "intermediate",
            "verification_status": "verified", "experience_status": "verified", "verification_confidence": 0.89, "created_at": now, "updated_at": now
        }
        exp13_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee13"
        self.experiences[exp13_id] = {
            "id": exp13_id, "worker_id": w6_id,
            "title": "Smartphone USB-C Charging Port Replacement",
            "problem_description": "Phone charges intermittently only when cable is held at specific angle.",
            "diagnosis": "Worn pin contacts and damaged flex cable connector inside Type-C port.",
            "outcome_summary": "Soldered new sub-board charging port connector.",
            "repair_type": "charging port replacement", "device_category": "Smartphone / Electronics",
            "brand": "Vivo", "model": "V25 Pro", "difficulty": "basic",
            "verification_status": "unverified", "experience_status": "submitted", "verification_confidence": 0.0, "created_at": now, "updated_at": now
        }

        # --- Worker G (Priya Nair) --- 2 Experiences (1 Verified)
        exp14_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee14"
        self.experiences[exp14_id] = {
            "id": exp14_id, "worker_id": w7_id,
            "title": "Samsung 55-inch Smart TV Power Supply Board Repair",
            "problem_description": "Samsung 4K TV standby LED blinking, screen fails to power on.",
            "diagnosis": "Blown electrolytic capacitors in SMPS secondary power section.",
            "outcome_summary": "Replaced low-ESR capacitors on SMPS board; TV powered up normally.",
            "repair_type": "TV power supply repair", "device_category": "Consumer Electronics / TV",
            "brand": "Samsung", "model": "UA55TU8000", "difficulty": "intermediate",
            "verification_status": "verified", "experience_status": "verified", "verification_confidence": 0.93, "created_at": now, "updated_at": now
        }
        exp15_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee15"
        self.experiences[exp15_id] = {
            "id": exp15_id, "worker_id": w7_id,
            "title": "LG LED TV T-Con Board Distortion Fixing",
            "problem_description": "Vertical colored lines appeared across LED TV screen.",
            "diagnosis": "T-Con board timing IC overheating and loose ribbon connector.",
            "outcome_summary": "Cleaned ribbon contacts and applied thermal paste to T-Con IC.",
            "repair_type": "T-Con board diagnostics", "device_category": "Consumer Electronics / TV",
            "brand": "LG", "model": "43UQ7550", "difficulty": "intermediate",
            "verification_status": "unverified", "experience_status": "submitted", "verification_confidence": 0.0, "created_at": now, "updated_at": now
        }

        # --- Worker H (Mehul Chhabra) --- 2 Experiences (1 Verified)
        exp16_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee16"
        self.experiences[exp16_id] = {
            "id": exp16_id, "worker_id": w8_id,
            "title": "Commercial 3KVA UPS Power Failure Diagnosis",
            "problem_description": "3KVA Online UPS shutting down instantly upon mains outage.",
            "diagnosis": "Degraded lead-acid battery bank cell short circuit and relay failure.",
            "outcome_summary": "Replaced 4x 12V batteries and recalibrated float charging voltage.",
            "repair_type": "UPS power system overhaul", "device_category": "Power Systems",
            "brand": "APC", "model": "Smart-UPS 3000", "difficulty": "advanced",
            "verification_status": "verified", "experience_status": "verified", "verification_confidence": 0.90, "created_at": now, "updated_at": now
        }
        exp17_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee17"
        self.experiences[exp17_id] = {
            "id": exp17_id, "worker_id": w8_id,
            "title": "Exide Inverter Overload Fault & Thermal Trip Fix",
            "problem_description": "Inverter tripping on thermal protection after 10 minutes of usage.",
            "diagnosis": "Clogged heat-sink cooling fan and dried thermal grease on MOSFET bridge.",
            "outcome_summary": "Replaced 12V DC cooling fan and reapplied thermal compound.",
            "repair_type": "inverter thermal system repair", "device_category": "Power Systems",
            "brand": "Exide", "model": "GXT 1050", "difficulty": "intermediate",
            "verification_status": "unverified", "experience_status": "submitted", "verification_confidence": 0.0, "created_at": now, "updated_at": now
        }

        # --- Worker I (Karan Joshi) --- 2 Experiences (1 Verified)
        exp18_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee18"
        self.experiences[exp18_id] = {
            "id": exp18_id, "worker_id": w9_id,
            "title": "Household Main MCB Tripping & Short Circuit Tracing",
            "problem_description": "Main 32A MCB trips repeatedly every time bedroom air conditioner turns on.",
            "diagnosis": "Insulation breakdown in AC concealed copper wiring causing line-to-earth short.",
            "outcome_summary": "Traced short circuit location with insulation tester and replaced damaged wire section.",
            "repair_type": "short circuit tracing", "device_category": "Home Electrical",
            "brand": "Schneider", "model": "Acti9 MCB", "difficulty": "intermediate",
            "verification_status": "verified", "experience_status": "verified", "verification_confidence": 0.88, "created_at": now, "updated_at": now
        }
        exp19_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee19"
        self.experiences[exp19_id] = {
            "id": exp19_id, "worker_id": w9_id,
            "title": "3-Phase Distribution Board Neutral Wire Burn Fix",
            "problem_description": "Unstable voltage fluctuating between 180V and 290V across home appliances.",
            "diagnosis": "Loose neutral busbar screw causing floating neutral condition.",
            "outcome_summary": "Re-terminated main neutral connector and installed voltage protection relay.",
            "repair_type": "electrical distribution board repair", "device_category": "Home Electrical",
            "brand": "Legrand", "model": "DLP DB", "difficulty": "advanced",
            "verification_status": "unverified", "experience_status": "submitted", "verification_confidence": 0.0, "created_at": now, "updated_at": now
        }

        # --- Worker J (Sneha Kulkarni) --- 2 Experiences (0 Verified)
        exp20_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee20"
        self.experiences[exp20_id] = {
            "id": exp20_id, "worker_id": w10_id,
            "title": "Kitchen Appliance Switchboard Repair & Socket Replacement",
            "problem_description": "16A microwave power socket sparking and smelling burnt.",
            "diagnosis": "Melted terminal screws due to loose high-draw connection.",
            "outcome_summary": "Replaced heavy-duty 16A socket and switch unit with flame-retardant box.",
            "repair_type": "switchboard repair", "device_category": "Home Electrical",
            "brand": "Crabtree", "model": "Athena", "difficulty": "basic",
            "verification_status": "unverified", "experience_status": "submitted", "verification_confidence": 0.0, "created_at": now, "updated_at": now
        }
        exp21_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee21"
        self.experiences[exp21_id] = {
            "id": exp21_id, "worker_id": w10_id,
            "title": "Ceiling Fan Regulator & Wiring Connection",
            "problem_description": "Ceiling fan running at full speed only, regulator knob ineffective.",
            "diagnosis": "Blown capacitor inside step-type regulator module.",
            "outcome_summary": "Installed new hum-free electronic fan regulator.",
            "repair_type": "appliance wiring repair", "device_category": "Home Electrical",
            "brand": "Orient", "model": "Reg-5S", "difficulty": "basic",
            "verification_status": "unverified", "experience_status": "submitted", "verification_confidence": 0.0, "created_at": now, "updated_at": now
        }

        # Register all 21 experiences into self.experiences dict
        for exp in [
            self.experiences[exp1_id], self.experiences[exp2_id], self.experiences[exp3_id],
            self.experiences[exp4_id], self.experiences[exp5_id], self.experiences[exp6_id],
            self.experiences[exp7_id], self.experiences[exp8_id], self.experiences[exp9_id],
            self.experiences[exp10_id], self.experiences[exp11_id], self.experiences[exp12_id],
            self.experiences[exp13_id], self.experiences[exp14_id], self.experiences[exp15_id],
            self.experiences[exp16_id], self.experiences[exp17_id], self.experiences[exp18_id],
            self.experiences[exp19_id], self.experiences[exp20_id], self.experiences[exp21_id]
        ]:
            self.experiences[exp["id"]] = exp

        # --------------------------------------------------------------------
        # 14. KNOWLEDGE CASES (9 Realistic Cases)
        # --------------------------------------------------------------------
        kc1_id = "dddddddd-dddd-dddd-dddd-dddddddddd01"
        self.knowledge_cases[kc1_id] = {
            "id": kc1_id, "worker_id": w1_id, "experience_id": exp1_id,
            "title": "Samsung S23 No Power After Physical Drop",
            "problem_summary": "Device completely dead following a drop, drawing 0mA on DC power supply.",
            "diagnosis_summary": "Primary power management IC (PMIC) cracked under shielding bracket, VBAT rail shorted to ground.",
            "solution_summary": "Carefully lifted the shield with hot air at 320C, replaced damaged PMIC and decoupling capacitor C4021.",
            "lesson_learned": "Always inspect the inductor pads next to PMIC for trace hairline fractures after drop impact.",
            "difficulty_level": "advanced", "difficulty": "advanced",
            "device_category": "Smartphone / PCB", "brand": "Samsung", "model": "Galaxy S23",
            "visibility_status": "published", "is_published": True, "is_verified": True, "view_count": 142,
            "created_at": now, "updated_at": now
        }
        kc2_id = "dddddddd-dddd-dddd-dddd-dddddddddd02"
        self.knowledge_cases[kc2_id] = {
            "id": kc2_id, "worker_id": w2_id, "experience_id": exp4_id,
            "title": "Luminous 1100VA Inverter Continuous Overload Alarm",
            "problem_summary": "Inverter beeps continuously indicating overload even with zero connected load on backup.",
            "diagnosis_summary": "Damaged MOSFET pair on the primary H-bridge stage causing feedback loop sensing anomaly.",
            "solution_summary": "Replaced IRF3205 MOSFETs and 10 ohm gate resistors. Tested inverter under 600W resistive load.",
            "lesson_learned": "Always replace gate driver resistors in pairs whenever MOSFETs fail in an inverter circuit.",
            "difficulty_level": "intermediate", "difficulty": "intermediate",
            "device_category": "Power Inverter", "brand": "Luminous", "model": "Zelio 1100",
            "visibility_status": "published", "is_published": True, "is_verified": True, "view_count": 89,
            "created_at": now, "updated_at": now
        }
        kc3_id = "dddddddd-dddd-dddd-dddd-dddddddddd03"
        self.knowledge_cases[kc3_id] = {
            "id": kc3_id, "worker_id": w4_id, "experience_id": exp8_id,
            "title": "Samsung S22 No Power After Drop Diagnosis",
            "problem_summary": "Galaxy S22 phone dead after fall, no boot vibration or current draw.",
            "diagnosis_summary": "Impact caused Ceramic Capacitor on PM8350 rail to short internally.",
            "solution_summary": "Injected 1.8V to isolate heating cap using thermal camera, replaced cap.",
            "lesson_learned": "Current injection at low voltage safely isolates shorted caps on modern 4nm phone logic boards.",
            "difficulty_level": "advanced", "difficulty": "advanced",
            "device_category": "Smartphone / PCB", "brand": "Samsung", "model": "Galaxy S22",
            "visibility_status": "published", "is_published": True, "is_verified": True, "view_count": 115,
            "created_at": now, "updated_at": now
        }
        kc4_id = "dddddddd-dddd-dddd-dddd-dddddddddd04"
        self.knowledge_cases[kc4_id] = {
            "id": kc4_id, "worker_id": w5_id, "experience_id": exp10_id,
            "title": "Smartphone Board-Level Power Diagnosis & Thermal Tracing",
            "problem_summary": "Mobile motherboard drawing high standby current and heating up.",
            "diagnosis_summary": "Secondary rail short circuit traced via micro-multimeter diode mode testing.",
            "solution_summary": "Removed shorted component and verified voltage rail stability.",
            "lesson_learned": "Diode mode values comparing ground reference are faster than resistance readings for SMD shorts.",
            "difficulty_level": "advanced", "difficulty": "advanced",
            "device_category": "Smartphone / Electronics", "brand": "Xiaomi", "model": "Redmi Note 12",
            "visibility_status": "published", "is_published": True, "is_verified": True, "view_count": 78,
            "created_at": now, "updated_at": now
        }
        kc5_id = "dddddddd-dddd-dddd-dddd-dddddddddd05"
        self.knowledge_cases[kc5_id] = {
            "id": kc5_id, "worker_id": w7_id, "experience_id": exp14_id,
            "title": "Samsung TV Power Supply Board Failure Repair",
            "problem_summary": "Samsung Smart TV red LED blinks 2 times, no backlight or audio.",
            "diagnosis_summary": "Blown filter capacitors in SMPS secondary stage causing voltage dip.",
            "solution_summary": "Replaced blown 105C high-temp electrolytic capacitors on power board.",
            "lesson_learned": "Check secondary rail voltages under standby before replacing whole TV power board.",
            "difficulty_level": "intermediate", "difficulty": "intermediate",
            "device_category": "Consumer Electronics / TV", "brand": "Samsung", "model": "UA55TU8000",
            "visibility_status": "published", "is_published": True, "is_verified": True, "view_count": 94,
            "created_at": now, "updated_at": now
        }
        kc6_id = "dddddddd-dddd-dddd-dddd-dddddddddd06"
        self.knowledge_cases[kc6_id] = {
            "id": kc6_id, "worker_id": w9_id, "experience_id": exp18_id,
            "title": "Household MCB Tripping & Short Circuit Isolation",
            "problem_summary": "Main circuit breaker trips constantly when heavy load turned on.",
            "diagnosis_summary": "Wiring insulation degradation creating phase-to-earth leakage.",
            "solution_summary": "Isolated damaged wiring segment using megohmmeter continuity tester.",
            "lesson_learned": "Always test line-to-earth resistance across individual circuits when main RCD/MCB trips.",
            "difficulty_level": "intermediate", "difficulty": "intermediate",
            "device_category": "Home Electrical", "brand": "Schneider", "model": "Acti9 MCB",
            "visibility_status": "published", "is_published": True, "is_verified": True, "view_count": 62,
            "created_at": now, "updated_at": now
        }
        kc7_id = "dddddddd-dddd-dddd-dddd-dddddddddd07"
        self.knowledge_cases[kc7_id] = {
            "id": kc7_id, "worker_id": w8_id, "experience_id": exp16_id,
            "title": "3KVA Online UPS Battery Bank Failover Troubleshooting",
            "problem_summary": "Commercial UPS fails to support load during blackouts.",
            "diagnosis_summary": "High internal resistance in one degraded battery dragging down entire DC bus.",
            "solution_summary": "Replaced weak battery cell and equalized charge voltages across string.",
            "lesson_learned": "Measure individual battery voltage under load, not open-circuit voltage.",
            "difficulty_level": "advanced", "difficulty": "advanced",
            "device_category": "Power Systems", "brand": "APC", "model": "Smart-UPS 3000",
            "visibility_status": "published", "is_published": True, "is_verified": True, "view_count": 51,
            "created_at": now, "updated_at": now
        }
        kc8_id = "dddddddd-dddd-dddd-dddd-dddddddddd08"
        self.knowledge_cases[kc8_id] = {
            "id": kc8_id, "worker_id": w6_id, "experience_id": exp12_id,
            "title": "Samsung Galaxy S-Series Curved Display Replacement",
            "problem_summary": "Curved AMOLED screen glass smashed after fall.",
            "diagnosis_summary": "Digitizer glass broken; OLED panel functional but fragile flex cable pinched.",
            "solution_summary": "Extracted frame assembly with isopropyl alcohol and glued original panel.",
            "lesson_learned": "Heat frame to 80C before lifting curved glass edges to prevent OLED panel tearing.",
            "difficulty_level": "intermediate", "difficulty": "intermediate",
            "device_category": "Smartphone / Electronics", "brand": "Samsung", "model": "Galaxy S21 Ultra",
            "visibility_status": "published", "is_published": True, "is_verified": True, "view_count": 108,
            "created_at": now, "updated_at": now
        }
        kc9_id = "dddddddd-dddd-dddd-dddd-dddddddddd09"
        self.knowledge_cases[kc9_id] = {
            "id": kc9_id, "worker_id": w3_id, "experience_id": exp6_id,
            "title": "Distribution Board Phase Balancing for Residential Apartments",
            "problem_summary": "Uneven voltage causing lights to dim when air conditioner starts.",
            "diagnosis_summary": "Single phase heavily overloaded while other 2 phases underutilized.",
            "solution_summary": "Redistributed high-amperage appliances evenly across 3 incoming phases.",
            "lesson_learned": "Calculate peak concurrent wattage for kitchen and AC points during DB wiring layout.",
            "difficulty_level": "intermediate", "difficulty": "intermediate",
            "device_category": "Home Electrical", "brand": "Havells", "model": "DB-12Way",
            "visibility_status": "published", "is_published": True, "is_verified": False, "view_count": 45,
            "created_at": now, "updated_at": now
        }

        for kc in [
            self.knowledge_cases[kc1_id], self.knowledge_cases[kc2_id], self.knowledge_cases[kc3_id],
            self.knowledge_cases[kc4_id], self.knowledge_cases[kc5_id], self.knowledge_cases[kc6_id],
            self.knowledge_cases[kc7_id], self.knowledge_cases[kc8_id], self.knowledge_cases[kc9_id]
        ]:
            self.knowledge_cases[kc["id"]] = kc

db = SupabaseDataStore()

