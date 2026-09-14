"""Test wiring: the real app, with Supabase, pgvector and Gemini replaced by fakes.

Everything between the HTTP boundary and the external services is the production code
path — routers, dependencies, authorization, schemas, the matching pipeline. Only the
three things that need network or credentials are substituted.
"""
from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.tests import fakes
from backend.tests.fakes import FakeSupabase, fake_embedding


@pytest.fixture
def store() -> FakeSupabase:
    return FakeSupabase()


@pytest.fixture
def client(store, monkeypatch) -> TestClient:
    from backend import main
    from backend.api import deps
    from backend.services.ai import embeddings, fingerprint
    from backend.services.graph import neo4j_client
    from backend.services.matching import retrieval

    # db.supabase.table() resolves get_supabase() on each call, so patching the factory
    # reaches every module that imported `table` directly.
    monkeypatch.setattr("backend.db.supabase.get_supabase", lambda: store)

    monkeypatch.setattr(
        retrieval, "query", lambda sql, params=(): fakes.fake_vector_query(store, sql, params)
    )

    monkeypatch.setattr(embeddings, "embed_texts",
                        lambda texts, task_type=embeddings.DOCUMENT: [fake_embedding(t) for t in texts])
    monkeypatch.setattr(embeddings, "embed_text",
                        lambda text, task_type=embeddings.DOCUMENT: fake_embedding(text))
    monkeypatch.setattr(embeddings, "embed_query", lambda text: fake_embedding(text))
    monkeypatch.setattr(embeddings, "model_name", lambda: "fake-embedding-001")

    # Neo4j is optional by design; the default test run exercises the degraded path.
    monkeypatch.setattr(neo4j_client, "is_available", lambda: False)
    monkeypatch.setattr(neo4j_client, "enrich_workers", lambda ids: {})
    monkeypatch.setattr(neo4j_client, "project_experience", lambda **kwargs: False)

    def fake_fingerprint(title: str, description: str, images=None):
        """Derive a fingerprint from the text without calling a model."""
        blob = f"{title} {description}".lower()
        model = "Galaxy S23" if "s23" in blob else ("Galaxy S22" if "s22" in blob else None)
        stated = "motherboard" if "motherboard" in blob else None
        return fingerprint.Fingerprint(
            device_type="smartphone" if model else "ceiling fan",
            brand="Samsung" if model else None,
            model=model,
            category="electronics repair" if model else "home electrical",
            issue="no power" if "turn on" in blob or "power" in blob else "not working",
            symptoms=["no display"] if "display" in blob else [],
            context=["physical drop"] if ("fell" in blob or "drop" in blob) else [],
            suspected_component=stated,
            suspected_component_source=fingerprint.STATED if stated else None,
            repair_type="board-level diagnosis" if model else "electrical repair",
            extracted_skills=(
                ["samsung smartphone repair", "board-level repair"] if model
                else ["ceiling fan repair"]
            ),
            ai_summary="Test fingerprint.",
            safety_warning=fingerprint.detect_safety_risk(title, description),
            model_used="fake-gemma",
            raw_ai_output={"model": "fake-gemma"},
        )

    monkeypatch.setattr(fingerprint, "generate_fingerprint", fake_fingerprint)
    monkeypatch.setattr("backend.api.routes.problems.fp_service.generate_fingerprint",
                        fake_fingerprint)

    # Identity comes from the validated JWT; tests present the subject directly.
    monkeypatch.setattr(deps, "decode_access_token", lambda token: {"sub": token})

    with TestClient(main.app) as test_client:
        yield test_client


# --------------------------------------------------------------------------- helpers


def auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_id}"}


class World:
    """A populated fixture world: one customer, three workers with experiences."""

    def __init__(self, store: FakeSupabase):
        self.store = store
        self.customer = self._profile("Demo Customer", "customer")
        self.other_customer = self._profile("Other Customer", "customer")
        self.admin = self._profile("Admin", "admin")

        self.skill_samsung = self._skill("Samsung smartphone repair", "electronics")
        self.skill_board = self._skill("Board-level repair", "electronics")

        self.worker_a = self._worker("Ravi", 18.5204, 73.8567, 15)
        self.worker_b = self._worker("Arjun", 18.5089, 73.8553, 15)
        self.worker_c = self._worker("Meena", 18.5310, 73.8446, 15)
        self.worker_far = self._worker("Faraway", 19.0760, 72.8777, 5)

    def _profile(self, name: str, role: str) -> str:
        user_id = str(uuid.uuid4())
        self.store.seed("profiles", [{
            "id": user_id, "display_name": name, "role": role, "is_active": True,
        }])
        return user_id

    def _skill(self, name: str, category: str) -> str:
        skill_id = str(uuid.uuid4())
        self.store.seed("skills", [{
            "id": skill_id, "name": name, "category": category, "is_active": True,
        }])
        return skill_id

    def _worker(self, name: str, lat: float, lon: float, radius: float) -> str:
        user_id = self._profile(name, "worker")
        self.store.seed("worker_profiles", [{
            "user_id": user_id,
            "professional_title": "Mobile Repair Technician",
            "years_experience": 5,
            "service_radius_km": radius,
            "latitude": lat,
            "longitude": lon,
            "city": "Pune",
            "availability_status": "available",
            "is_verified": True,
        }])
        return user_id

    def add_experience(
        self,
        worker_id: str,
        title: str,
        description: str,
        status: str = "verified",
        confidence: float = 90,
        contexts: list[tuple[str, str]] | None = None,
        skills: list[str] | None = None,
    ) -> str:
        experience_id = str(uuid.uuid4())
        self.store.seed("experiences", [{
            "id": experience_id,
            "worker_id": worker_id,
            "title": title,
            "problem_description": description,
            "diagnosis": description,
            "outcome_summary": "Repaired.",
            "experience_status": status,
            "verification_confidence": confidence,
        }])
        for context_type, context_value in (contexts or []):
            self.store.seed("experience_contexts", [{
                "id": str(uuid.uuid4()),
                "experience_id": experience_id,
                "context_type": context_type,
                "context_value": context_value,
                "importance_score": 0.8,
            }])
        for skill_id in (skills or []):
            self.store.seed("experience_skills", [{
                "id": str(uuid.uuid4()),
                "experience_id": experience_id,
                "skill_id": skill_id,
            }])
        source = f"{title} {description}"
        self.store.seed("experience_embeddings", [{
            "id": str(uuid.uuid4()),
            "experience_id": experience_id,
            "embedding": fake_embedding(source),
            "embedding_model": "fake-embedding-001",
            "embedding_version": "v1",
            "source_text": source,
        }])
        return experience_id


@pytest.fixture
def world(store) -> World:
    return World(store)
