"""In-memory stand-ins for Supabase, pgvector and the Gemini models.

The fake database is deliberately strict rather than permissive: it enforces the
NOT NULL columns and CHECK value sets recorded in docs/schema-reference.md. A test
that writes a value the real PostgreSQL schema would reject fails here too, which is
the only way to check the API against the documented schema without a live project.
"""
from __future__ import annotations

import hashlib
import math
import re
import uuid
from datetime import datetime, timezone
from typing import Any

# --------------------------------------------------------------------------- schema

# NOT NULL columns that have no database default, so an insert must supply them.
REQUIRED: dict[str, set[str]] = {
    "profiles": {"display_name"},
    "worker_profiles": {"user_id", "professional_title"},
    "skills": {"name", "category"},
    "worker_skills": {"worker_id", "skill_id"},
    "certificates": {"worker_id", "certificate_name"},
    "problems": {"customer_id", "title", "description"},
    "problem_media": {"problem_id", "storage_path", "media_type"},
    "problem_fingerprints": {"problem_id"},
    "experiences": {"worker_id", "title", "problem_description"},
    "experience_contexts": {
        "experience_id", "context_type", "context_value", "importance_score",
    },
    "experience_actions": {
        "experience_id", "step_number", "action_type", "action_description",
    },
    "experience_outcomes": {"experience_id", "outcome_type", "outcome_description"},
    "experience_skills": {"experience_id", "skill_id"},
    "experience_media": {"experience_id", "storage_path", "media_type"},
    "experience_embeddings": {"experience_id", "embedding", "source_text"},
    "service_requests": {"problem_id", "worker_id"},
    "jobs": {"service_request_id"},
    "job_status_history": {"job_id", "status"},
    "verifications": {"job_id", "verification_type"},
    "feedback": {"job_id", "customer_id", "worker_id", "rating"},
    "knowledge_cases": {"worker_id", "title", "problem_summary"},
    "knowledge_case_media": {"knowledge_case_id", "storage_path", "media_type"},
    "knowledge_case_embeddings": {"knowledge_case_id", "embedding", "source_text"},
    "match_results": {
        "problem_id", "worker_id", "problem_similarity", "context_similarity",
        "verified_experience_confidence", "proximity_score", "match_score",
        "rank_position",
    },
    "notifications": {"user_id", "notification_type", "title", "message"},
}

# CHECK constraint value sets, from the table documentation.
ENUMS: dict[tuple[str, str], set[str]] = {
    ("profiles", "role"): {"customer", "worker", "admin"},
    ("worker_profiles", "availability_status"): {"available", "busy", "offline"},
    ("worker_skills", "proficiency_level"): {"beginner", "intermediate", "advanced", "expert"},
    ("certificates", "verification_status"): {"pending", "verified", "rejected", "expired"},
    ("problems", "status"): {
        "open", "matched", "requested", "in_progress", "resolved", "cancelled",
    },
    ("problem_media", "media_type"): {"image", "video", "document"},
    ("problem_fingerprints", "embedding_status"): {"pending", "generated", "failed"},
    ("experiences", "experience_status"): {
        "draft", "submitted", "verified", "disputed", "archived",
    },
    ("experience_outcomes", "success_status"): {
        "successful", "partially_successful", "unsuccessful", "unknown",
    },
    ("experience_skills", "proficiency_demonstrated"): {
        "beginner", "intermediate", "advanced", "expert",
    },
    ("experience_media", "media_type"): {"image", "video", "document"},
    ("experience_media", "media_role"): {
        "evidence", "before", "during", "after", "diagnostic", "other",
    },
    ("service_requests", "status"): {
        "pending", "accepted", "rejected", "cancelled", "expired",
    },
    ("jobs", "status"): {"confirmed", "in_progress", "completed", "cancelled", "disputed"},
    ("job_status_history", "status"): {
        "confirmed", "in_progress", "completed", "cancelled", "disputed",
    },
    ("verifications", "verification_type"): {
        "customer_confirmation", "evidence_review", "admin_review", "dispute",
    },
    ("verifications", "verification_status"): {"pending", "verified", "rejected", "disputed"},
    ("knowledge_cases", "difficulty_level"): {
        "beginner", "intermediate", "advanced", "expert",
    },
    ("knowledge_cases", "visibility_status"): {"draft", "published", "archived"},
    ("knowledge_case_media", "media_type"): {"image", "video", "document"},
}

# Numeric ranges the CHECK constraints enforce.
RANGES: dict[tuple[str, str], tuple[float, float]] = {
    ("experiences", "verification_confidence"): (0, 100),
    ("experience_contexts", "importance_score"): (0, 1),
    ("verifications", "verification_score"): (0, 100),
    ("feedback", "rating"): (1, 5),
    ("match_results", "problem_similarity"): (0, 100),
    ("match_results", "context_similarity"): (0, 100),
    ("match_results", "verified_experience_confidence"): (0, 100),
    ("match_results", "proximity_score"): (0, 100),
    ("match_results", "match_score"): (0, 100),
    ("problems", "latitude"): (-90, 90),
    ("problems", "longitude"): (-180, 180),
    ("worker_profiles", "latitude"): (-90, 90),
    ("worker_profiles", "longitude"): (-180, 180),
}

# Column defaults applied on insert when the caller omits the column.
DEFAULTS: dict[str, dict[str, Any]] = {
    "profiles": {"role": "customer", "is_active": True},
    "worker_profiles": {
        "years_experience": 0, "service_radius_km": 10,
        "availability_status": "available", "is_verified": False,
    },
    "skills": {"is_active": True},
    "worker_skills": {
        "proficiency_level": "intermediate", "years_experience": 0, "is_primary": False,
    },
    "certificates": {"verification_status": "pending"},
    "problems": {"status": "open"},
    "problem_media": {"media_type": "image"},
    "problem_fingerprints": {"embedding_status": "pending", "fingerprint_version": "v1"},
    "experiences": {"experience_status": "draft", "verification_confidence": 0},
    "experience_outcomes": {
        "success_status": "successful", "customer_confirmed": False,
        "follow_up_required": False,
    },
    "experience_skills": {"is_primary_skill": False},
    "experience_media": {"media_role": "evidence", "is_verified": False},
    "experience_embeddings": {
        "embedding_model": "text-embedding-3-small", "embedding_version": "v1",
    },
    "knowledge_case_embeddings": {
        "embedding_model": "text-embedding-3-small", "embedding_version": "v1",
    },
    "service_requests": {"status": "pending"},
    "jobs": {"status": "confirmed"},
    "verifications": {"verification_status": "pending"},
    "knowledge_cases": {
        "difficulty_level": "intermediate", "visibility_status": "draft",
        "is_verified": False,
    },
    "notifications": {"is_read": False},
}

# Tables whose primary key is not "id".
PK = {
    "profiles": "id",
    "worker_profiles": "user_id",
}

UNIQUE = {
    "problem_fingerprints": "problem_id",
    "experience_embeddings": "experience_id",
    "knowledge_case_embeddings": "knowledge_case_id",
    "jobs": "service_request_id",
}


class ConstraintError(AssertionError):
    """Raised when a write would violate the documented schema."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------------ fake client


class _Result:
    def __init__(self, data: list[dict[str, Any]]):
        self.data = data


class FakeTable:
    def __init__(self, store: "FakeSupabase", name: str):
        self.store = store
        self.name = name
        self.rows = store.data.setdefault(name, [])
        self._op = "select"
        self._columns = "*"
        self._payload: Any = None
        self._on_conflict: str | None = None
        self._filters: list[tuple[str, str, Any]] = []
        self._order: list[tuple[str, bool]] = []
        self._range: tuple[int, int] | None = None
        self._limit: int | None = None

    # -- query building ----------------------------------------------------
    def select(self, columns: str = "*", **_: Any) -> "FakeTable":
        self._op = "select"
        self._columns = columns
        return self

    def insert(self, payload: Any) -> "FakeTable":
        self._op = "insert"
        self._payload = payload
        return self

    def upsert(self, payload: Any, on_conflict: str | None = None) -> "FakeTable":
        self._op = "upsert"
        self._payload = payload
        self._on_conflict = on_conflict
        return self

    def update(self, payload: dict[str, Any]) -> "FakeTable":
        self._op = "update"
        self._payload = payload
        return self

    def delete(self) -> "FakeTable":
        self._op = "delete"
        return self

    def eq(self, column: str, value: Any) -> "FakeTable":
        self._filters.append((column, "eq", value))
        return self

    def neq(self, column: str, value: Any) -> "FakeTable":
        self._filters.append((column, "neq", value))
        return self

    def in_(self, column: str, values: list[Any]) -> "FakeTable":
        self._filters.append((column, "in", list(values)))
        return self

    def ilike(self, column: str, pattern: str) -> "FakeTable":
        self._filters.append((column, "ilike", pattern))
        return self

    def order(self, column: str, desc: bool = False) -> "FakeTable":
        self._order.append((column, desc))
        return self

    def limit(self, count: int) -> "FakeTable":
        self._limit = count
        return self

    def range(self, start: int, end: int) -> "FakeTable":
        self._range = (start, end)
        return self

    # -- execution ---------------------------------------------------------
    def _matches(self, row: dict[str, Any]) -> bool:
        for column, op, value in self._filters:
            actual = row.get(column)
            if op == "eq":
                if str(actual) != str(value):
                    return False
            elif op == "neq":
                if str(actual) == str(value):
                    return False
            elif op == "in":
                if str(actual) not in {str(v) for v in value}:
                    return False
            elif op == "ilike":
                pattern = "^" + re.escape(value).replace("%", ".*") + "$"
                if not re.match(pattern, str(actual or ""), re.IGNORECASE):
                    return False
        return True

    def _validate(self, row: dict[str, Any], is_insert: bool) -> None:
        if is_insert:
            missing = {
                c for c in REQUIRED.get(self.name, set())
                if row.get(c) is None
            }
            if missing:
                raise ConstraintError(
                    f"{self.name}: NOT NULL column(s) {sorted(missing)} missing on insert"
                )
        for column, value in row.items():
            if value is None:
                continue
            allowed = ENUMS.get((self.name, column))
            if allowed and str(value) not in allowed:
                raise ConstraintError(
                    f"{self.name}.{column}: '{value}' violates CHECK "
                    f"(allowed: {sorted(allowed)})"
                )
            bounds = RANGES.get((self.name, column))
            if bounds is not None:
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    raise ConstraintError(f"{self.name}.{column}: '{value}' is not numeric")
                low, high = bounds
                if not low <= numeric <= high:
                    raise ConstraintError(
                        f"{self.name}.{column}: {numeric} outside CHECK range {bounds}"
                    )

    def _prepare(self, payload: dict[str, Any]) -> dict[str, Any]:
        row = {**DEFAULTS.get(self.name, {}), **payload}
        pk = PK.get(self.name, "id")
        row.setdefault(pk, str(uuid.uuid4()))
        row.setdefault("created_at", _now())
        if self.name not in {"problem_media", "experience_media", "knowledge_case_media",
                             "job_status_history", "notifications"}:
            row.setdefault("updated_at", _now())
        if self.name == "job_status_history":
            row.setdefault("changed_at", _now())
        if self.name == "service_requests":
            row.setdefault("requested_at", _now())
        self._validate(row, is_insert=True)
        return row

    def _embed(self, row: dict[str, Any]) -> dict[str, Any]:
        """Resolve PostgREST embedded selects such as 'skills(name)'."""
        out = dict(row)
        for match in re.finditer(r"(\w+)\(([^)]*)\)", self._columns):
            related, columns = match.group(1), match.group(2)
            fk = related.rstrip("s") + "_id"
            target_id = row.get(fk)
            if target_id is None:
                out[related] = None
                continue
            found = next(
                (r for r in self.store.data.get(related, [])
                 if str(r.get(PK.get(related, "id"))) == str(target_id)),
                None,
            )
            if found is None:
                out[related] = None
            elif columns.strip() == "*":
                out[related] = dict(found)
            else:
                wanted = [c.strip() for c in columns.split(",")]
                out[related] = {c: found.get(c) for c in wanted}
        return out

    def execute(self) -> _Result:
        if self._op == "select":
            selected = [r for r in self.rows if self._matches(r)]
            for column, desc in reversed(self._order):
                selected.sort(
                    key=lambda r: (r.get(column) is None, r.get(column) or 0
                                   if isinstance(r.get(column), (int, float))
                                   else str(r.get(column) or "")),
                    reverse=desc,
                )
            if self._range is not None:
                start, end = self._range
                selected = selected[start : end + 1]
            if self._limit is not None:
                selected = selected[: self._limit]
            return _Result([self._embed(r) for r in selected])

        if self._op in {"insert", "upsert"}:
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            written: list[dict[str, Any]] = []
            for payload in payloads:
                conflict = self._on_conflict or UNIQUE.get(self.name)
                existing = None
                if self._op == "upsert" and conflict and payload.get(conflict) is not None:
                    existing = next(
                        (r for r in self.rows
                         if str(r.get(conflict)) == str(payload[conflict])),
                        None,
                    )
                if existing is not None:
                    self._validate(payload, is_insert=False)
                    existing.update(payload)
                    existing["updated_at"] = _now()
                    written.append(dict(existing))
                    continue

                unique_column = UNIQUE.get(self.name)
                if (
                    self._op == "insert"
                    and unique_column
                    and payload.get(unique_column) is not None
                    and any(
                        str(r.get(unique_column)) == str(payload[unique_column])
                        for r in self.rows
                    )
                ):
                    raise ConstraintError(
                        f"{self.name}.{unique_column}: duplicate value "
                        f"'{payload[unique_column]}' violates UNIQUE"
                    )
                row = self._prepare(payload)
                self.rows.append(row)
                written.append(dict(row))
            return _Result(written)

        if self._op == "update":
            updated = []
            for row in self.rows:
                if not self._matches(row):
                    continue
                self._validate(self._payload, is_insert=False)
                row.update(self._payload)
                updated.append(dict(row))
            return _Result(updated)

        if self._op == "delete":
            removed = [r for r in self.rows if self._matches(r)]
            self.rows[:] = [r for r in self.rows if not self._matches(r)]
            return _Result([dict(r) for r in removed])

        raise AssertionError(f"unsupported operation {self._op}")


class _FakeAdmin:
    def __init__(self, store: "FakeSupabase"):
        self.store = store

    def create_user(self, payload: dict[str, Any]):
        raise NotImplementedError("auth admin is not exercised by the API tests")


class _FakeAuth:
    def __init__(self, store: "FakeSupabase"):
        self.admin = _FakeAdmin(store)


class FakeSupabase:
    """Minimal stand-in for the Supabase client surface this backend uses."""

    def __init__(self) -> None:
        self.data: dict[str, list[dict[str, Any]]] = {}
        self.auth = _FakeAuth(self)

    def table(self, name: str) -> FakeTable:
        return FakeTable(self, name)

    # -- test helpers ------------------------------------------------------
    def seed(self, table_name: str, rows: list[dict[str, Any]]) -> None:
        self.data.setdefault(table_name, []).extend(rows)

    def all(self, table_name: str) -> list[dict[str, Any]]:
        return self.data.get(table_name, [])

    def count(self, table_name: str) -> int:
        return len(self.data.get(table_name, []))


# ------------------------------------------------------------------------- fake AI

EMBED_DIM = 1536


def fake_embedding(text: str) -> list[float]:
    """Deterministic bag-of-tokens vector.

    Texts that share vocabulary land close together, so retrieval and ranking can be
    exercised meaningfully without calling a model.
    """
    vector = [0.0] * EMBED_DIM
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    for token in tokens:
        digest = hashlib.md5(token.encode()).digest()
        index = int.from_bytes(digest[:4], "big") % EMBED_DIM
        vector[index] += 1.0
    norm = math.sqrt(sum(v * v for v in vector))
    if norm:
        vector = [v / norm for v in vector]
    return vector


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def fake_vector_query(store: FakeSupabase, sql: str, params: tuple[Any, ...]):
    """Stand in for the pgvector SQL in services/matching/retrieval.py."""
    literal = params[0]
    query_vector = [float(x) for x in literal.strip("[]").split(",")]
    limit = params[-1]

    if "knowledge_case_embeddings" in sql:
        results = []
        for embedding in store.all("knowledge_case_embeddings"):
            case = next(
                (c for c in store.all("knowledge_cases")
                 if str(c["id"]) == str(embedding["knowledge_case_id"])),
                None,
            )
            if case is None or case.get("visibility_status") != "published":
                continue
            results.append(
                {
                    "knowledge_case_id": case["id"],
                    "similarity": cosine(query_vector, embedding["embedding"]),
                    "title": case.get("title"),
                    "worker_id": case.get("worker_id"),
                    "is_verified": case.get("is_verified"),
                    "difficulty_level": case.get("difficulty_level"),
                }
            )
        results.sort(key=lambda r: r["similarity"], reverse=True)
        return results[:limit]

    results = []
    for embedding in store.all("experience_embeddings"):
        experience = next(
            (e for e in store.all("experiences")
             if str(e["id"]) == str(embedding["experience_id"])),
            None,
        )
        if experience is None or experience.get("experience_status") == "archived":
            continue
        results.append(
            {
                "experience_id": experience["id"],
                "worker_id": experience["worker_id"],
                "similarity": cosine(query_vector, embedding["embedding"]),
                "title": experience.get("title"),
                "problem_description": experience.get("problem_description"),
                "diagnosis": experience.get("diagnosis"),
                "outcome_summary": experience.get("outcome_summary"),
                "experience_status": experience.get("experience_status"),
                "verification_confidence": experience.get("verification_confidence") or 0,
                "source_text": embedding.get("source_text") or "",
            }
        )

    if "CASE WHEN" in sql:  # the similar-experiences ordering prefers verified rows
        results.sort(
            key=lambda r: (r["experience_status"] != "verified", -r["similarity"])
        )
    else:
        results.sort(key=lambda r: r["similarity"], reverse=True)
    return results[:limit]
