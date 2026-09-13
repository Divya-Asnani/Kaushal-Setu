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

### Deploying to Render

Create a **Web Service** — not a Background Worker. A worker has no public URL or HTTP
port; this is an API the Flutter client calls.

- **Runtime:** Docker (Render uses the `Dockerfile` in the repo root).
- **Health check path:** `/health`
- **Environment variables:** everything from `.env.example`. `render.yaml` lists them,
  with the secrets marked `sync: false` so they are entered in the dashboard rather
  than committed.
- **`DATABASE_URL` must be the Session pooler string.** Render, like Docker, cannot
  reach Supabase's IPv6-only direct host.

The container binds to `$PORT` when the platform sets one and falls back to 8000
locally, so the same image runs in both places.

> **The free plan sleeps after ~15 minutes of inactivity**, and the next request pays a
> cold start of roughly a minute. That is survivable for sharing a link, but do not let
> a live demo be the request that wakes it — hit the URL a few minutes beforehand.

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
  so similarity queries use a direct Postgres connection; everything else goes through
  the Supabase client. It points at the *same* Supabase database as `SUPABASE_URL` —
  only the protocol differs.

  **Use the Session pooler string, not the direct one.** Supabase's direct host,
  `db.<ref>.supabase.co`, resolves to IPv6 only. That works from a machine with IPv6
  but fails from inside a Docker container on a default bridge network, with
  `Network is unreachable`. The Session pooler
  (`postgresql://postgres.<ref>:<password>@<region>.pooler.supabase.com:5432/postgres`)
  is reachable over IPv4 and works in both. Percent-encode special characters in the
  password — `@` becomes `%40`.

  If it is unreachable, vector search returns `VECTOR_SEARCH_ERROR` with that hint in
  `details` and the rest of the API keeps working.
- `GEMINI_API_KEY` — fingerprints and embeddings. Must be an AI Studio key (see above).
- `SUPABASE_JWT_SECRET` — only for legacy HS256 projects. Leave blank and tokens are
  verified against the project's JWKS instead.

Neo4j is optional. If it is unreachable the matching pipeline logs it once and
continues with relational context, which is what the PRD requires of a projection.


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
