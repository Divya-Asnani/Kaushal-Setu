"""Keeping the vector index in step with the relational source of truth.

Whenever searchable content changes -- an experience is edited, a job completes, a
knowledge case is published -- the corresponding embedding row is rebuilt. Indexing
failures are logged and swallowed rather than raised: PostgreSQL is the system of
record, and a stale vector row must never roll back a committed job transition.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.db.supabase import rows, table
from backend.services.ai import canonical, embeddings

log = logging.getLogger(__name__)

EMBEDDING_VERSION = "v1"


def _load_experience_parts(experience_id: str) -> dict[str, Any]:
    contexts = rows(
        table("experience_contexts").select("*").eq("experience_id", experience_id).execute()
    )
    actions = rows(
        table("experience_actions").select("*").eq("experience_id", experience_id).execute()
    )
    outcomes = rows(
        table("experience_outcomes").select("*").eq("experience_id", experience_id).execute()
    )
    skill_links = rows(
        table("experience_skills")
        .select("skill_id, skills(name)")
        .eq("experience_id", experience_id)
        .execute()
    )
    skills = [
        (link.get("skills") or {}).get("name")
        for link in skill_links
        if (link.get("skills") or {}).get("name")
    ]
    return {
        "contexts": contexts,
        "actions": actions,
        "outcomes": outcomes,
        "skills": skills,
    }


def build_experience_text(experience: dict[str, Any]) -> str:
    parts = _load_experience_parts(experience["id"])
    return canonical.experience_text(experience, **parts)


def index_experience(experience_id: str) -> bool:
    """Rebuild the embedding for one experience. Returns True on success."""
    try:
        experience = (
            rows(table("experiences").select("*").eq("id", experience_id).limit(1).execute()) or [None]
        )[0]
        if experience is None:
            log.warning("Cannot index missing experience %s", experience_id)
            return False

        source_text = build_experience_text(experience)
        if not source_text.strip():
            log.warning("Experience %s has no searchable content; skipping", experience_id)
            return False

        vector = embeddings.embed_text(source_text, embeddings.DOCUMENT)
        table("experience_embeddings").upsert(
            {
                "experience_id": experience_id,
                "embedding": vector,
                "embedding_model": embeddings.model_name(),
                "embedding_version": EMBEDDING_VERSION,
                "source_text": source_text,
            },
            on_conflict="experience_id",
        ).execute()
        return True
    except Exception:
        log.exception("Failed to index experience %s", experience_id)
        return False


def index_knowledge_case(case_id: str) -> bool:
    """Rebuild the embedding for one knowledge case. Returns True on success."""
    try:
        case = (
            rows(table("knowledge_cases").select("*").eq("id", case_id).limit(1).execute()) or [None]
        )[0]
        if case is None:
            log.warning("Cannot index missing knowledge case %s", case_id)
            return False

        source_text = canonical.knowledge_case_text(case)
        if not source_text.strip():
            return False

        vector = embeddings.embed_text(source_text, embeddings.DOCUMENT)
        table("knowledge_case_embeddings").upsert(
            {
                "knowledge_case_id": case_id,
                "embedding": vector,
                "embedding_model": embeddings.model_name(),
                "embedding_version": EMBEDDING_VERSION,
                "source_text": source_text,
            },
            on_conflict="knowledge_case_id",
        ).execute()
        return True
    except Exception:
        log.exception("Failed to index knowledge case %s", case_id)
        return False
