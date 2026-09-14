"""Problem Fingerprint extraction (PRD section 11).

Text plus optional images become a structured record. Two safety rules from the PRD
are enforced here rather than left to the prompt alone:

  * ``suspected_component`` is only ever a hypothesis. The model is told to fill it in
    only when the customer said so, and every fingerprint carries an explicit
    ``suspected_component_source`` so downstream code and the UI can never present it
    as an established fault.
  * High-risk electrical wording raises a safety warning telling the user to involve
    a qualified professional.

Extraction runs entirely on Gemma. Gemma has no structured-output mode, so JSON is
requested in the prompt and parsed defensively, and it returns 500 INTERNAL
intermittently, so server-side faults are retried with backoff. See
``generate_fingerprint`` for how the two failure modes are told apart.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from backend.services.ai_engine.config import settings
from backend.services.ai_engine.errors import AI_ERROR, APIError
from backend.services.ai_engine.client import (
    get_client,
    is_quota_error,
    is_transient_server_error,
)

log = logging.getLogger(__name__)

FINGERPRINT_VERSION = "v1"

# Base delay between retries of a server-side fault; doubles each attempt.
_BACKOFF_SECONDS = 1.5

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
    "likely_causes": list,
    "diagnostic_steps": list,
    "suspected_component": str,
    "suspected_component_source": str,
    "repair_type": str,
    "urgency": str,
    "extracted_skills": list,
    "ai_summary": str,
}

_PROMPT = """You are an experienced electrical and electronics repair technician doing
triage. A customer has described a fault in plain language. Work out what is most
likely wrong, the way a technician would before opening the device, and return it as
structured data.

Return ONLY a JSON object. No prose, no markdown fences, nothing before or after it.

{
  "device_type": string or null,
  "brand": string or null,
  "model": string or null,
  "category": string or null,
  "issue": string or null,
  "symptoms": [string],
  "context": [string],
  "likely_causes": [
    {"component": string, "reasoning": string, "confidence": "high"|"medium"|"low",
     "check": string}
  ],
  "diagnostic_steps": [string],
  "suspected_component": string or null,
  "suspected_component_source": "customer_stated" or "ai_inferred" or null,
  "repair_type": string or null,
  "urgency": "normal" or "urgent" or null,
  "extracted_skills": [string],
  "ai_summary": string
}

HOW TO REASON

Separate three different things before you answer:
  1. The SYMPTOM  - what the customer observes.
  2. The CONTEXT  - what was happening around the failure (age, weather, impact, load).
  3. The CAUSE    - the part that is actually likely at fault.

The customer describes symptoms. Your value is naming plausible causes.

Do not blame a protective device for doing its job. An MCB, RCCB, fuse or thermal
cut-out that trips is usually reporting a fault elsewhere - in the appliance, the
wiring or the earth path. Only suspect the protective device itself when the evidence
points at it, such as tripping with every load disconnected.

Do not blame the part the customer happened to name. Read what they observed, then
reason about what causes that observation.

Use the details the customer volunteers. Age ("3 years old"), weather ("after the
rains"), impact ("dropped"), and which loads are affected are diagnostic evidence,
not background.

LIKELY CAUSES

Give two to four entries, ordered most likely first. Each needs:
  - component: the specific part, in technician vocabulary (starting capacitor, power
    IC, backlight LED strip, heating element, changeover relay, charging flex).
  - reasoning: why these symptoms point there, in one sentence.
  - confidence: high only when the symptom pattern is close to definitive.
  - check: the measurement or test that would confirm or rule it out.

If the description is too vague to support any cause, return an empty list rather than
inventing one.

DIAGNOSTIC STEPS

Two to four checks, in the order a technician would do them: cheapest, safest and most
informative first. Make them specific ("measure voltage across the capacitor
terminals"), not generic ("inspect the device").

OTHER FIELDS

- issue: characterise the fault, do not restate the title. "Runs at reduced speed with
  audible hum" is useful; "fan problem" is not.
- symptoms: only what the customer observed. No conclusions.
- context: circumstances, not symptoms. Do not repeat a symptom here.
- suspected_component: whichever part the customer named, if they named one - even if
  you rank a different cause higher. Their hypothesis is recorded as theirs, and your
  own ranking is what likely_causes is for. If the customer named nothing, use
  likely_causes[0]. Null if nothing is supportable.
- suspected_component_source: "customer_stated" whenever the customer named that part,
  regardless of whether you agree with them; "ai_inferred" when you chose it yourself.

  When you disagree with a customer's guess, keep their part in suspected_component,
  put your own candidate first in likely_causes, and include their part in
  likely_causes too with the confidence you actually think it deserves. Never silently
  replace their hypothesis - the customer needs to see that you considered it.
- repair_type: the work involved, such as board-level diagnosis, capacitor replacement,
  rewiring, backlight replacement.
- urgency: "urgent" for burning smell, sparking, shock, smoke, exposed live conductors,
  or anything with a fire or injury risk. Otherwise "normal".
- extracted_skills: two to four skills a technician needs, specific enough to match on:
  "ceiling fan capacitor replacement", "board-level micro-soldering", "earth leakage
  fault finding".
- ai_summary: one neutral sentence a customer would understand.

SAFETY

Never state that a part IS faulty. Everything here is a hypothesis for a technician to
verify. Phrase reasoning as likelihood, not fact.

EXAMPLES

Input: "The MCB trips every time I switch on the geyser. Other appliances work fine."
Correct reasoning: the MCB is protecting the circuit; the fault is in the geyser or its
circuit. The strongest candidate is a heating element leaking to earth. Wrong answer:
blaming the MCB because the customer named it.

Input: "Ceiling fan runs slow and hums, worse after the rains."
Correct reasoning: hum with reduced speed is the classic failing-capacitor pattern;
damp ingress raises winding insulation problems as a secondary candidate.

Input: "TV has sound but no picture, faint image under a torch."
Correct reasoning: the panel is receiving signal, so the fault is in the backlight
circuit - LED strips or the driver - not the main board.

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
    # Ranked differential: each entry is {component, reasoning, confidence, check}.
    likely_causes: list[dict[str, Any]] = field(default_factory=list)
    diagnostic_steps: list[str] = field(default_factory=list)
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
                "likely_causes": self.likely_causes,
                "diagnostic_steps": self.diagnostic_steps,
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
        likely_causes=list(context.get("likely_causes") or []),
        diagnostic_steps=list(context.get("diagnostic_steps") or []),
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


_CONFIDENCE = {"high", "medium", "low"}


def _coerce_causes(value: Any) -> list[dict[str, Any]]:
    """Normalise the differential into a predictable list of dicts.

    The model sometimes returns plain strings instead of objects, so a bare string is
    accepted as a component name with the rest left empty. Confidence is clamped to the
    three allowed values and defaults to the weakest, so an unrecognised value can never
    make a guess look more certain than it is.
    """
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []

    causes: list[dict[str, Any]] = []
    for item in value[:4]:
        if isinstance(item, str):
            item = {"component": item}
        if not isinstance(item, dict):
            continue
        component = str(item.get("component") or "").strip()
        if not component:
            continue
        confidence = str(item.get("confidence") or "").strip().lower()
        causes.append({
            "component": component,
            "reasoning": str(item.get("reasoning") or "").strip(),
            "confidence": confidence if confidence in _CONFIDENCE else "low",
            "check": str(item.get("check") or "").strip(),
        })
    return causes


def _coerce(payload: dict[str, Any]) -> dict[str, Any]:
    """Force the model output into the declared shapes."""
    clean: dict[str, Any] = {}
    for key, kind in _FIELDS.items():
        value = payload.get(key)
        if key == "likely_causes":
            clean[key] = _coerce_causes(value)
        elif kind is list:
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


def _call_model(model: str, contents: Any, structured: bool) -> str:
    from google.genai import types

    config = types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=1200,
        # Gemma can take over a minute when the backend is strained. A demo cannot
        # wait that long, so a slow call is cut short and the backup model takes over.
        http_options=types.HttpOptions(timeout=settings.fingerprint_timeout_seconds * 1000),
    )
    if structured:
        # Only the Gemini backup supports this; Gemma rejects it.
        config.response_mime_type = "application/json"

    response = get_client().models.generate_content(
        model=model, contents=contents, config=config
    )
    return (response.text or "").strip()


def _try_model(
    model: str,
    structured: bool,
    attempts: int,
    title: str,
    description: str,
    images: list[tuple[bytes, str]],
) -> tuple[Fingerprint | None, Exception | None]:
    """Run one model up to ``attempts`` times. Returns (result, last_error).

    Two failures are retried for different reasons: an unparseable reply gets a
    stricter instruction appended, while a transient 5xx gets the same prompt again
    after a backoff. A quota error stops this model immediately -- repeating it cannot
    help, and the caller should move on to the next model.
    """
    last_error: Exception | None = None
    nudge = ""

    for attempt in range(attempts):
        try:
            contents = _build_contents(title, description, images, nudge=nudge)
            payload = _extract_json(_call_model(model, contents, structured))
            clean = _coerce(payload)
            return (
                Fingerprint(
                    **clean,
                    safety_warning=detect_safety_risk(
                        title, description, clean.get("issue")
                    ),
                    model_used=model,
                    raw_ai_output={
                        "model": model,
                        "attempt": attempt + 1,
                        "response": payload,
                    },
                ),
                None,
            )
        except Exception as exc:
            last_error = exc

            if is_quota_error(exc):
                log.warning("Fingerprint model %s is out of quota", model)
                return None, exc

            transient = is_transient_server_error(exc)
            log.warning(
                "Fingerprint attempt %d/%d on %s failed (%s%s)",
                attempt + 1, attempts, model, type(exc).__name__,
                ", transient" if transient else "",
            )

            if attempt < attempts - 1:
                if transient:
                    time.sleep(_BACKOFF_SECONDS * (2**attempt))
                else:
                    nudge = _RETRY_NUDGE

    return None, last_error


def generate_fingerprint(
    title: str,
    description: str,
    images: list[tuple[bytes, str]] | None = None,
) -> Fingerprint:
    """Extract a fingerprint. Raises APIError(AI_ERROR) only if every model fails.

    Gemma is the primary model, for its free request-per-day allowance. It is also
    unreliable in practice -- intermittent 500s and calls that run for over a minute --
    so a Gemini backup takes over once Gemma has had its attempts. The backup supports
    real structured output, so it rescues the malformed-JSON case rather than repeating
    it.
    """
    images = images or []
    primary = settings.gemini_fingerprint_model
    backup = settings.gemini_fingerprint_fallback_model

    plan: list[tuple[str, bool, int]] = [
        (primary, False, max(1, settings.fingerprint_max_attempts)),
    ]
    if backup and backup != primary:
        plan.append((backup, True, max(1, settings.fingerprint_fallback_attempts)))

    last_error: Exception | None = None
    for model, structured, attempts in plan:
        result, error = _try_model(
            model, structured, attempts, title, description, images
        )
        if result is not None:
            if model != primary:
                log.info("Fingerprint served by backup model %s", model)
            return result
        last_error = error or last_error

    if last_error is not None and is_quota_error(last_error):
        raise APIError(
            AI_ERROR,
            "The fingerprint models are temporarily out of quota. Please try again later.",
        ) from last_error
    raise APIError(AI_ERROR, "Could not extract a problem fingerprint.") from last_error
