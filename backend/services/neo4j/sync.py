"""
Neo4j synchronization layer for Kaushal Setu.

PostgreSQL/Supabase remains the source of truth.
Neo4j is a graph projection used for relationship and context intelligence.

Graph model:

Worker
  └── SOLVED ──> Experience
                    ├── ABOUT ──> Problem
                    ├── INVOLVES ──> Device
                    ├── HAS_ISSUE ──> Issue
                    ├── OCCURRED_IN ──> Context
                    ├── REQUIRED_SKILL ──> Skill
                    └── RESULTED_IN ──> Outcome

Worker ── HAS_SKILL ──> Skill

KnowledgeCase ── BASED_ON ──> Experience
KnowledgeCase ── ABOUT ──> Issue
KnowledgeCase ── REQUIRES_SKILL ──> Skill
"""

import logging
import re
from typing import Any, Dict, List, Optional

from backend.db.supabase_client import db
from backend.services.neo4j.client import neo4j_client


logger = logging.getLogger("kaushalsetu.neo4j.sync")


# ============================================================================
# GENERAL HELPERS
# ============================================================================

def _records(table_name: str) -> List[Dict[str, Any]]:
    """Return all records from the existing SupabaseDataStore."""

    records = getattr(db, table_name, {})

    if isinstance(records, dict):
        return list(records.values())

    return []


def _find_by_id(
    table_name: str,
    record_id: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Find one record by ID."""

    if not record_id:
        return None

    for record in _records(table_name):
        if str(record.get("id")) == str(record_id):
            return record

    return None


def _safe_str(value: Any) -> Optional[str]:
    """Convert a value to string while preserving None."""

    if value is None:
        return None

    return str(value)


def _normalize(value: Any) -> str:
    """
    Normalize a value so it can be safely used as a graph identity key.
    """

    if value is None:
        return ""

    value = str(value).strip().lower()

    value = re.sub(r"\s+", " ", value)

    return value


def _slug(value: Any) -> str:
    """
    Create a deterministic identifier component.

    Example:
        'Samsung Galaxy S23'
        -> 'samsung_galaxy_s23'
    """

    value = _normalize(value)

    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_")


def _worker_name(worker_id: str) -> str:
    """Resolve worker name through worker_profiles -> profiles."""

    worker = _find_by_id("worker_profiles", worker_id)

    if not worker:
        return "Unknown Worker"

    user_id = worker.get("user_id") or worker.get("id")

    profile = _find_by_id("profiles", user_id)

    if profile:
        return (
            profile.get("full_name")
            or profile.get("display_name")
            or "Worker"
        )

    return "Worker"


# ============================================================================
# CONSTRAINTS
# ============================================================================

def create_constraints() -> None:
    """Create uniqueness constraints for primary graph entities."""

    constraints = [
        """
        CREATE CONSTRAINT worker_id IF NOT EXISTS
        FOR (w:Worker)
        REQUIRE w.id IS UNIQUE
        """,

        """
        CREATE CONSTRAINT skill_id IF NOT EXISTS
        FOR (s:Skill)
        REQUIRE s.id IS UNIQUE
        """,

        """
        CREATE CONSTRAINT experience_id IF NOT EXISTS
        FOR (e:Experience)
        REQUIRE e.id IS UNIQUE
        """,

        """
        CREATE CONSTRAINT knowledge_case_id IF NOT EXISTS
        FOR (k:KnowledgeCase)
        REQUIRE k.id IS UNIQUE
        """,

        """
        CREATE CONSTRAINT problem_id IF NOT EXISTS
        FOR (p:Problem)
        REQUIRE p.id IS UNIQUE
        """,

        """
        CREATE CONSTRAINT device_id IF NOT EXISTS
        FOR (d:Device)
        REQUIRE d.id IS UNIQUE
        """,

        """
        CREATE CONSTRAINT issue_id IF NOT EXISTS
        FOR (i:Issue)
        REQUIRE i.id IS UNIQUE
        """,

        """
        CREATE CONSTRAINT context_id IF NOT EXISTS
        FOR (c:Context)
        REQUIRE c.id IS UNIQUE
        """,

        """
        CREATE CONSTRAINT outcome_id IF NOT EXISTS
        FOR (o:Outcome)
        REQUIRE o.id IS UNIQUE
        """,
    ]

    for statement in constraints:
        neo4j_client.execute(statement)

    logger.info("Neo4j constraints created/verified.")


# ============================================================================
# WORKERS
# ============================================================================

def sync_workers() -> int:
    """Create/update Worker nodes."""

    workers = _records("worker_profiles")

    payload = []

    for worker in workers:
        worker_id = worker.get("id")

        if not worker_id:
            continue

        payload.append(
            {
                "id": _safe_str(worker_id),
                "user_id": _safe_str(
                    worker.get("user_id") or worker_id
                ),
                "name": _worker_name(str(worker_id)),
                "headline": (
                    worker.get("headline")
                    or worker.get("professional_title")
                ),
                "bio": worker.get("bio"),
                "experience_years": worker.get(
                    "experience_years",
                    worker.get("years_experience", 0),
                ),
                "service_radius_km": worker.get(
                    "service_radius_km",
                    15,
                ),
                "latitude": worker.get("latitude"),
                "longitude": worker.get("longitude"),
                "locality": worker.get("locality"),
                "city": worker.get("city"),
                "state": worker.get("state"),
                "is_available": worker.get(
                    "is_available",
                    worker.get("availability_status") == "available",
                ),
                "is_verified": worker.get(
                    "is_verified",
                    False,
                ),
                "rating": worker.get("rating", 5.0),
                "total_reviews": worker.get(
                    "total_reviews",
                    0,
                ),
            }
        )

    if not payload:
        return 0

    query = """
    UNWIND $workers AS w

    MERGE (worker:Worker {id: w.id})

    SET worker.user_id = w.user_id,
        worker.name = w.name,
        worker.headline = w.headline,
        worker.bio = w.bio,
        worker.experience_years = w.experience_years,
        worker.service_radius_km = w.service_radius_km,
        worker.latitude = w.latitude,
        worker.longitude = w.longitude,
        worker.locality = w.locality,
        worker.city = w.city,
        worker.state = w.state,
        worker.is_available = w.is_available,
        worker.is_verified = w.is_verified,
        worker.rating = w.rating,
        worker.total_reviews = w.total_reviews
    """

    neo4j_client.execute(query, {"workers": payload})

    logger.info("Synced %s Worker nodes.", len(payload))

    return len(payload)


# ============================================================================
# SKILLS
# ============================================================================

def sync_worker_skills() -> int:
    """Create Skill nodes and Worker-HAS_SKILL relationships."""

    records = _records("worker_skills")

    payload = []

    for record in records:

        worker_id = record.get("worker_id")
        skill_id = record.get("skill_id")

        if not worker_id or not skill_id:
            continue

        skill = _find_by_id("skills", skill_id)

        if not skill:
            continue

        payload.append(
            {
                "worker_id": _safe_str(worker_id),
                "skill_id": _safe_str(skill_id),
                "skill_name": (
                    skill.get("name")
                    or skill.get("skill_name")
                    or "Unknown Skill"
                ),
                "category": skill.get("category"),
                "proficiency": record.get(
                    "proficiency_level"
                ),
                "verified": record.get(
                    "verified",
                    False,
                ),
                "is_primary": record.get(
                    "is_primary",
                    False,
                ),
            }
        )

    if not payload:
        return 0

    query = """
    UNWIND $skills AS s

    MERGE (skill:Skill {id: s.skill_id})

    SET skill.name = s.skill_name,
        skill.category = s.category

    WITH s, skill

    MATCH (worker:Worker {id: s.worker_id})

    MERGE (worker)-[r:HAS_SKILL]->(skill)

    SET r.proficiency_level = s.proficiency,
        r.verified = s.verified,
        r.is_primary = s.is_primary
    """

    neo4j_client.execute(query, {"skills": payload})

    logger.info(
        "Synced %s Worker-Skill relationships.",
        len(payload),
    )

    return len(payload)


# ============================================================================
# EXPERIENCE
# ============================================================================

def sync_experiences() -> int:
    """Create Experience nodes and Worker-SOLVED relationships."""

    experiences = _records("experiences")

    payload = []

    for experience in experiences:

        experience_id = experience.get("id")
        worker_id = experience.get("worker_id")

        if not experience_id or not worker_id:
            continue

        payload.append(
            {
                "id": _safe_str(experience_id),
                "worker_id": _safe_str(worker_id),
                "title": experience.get("title"),
                "description": experience.get(
                    "problem_description"
                ),
                "diagnosis": experience.get(
                    "diagnosis"
                ),
                "repair_type": experience.get(
                    "repair_type"
                ),
                "device_category": experience.get(
                    "device_category"
                ),
                "brand": experience.get("brand"),
                "model": experience.get("model"),
                "difficulty": experience.get(
                    "difficulty"
                ),
                "status": experience.get(
                    "experience_status"
                ),
                "verification_status": experience.get(
                    "verification_status"
                ),
                "verification_confidence": experience.get(
                    "verification_confidence"
                ),
                "outcome_summary": experience.get(
                    "outcome_summary"
                ),
            }
        )

    if not payload:
        return 0

    query = """
    UNWIND $experiences AS e

    MERGE (experience:Experience {id: e.id})

    SET experience.title = e.title,
        experience.description = e.description,
        experience.diagnosis = e.diagnosis,
        experience.repair_type = e.repair_type,
        experience.device_category = e.device_category,
        experience.brand = e.brand,
        experience.model = e.model,
        experience.difficulty = e.difficulty,
        experience.status = e.status,
        experience.verification_status = e.verification_status,
        experience.verification_confidence = e.verification_confidence,
        experience.outcome_summary = e.outcome_summary

    WITH e, experience

    MATCH (worker:Worker {id: e.worker_id})

    MERGE (worker)-[r:SOLVED]->(experience)

    SET r.verified =
        CASE
            WHEN e.verification_status = 'verified'
            OR e.status = 'verified'
            THEN true
            ELSE false
        END,

        r.confidence = e.verification_confidence
    """

    neo4j_client.execute(
        query,
        {"experiences": payload},
    )

    logger.info(
        "Synced %s Experience nodes.",
        len(payload),
    )

    return len(payload)


# ============================================================================
# PROBLEM / DEVICE / ISSUE / CONTEXT
# ============================================================================

def sync_experience_intelligence() -> Dict[str, int]:
    """
    Build the Experience Intelligence layer.

    For every experience:

        Experience
             |
             +-- ABOUT --> Problem
             |
             +-- INVOLVES --> Device
             |
             +-- HAS_ISSUE --> Issue
             |
             +-- OCCURRED_IN --> Context
    """

    experiences = _records("experiences")

    if not experiences:
        return {
            "problems": 0,
            "devices": 0,
            "issues": 0,
            "contexts": 0,
        }

    payload = []

    for experience in experiences:

        experience_id = experience.get("id")

        if not experience_id:
            continue

        description = (
            experience.get("problem_description")
            or experience.get("diagnosis")
            or experience.get("title")
            or "Repair problem"
        )

        brand = experience.get("brand")
        model = experience.get("model")
        device_category = experience.get(
            "device_category"
        )

        repair_type = experience.get(
            "repair_type"
        )

        # ------------------------------------------------------------
        # Problem
        # ------------------------------------------------------------

        problem_id = f"experience_problem_{experience_id}"

        # ------------------------------------------------------------
        # Device
        # ------------------------------------------------------------

        device_key = _slug(
            f"{brand or ''}_{model or ''}_{device_category or ''}"
        )

        device_id = (
            f"device_{device_key}"
            if device_key
            else None
        )

        # ------------------------------------------------------------
        # Issue
        # ------------------------------------------------------------

        issue_text = (
            experience.get("diagnosis")
            or experience.get("title")
            or "Repair issue"
        )

        issue_id = (
            f"issue_{_slug(issue_text)}"
            if issue_text
            else None
        )

        # ------------------------------------------------------------
        # Context
        # ------------------------------------------------------------

        context_text = None

        description_lower = description.lower()

        if "after drop" in description_lower:
            context_text = "Physical drop / impact"

        elif "dropped" in description_lower:
            context_text = "Physical drop / impact"

        elif "water" in description_lower:
            context_text = "Water exposure"

        elif "overload" in description_lower:
            context_text = "Overload condition"

        elif "tripping" in description_lower:
            context_text = "Electrical tripping"

        if context_text:
            context_id = (
                f"context_{_slug(context_text)}"
            )
        else:
            context_id = None

        payload.append(
            {
                "experience_id": _safe_str(
                    experience_id
                ),
                "problem_id": problem_id,
                "problem_description": description,

                "device_id": device_id,
                "device_category": device_category,
                "brand": brand,
                "model": model,

                "issue_id": issue_id,
                "issue_text": issue_text,

                "context_id": context_id,
                "context_text": context_text,

                "repair_type": repair_type,
            }
        )

    # ----------------------------------------------------------------
    # Problem
    # ----------------------------------------------------------------

    problem_query = """
    UNWIND $items AS x

    MERGE (problem:Problem {id: x.problem_id})

    SET problem.description = x.problem_description

    WITH x, problem

    MATCH (experience:Experience {
        id: x.experience_id
    })

    MERGE (experience)-[:ABOUT]->(problem)
    """

    neo4j_client.execute(
        problem_query,
        {"items": payload},
    )

    # ----------------------------------------------------------------
    # Device
    # ----------------------------------------------------------------

    device_items = [
        item
        for item in payload
        if item["device_id"]
    ]

    if device_items:

        device_query = """
        UNWIND $items AS x

        MERGE (device:Device {id: x.device_id})

        SET device.category = x.device_category,
            device.brand = x.brand,
            device.model = x.model

        WITH x, device

        MATCH (experience:Experience {
            id: x.experience_id
        })

        MERGE (experience)-[:INVOLVES]->(device)

        WITH x, device

        MATCH (problem:Problem {
            id: x.problem_id
        })

        MERGE (problem)-[:INVOLVES]->(device)
        """

        neo4j_client.execute(
            device_query,
            {"items": device_items},
        )

    # ----------------------------------------------------------------
    # Issue
    # ----------------------------------------------------------------

    issue_items = [
        item
        for item in payload
        if item["issue_id"]
    ]

    if issue_items:

        issue_query = """
        UNWIND $items AS x

        MERGE (issue:Issue {id: x.issue_id})

        SET issue.name = x.issue_text

        WITH x, issue

        MATCH (experience:Experience {
            id: x.experience_id
        })

        MERGE (experience)-[:HAS_ISSUE]->(issue)

        WITH x, issue

        MATCH (problem:Problem {
            id: x.problem_id
        })

        MERGE (problem)-[:HAS_ISSUE]->(issue)
        """

        neo4j_client.execute(
            issue_query,
            {"items": issue_items},
        )

    # ----------------------------------------------------------------
    # Context
    # ----------------------------------------------------------------

    context_items = [
        item
        for item in payload
        if item["context_id"]
    ]

    if context_items:

        context_query = """
        UNWIND $items AS x

        MERGE (context:Context {
            id: x.context_id
        })

        SET context.name = x.context_text

        WITH x, context

        MATCH (experience:Experience {
            id: x.experience_id
        })

        MERGE (experience)-[:OCCURRED_IN]->(context)

        WITH x, context

        MATCH (problem:Problem {
            id: x.problem_id
        })

        MERGE (problem)-[:HAS_CONTEXT]->(context)
        """

        neo4j_client.execute(
            context_query,
            {"items": context_items},
        )

    logger.info(
        "Synced Experience Intelligence: "
        "%s problems, %s devices, %s issues, %s contexts.",
        len(payload),
        len(device_items),
        len(issue_items),
        len(context_items),
    )

    return {
        "problems": len(payload),
        "devices": len(device_items),
        "issues": len(issue_items),
        "contexts": len(context_items),
    }


# ============================================================================
# EXPERIENCE OUTCOMES
# ============================================================================

def sync_experience_outcomes() -> int:
    """
    Sync actual experience_outcomes records.

    We deliberately do NOT invent an outcome when none exists.
    """

    outcomes = _records("experience_outcomes")

    payload = []

    for outcome in outcomes:

        outcome_id = outcome.get("id")
        experience_id = outcome.get(
            "experience_id"
        )

        if not outcome_id or not experience_id:
            continue

        payload.append(
            {
                "id": _safe_str(outcome_id),
                "experience_id": _safe_str(
                    experience_id
                ),
                "outcome_type": outcome.get(
                    "outcome_type"
                ),
                "description": outcome.get(
                    "outcome_description"
                ),
                "success_status": outcome.get(
                    "success_status"
                ),
                "customer_confirmed": outcome.get(
                    "customer_confirmed"
                ),
                "follow_up_required": outcome.get(
                    "follow_up_required"
                ),
            }
        )

    if not payload:
        logger.info(
            "No experience outcome records found."
        )
        return 0

    query = """
    UNWIND $outcomes AS x

    MERGE (outcome:Outcome {id: x.id})

    SET outcome.type = x.outcome_type,
        outcome.description = x.description,
        outcome.success_status = x.success_status,
        outcome.customer_confirmed = x.customer_confirmed,
        outcome.follow_up_required = x.follow_up_required

    WITH x, outcome

    MATCH (experience:Experience {
        id: x.experience_id
    })

    MERGE (experience)-[:RESULTED_IN]->(outcome)
    """

    neo4j_client.execute(
        query,
        {"outcomes": payload},
    )

    logger.info(
        "Synced %s Outcome nodes.",
        len(payload),
    )

    return len(payload)


# ============================================================================
# EXPERIENCE SKILLS
# ============================================================================

def sync_experience_skills() -> int:
    """Create Experience-REQUIRED_SKILL relationships."""

    records = _records("experience_skills")

    if not records:
        logger.info(
            "No experience-skill records found."
        )
        return 0

    payload = []

    for record in records:

        experience_id = record.get(
            "experience_id"
        )
        skill_id = record.get("skill_id")

        if not experience_id or not skill_id:
            continue

        skill = _find_by_id(
            "skills",
            skill_id,
        )

        if not skill:
            continue

        payload.append(
            {
                "experience_id": _safe_str(
                    experience_id
                ),
                "skill_id": _safe_str(skill_id),
                "skill_name": (
                    skill.get("name")
                    or "Unknown Skill"
                ),
                "proficiency": record.get(
                    "proficiency_demonstrated"
                ),
                "is_primary": record.get(
                    "is_primary_skill",
                    False,
                ),
            }
        )

    if not payload:
        return 0

    query = """
    UNWIND $skills AS x

    MERGE (skill:Skill {id: x.skill_id})

    SET skill.name = x.skill_name

    WITH x, skill

    MATCH (experience:Experience {
        id: x.experience_id
    })

    MERGE (experience)-[r:REQUIRED_SKILL]->(skill)

    SET r.proficiency_level = x.proficiency,
        r.is_primary = x.is_primary
    """

    neo4j_client.execute(
        query,
        {"skills": payload},
    )

    logger.info(
        "Synced %s Experience-Skill relationships.",
        len(payload),
    )

    return len(payload)


# ============================================================================
# KNOWLEDGE CASES
# ============================================================================

def sync_knowledge_cases() -> int:
    """Create KnowledgeCase nodes and graph relationships."""

    cases = _records("knowledge_cases")

    payload = []

    for case in cases:

        case_id = case.get("id")

        if not case_id:
            continue

        payload.append(
            {
                "id": _safe_str(case_id),
                "worker_id": _safe_str(
                    case.get("worker_id")
                ),
                "experience_id": _safe_str(
                    case.get("experience_id")
                ),
                "title": case.get("title"),
                "problem_summary": case.get(
                    "problem_summary"
                ),
                "diagnosis_summary": case.get(
                    "diagnosis_summary"
                ),
                "solution_summary": case.get(
                    "solution_summary"
                ),
                "lesson_learned": case.get(
                    "lesson_learned"
                ),
                "difficulty_level": case.get(
                    "difficulty_level"
                ),
                "visibility_status": case.get(
                    "visibility_status"
                ),
                "is_verified": case.get(
                    "is_verified",
                    False,
                ),
                "brand": case.get("brand"),
                "model": case.get("model"),
                "device_category": case.get(
                    "device_category"
                ),
            }
        )

    if not payload:
        return 0

    query = """
    UNWIND $cases AS k

    MERGE (knowledge:KnowledgeCase {
        id: k.id
    })

    SET knowledge.title = k.title,
        knowledge.problem_summary = k.problem_summary,
        knowledge.diagnosis_summary = k.diagnosis_summary,
        knowledge.solution_summary = k.solution_summary,
        knowledge.lesson_learned = k.lesson_learned,
        knowledge.difficulty_level = k.difficulty_level,
        knowledge.visibility_status = k.visibility_status,
        knowledge.is_verified = k.is_verified,
        knowledge.brand = k.brand,
        knowledge.model = k.model,
        knowledge.device_category = k.device_category

    WITH k, knowledge

    OPTIONAL MATCH (
        experience:Experience {
            id: k.experience_id
        }
    )

    FOREACH (
        ignored IN CASE
            WHEN experience IS NULL
            THEN []
            ELSE [1]
        END |
        MERGE (knowledge)-[:BASED_ON]->(experience)
    )

    WITH k, knowledge

    OPTIONAL MATCH (
        device:Device {
            brand: k.brand,
            model: k.model
        }
    )

    FOREACH (
        ignored IN CASE
            WHEN device IS NULL
            THEN []
            ELSE [1]
        END |
        MERGE (knowledge)-[:ABOUT]->(device)
    )
    """

    neo4j_client.execute(
        query,
        {"cases": payload},
    )

    logger.info(
        "Synced %s KnowledgeCase nodes.",
        len(payload),
    )

    return len(payload)


# ============================================================================
# FULL SYNC
# ============================================================================

def sync_all() -> Dict[str, int]:
    """Run the complete PostgreSQL/Supabase -> Neo4j projection."""

    logger.info(
        "Starting Neo4j synchronization..."
    )

    create_constraints()

    counts: Dict[str, int] = {}

    counts["workers"] = sync_workers()

    counts["worker_skills"] = sync_worker_skills()

    counts["experiences"] = sync_experiences()

    intelligence = sync_experience_intelligence()

    counts.update(intelligence)

    counts["experience_outcomes"] = (
        sync_experience_outcomes()
    )

    counts["experience_skills"] = (
        sync_experience_skills()
    )

    counts["knowledge_cases"] = (
        sync_knowledge_cases()
    )

    logger.info(
        "Neo4j synchronization completed: %s",
        counts,
    )

    return counts


# ============================================================================
# COMMAND LINE
# ============================================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    try:

        if not neo4j_client.health_check():
            raise RuntimeError(
                "Neo4j health check failed."
            )

        result = sync_all()

        print()
        print(
            "Neo4j synchronization successful."
        )
        print(
            "---------------------------------"
        )

        for name, count in result.items():
            print(
                f"{name}: {count}"
            )

    except Exception as exc:

        logger.exception(
            "Neo4j synchronization failed."
        )

        print()
        print(
            "Neo4j synchronization failed."
        )

        print(
            f"Error: {exc}"
        )

        raise