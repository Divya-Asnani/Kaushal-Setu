# iBolt / Kaushal Setu — Backend & AI

FastAPI application layer, Problem Fingerprint extraction, embeddings, pgvector
retrieval and the hybrid matching engine. This is the **Person 1 — Backend & AI**
column of the sprint board.

Frontend (Flutter) is Person 2. Database, seed data, Neo4j and Storage are Person 3;
this backend reads and writes their schema but does not define it.

## What this implements

| Area | Status |
|---|---|
| FastAPI app, `/api/v1`, standard error contract, request ids | done |
| Supabase JWT validation (HS256 secret **or** JWKS), role + ownership checks | done |
| All 32 endpoints from the API contract | done |
| Problem Fingerprint from text + images (Gemini/Gemma, multimodal) | done |
| Canonicalisation and 1536-D embeddings | done |
| pgvector similarity search, Neo4j enrichment, hybrid ranking + explanations | done |
| Service request / job / verification state machines | done |
| Knowledge Hub semantic search | done |

## Gemini instead of OpenAI

The frozen spec named `text-embedding-3-small`. The team runs on Gemini, so:

- **Embeddings** — `gemini-embedding-001` with `output_dimensionality=1536`. The
  dimension is unchanged, so the existing `vector(1536)` columns and HNSW indexes need
  no migration. Google only pre-normalises its full 3072-dimension output, so truncated
  vectors are L2-normalised in `services/ai/embeddings.py` before storage; without that,
  cosine distances would not be comparable between rows.
- **Fingerprint extraction** — `gemma-3-27b-it`, for its large free daily request
  allowance. Gemma has no structured-output mode, so JSON is requested in the prompt and
  parsed defensively; a malformed reply is retried on the same model with a stricter
  instruction (`FINGERPRINT_MAX_ATTEMPTS`, default 3). A quota error is not retried,
  because repeating the call cannot help and only burns the remaining allowance.

> **Your API key must be an AI Studio key.** Gemma is served to keys from
> [aistudio.google.com/apikey](https://aistudio.google.com/apikey), which look like
> `AIza…`. A Google Cloud / Code Assist key (`AQ.…`) returns 404 for every Gemma model
> and only exposes `gemini-2.5-flash`, whose rate limit is low enough to hit during a
> demo. `GET /health` reports the configured model; if fingerprinting 404s, this is why.

`experience_embeddings.embedding_model` has a column default of
`'text-embedding-3-small'` from the original spec. Every insert writes the real model
name explicitly, so the default is never relied on.

## Running it

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
cp .env.example .env      # then fill it in
.venv/Scripts/python -m uvicorn backend.main:app --reload
```

`GET /health` reports which parts of the configuration are present (never their
values). Interactive docs are at `/docs`.

### Environment

See `.env.example`. The ones without which nothing works:

- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — all CRUD.
- `DATABASE_URL` — pgvector search only. PostgREST cannot express a vector ordering,
  so similarity queries use a direct connection; everything else goes through the
  Supabase client.
- `GEMINI_API_KEY` — fingerprints and embeddings. Must be an AI Studio key (see above).
- `SUPABASE_JWT_SECRET` — only for legacy HS256 projects. Leave blank and tokens are
  verified against the project's JWKS instead.

Neo4j is optional. If it is unreachable the matching pipeline logs it once and
continues with relational context, which is what the PRD requires of a projection.

## Demo data

Matching cannot be demonstrated against an empty `experience_embeddings`. Seed data is
Person 3's deliverable; this script exists so the pipeline can be exercised now and as a
reproducible demo fixture. It is idempotent.

```bash
.venv/Scripts/python -m backend.scripts.seed_demo
.venv/Scripts/python -m backend.scripts.seed_demo --purge
```

It creates 10 skills, 6 workers around Pune, 12 solved experiences, 2 knowledge cases
and one customer account. Every account uses the `@demo.ibolt.local` domain and the
password `DemoPass123!`, so demo data stays obviously distinguishable from real data.

The seeded experiences are built around the PRD's Samsung S23 scenario: Ravi has the
same model with the same post-drop context and verified outcomes, Meena has the same
model with a different fault, Arjun has a different model. A correct ranking puts them
in that order.

## Test page

`testpage/index.html` is a plain page for driving the pipeline by hand — sign in, create
a problem, extract the fingerprint, see the ranked workers with their explanations, run
semantic searches. Open the file directly and point it at a running backend. It is a
development tool, not part of the product.

## Tests

```bash
.venv/Scripts/python -m pytest
```

154 tests, no credentials or network required. `backend/tests/fakes.py` stands in for
Supabase, pgvector and the Gemini models, so everything between the HTTP boundary and
those three services is the real code path — routers, dependencies, authorization,
schemas, the matching pipeline.

The fake database is deliberately strict: it enforces the NOT NULL columns, CHECK value
sets and numeric ranges recorded in `docs/schema-reference.md`. A write the real
PostgreSQL schema would reject fails here too, which is how the API is checked against
the documented schema without a live project.

Coverage:

| File | What it covers |
|---|---|
| `test_matching_logic.py` | JSON extraction from untidy model output, fingerprint coercion and provenance, safety detection, canonical text, scoring functions, state machines |
| `test_api_golden_path.py` | The whole customer journey end to end, plus fingerprint reuse, corrections, request expiry, disputes and status history |
| `test_api_authz.py` | Authentication, the role matrix, ownership boundaries, state-machine guards, the error contract |
| `test_api_contract.py` | Every documented endpoint is published, nothing undocumented is exposed, response shapes match the spec |
| `test_seed_and_graph.py` | Seed-fixture consistency, graph enrichment on and off, failure isolation |

The PRD's Samsung S23 ranking scenario is asserted directly, at both the unit and the
API level — if that ordering breaks, the product claim breaks.

Not covered: behaviour that only a live project can show — real pgvector index
behaviour, Supabase Auth, actual Gemma output quality. Use the test page against a
seeded project for those.

## Layout

```
backend/
  main.py                    app, middleware, router wiring
  core/                      config, error contract, JWT validation
  db/                        supabase client (CRUD), psycopg pool (pgvector only)
  api/deps.py                identity, role and ownership dependencies
  api/routes/                one module per resource
  schemas/                   request/response models
  services/ai/               gemini client, fingerprint, canonical text, embeddings, indexing
  services/matching/         retrieval, ranking, pipeline
  services/graph/            Neo4j enrichment and projection
  services/jobs/             state machines and transitions
  services/notifications/    in-app notifications
  scripts/seed_demo.py
  tests/
docs/schema-reference.md     columns and CHECK values for all 25 tables
testpage/index.html
```

## Design notes worth knowing

**Ranking.** `0.40*problem + 0.30*context + 0.20*verified + 0.10*proximity`, every
weight configurable. These are prototype parameters chosen by the team, not fitted
coefficients, and `match_results.matching_metadata` says so on every row.

Vector similarity alone cannot tell a Galaxy S23 from an S22, or a post-drop failure
from an unrelated charging fault — so the context signal scores structured agreement on
model, brand, device, component and circumstances separately, weighting model agreement
highest.

**Trust.** Self-reported experience is capped at a low confidence no matter how much of
it a worker records; only a customer verification on a real job produces verified
experience. Disputed cases are penalised and never count as verified. Ratings are stored
and displayed but are deliberately not an input to the ranking.

**Safety.** `suspected_component` always carries a provenance marker
(`customer_stated` / `ai_inferred`) so no layer can present a hypothesis as a diagnosis.
High-risk electrical wording attaches a warning to use a qualified professional. A
customer correcting the component upgrades its provenance to `customer_stated`.

**Authorization.** RLS is off in this prototype, and the backend uses the service-role
key, so FastAPI is the only thing standing between a caller and the data. Identity comes
from the validated JWT on every request; a `user_id` in a request body is never trusted.

**Failure isolation.** PostgreSQL is the source of truth. Embedding failures, Neo4j
failures and notification failures are logged and swallowed rather than rolling back a
committed state transition; each derived store can be rebuilt.

## Known gaps

- `job_status_history` is written immediately after the job update rather than in one
  transaction, because PostgREST has no multi-statement transaction. Making this
  properly atomic needs either a Postgres function or moving job writes to the direct
  connection.
- Service-request expiry is stored as `expires_at` but nothing sweeps it; expiry is
  currently an admin action. A scheduled job would close that.
- Media upload goes to Supabase Storage from the client; this backend records the
  metadata and reads public objects back for the fingerprint. Buckets are public in the
  prototype.
