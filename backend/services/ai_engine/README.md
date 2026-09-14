# AI engine

Real Problem Fingerprint extraction and semantic matching, replacing the heuristic
implementations the application ships with.

| | Built-in (`services/ai`, `services/matching`) | This engine |
|---|---|---|
| Fingerprint | keyword and regex rules | Gemini, multimodal-capable |
| Problem similarity | skill-name set overlap | 1536-D embeddings, pgvector cosine + HNSW |
| Context similarity | fixed 0.70, nudged on brand match | structured agreement on model, brand, device, component |
| Explanations | template strings | derived from the cases actually retrieved |

## How it is wired

Two import lines, one in each route module:

```python
# backend/api/routes/problems.py
from backend.services.ai_engine.adapters import extract_problem_fingerprint

# backend/api/routes/matching.py
from backend.services.ai_engine.adapters import compute_matches_for_problem
```

`adapters.py` keeps the exact signatures and return shapes of the built-in functions,
so nothing else changes — the routes, the schemas and the Flutter client are untouched.

## It cannot take the application down

Every adapter falls back to the original heuristic when the engine is unconfigured or a
call fails. No Gemini key, expired quota, unreachable database, malformed model output —
all of them degrade the *quality* of a result rather than failing the request. The
built-in implementations stay in the tree and stay reachable; they are the fallback.

Force the heuristics explicitly with `AI_ENGINE_FINGERPRINT=false` or
`AI_ENGINE_MATCHING=false`.

## Configuration

Read from the environment (see `.env.example`), deliberately not from
`backend/config.py`: the engine needs credentials the rest of the application never
needed, and keeping them separate means it can be removed without touching the
application's own configuration.

- `GEMINI_API_KEY` — enables real fingerprint extraction and embeddings.
- `DATABASE_URL` — enables pgvector search. **Use the Supabase Session pooler string**;
  the direct host is IPv6-only and unreachable from Docker and most hosting networks.
- Ranking weights reuse the application's own `WEIGHT_*` names so the two cannot drift.

`backend.services.ai_engine.status()` reports what is configured, never any value.

## Models

- **Embeddings** — `gemini-embedding-2` at 1536 dimensions, matching the existing
  `vector(1536)` columns and HNSW indexes. Vectors are L2-normalised; without that,
  cosine distances would not be comparable between rows.
- **Fingerprints** — `gemma-4-31b-it` first for its large free daily allowance, with
  `gemini-3.5-flash-lite` as backup. Gemma has no structured-output mode, so its JSON is
  parsed from a prompted schema and retried with a stricter instruction; the backup
  enforces a real JSON response.

> Gemma is unreliable in practice: intermittent `500 INTERNAL` and 37–93 s latency. The
> 20-second timeout means the backup serves most requests, at 2–4 s. The ordering is
> deliberate — if Gemma stabilises it takes over again and stops spending the backup's
> smaller daily budget.

## What the fingerprint contains

Beyond the columns the table has, the extractor produces a differential diagnosis that
rides in the `context` jsonb:

- `likely_causes` — two to four candidate parts, most likely first, each with the
  reasoning, a confidence of high/medium/low, and the check that would confirm it.
- `diagnostic_steps` — what a technician would check first, cheapest and safest first.

The prompt is written around diagnostic reasoning rather than extraction, which changes
the answers materially. Two rules matter most:

- **A protective device that trips is reporting a fault elsewhere.** "The MCB trips when
  I switch on the geyser" is a geyser fault, not an MCB fault. Before this, the extractor
  blamed the MCB because the customer named it, and matching then hunted for MCB repair
  experience instead of earth-leakage experience.
- **Details the customer volunteers are evidence.** Battery age, "after the rains", a
  drop, and which loads are affected all change the differential.

Candidate parts are also folded into the text that gets embedded, so a better diagnosis
directly improves retrieval: "starting capacitor" pulls toward fan repairs where
"ceiling fan not working" alone does not.

## Safety rules carried into the output

- `suspected_component` always travels with `context.suspected_component_source`,
  either `customer_stated` or `ai_inferred`. **The UI must not present either as a
  confirmed diagnosis.**
- When the customer names a part, it stays in `suspected_component` as theirs even if
  the model ranks something else higher. The model's own candidate leads
  `likely_causes`, and the customer's guess appears there too at whatever confidence it
  deserves, so a customer can see their hypothesis was considered rather than silently
  discarded.
- High-risk electrical wording sets `context.safety_warning`, which should be shown
  rather than buried.

## Tests

```bash
python -m pytest backend/services/ai_engine/tests -q
```

43 tests, no credentials or network needed. They cover parsing untidy model output, the
provenance and safety rules, canonical text, both fallback paths, and that the adapter
returns exactly the same keys as the built-in extractor.
