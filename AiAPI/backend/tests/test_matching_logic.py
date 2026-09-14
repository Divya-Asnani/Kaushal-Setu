"""Tests for the AI and matching logic that does not need a live database.

The Samsung S23 scenario from PRD section 12 is the acceptance case: Worker A (same
model, same context, verified) must outrank Worker C (same model, different fault) and
Worker B (different model). If that ordering ever breaks, the product claim breaks.
"""
from __future__ import annotations

import pytest

from backend.services.ai import canonical
from backend.services.ai.fingerprint import (
    INFERRED,
    STATED,
    Fingerprint,
    _coerce,
    _extract_json,
    detect_safety_risk,
    from_row,
)
from backend.services.jobs.lifecycle import (
    assert_job_transition,
    assert_request_transition,
)
from backend.core.errors import APIError
from backend.services.matching.ranking import (
    WorkerCandidate,
    haversine_km,
    rank,
)
from backend.services.matching.retrieval import ExperienceCandidate


# ------------------------------------------------------------------ JSON extraction


def test_extract_json_from_fenced_response():
    assert _extract_json('```json\n{"issue": "no power"}\n```') == {"issue": "no power"}


def test_extract_json_from_chatty_response():
    text = 'Sure! Here is the fingerprint:\n{"issue": "no power", "brand": "Samsung"}\nHope that helps.'
    assert _extract_json(text)["brand"] == "Samsung"


def test_extract_json_handles_nested_objects():
    text = 'prefix {"a": {"b": 1}, "c": [1,2]} suffix'
    assert _extract_json(text) == {"a": {"b": 1}, "c": [1, 2]}


def test_extract_json_rejects_garbage():
    with pytest.raises(ValueError):
        _extract_json("there is no JSON here at all")


# ---------------------------------------------------------------------- coercion


def test_coerce_forces_list_fields():
    clean = _coerce({"symptoms": "no display", "extracted_skills": None})
    assert clean["symptoms"] == ["no display"]
    assert clean["extracted_skills"] == []


def test_coerce_defaults_component_provenance_to_the_weaker_claim():
    clean = _coerce({"suspected_component": "motherboard"})
    assert clean["suspected_component_source"] == INFERRED


def test_coerce_clears_provenance_when_no_component():
    clean = _coerce({"suspected_component": None, "suspected_component_source": STATED})
    assert clean["suspected_component_source"] is None


def test_coerce_rejects_invented_urgency_values():
    assert _coerce({"urgency": "catastrophic"})["urgency"] is None


# ------------------------------------------------------------------------- safety


@pytest.mark.parametrize(
    "text",
    [
        "I got a shock from the switch",
        "There were sparks from the board",
        "the wiring started smoking",
        "smell of burning near the MCB",
    ],
)
def test_high_risk_wording_raises_a_safety_warning(text):
    assert detect_safety_risk(text) is not None


def test_ordinary_problem_has_no_safety_warning():
    assert detect_safety_risk("My phone screen is cracked and the touch is unresponsive") is None


# ------------------------------------------------------------------ canonical text


def test_fingerprint_text_marks_a_customer_stated_component_as_reported():
    fp = Fingerprint(
        brand="Samsung",
        model="Galaxy S23",
        suspected_component="motherboard",
        suspected_component_source=STATED,
    )
    assert "motherboard (reported by customer)" in canonical.fingerprint_text(fp)


def test_fingerprint_text_marks_an_inferred_component_as_unconfirmed():
    fp = Fingerprint(suspected_component="motherboard", suspected_component_source=INFERRED)
    assert "unconfirmed" in canonical.fingerprint_text(fp)


def test_skill_normalisation_collapses_spelling_variants():
    assert canonical.normalise_skill("Samsung  Smartphone Repair!") == "samsung smartphone repair"
    assert canonical.normalise_skills(["Board-Level Repair", "board-level repair"]) == [
        "board-level repair"
    ]


def test_round_trip_through_a_stored_row_keeps_provenance():
    original = Fingerprint(
        brand="Samsung",
        model="Galaxy S23",
        context=["physical drop"],
        urgency="urgent",
        suspected_component="motherboard",
        suspected_component_source=STATED,
        safety_warning="warn",
    )
    restored = from_row(original.to_row("problem-1"))
    assert restored.suspected_component_source == STATED
    assert restored.context == ["physical drop"]
    assert restored.urgency == "urgent"
    assert restored.safety_warning == "warn"


# ---------------------------------------------------------------------- geography


def test_haversine_matches_a_known_distance():
    # Pune to Mumbai is roughly 120 km.
    distance = haversine_km(18.5204, 73.8567, 19.0760, 72.8777)
    assert 110 < distance < 130


# ------------------------------------------------------------------------ ranking


def _candidate(worker_id, similarity, status, confidence, text, *, lat=18.52, lon=73.86,
               radius=15, contexts=None, verified_extra=0):
    experiences = [
        ExperienceCandidate(
            experience_id=f"{worker_id}-e{i}",
            worker_id=worker_id,
            similarity=similarity,
            title=text,
            problem_description=text,
            diagnosis=text,
            outcome_summary="repaired",
            experience_status=status,
            verification_confidence=confidence,
            source_text=text,
        )
        for i in range(1 + verified_extra)
    ]
    return WorkerCandidate(
        worker_id=worker_id,
        experiences=experiences,
        profile={
            "user_id": worker_id,
            "latitude": lat,
            "longitude": lon,
            "service_radius_km": radius,
            "availability_status": "available",
            "is_verified": False,
        },
        contexts_by_experience={
            e.experience_id: [{"context_type": "damage", "context_value": c} for c in (contexts or [])]
            for e in experiences
        },
        skills_by_experience={e.experience_id: [] for e in experiences},
    )


@pytest.fixture
def s23_fingerprint():
    return Fingerprint(
        device_type="smartphone",
        brand="Samsung",
        model="Galaxy S23",
        issue="no power",
        symptoms=["no display", "no boot"],
        context=["physical drop"],
        suspected_component="motherboard",
        suspected_component_source=STATED,
        repair_type="board-level diagnosis",
        extracted_skills=["samsung smartphone repair", "board-level repair"],
    )


def test_prd_samsung_scenario_orders_workers_as_specified(s23_fingerprint):
    worker_a = _candidate(
        "A", 0.93, "verified", 95,
        "Galaxy S23 no power after physical drop, motherboard power IC repair",
        contexts=["physical drop"], verified_extra=2,
    )
    worker_b = _candidate(
        "B", 0.85, "verified", 90,
        "Galaxy S22 no power, motherboard repair",
    )
    worker_c = _candidate(
        "C", 0.88, "verified", 92,
        "Galaxy S23 charging failure, motherboard charging IC repair",
    )

    ranked = rank([worker_b, worker_c, worker_a], s23_fingerprint, 18.52, 73.86, limit=3)
    order = [r.worker_id for r in ranked]

    assert order[0] == "A", "same model + same context + verified must rank first"
    assert order.index("C") < order.index("B"), "same model must beat a different model"


def test_verified_experience_beats_self_reported_at_equal_similarity(s23_fingerprint):
    verified = _candidate("V", 0.90, "verified", 95, "Galaxy S23 no power after drop")
    self_reported = _candidate("S", 0.90, "draft", 0, "Galaxy S23 no power after drop")

    ranked = rank([self_reported, verified], s23_fingerprint, 18.52, 73.86, limit=2)
    assert ranked[0].worker_id == "V"
    assert ranked[0].verified_experience_confidence > ranked[1].verified_experience_confidence


def test_self_reported_experience_cannot_reach_high_confidence(s23_fingerprint):
    """PRD section 15: self-reported experience alone never becomes verified."""
    many_claims = _candidate(
        "S", 0.95, "submitted", 0, "Galaxy S23 no power after drop", verified_extra=9
    )
    ranked = rank([many_claims], s23_fingerprint, 18.52, 73.86, limit=1)
    assert ranked[0].verified_experience_confidence <= 25


def test_disputed_experience_is_penalised(s23_fingerprint):
    clean_worker = _candidate("C", 0.90, "verified", 90, "Galaxy S23 no power after drop")
    disputed = _candidate("D", 0.90, "disputed", 90, "Galaxy S23 no power after drop")
    ranked = rank([disputed, clean_worker], s23_fingerprint, 18.52, 73.86, limit=2)
    assert ranked[0].worker_id == "C"


def test_workers_outside_their_service_radius_are_excluded(s23_fingerprint):
    far = _candidate(
        "F", 0.95, "verified", 95, "Galaxy S23 no power after drop",
        lat=19.076, lon=72.877, radius=5,
    )
    assert rank([far], s23_fingerprint, 18.52, 73.86, limit=5) == []


def test_offline_workers_are_excluded(s23_fingerprint):
    offline = _candidate("O", 0.95, "verified", 95, "Galaxy S23 no power after drop")
    offline.profile["availability_status"] = "offline"
    assert rank([offline], s23_fingerprint, 18.52, 73.86, limit=5) == []


def test_missing_coordinates_do_not_exclude_a_worker(s23_fingerprint):
    """Absent location is not evidence of being far away."""
    unlocated = _candidate(
        "U", 0.90, "verified", 90, "Galaxy S23 no power after drop", lat=None, lon=None
    )
    ranked = rank([unlocated], s23_fingerprint, 18.52, 73.86, limit=1)
    assert len(ranked) == 1
    assert ranked[0].proximity_score == 50.0


def test_every_result_carries_explanations(s23_fingerprint):
    worker = _candidate("A", 0.93, "verified", 95, "Galaxy S23 no power after physical drop")
    ranked = rank([worker], s23_fingerprint, 18.52, 73.86, limit=1)
    assert ranked[0].explanation
    assert any("verified" in reason.lower() for reason in ranked[0].explanation)


def test_unverified_worker_explanation_says_so(s23_fingerprint):
    worker = _candidate("S", 0.93, "draft", 0, "Galaxy S23 no power after drop")
    ranked = rank([worker], s23_fingerprint, 18.52, 73.86, limit=1)
    assert any("not yet customer-verified" in reason for reason in ranked[0].explanation)


def test_scores_stay_within_the_numeric_5_2_column_range(s23_fingerprint):
    worker = _candidate(
        "A", 1.0, "verified", 100, "Galaxy S23 no power after physical drop motherboard",
        contexts=["physical drop"], verified_extra=5,
    )
    ranked = rank([worker], s23_fingerprint, 18.52, 73.86, limit=1)
    result = ranked[0]
    for value in (
        result.match_score,
        result.problem_similarity,
        result.context_similarity,
        result.verified_experience_confidence,
        result.proximity_score,
    ):
        assert 0 <= value <= 100


def test_metadata_flags_the_weights_as_prototype_parameters(s23_fingerprint):
    worker = _candidate("A", 0.9, "verified", 90, "Galaxy S23 no power")
    ranked = rank([worker], s23_fingerprint, 18.52, 73.86, limit=1)
    assert "not trained" in ranked[0].metadata["weights_note"]


# ----------------------------------------------------------------- state machines


@pytest.mark.parametrize(
    "current,target",
    [("confirmed", "in_progress"), ("in_progress", "completed"), ("completed", "disputed")],
)
def test_valid_job_transitions(current, target):
    assert_job_transition(current, target)


@pytest.mark.parametrize(
    "current,target",
    [("confirmed", "completed"), ("completed", "in_progress"), ("cancelled", "in_progress")],
)
def test_invalid_job_transitions_are_rejected(current, target):
    with pytest.raises(APIError):
        assert_job_transition(current, target)


def test_an_accepted_request_cannot_change_again():
    with pytest.raises(APIError):
        assert_request_transition("accepted", "rejected")


def test_a_pending_request_can_be_accepted():
    assert_request_transition("pending", "accepted")


# ----------------------------------------------- retry and fallback behaviour


class _Boom(Exception):
    """Stands in for a google-genai error carrying a status in its message."""


GOOD = '{"issue": "no power", "brand": "Samsung"}'


def _script(monkeypatch, responses):
    """Feed generate_fingerprint a scripted sequence of replies or exceptions.

    Records the model and prompt of every call so tests can assert which model served
    the request and whether the stricter instruction was appended.
    """
    from backend.services.ai import fingerprint as fp

    calls: list[dict] = []

    def fake_call(model, contents, structured):
        index = len(calls)
        calls.append({"model": model, "prompt": contents, "structured": structured})
        item = responses[min(index, len(responses) - 1)]
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(fp, "_call_model", fake_call)
    monkeypatch.setattr(fp, "_build_contents",
                        lambda title, desc, images, nudge="": nudge)
    monkeypatch.setattr(fp.time, "sleep", lambda _s: None)
    return calls


@pytest.fixture
def models(monkeypatch):
    from backend.core.config import settings

    monkeypatch.setattr(settings, "gemini_fingerprint_model", "gemma-4-31b-it")
    monkeypatch.setattr(settings, "gemini_fingerprint_fallback_model", "gemini-3.5-flash-lite")
    monkeypatch.setattr(settings, "fingerprint_max_attempts", 2)
    monkeypatch.setattr(settings, "fingerprint_fallback_attempts", 2)
    return settings


def test_gemma_serves_the_request_when_it_works(models, monkeypatch):
    from backend.services.ai import fingerprint as fp

    calls = _script(monkeypatch, [GOOD])
    result = fp.generate_fingerprint("t", "d")
    assert result.model_used == "gemma-4-31b-it"
    assert len(calls) == 1, "the backup must not be touched when Gemma succeeds"


def test_a_transient_server_error_is_retried_on_gemma_first(models, monkeypatch):
    from backend.services.ai import fingerprint as fp

    calls = _script(monkeypatch, [_Boom("500 INTERNAL"), GOOD])
    result = fp.generate_fingerprint("t", "d")
    assert result.model_used == "gemma-4-31b-it"
    assert [c["model"] for c in calls] == ["gemma-4-31b-it"] * 2
    assert calls[1]["prompt"] == "", "a server fault must not change the prompt"


def test_an_unparseable_reply_is_retried_with_a_stricter_instruction(models, monkeypatch):
    from backend.services.ai import fingerprint as fp

    calls = _script(monkeypatch, ["I cannot help with that", GOOD])
    assert fp.generate_fingerprint("t", "d").model_used == "gemma-4-31b-it"
    assert calls[0]["prompt"] == ""
    assert "JSON object ONLY" in calls[1]["prompt"]


def test_the_backup_takes_over_once_gemma_is_exhausted(models, monkeypatch):
    """Gemma's real failure mode: repeated 500s. The demo must still get an answer."""
    from backend.services.ai import fingerprint as fp

    calls = _script(monkeypatch, [_Boom("500 INTERNAL"), _Boom("500 INTERNAL"), GOOD])
    result = fp.generate_fingerprint("t", "d")
    assert result.model_used == "gemini-3.5-flash-lite"
    assert [c["model"] for c in calls] == [
        "gemma-4-31b-it", "gemma-4-31b-it", "gemini-3.5-flash-lite",
    ]


def test_the_backup_asks_for_enforced_json(models, monkeypatch):
    from backend.services.ai import fingerprint as fp

    calls = _script(monkeypatch, [_Boom("500"), _Boom("500"), GOOD])
    fp.generate_fingerprint("t", "d")
    assert calls[0]["structured"] is False, "Gemma rejects response_mime_type"
    assert calls[-1]["structured"] is True, "the backup enforces real JSON"


def test_a_gemma_quota_error_moves_straight_to_the_backup(models, monkeypatch):
    """Repeating a 429 cannot help, so Gemma is abandoned immediately."""
    from backend.services.ai import fingerprint as fp

    calls = _script(monkeypatch, [_Boom("429 RESOURCE_EXHAUSTED"), GOOD])
    result = fp.generate_fingerprint("t", "d")
    assert result.model_used == "gemini-3.5-flash-lite"
    assert len([c for c in calls if c["model"] == "gemma-4-31b-it"]) == 1


def test_an_error_is_raised_only_when_both_models_fail(models, monkeypatch):
    from backend.services.ai import fingerprint as fp

    calls = _script(monkeypatch, [_Boom("500 INTERNAL")])
    with pytest.raises(APIError):
        fp.generate_fingerprint("t", "d")
    assert len(calls) == 4, "2 attempts on Gemma, then 2 on the backup"


def test_running_without_a_backup_is_supported(monkeypatch):
    from backend.core.config import settings
    from backend.services.ai import fingerprint as fp

    monkeypatch.setattr(settings, "gemini_fingerprint_model", "gemma-4-31b-it")
    monkeypatch.setattr(settings, "gemini_fingerprint_fallback_model", "")
    monkeypatch.setattr(settings, "fingerprint_max_attempts", 2)
    calls = _script(monkeypatch, [_Boom("500 INTERNAL")])
    with pytest.raises(APIError):
        fp.generate_fingerprint("t", "d")
    assert len(calls) == 2, "Gemma only"


def test_exhausted_quota_on_both_models_says_so(models, monkeypatch):
    from backend.services.ai import fingerprint as fp

    _script(monkeypatch, [_Boom("429 RESOURCE_EXHAUSTED")])
    with pytest.raises(APIError) as caught:
        fp.generate_fingerprint("t", "d")
    assert "quota" in caught.value.message.lower()


def test_transient_and_quota_errors_are_told_apart():
    from backend.services.ai.client import is_quota_error, is_transient_server_error

    assert is_transient_server_error(_Boom("500 INTERNAL. Internal error encountered."))
    assert is_transient_server_error(_Boom("503 UNAVAILABLE"))
    assert not is_quota_error(_Boom("500 INTERNAL"))
    assert is_quota_error(_Boom("429 RESOURCE_EXHAUSTED"))
