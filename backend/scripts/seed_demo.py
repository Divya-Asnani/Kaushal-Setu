"""Seed demo data so the matching pipeline has something to retrieve.

Seed data is Person 3's deliverable; this script exists so the AI and matching work can
be exercised end to end before that lands, and as a reproducible demo fixture. It is
idempotent: re-running updates rather than duplicating.

Every seeded row is tagged in a way that makes it obviously demo data (PRD section 28:
prototype data must be distinguishable from real user data) -- accounts use the
@demo.ibolt.local domain.

    python -m backend.scripts.seed_demo            # create/refresh
    python -m backend.scripts.seed_demo --purge    # remove everything it created
"""
from __future__ import annotations

import argparse
import logging
import sys

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stdout)
log = logging.getLogger("seed")

from backend.db.supabase import get_supabase, rows, table  # noqa: E402
from backend.services.ai import indexing  # noqa: E402

DEMO_DOMAIN = "demo.ibolt.local"
DEMO_PASSWORD = "DemoPass123!"

SKILLS = [
    ("Samsung smartphone repair", "electronics"),
    ("Board-level repair", "electronics"),
    ("Power IC repair", "electronics"),
    ("Charging port repair", "electronics"),
    ("Display replacement", "electronics"),
    ("Ceiling fan repair", "home electrical"),
    ("MCB troubleshooting", "home electrical"),
    ("House wiring", "home electrical"),
    ("Inverter and UPS repair", "power systems"),
    ("Washing machine repair", "appliances"),
]

# (key, name, title, city, lat, lon, radius, skills)
WORKERS = [
    ("ravi", "Ravi Kulkarni", "Mobile Repair Technician", "Pune", 18.5204, 73.8567, 15,
     ["Samsung smartphone repair", "Board-level repair", "Power IC repair"]),
    ("meena", "Meena Shah", "Electronics Repair Technician", "Pune", 18.5310, 73.8446, 12,
     ["Samsung smartphone repair", "Charging port repair", "Board-level repair"]),
    ("arjun", "Arjun Patil", "Mobile Repair Technician", "Pune", 18.5089, 73.8553, 10,
     ["Display replacement", "Samsung smartphone repair"]),
    ("sunita", "Sunita Deshmukh", "Electrician", "Pune", 18.5679, 73.9143, 20,
     ["Ceiling fan repair", "MCB troubleshooting", "House wiring"]),
    ("imran", "Imran Sheikh", "Inverter Technician", "Pune", 18.4980, 73.8070, 18,
     ["Inverter and UPS repair", "MCB troubleshooting"]),
    ("priya", "Priya Nair", "Appliance Repair Technician", "Pune", 18.5421, 73.8290, 14,
     ["Washing machine repair", "House wiring"]),
]

# (worker_key, title, problem, diagnosis, outcome, status, confidence, contexts, skills)
EXPERIENCES = [
    ("ravi", "Samsung Galaxy S23 no power after drop",
     "Customer dropped the phone; it stopped powering on with no display and no boot.",
     "Board inspection found a fault in the power section after impact damage.",
     "Phone restored to full working condition.", "verified", 95,
     [("damage", "physical drop"), ("symptom", "no display")],
     ["Samsung smartphone repair", "Board-level repair", "Power IC repair"]),
    ("ravi", "Galaxy S23 dead after fall from pocket",
     "Phone fell and would not switch on afterwards.",
     "Power rail fault traced on the mainboard.",
     "Device powers on normally.", "verified", 92,
     [("damage", "physical drop")],
     ["Samsung smartphone repair", "Power IC repair"]),
    ("ravi", "Samsung S22 Ultra no boot after impact",
     "No boot after the phone was dropped on a hard floor.",
     "Board-level power fault.", "Repaired and returned working.", "verified", 90,
     [("damage", "physical drop")],
     ["Samsung smartphone repair", "Board-level repair"]),
    ("ravi", "Redmi Note dead board",
     "Phone stopped switching on with no prior damage.",
     "Board-level power fault.", "Repaired.", "submitted", 0,
     [], ["Board-level repair"]),

    ("meena", "Samsung Galaxy S23 charging failure",
     "Phone would not charge from any cable or adapter.",
     "Charging circuit fault on the mainboard.",
     "Charging restored.", "verified", 93,
     [("symptom", "not charging")],
     ["Samsung smartphone repair", "Charging port repair", "Board-level repair"]),
    ("meena", "Galaxy S23 slow charging and heating",
     "Phone charged very slowly and became hot.",
     "Charging section fault identified on the board.",
     "Normal charging restored.", "verified", 88,
     [("symptom", "overheating")],
     ["Samsung smartphone repair", "Charging port repair"]),

    ("arjun", "Samsung Galaxy S22 no power",
     "Phone stopped turning on; no display at all.",
     "Mainboard power fault.", "Device repaired.", "verified", 85,
     [("symptom", "no display")],
     ["Samsung smartphone repair"]),
    ("arjun", "Galaxy S21 cracked screen replacement",
     "Screen cracked after a drop; touch not responding.",
     "Display assembly damaged by impact.",
     "Display replaced.", "verified", 80,
     [("damage", "physical drop")],
     ["Display replacement"]),

    ("sunita", "Ceiling fan not starting",
     "Fan hummed but the blades would not turn.",
     "Starting capacitor had failed.",
     "Fan runs at full speed again.", "verified", 90,
     [("symptom", "humming")], ["Ceiling fan repair"]),
    ("sunita", "MCB tripping repeatedly in kitchen circuit",
     "The kitchen MCB tripped every time the oven was switched on.",
     "Overloaded circuit with a damaged section of wiring.",
     "Circuit rewired and the tripping stopped.", "verified", 94,
     [("symptom", "tripping")], ["MCB troubleshooting", "House wiring"]),

    ("imran", "Inverter not switching to battery",
     "Inverter failed to take over during a power cut.",
     "Faulty changeover relay.",
     "Backup restored.", "verified", 89,
     [("symptom", "no backup")], ["Inverter and UPS repair"]),

    ("priya", "Washing machine not draining",
     "Machine stopped mid-cycle with water still in the drum.",
     "Blocked drain pump.", "Drainage restored.", "verified", 86,
     [("symptom", "not draining")], ["Washing machine repair"]),
]

KNOWLEDGE_CASES = [
    ("ravi", "Diagnosing no-power Samsung phones after physical impact",
     "A Samsung phone stops powering on after being dropped.",
     "Impact commonly disturbs the power section of the mainboard.",
     "Inspect the power rails before assuming the whole board needs replacing.",
     "Check the power path first; a full board swap is rarely necessary.", "advanced"),
    ("sunita", "Tracing a repeatedly tripping MCB",
     "An MCB trips whenever a particular appliance is switched on.",
     "Usually an overloaded circuit or damaged insulation, not a faulty MCB.",
     "Isolate circuits one at a time and measure load before replacing the MCB.",
     "Replacing the MCB without finding the cause hides a real fault.", "intermediate"),
]


def _email(key: str) -> str:
    return f"{key}@{DEMO_DOMAIN}"


def _ensure_auth_user(email: str, display_name: str, role: str) -> str:
    """Create the Supabase Auth user if absent and return its id."""
    client = get_supabase()
    existing = rows(table("profiles").select("id").eq("display_name", display_name).limit(1).execute())
    if existing:
        return str(existing[0]["id"])
    try:
        created = client.auth.admin.create_user(
            {
                "email": email,
                "password": DEMO_PASSWORD,
                "email_confirm": True,
                "user_metadata": {"display_name": display_name, "demo": True},
            }
        )
        return str(created.user.id)
    except Exception as exc:
        # Most likely the auth user exists but its profile row does not.
        log.warning("Could not create auth user %s (%s); looking it up", email, exc)
        for user in client.auth.admin.list_users():
            if getattr(user, "email", None) == email:
                return str(user.id)
        raise


def _upsert_profile(user_id: str, display_name: str, role: str) -> None:
    table("profiles").upsert(
        {"id": user_id, "display_name": display_name, "role": role, "is_active": True},
        on_conflict="id",
    ).execute()


def seed_skills() -> dict[str, str]:
    ids: dict[str, str] = {}
    for name, category in SKILLS:
        existing = rows(table("skills").select("id").eq("name", name).limit(1).execute())
        if existing:
            ids[name] = str(existing[0]["id"])
            continue
        created = rows(
            table("skills").insert({"name": name, "category": category, "is_active": True}).execute()
        )[0]
        ids[name] = str(created["id"])
    log.info("Skills ready: %d", len(ids))
    return ids


def seed_workers(skill_ids: dict[str, str]) -> dict[str, str]:
    worker_ids: dict[str, str] = {}
    for key, name, title, city, lat, lon, radius, skills in WORKERS:
        user_id = _ensure_auth_user(_email(key), name, "worker")
        _upsert_profile(user_id, name, "worker")
        table("worker_profiles").upsert(
            {
                "user_id": user_id,
                "professional_title": title,
                "bio": f"{title} working in and around {city}.",
                "years_experience": 6,
                "service_radius_km": radius,
                "locality": city,
                "city": city,
                "state": "Maharashtra",
                "latitude": lat,
                "longitude": lon,
                "availability_status": "available",
                "is_verified": True,
            },
            on_conflict="user_id",
        ).execute()

        table("worker_skills").delete().eq("worker_id", user_id).execute()
        links = [
            {
                "worker_id": user_id,
                "skill_id": skill_ids[s],
                "proficiency_level": "advanced",
                "years_experience": 5,
                "is_primary": i == 0,
            }
            for i, s in enumerate(skills)
            if s in skill_ids
        ]
        if links:
            table("worker_skills").insert(links).execute()
        worker_ids[key] = user_id
    log.info("Workers ready: %d", len(worker_ids))
    return worker_ids


def seed_experiences(worker_ids: dict[str, str], skill_ids: dict[str, str]) -> int:
    indexed = 0
    for (key, title, problem, diagnosis, outcome, status, confidence,
         contexts, skills) in EXPERIENCES:
        worker_id = worker_ids.get(key)
        if worker_id is None:
            continue

        existing = rows(
            table("experiences")
            .select("id")
            .eq("worker_id", worker_id)
            .eq("title", title)
            .limit(1)
            .execute()
        )
        if existing:
            experience_id = str(existing[0]["id"])
            table("experiences").update(
                {"experience_status": status, "verification_confidence": confidence}
            ).eq("id", experience_id).execute()
        else:
            created = rows(
                table("experiences")
                .insert(
                    {
                        "worker_id": worker_id,
                        "title": title,
                        "problem_description": problem,
                        "diagnosis": diagnosis,
                        "outcome_summary": outcome,
                        "experience_status": status,
                        "verification_confidence": confidence,
                    }
                )
                .execute()
            )[0]
            experience_id = str(created["id"])

        table("experience_contexts").delete().eq("experience_id", experience_id).execute()
        if contexts:
            table("experience_contexts").insert(
                [
                    {
                        "experience_id": experience_id,
                        "context_type": ctype,
                        "context_value": cvalue,
                        "importance_score": 0.8,
                    }
                    for ctype, cvalue in contexts
                ]
            ).execute()

        table("experience_outcomes").delete().eq("experience_id", experience_id).execute()
        table("experience_outcomes").insert(
            {
                "experience_id": experience_id,
                "outcome_type": "repair_result",
                "outcome_description": outcome,
                "success_status": "successful",
                "customer_confirmed": status == "verified",
            }
        ).execute()

        table("experience_skills").delete().eq("experience_id", experience_id).execute()
        links = [
            {"experience_id": experience_id, "skill_id": skill_ids[s]}
            for s in skills
            if s in skill_ids
        ]
        if links:
            table("experience_skills").insert(links).execute()

        if indexing.index_experience(experience_id):
            indexed += 1
    log.info("Experiences ready: %d (%d embedded)", len(EXPERIENCES), indexed)
    return indexed


def seed_knowledge_cases(worker_ids: dict[str, str]) -> int:
    indexed = 0
    for key, title, problem, diagnosis, solution, lesson, difficulty in KNOWLEDGE_CASES:
        worker_id = worker_ids.get(key)
        if worker_id is None:
            continue
        existing = rows(
            table("knowledge_cases").select("id").eq("title", title).limit(1).execute()
        )
        if existing:
            case_id = str(existing[0]["id"])
        else:
            created = rows(
                table("knowledge_cases")
                .insert(
                    {
                        "worker_id": worker_id,
                        "title": title,
                        "problem_summary": problem,
                        "diagnosis_summary": diagnosis,
                        "solution_summary": solution,
                        "lesson_learned": lesson,
                        "difficulty_level": difficulty,
                        "visibility_status": "published",
                        "is_verified": True,
                    }
                )
                .execute()
            )[0]
            case_id = str(created["id"])
        if indexing.index_knowledge_case(case_id):
            indexed += 1
    log.info("Knowledge cases ready: %d (%d embedded)", len(KNOWLEDGE_CASES), indexed)
    return indexed


def seed_customer() -> str:
    user_id = _ensure_auth_user(_email("customer"), "Demo Customer", "customer")
    _upsert_profile(user_id, "Demo Customer", "customer")
    log.info("Demo customer: %s / %s", _email("customer"), DEMO_PASSWORD)
    return user_id


def purge() -> None:
    """Remove demo rows. Auth users are left alone; deleting accounts is not this script's call."""
    demo_profiles = rows(table("profiles").select("id, display_name").execute())
    names = {w[1] for w in WORKERS} | {"Demo Customer"}
    ids = [str(p["id"]) for p in demo_profiles if p.get("display_name") in names]
    if not ids:
        log.info("Nothing to purge.")
        return

    for case in rows(table("knowledge_cases").select("id").in_("worker_id", ids).execute()):
        table("knowledge_case_embeddings").delete().eq("knowledge_case_id", case["id"]).execute()
    table("knowledge_cases").delete().in_("worker_id", ids).execute()

    for exp in rows(table("experiences").select("id").in_("worker_id", ids).execute()):
        table("experience_embeddings").delete().eq("experience_id", exp["id"]).execute()
    table("experiences").delete().in_("worker_id", ids).execute()

    table("worker_skills").delete().in_("worker_id", ids).execute()
    table("worker_profiles").delete().in_("user_id", ids).execute()
    log.info("Purged demo experiences, cases and worker profiles for %d accounts.", len(ids))


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed iBolt demo data")
    parser.add_argument("--purge", action="store_true", help="remove seeded rows instead")
    args = parser.parse_args()

    if args.purge:
        purge()
        return

    skill_ids = seed_skills()
    worker_ids = seed_workers(skill_ids)
    seed_experiences(worker_ids, skill_ids)
    seed_knowledge_cases(worker_ids)
    seed_customer()
    log.info("Seed complete. All demo accounts use the password %s", DEMO_PASSWORD)


if __name__ == "__main__":
    main()
