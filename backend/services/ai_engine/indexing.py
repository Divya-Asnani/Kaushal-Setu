"""Populate the pgvector index from the experiences already in PostgreSQL.

Semantic matching can only retrieve experiences that have an embedding row. Nothing in
the request path writes one, so this is run as a maintenance task: after seeding data,
and again whenever experiences are added or their searchable text changes.

    python -m backend.services.ai_engine.indexing            # index anything missing
    python -m backend.services.ai_engine.indexing --all      # re-embed everything
    python -m backend.services.ai_engine.indexing --status   # report coverage only

Leaving this unwired from the routes is deliberate: embedding on every write would put
a model call in the middle of a user request. The cost is that the index goes stale
between runs, so run it after any batch of new experiences.
"""
from __future__ import annotations

import argparse
import logging
import sys

from backend.services.ai_engine import canonical, embeddings, retrieval
from backend.services.ai_engine.config import settings

log = logging.getLogger("kaushalsetu.ai_engine.indexing")

EMBEDDING_VERSION = "v1"

_UNINDEXED = """
SELECT e.id, e.title, e.problem_description, e.diagnosis, e.outcome_summary
FROM experiences e
LEFT JOIN experience_embeddings ee ON ee.experience_id = e.id
WHERE ee.experience_id IS NULL
"""

_ALL = """
SELECT e.id, e.title, e.problem_description, e.diagnosis, e.outcome_summary
FROM experiences e
"""

_CONTEXTS = """
SELECT context_type, context_value FROM experience_contexts WHERE experience_id = %s
"""

_SKILLS = """
SELECT s.name
FROM experience_skills es JOIN skills s ON s.id = es.skill_id
WHERE es.experience_id = %s
"""

_UPSERT = """
INSERT INTO experience_embeddings
    (experience_id, embedding, embedding_model, embedding_version, source_text)
VALUES (%s, %s::vector, %s, %s, %s)
ON CONFLICT (experience_id) DO UPDATE SET
    embedding        = EXCLUDED.embedding,
    embedding_model  = EXCLUDED.embedding_model,
    embedding_version= EXCLUDED.embedding_version,
    source_text      = EXCLUDED.source_text
"""


def _source_text(row: dict) -> str:
    """Canonical text for one experience, including its contexts and skills."""
    contexts = retrieval.query(_CONTEXTS, (row["id"],))
    skills = [r["name"] for r in retrieval.query(_SKILLS, (row["id"],)) if r.get("name")]
    return canonical.experience_text(
        {
            "title": row.get("title"),
            "problem_description": row.get("problem_description"),
            "diagnosis": row.get("diagnosis"),
            "outcome_summary": row.get("outcome_summary"),
        },
        contexts=contexts,
        skills=skills,
    )


def index_experience(row: dict) -> bool:
    """Embed and upsert one experience. Returns True on success."""
    try:
        text = _source_text(row)
        if not text.strip():
            log.warning("Experience %s has no searchable content; skipped", row["id"])
            return False
        vector = embeddings.embed_text(text, embeddings.DOCUMENT)
        retrieval.execute(
            _UPSERT,
            (
                row["id"],
                retrieval.to_vector_literal(vector),
                embeddings.model_name(),
                EMBEDDING_VERSION,
                text,
            ),
        )
        return True
    except Exception:
        log.exception("Failed to index experience %s", row.get("id"))
        return False


def coverage() -> dict[str, int]:
    total = retrieval.query("SELECT count(*) AS n FROM experiences")[0]["n"]
    indexed = retrieval.query("SELECT count(*) AS n FROM experience_embeddings")[0]["n"]
    return {"experiences": int(total), "indexed": int(indexed), "missing": int(total) - int(indexed)}


def run(reindex_all: bool = False) -> int:
    rows = retrieval.query(_ALL if reindex_all else _UNINDEXED)
    if not rows:
        log.info("Nothing to index.")
        return 0
    log.info("Indexing %d experience(s) with %s", len(rows), embeddings.model_name())
    done = sum(1 for row in rows if index_experience(row))
    log.info("Indexed %d of %d", done, len(rows))
    return done


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s",
                        stream=sys.stdout)
    parser = argparse.ArgumentParser(description="Populate the pgvector index")
    parser.add_argument("--all", action="store_true", help="re-embed every experience")
    parser.add_argument("--status", action="store_true", help="report coverage and exit")
    args = parser.parse_args()

    if not settings.database_url or not settings.gemini_api_key:
        print("DATABASE_URL and GEMINI_API_KEY are required. See .env.example.")
        raise SystemExit(1)

    if args.status:
        for key, value in coverage().items():
            print(f"  {key}: {value}")
        return

    run(reindex_all=args.all)
    for key, value in coverage().items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
