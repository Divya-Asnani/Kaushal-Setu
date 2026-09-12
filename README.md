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
| Storage path validation and media metadata rules | done |

## Gemini instead of OpenAI

The frozen spec named `text-embedding-3-small`. The team runs on Gemini, so:

- **Embeddings** — `gemini-embedding-2` at `output_dimensionality=1536`. The dimension
  is unchanged, so the existing `vector(1536)` columns and HNSW indexes need no
  migration. Vectors are L2-normalised in `services/ai/embeddings.py`. That step is not
  cosmetic: the older `gemini-embedding-001` returns a vector of norm 0.69 at 1536
  dimensions, and without normalising, cosine distances would not be comparable between
  rows. `gemini-embedding-2` already returns unit vectors, so the step is now a cheap
  safeguard rather than a correction.
- **Fingerprint extraction** — `gemma-4-31b-it` first, for its large free daily
  allowance, with `gemini-3.5-flash-lite` as the backup. Gemma has no structured-output
  mode, so its JSON is parsed from a prompted schema and a malformed reply is retried
  with a stricter instruction; the backup enforces a real JSON response. A transient
  `500` is retried with backoff, a `429` moves straight to the backup, and a single call
  is cut off after `FINGERPRINT_TIMEOUT_SECONDS`. Set
  `GEMINI_FINGERPRINT_FALLBACK_MODEL` blank to run on Gemma alone.

> **Gemma is currently unreliable on this endpoint.** Measured live: intermittent
> `500 INTERNAL` on roughly half of calls, and 37–93 s latency when it does answer.
> Because a demo cannot wait 90 s the timeout is 20 s, which means Gemma rarely wins
> even when it would eventually succeed — in live testing the backup served every
> request, at 2–4 s. The ordering is still deliberate: if Gemma stabilises it takes over
> again automatically and the backup's smaller daily budget stops being spent. Nothing
> needs changing for that to happen. To favour Gemma instead, raise
> `FINGERPRINT_TIMEOUT_SECONDS`.

**Model names vary by key.** Not every key exposes every model, and `ListModels` is
unavailable on some, so the reachable set has to be probed. On the team's current key
`gemma-4-31b-it`, `gemini-3.5-flash-lite` and `gemini-embedding-2` all work, while the
older `gemma-3-*` names return 404. `GET /health` reports which models are configured;
if fingerprinting 404s, the model name is the first thing to check.

`experience_embeddings.embedding_model` has a column default of
`'text-embedding-3-small'` from the original spec. Every insert writes the real model
name explicitly, so the default is never relied on.

## Running it

### Docker (recommended)

```bash
cp .env.example .env      # then fill it in
docker compose up
```

The API is on <http://localhost:8000>, docs at `/docs`, health at `/health`. Add `-d`
to detach, `docker compose logs -f api` to follow, `docker compose down` to stop.

Supabase, Gemini and Neo4j are all hosted services, so nothing else runs in compose —
the container needs credentials, not sibling containers. `.env` is passed in via
`env_file` and is excluded from the build context by `.dockerignore`, so **no secret is
ever baked into an image layer**. The container runs as a non-root user.

Change the published port with `API_PORT=9000 docker compose up`.

To also serve the test page at <http://localhost:8080>:

```bash
docker compose --profile testpage up
```

> If you point `DATABASE_URL` or `NEO4J_URI` at a service on your own machine, use
> `host.docker.internal` rather than `localhost` — inside a container `localhost` is the
> container itself.

Run the tests inside the image:

```bash
docker compose run --rm --entrypoint python api -m pytest -q
```

### Without Docker

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

183 tests, no credentials or network required. `backend/tests/fakes.py` stands in for
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
| `test_storage.py` | Bucket resolution, path traversal and URI-scheme rejection, upload limits |

The PRD's Samsung S23 ranking scenario is asserted directly, at both the unit and the
API level — if that ordering breaks, the product claim breaks.

### Verified against the live project

Confirmed by hand against the team's Supabase project and the Gemini API:

- All 25 tables reachable, and their columns diffed against `docs/schema-reference.md`.
  That diff is what turned up `service_requests.match_result_id`, which the API had been
  accepting and silently dropping.
- Embedding generation and indexing: all existing experiences embedded through
  `gemini-embedding-2`, with the model name and canonical `source_text` written correctly.
- Token validation against the project's JWKS endpoint.
- Fingerprint extraction, including the `customer_stated` / `ai_inferred` provenance
  marker and the high-risk safety warning.

**Not yet verified: pgvector similarity search**, which needs `DATABASE_URL`. Without it
those endpoints return a clean `VECTOR_SEARCH_ERROR` rather than failing oddly, but the
ranking has not been exercised against the real HNSW indexes. That is the one gap
between this backend and a fully proven end-to-end path.

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
  services/storage/          bucket resolution, path validation, object fetch
  scripts/seed_demo.py
  tests/
docs/schema-reference.md     columns and CHECK values for all 25 tables
testpage/index.html
Dockerfile                   multi-stage build, non-root runtime
docker-compose.yml           the api service, plus an optional testpage profile
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
