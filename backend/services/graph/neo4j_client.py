"""Neo4j contextual enrichment and projection.

Neo4j is a rebuildable projection, never the system of record (PRD section 16), so
every function here fails soft. If the graph is unreachable the matching pipeline
carries on with relational context only, which is exactly what the PRD requires.

Person 3 owns the graph schema; this module only reads for enrichment and writes the
projection for experiences that have become customer-verified.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from backend.core.config import settings

log = logging.getLogger(__name__)

_driver = None
_lock = threading.Lock()
_unavailable = False


def _get_driver():
    global _driver, _unavailable
    if _unavailable or not settings.neo4j_uri:
        return None
    with _lock:
        if _driver is None:
            try:
                from neo4j import GraphDatabase

                _driver = GraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_username, settings.neo4j_password),
                )
                _driver.verify_connectivity()
                log.info("Neo4j connected")
            except Exception as exc:
                log.warning("Neo4j unavailable (%s); continuing without graph enrichment", exc)
                _driver = None
                _unavailable = True
    return _driver


def is_available() -> bool:
    return _get_driver() is not None


_ENRICH_CYPHER = """
MATCH (w:Worker)-[:SOLVED]->(p:Problem)
WHERE w.worker_id IN $worker_ids
OPTIONAL MATCH (p)-[:HAS_CONTEXT]->(c:Context)
OPTIONAL MATCH (p)-[:REQUIRES_SKILL]->(s:Skill)
OPTIONAL MATCH (p)-[:RESULTED_IN]->(o:Outcome)
OPTIONAL MATCH (o)-[:SUPPORTED_BY]->(ev:Evidence)
RETURN w.worker_id                        AS worker_id,
       collect(DISTINCT c.value)          AS contexts,
       collect(DISTINCT s.name)           AS skills,
       count(DISTINCT p)                  AS solved_count,
       count(DISTINCT ev)                 AS evidence_count,
       sum(CASE WHEN o.customer_verified THEN 1 ELSE 0 END) AS verified_outcomes
"""


def enrich_workers(worker_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Contextual signals per worker. Returns {} whenever the graph cannot answer."""
    driver = _get_driver()
    if driver is None or not worker_ids:
        return {}
    try:
        with driver.session() as session:
            records = session.run(_ENRICH_CYPHER, worker_ids=list(worker_ids))
            return {
                str(r["worker_id"]): {
                    "contexts": [c for c in (r["contexts"] or []) if c],
                    "skills": [s for s in (r["skills"] or []) if s],
                    "solved_count": int(r["solved_count"] or 0),
                    "evidence_count": int(r["evidence_count"] or 0),
                    "verified_outcomes": int(r["verified_outcomes"] or 0),
                }
                for r in records
            }
    except Exception:
        log.warning("Neo4j enrichment failed; falling back to relational context", exc_info=True)
        return {}


_PROJECT_CYPHER = """
MERGE (w:Worker {worker_id: $worker_id})
MERGE (e:Experience {experience_id: $experience_id})
  SET e.title = $title,
      e.verified = $verified,
      e.updated_at = datetime()
MERGE (w)-[:HAS_EXPERIENCE]->(e)
MERGE (p:Problem {problem_key: $problem_key})
  SET p.description = $problem_description
MERGE (w)-[:SOLVED]->(p)
MERGE (e)-[:ABOUT]->(p)
WITH w, e, p
UNWIND $contexts AS ctx
  MERGE (c:Context {value: ctx})
  MERGE (p)-[:HAS_CONTEXT]->(c)
WITH w, e, p
UNWIND $skills AS skill
  MERGE (s:Skill {name: skill})
  MERGE (p)-[:REQUIRES_SKILL]->(s)
"""


def project_experience(
    experience_id: str,
    worker_id: str,
    title: str,
    problem_description: str,
    contexts: list[str],
    skills: list[str],
    verified: bool,
) -> bool:
    """Project a verified experience into the graph. Never raises."""
    driver = _get_driver()
    if driver is None:
        return False
    try:
        with driver.session() as session:
            session.run(
                _PROJECT_CYPHER,
                experience_id=str(experience_id),
                worker_id=str(worker_id),
                title=title or "",
                problem_description=problem_description or "",
                problem_key=str(experience_id),
                contexts=[c for c in contexts if c],
                skills=[s for s in skills if s],
                verified=bool(verified),
            )
        return True
    except Exception:
        log.warning("Neo4j projection failed for experience %s", experience_id, exc_info=True)
        return False


def close() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
