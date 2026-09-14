"""Tests for the AI engine: parsing, safety rules, canonical text and the adapters.

None of these need credentials or a network. The Gemini call and the pgvector query are
the only things stubbed; everything else is the real code path.
"""
from __future__ import annotations

import pytest

from backend.services.ai_engine import canonical
from backend.services.ai_engine.fingerprint import (
    INFERRED,
    STATED,
    Fingerprint,
    _coerce,
    _extract_json,
    detect_safety_risk,
)


# ----------------------------------------------------------- parsing model output


def test_json_is_recovered_from_a_fenced_reply():
    assert _extract_json('```json\n{"issue": "no power"}\n```') == {"issue": "no power"}


def test_json_is_recovered_from_a_chatty_reply():
    text = 'Sure! Here it is:\n{"issue": "no power", "brand": "Samsung"}\nHope that helps.'
    assert _extract_json(text)["brand"] == "Samsung"


def test_a_reply_with_no_json_is_rejected():
    with pytest.raises(ValueError):
        _extract_json("there is no JSON object here at all")


def test_list_fields_are_coerced():
    clean = _coerce({"symptoms": "no display", "extracted_skills": None})
    assert clean["symptoms"] == ["no display"]
    assert clean["extracted_skills"] == []


def test_invented_urgency_values_are_discarded():
    assert _coerce({"urgency": "catastrophic"})["urgency"] is None


# ------------------------------------------------------------------ safety rules


def test_a_named_component_always_carries_provenance():
    """A suspected component must never be presented as an established fault."""
    clean = _coerce({"suspected_component": "motherboard"})
    assert clean["suspected_component_source"] == INFERRED


def test_provenance_is_cleared_when_no_component_is_named():
    clean = _coerce({"suspected_component": None, "suspected_component_source": STATED})
    assert clean["suspected_component_source"] is None


@pytest.mark.parametrize("text", [
    "I got a shock from the switch",
    "There were sparks from the board",
    "the wiring started smoking",
    "smell of burning near the MCB",
])
def test_high_risk_wording_raises_a_warning(text):
    assert detect_safety_risk(text) is not None


def test_an_ordinary_fault_raises_no_warning():
    assert detect_safety_risk("The screen is cracked and touch is unresponsive") is None


# --------------------------------------------------------------- canonical text


def test_a_customer_stated_component_reads_as_reported():
    fp = Fingerprint(brand="Samsung", model="Galaxy S23",
                     suspected_component="motherboard", suspected_component_source=STATED)
    assert "motherboard (reported by customer)" in canonical.fingerprint_text(fp)


def test_an_inferred_component_reads_as_unconfirmed():
    fp = Fingerprint(suspected_component="motherboard", suspected_component_source=INFERRED)
    assert "unconfirmed" in canonical.fingerprint_text(fp)


def test_skill_spelling_variants_collapse():
    assert canonical.normalise_skill("Samsung  Smartphone Repair!") == "samsung smartphone repair"


# --------------------------------------------------------------------- adapters


def _stub_engine(monkeypatch, fingerprint=None, raises=None):
    """Point the adapter at a scripted engine result instead of a real model call."""
    from backend.services.ai_engine import adapters
    from backend.services.ai_engine.config import settings

    monkeypatch.setattr(settings, "gemini_api_key", "present")

    def fake(title, description, images=None):
        if raises is not None:
            raise raises
        return fingerprint

    monkeypatch.setattr(adapters.fp_engine, "generate_fingerprint", fake)
    return adapters


def test_fingerprint_adapter_falls_back_when_the_engine_is_off(monkeypatch):
    """No credentials must degrade the result, never fail the request."""
    from backend.services.ai_engine import adapters
    from backend.services.ai_engine.config import settings

    monkeypatch.setattr(settings, "gemini_api_key", "")
    result = adapters.extract_problem_fingerprint("Fan issue", "Ceiling fan hums, no spin.")
    assert result["device_type"]
    assert "extracted_skills" in result


def test_fingerprint_adapter_falls_back_when_the_model_fails(monkeypatch):
    adapters = _stub_engine(monkeypatch, raises=RuntimeError("model down"))
    result = adapters.extract_problem_fingerprint("Fan issue", "Ceiling fan hums, no spin.")
    assert result["device_type"]


def test_the_adapter_returns_the_same_keys_as_the_builtin_extractor(monkeypatch):
    """The route stores this dict directly, so the shape cannot drift."""
    from backend.services.ai.fingerprint import extract_problem_fingerprint as heuristic

    adapters = _stub_engine(monkeypatch, fingerprint=Fingerprint(
        device_type="smartphone", brand="Samsung", model="Galaxy S23",
        category="electronics repair", issue="no power", symptoms=["no display"],
        context=["physical drop"], suspected_component="motherboard",
        suspected_component_source=STATED, repair_type="board-level diagnosis",
        extracted_skills=["board-level repair"], ai_summary="Summary.",
        model_used="test-model",
    ))
    title, description = "Phone dead", "Samsung S23 fell and will not power on."
    assert set(adapters.extract_problem_fingerprint(title, description)) == set(
        heuristic(title, description)
    )


def test_the_adapter_never_blanks_a_field_the_model_left_empty(monkeypatch):
    """An empty model answer must not regress a field the heuristic could fill."""
    adapters = _stub_engine(monkeypatch, fingerprint=Fingerprint(ai_summary=""))
    result = adapters.extract_problem_fingerprint("Fan", "Ceiling fan hums but will not spin.")
    assert result["device_type"]
    assert result["symptoms"]
    assert result["ai_summary"]


def test_the_adapter_records_component_provenance_for_the_client(monkeypatch):
    adapters = _stub_engine(monkeypatch, fingerprint=Fingerprint(
        suspected_component="motherboard", suspected_component_source=STATED,
        safety_warning="Careful.", model_used="test-model",
    ))
    context = adapters.extract_problem_fingerprint("t", "d")["context"]
    assert context["suspected_component_source"] == STATED
    assert context["safety_warning"] == "Careful."
    assert context["extracted_by"] == "test-model"


def test_matching_adapter_falls_back_when_the_engine_is_off(monkeypatch):
    from backend.services.ai_engine import adapters
    from backend.services.ai_engine.config import settings

    monkeypatch.setattr(settings, "database_url", "")
    called = {}

    import backend.services.matching.matcher as builtin

    def fake(pid, limit=5):
        called["hit"] = True
        return []

    monkeypatch.setattr(builtin, "compute_matches_for_problem", fake)
    adapters.compute_matches_for_problem("some-problem", limit=5)
    assert called.get("hit"), "the built-in matcher should have been used"


def test_structured_context_scoring_prefers_an_exact_model_match():
    """Vector similarity alone cannot tell an S23 from an S22; this signal can."""
    from backend.services.ai_engine.adapters import _structured_context_score

    fp = Fingerprint(brand="Samsung", model="galaxy s23", device_type="smartphone",
                     suspected_component="motherboard")
    exact = [{"title": "Galaxy S23 no power", "diagnosis": "motherboard repair",
              "brand": "Samsung", "device_category": "smartphone"}]
    other = [{"title": "Galaxy S22 no power", "diagnosis": "screen replacement",
              "brand": "Samsung", "device_category": "smartphone"}]
    assert _structured_context_score(fp, exact, []) > _structured_context_score(fp, other, [])


def test_context_scoring_never_returns_zero():
    """Structured agreement is supporting evidence, not a veto."""
    from backend.services.ai_engine.adapters import _structured_context_score

    score = _structured_context_score(Fingerprint(model="galaxy s23"), [], [])
    assert 0 < score <= 1.0


# ------------------------------------------------------- relevance filtering


def _candidate(worker_id, score, evidence=True, in_radius=True, user_id=None):
    return {
        "_user_id": user_id or worker_id,
        "_has_evidence": evidence,
        "_within_radius": in_radius,
        "worker_id": worker_id,
        "match_score": score,
    }


def test_a_technician_with_no_evidence_is_not_offered():
    """The reported bug: every technician came back regardless of relevance."""
    from backend.services.ai_engine.adapters import _filter_relevant

    kept = _filter_relevant([
        _candidate("relevant", 0.85, evidence=True),
        _candidate("unrelated", 0.39, evidence=False),
    ])
    assert [c["worker_id"] for c in kept] == ["relevant"]


def test_technicians_outside_their_service_radius_are_excluded():
    from backend.services.ai_engine.adapters import _filter_relevant

    kept = _filter_relevant([
        _candidate("near", 0.80, in_radius=True),
        _candidate("far", 0.79, in_radius=False),
    ])
    assert [c["worker_id"] for c in kept] == ["near"]


def test_filtering_never_returns_an_empty_list():
    """A customer with no options cannot proceed; a weak match beats nothing."""
    from backend.services.ai_engine.adapters import _filter_relevant

    kept = _filter_relevant([
        _candidate("weak", 0.10, evidence=False, in_radius=False),
    ])
    assert len(kept) == 1


def test_the_score_floor_drops_weak_matches():
    from backend.services.ai_engine.adapters import _filter_relevant
    from backend.services.ai_engine.config import settings

    kept = _filter_relevant([
        _candidate("strong", settings.match_min_score + 0.2),
        _candidate("weak", settings.match_min_score - 0.2),
    ])
    assert [c["worker_id"] for c in kept] == ["strong"]


def test_one_card_per_person_even_with_duplicate_worker_rows():
    """The data holds more than one worker_profiles row per profile."""
    from backend.services.ai_engine.adapters import _deduplicate

    kept = _deduplicate([
        _candidate("row-a", 0.90, user_id="same-person"),
        _candidate("row-b", 0.70, user_id="same-person"),
        _candidate("row-c", 0.60, user_id="other-person"),
    ])
    assert [c["worker_id"] for c in kept] == ["row-a", "row-c"]
    assert kept[0]["match_score"] == 0.90, "the better-scoring row should survive"
