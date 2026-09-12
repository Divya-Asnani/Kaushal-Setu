"""Problem Fingerprint extraction (PRD section 11).

Text plus optional images become a structured record. Two safety rules from the PRD
are enforced here rather than left to the prompt alone:

  * ``suspected_component`` is only ever a hypothesis. The model is told to fill it in
    only when the customer said so, and every fingerprint carries an explicit
    ``suspected_component_source`` so downstream code and the UI can never present it
    as an established fault.
  * High-risk electrical wording raises a safety warning telling the user to involve
    a qualified professional.

Gemma has a large free daily allowance but no structured-output mode, so JSON is
requested in the prompt and parsed defensively. If that fails, or the model is out of
quota, the request falls back to a Gemini model with real schema enforcement.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from backend.core.config import settings
from backend.core.errors import AI_ERROR, APIError
from backend.services.ai.client import get_client, is_quota_error

log = logging.getLogger(__name__)

FINGERPRINT_VERSION = "v1"

STATED = "customer_stated"
INFERRED = "ai_inferred"

_FIELDS: dict[str, type] = {
    "device_type": str,
    "brand": str,
    "model": str,
    "category": str,
    "issue": str,
    "symptoms": list,
    "context": list,
    "suspected_component": str,
    "suspected_component_source": str,
    "repair_type": str,
    "urgency": str,
    "extracted_skills": list,
    "ai_summary": str,
}

_PROMPT = """You analyse repair problems reported by customers of an electrical and
electronics repair marketplace. Extract a structured Problem Fingerprint.

Return ONLY a JSON object, no prose and no markdown fences, with exactly these keys:

{
  "device_type": string or null,
  "brand": string or null,
  "model": string or null,
  "category": string or null,
  "issue": string or null,
  "symptoms": [string],
  "context": [string],
  "suspected_component": string or null,
  "suspected_component_source": "customer_stated" or "ai_inferred" or null,
  "repair_type": string or null,
  "urgency": "normal" or "urgent" or null,
  "extracted_skills": [string],
  "ai_summary": string
}

Field meanings:
- device_type: the thing being repaired, such as smartphone, ceiling fan, inverter.
- category: the broad domain, such as electronics repair or home electrical.
- issue: the primary fault in a few words, such as no power.
- symptoms: what is observed, such as no display or no boot.
- context: circumstances around the failure, such as physical drop or after rain.
- repair_type: the kind of work needed, such as board-level diagnosis or rewiring.
- extracted_skills: short canonical skill phrases a worker would need, such as
  Samsung smartphone repair, board-level repair, MCB troubleshooting.
- ai_summary: one neutral sentence describing the problem.

Rules you must follow:
- Only record what the text or image supports. Use null rather than guessing.
- Set suspected_component ONLY if the customer named or clearly implied a component,
  or an attached image plainly shows the damaged part. Then set
  suspected_component_source to customer_stated when the customer said it, or
  ai_inferred when you concluded it from an image.
- Never assert that a component is faulty. It is a hypothesis for a technician to check.

Customer problem title: __TITLE__
Customer problem description: __DESCRIPTION__
"""

_HIGH_RISK = [
    r"\bshock(ed|ing)?\b",
    r"\bspark(s|ing|ed)?\b",
    r"\bburn(t|ing|ed)?\b",
    r"\bsmok(e|ing|ed)\b",
    r"\bfire\b",
    r"\bmelt(ed|ing)?\b",
    r"\bexposed wire",
    r"\blive wire",
    r"\bshort[ -]?circuit",
    r"\belectrocut",
    r"\bgas leak",
    r"\bwater.{0,20}(socket|outlet|wiring|board)",
    r"\btripping repeatedly",
]

SAFETY_WARNING = (
    "This report mentions signs of a potentially dangerous electrical fault. "
    "Switch off the supply at the mains if it is safe to do so, and have a qualified "
    "professional inspect it before using the equipment again."
)


@dataclass
class Fingerprint:
    device_type: str | None = None
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    issue: str | None = None
    symptoms: list[str] = field(default_factory=list)
    context: list[str] = field(default_factory=list)
    suspected_component: str | None = None
    suspected_component_source: str | None = None
    repair_type: str | None = None
    urgency: str | None = None
    extracted_skills: list[str] = field(default_factory=list)
    ai_summary: str = ""
    safety_warning: str | None = None
    model_used: str = ""
    raw_ai_output: dict[str, Any] = field(default_factory=dict)

    def to_row(self, problem_id: str) -> dict[str, Any]:
        """Shape for the problem_fingerprints table.

        ``context`` is a jsonb column, so the circumstance list is stored together with
        the provenance and safety markers, which have no dedicated columns of their own.
        """
        return {
            "problem_id": problem_id,
            "device_type": self.device_type,
            "brand": self.brand,
            "model": self.model,
            "category": self.category,
            "issue": self.issue,
            "symptoms": self.symptoms,
            "context": {
                "items": self.context,
                "urgency": self.urgency,
                "suspected_component_source": self.suspected_component_source,
                "safety_warning": self.safety_warning,
            },
            "suspected_component": self.suspected_component,
            "repair_type": self.repair_type,
            "extracted_skills": self.extracted_skills,
            "ai_summary": self.ai_summary,
            "raw_ai_output": self.raw_ai_output,
            "fingerprint_version": FINGERPRINT_VERSION,
        }


def from_row(row: dict[str, Any]) -> Fingerprint:
    """Rebuild a Fingerprint from a stored problem_fingerprints row."""
    context = row.get("context") or {}
    if isinstance(context, list):  # tolerate an older shape
        context = {"items": context}
    return Fingerprint(
        device_type=row.get("device_type"),
        brand=row.get("brand"),
        model=row.get("model"),
        category=row.get("category"),
        issue=row.get("issue"),
        symptoms=list(row.get("symptoms") or []),
        context=list(context.get("items") or []),
        suspected_component=row.get("suspected_component"),
        suspected_component_source=context.get("suspected_component_source"),
        repair_type=row.get("repair_type"),
        urgency=context.get("urgency"),
        extracted_skills=list(row.get("extracted_skills") or []),
        ai_summary=row.get("ai_summary") or "",
        safety_warning=context.get("safety_warning"),
        raw_ai_output=row.get("raw_ai_output") or {},
    )


def detect_safety_risk(*texts: str | None) -> str | None:
    blob = " ".join(t for t in texts if t).lower()
    for pattern in _HIGH_RISK:
        if re.search(pattern, blob):
            return SAFETY_WARNING
    return None


def _extract_json(text: str) -> dict[str, Any]:
    """Pull a JSON object out of a response that may be wrapped in prose or fences."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(text[start : i + 1])
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        break
    raise ValueError("no JSON object in model response")


def _coerce(payload: dict[str, Any]) -> dict[str, Any]:
    """Force the model output into the declared shapes."""
    clean: dict[str, Any] = {}
    for key, kind in _FIELDS.items():
        value = payload.get(key)
        if kind is list:
            if isinstance(value, str):
                value = [value]
            elif not isinstance(value, list):
                value = []
            clean[key] = [str(v).strip() for v in value if str(v).strip()]
        elif value is None or (isinstance(value, str) and not value.strip()):
            clean[key] = None
        else:
            clean[key] = str(value).strip()

    if clean.get("urgency") not in {"normal", "urgent", None}:
        clean["urgency"] = None
    if clean.get("suspected_component_source") not in {STATED, INFERRED, None}:
        clean["suspected_component_source"] = None
    # Provenance is mandatory whenever a component is named; default to the weaker claim.
    if clean.get("suspected_component"):
        clean["suspected_component_source"] = clean.get("suspected_component_source") or INFERRED
    else:
        clean["suspected_component_source"] = None
    clean["ai_summary"] = clean.get("ai_summary") or ""
    return clean


def _build_contents(
    title: str, description: str, images: list[tuple[bytes, str]], nudge: str = ""
):
    from google.genai import types

    prompt = _PROMPT.replace("__TITLE__", title or "").replace(
        "__DESCRIPTION__", description or ""
    ) + nudge
    parts: list[Any] = [types.Part.from_text(text=prompt)]
    for data, mime_type in images:
        parts.append(types.Part.from_bytes(data=data, mime_type=mime_type))
    return [types.Content(role="user", parts=parts)]


_RETRY_NUDGE = (
    "\n\nIMPORTANT: your previous reply could not be parsed. Reply with the JSON object "
    "ONLY. No explanation, no markdown fences, nothing before or after the object."
)


def _call_model(contents: Any) -> str:
    from google.genai import types

    # No response_mime_type here: Gemma does not support structured output, and this
    # pipeline deliberately stays on Gemma for its free request-per-day allowance.
    response = get_client().models.generate_content(
        model=settings.gemini_fingerprint_model,
        contents=contents,
        config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=1200),
    )
    return (response.text or "").strip()


def generate_fingerprint(
    title: str,
    description: str,
    images: list[tuple[bytes, str]] | None = None,
) -> Fingerprint:
    """Extract a fingerprint using Gemma. Raises APIError(AI_ERROR) if it cannot.

    Because Gemma cannot be forced to emit JSON, a malformed reply is retried on the
    same model with a stricter instruction. A quota error is not retried -- repeating
    the call would not help and only burns the remaining allowance.
    """
    model = settings.gemini_fingerprint_model
    last_error: Exception | None = None

    for attempt in range(max(1, settings.fingerprint_max_attempts)):
        contents = _build_contents(
            title, description, images or [], nudge=_RETRY_NUDGE if attempt else ""
        )
        try:
            payload = _extract_json(_call_model(contents))
            clean = _coerce(payload)
            return Fingerprint(
                **clean,
                safety_warning=detect_safety_risk(title, description, clean.get("issue")),
                model_used=model,
                raw_ai_output={"model": model, "attempt": attempt + 1, "response": payload},
            )
        except Exception as exc:
            last_error = exc
            if is_quota_error(exc):
                log.warning("Fingerprint model %s is out of quota", model)
                raise APIError(
                    AI_ERROR,
                    "The fingerprint model is temporarily out of quota. Please try again later.",
                ) from exc
            log.warning(
                "Fingerprint attempt %d/%d on %s failed (%s)",
                attempt + 1, settings.fingerprint_max_attempts, model, type(exc).__name__,
            )

    raise APIError(AI_ERROR, "Could not extract a problem fingerprint.") from last_error
