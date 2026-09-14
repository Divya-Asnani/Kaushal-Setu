"""Canonicalisation: structured records become the single text that gets embedded.

Both sides of a similarity comparison must be written the same way. A customer problem
and a worker experience come from completely different sources, so each is rendered
into the same labelled-field layout before embedding. Without that, the embedding
picks up on the difference in phrasing style as much as the difference in meaning.

Skill names are also normalised here so that "Samsung Smartphone Repair",
"samsung smartphone repair" and "Samsung  smartphone repair" map to one canonical skill.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from backend.services.ai.fingerprint import Fingerprint

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^a-z0-9+/& -]")


def normalise_skill(name: str) -> str:
    """Lowercase, collapse whitespace, drop stray punctuation. Used for skill matching."""
    text = _PUNCT.sub(" ", (name or "").lower())
    return _WS.sub(" ", text).strip()


def normalise_skills(names: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for name in names or []:
        key = normalise_skill(name)
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _line(label: str, value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        items = [str(v).strip() for v in value if str(v).strip()]
        if not items:
            return None
        value = ", ".join(items)
    text = str(value).strip()
    return f"{label}: {text}" if text else None


def _render(pairs: list[tuple[str, Any]]) -> str:
    return "\n".join(line for line in (_line(k, v) for k, v in pairs) if line)


def fingerprint_text(fp: Fingerprint) -> str:
    """Canonical search text for a customer problem.

    ``suspected_component`` is rendered with its provenance so the embedding reflects
    a hypothesis rather than a diagnosis, matching the PRD safety rule.
    """
    suspected = None
    if fp.suspected_component:
        qualifier = (
            "reported by customer"
            if fp.suspected_component_source == "customer_stated"
            else "possible, unconfirmed"
        )
        suspected = f"{fp.suspected_component} ({qualifier})"

    return _render(
        [
            ("Category", fp.category),
            ("Device", fp.device_type),
            ("Brand", fp.brand),
            ("Model", fp.model),
            ("Issue", fp.issue),
            ("Symptoms", fp.symptoms),
            ("Context", fp.context),
            ("Suspected component", suspected),
            ("Repair type", fp.repair_type),
            ("Skills", normalise_skills(fp.extracted_skills)),
            ("Summary", fp.ai_summary),
        ]
    )


def experience_text(
    experience: dict[str, Any],
    contexts: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
    outcomes: list[dict[str, Any]] | None = None,
    skills: list[str] | None = None,
) -> str:
    """Canonical search text for a solved worker experience.

    Deliberately mirrors ``fingerprint_text``: same labels, same order where the
    concepts line up, so problem-to-experience cosine similarity is meaningful.
    """
    context_values = [
        f"{c.get('context_type')}: {c.get('context_value')}".strip(": ")
        for c in (contexts or [])
        if c.get("context_value") or c.get("context_type")
    ]
    action_values = [
        str(a.get("action_description") or "").strip()
        for a in sorted(actions or [], key=lambda a: a.get("step_number") or 0)
        if a.get("action_description")
    ]
    outcome_values = [
        str(o.get("outcome_description") or "").strip()
        for o in (outcomes or [])
        if o.get("outcome_description")
    ]

    return _render(
        [
            ("Title", experience.get("title")),
            ("Issue", experience.get("problem_description")),
            ("Context", context_values),
            ("Diagnosis", experience.get("diagnosis")),
            ("Actions", action_values),
            ("Outcome", experience.get("outcome_summary") or outcome_values),
            ("Skills", normalise_skills(skills or [])),
        ]
    )


def knowledge_case_text(case: dict[str, Any]) -> str:
    """Canonical search text for a Knowledge Hub case."""
    return _render(
        [
            ("Title", case.get("title")),
            ("Problem", case.get("problem_summary")),
            ("Diagnosis", case.get("diagnosis_summary")),
            ("Solution", case.get("solution_summary")),
            ("Lesson", case.get("lesson_learned")),
            ("Difficulty", case.get("difficulty_level")),
        ]
    )
