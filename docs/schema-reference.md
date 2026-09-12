# iBolt / Kaushal Setu — Schema Reference (Person 1 working copy)

Derived from the team design doc. `public` schema, RLS disabled (authorization is
enforced in FastAPI). Every table has `created_at timestamptz not null default now()`;
most also have `updated_at`.

## profiles
- id :: uuid :: PK, FK -> auth.users.id
- role :: text :: not null default 'customer' :: CHECK in (customer, worker, admin)
- display_name :: text :: not null
- phone :: text :: nullable
- avatar_url :: text :: nullable
- is_active :: boolean :: not null default true
- created_at :: timestamptz :: not null default now()
- updated_at :: timestamptz :: not null default now()


## worker_profiles
- user_id :: uuid :: PRIMARY KEY
- professional_title :: text :: NOT NULL
- bio :: text :: Nullable
- years_experience :: integer :: NOT NULL :: default 0
- service_radius_km :: numeric(6,2) :: NOT NULL :: default 10
- address_line :: text :: Nullable
- locality :: text :: Nullable
- city :: text :: Nullable
- state :: text :: Nullable
- postal_code :: text :: Nullable
- latitude :: numeric(9,6) :: Nullable
- longitude :: numeric(9,6) :: Nullable
- availability_status :: text :: NOT NULL :: default available
- is_verified :: boolean :: NOT NULL :: default false
- created_at :: timestamptz :: NOT NULL :: default now()
- updated_at :: timestamptz :: NOT NULL :: default now()

## skills
- id :: uuid :: PRIMARY KEY :: default gen_random_uuid()
- name :: text :: NOT NULL UNIQUE
- category :: text :: NOT NULL
- description :: text :: Nullable
- is_active :: boolean :: NOT NULL :: default true
- created_at :: timestamptz :: NOT NULL :: default now()
- updated_at :: timestamptz :: NOT NULL :: default now()

## worker_skills
- worker_id :: uuid :: NOT NULL PRIMARY KEY component FOREIGN KEY :: -> public.worker_profiles(user_id)
- skill_id :: uuid :: NOT NULL PRIMARY KEY component FOREIGN KEY :: -> public.skills(id)
- proficiency_level :: text :: NOT NULL :: default intermediate
- years_experience :: integer :: NOT NULL CHECK years_experience \>= 0 :: default 0
- is_primary :: boolean :: NOT NULL :: default false
- created_at :: timestamptz :: NOT NULL :: default now()
- updated_at :: timestamptz :: NOT NULL :: default now()

## certificates
- id :: uuid :: PRIMARY KEY :: default gen_random_uuid()
- worker_id :: uuid :: NOT NULL FOREIGN KEY :: -> public.worker_profiles(user_id)
- certificate_name :: text :: NOT NULL
- issuing_organization :: text :: Nullable
- certificate_number :: text :: Nullable
- issue_date :: date :: Nullable
- expiry_date :: date :: Nullable
- certificate_url :: text :: Nullable
- verification_status :: text :: NOT NULL :: default pending
- verified_at :: timestamptz :: Nullable
- created_at :: timestamptz :: NOT NULL :: default now()
- updated_at :: timestamptz :: NOT NULL :: default now()

## problems
- id :: uuid :: PRIMARY KEY :: default gen_random_uuid()
- customer_id :: uuid :: NOT NULL FOREIGN KEY :: -> public.profiles(id)
- title :: text :: NOT NULL
- description :: text :: NOT NULL
- status :: text :: NOT NULL :: default open
- address_line :: text :: Nullable
- locality :: text :: Nullable
- city :: text :: Nullable
- state :: text :: Nullable
- postal_code :: text :: Nullable
- latitude :: numeric(9,6) :: Nullable Range -90 to 90
- longitude :: numeric(9,6) :: Nullable Range -180 to 180
- created_at :: timestamptz :: NOT NULL :: default now()
- updated_at :: timestamptz :: NOT NULL :: default now()

## problem_media
- id :: uuid :: PRIMARY KEY :: default gen_random_uuid()
- problem_id :: uuid :: NOT NULL FOREIGN KEY :: -> public.problems(id)
- storage_path :: text :: NOT NULL
- media_type :: text :: NOT NULL
- mime_type :: text :: Nullable
- file_name :: text :: Nullable
- file_size_bytes :: bigint :: Nullable CHECK \>= 0
- caption :: text :: Nullable
- created_at :: timestamptz :: NOT NULL :: default now()

## problem_fingerprints
- id :: uuid :: PRIMARY KEY :: default gen_random_uuid()
- problem_id :: uuid :: NOT NULL UNIQUE FOREIGN KEY :: -> public.problems(id)
- device_type :: text :: Nullable
- brand :: text :: Nullable
- model :: text :: Nullable
- category :: text :: Nullable
- issue :: text :: Nullable
- symptoms :: jsonb :: Nullable
- context :: jsonb :: Nullable
- suspected_component :: text :: Nullable
- repair_type :: text :: Nullable
- extracted_skills :: jsonb :: Nullable
- ai_summary :: text :: Nullable
- raw_ai_output :: jsonb :: Nullable
- embedding_status :: text :: NOT NULL :: default pending
- fingerprint_version :: text :: NOT NULL :: default v1
- created_at :: timestamptz :: NOT NULL :: default now()
- updated_at :: timestamptz :: NOT NULL :: default now()

## experiences
- id :: uuid :: PRIMARY KEY :: default gen_random_uuid()
- worker_id :: uuid :: NOT NULL FOREIGN KEY :: -> public.worker_profiles(user_id)
- title :: text :: NOT NULL
- problem_description :: text :: NOT NULL
- diagnosis :: text :: Nullable
- outcome_summary :: text :: Nullable
- experience_status :: text :: NOT NULL :: default draft
- verification_confidence :: numeric(5,2) :: NOT NULL CHECK between 0 and 100 :: default 0
- solved_at :: timestamptz :: Nullable
- created_at :: timestamptz :: NOT NULL :: default now()
- updated_at :: timestamptz :: NOT NULL :: default now()

## experience_contexts
- id :: uuid :: PRIMARY KEY :: default gen_random_uuid()
- experience_id :: uuid :: NOT NULL FOREIGN KEY :: -> public.experiences(id)
- context_type :: text :: NOT NULL
- context_value :: text :: NOT NULL
- context_details :: jsonb :: Nullable
- importance_score :: numeric(5,2) :: NOT NULL CHECK between 0 and 1
- created_at :: timestamptz :: NOT NULL :: default now()
- updated_at :: timestamptz :: NOT NULL :: default now()

## experience_actions
- id :: uuid :: PRIMARY KEY :: default gen_random_uuid()
- experience_id :: uuid :: NOT NULL FOREIGN KEY :: -> public.experiences(id)
- step_number :: integer :: NOT NULL CHECK \> 0
- action_type :: text :: NOT NULL
- action_description :: text :: NOT NULL
- tools_used :: jsonb :: Nullable
- components_involved :: jsonb :: Nullable
- result :: text :: Nullable
- created_at :: timestamptz :: NOT NULL :: default now()
- updated_at :: timestamptz :: NOT NULL :: default now()

## experience_outcomes
- id :: uuid :: PRIMARY KEY :: default gen_random_uuid()
- experience_id :: uuid :: NOT NULL FOREIGN KEY :: -> public.experiences(id)
- outcome_type :: text :: NOT NULL
- outcome_description :: text :: NOT NULL
- success_status :: text :: NOT NULL :: default successful
- customer_confirmed :: boolean :: NOT NULL :: default false
- follow_up_required :: boolean :: NOT NULL :: default false
- created_at :: timestamptz :: NOT NULL :: default now()
- updated_at :: timestamptz :: NOT NULL :: default now()

## experience_skills
- experience_id :: uuid :: NOT NULL PRIMARY KEY component FOREIGN KEY :: -> public.experiences(id)
- skill_id :: uuid :: NOT NULL PRIMARY KEY component FOREIGN KEY :: -> public.skills(id)
- proficiency_demonstrated :: text :: Nullable
- is_primary_skill :: boolean :: NOT NULL :: default false
- created_at :: timestamptz :: NOT NULL :: default now()
- updated_at :: timestamptz :: NOT NULL :: default now()

## experience_media
- id :: uuid :: PRIMARY KEY :: default gen_random_uuid()
- experience_id :: uuid :: NOT NULL FOREIGN KEY :: -> public.experiences(id)
- storage_path :: text :: NOT NULL
- media_type :: text :: NOT NULL
- mime_type :: text :: Nullable
- file_name :: text :: Nullable
- file_size_bytes :: bigint :: Nullable CHECK \>= 0
- media_role :: text :: NOT NULL :: default evidence
- caption :: text :: Nullable
- is_verified :: boolean :: NOT NULL :: default false
- created_at :: timestamptz :: NOT NULL :: default now()

## experience_embeddings
- id :: uuid :: PRIMARY KEY :: default gen_random_uuid()
- experience_id :: uuid :: NOT NULL UNIQUE FOREIGN KEY :: -> public.experiences(id)
- embedding :: vector(1536) :: NOT NULL
- embedding_model :: text :: NOT NULL :: default text-embedding-3-small
- embedding_version :: text :: NOT NULL :: default v1
- source_text :: text :: NOT NULL

## service_requests
- id :: uuid :: primary key default gen_random_uuid()

## jobs
- id :: uuid :: primary key default gen_random_uuid()

## job_status_history
- id :: uuid :: primary key default gen_random_uuid()

## verifications
- id :: uuid :: primary key default gen_random_uuid()

## feedback
- id :: uuid :: primary key default gen_random_uuid()

## knowledge_cases
- id :: uuid :: primary key default gen_random_uuid()

## knowledge_case_media
- id :: uuid :: primary key default gen_random_uuid()

## knowledge_case_embeddings
- id :: uuid :: primary key default gen_random_uuid()
- embedding_model :: text :: not null default 'text-embedding-3-small'

## match_results
- id :: uuid :: primary key default gen_random_uuid()

## notifications
- id :: uuid :: primary key default gen_random_uuid()
## service_requests
- id :: uuid :: primary key default gen_random_uuid()
- problem_id :: uuid :: not null foreign key → public.problems(id) on delete restrict
- worker_id :: uuid :: not null foreign key → public.worker_profiles(user_id) on delete restrict
- status :: text :: not null default 'pending'
- customer_message :: text :: nullable
- worker_response :: text :: nullable
- requested_at :: timestamptz :: not null default now()
- responded_at :: timestamptz :: nullable
- accepted_at :: timestamptz :: nullable
- expires_at :: timestamptz :: nullable
- created_at :: timestamptz :: not null default now()
- updated_at :: timestamptz :: not null default now()

## jobs
- id :: uuid :: primary key default gen_random_uuid()
- service_request_id :: uuid :: not null unique foreign key → public.service_requests(id) on delete restrict
- status :: text :: not null default 'confirmed'
- scheduled_at :: timestamptz :: nullable
- started_at :: timestamptz :: nullable
- completed_at :: timestamptz :: nullable
- created_at :: timestamptz :: not null default now()
- updated_at :: timestamptz :: not null default now()

## job_status_history
- id :: uuid :: primary key default gen_random_uuid()
- job_id :: uuid :: not null foreign key → public.jobs(id) on delete cascade
- status :: text :: not null
- changed_by :: uuid :: nullable foreign key → public.profiles(id) on delete set null
- notes :: text :: nullable
- changed_at :: timestamptz :: not null default now()
- created_at :: timestamptz :: not null default now()

## verifications
- id :: uuid :: primary key default gen_random_uuid()
- job_id :: uuid :: not null foreign key → public.jobs(id) on delete restrict
- experience_id :: uuid :: nullable foreign key → public.experiences(id) on delete set null
- verifier_id :: uuid :: nullable foreign key → public.profiles(id) on delete set null
- verification_type :: text :: not null
- verification_status :: text :: not null default 'pending'
- verification_score :: numeric(5,2) :: nullable 0 to 100
- comments :: text :: nullable
- verified_at :: timestamptz :: nullable
- created_at :: timestamptz :: not null default now()
- updated_at :: timestamptz :: not null default now()

## feedback
- id :: uuid :: primary key default gen_random_uuid()
- job_id :: uuid :: not null foreign key → public.jobs(id) on delete restrict
- customer_id :: uuid :: not null foreign key → public.profiles(id) on delete restrict
- worker_id :: uuid :: not null foreign key → public.worker_profiles(user_id) on delete restrict
- rating :: numeric(2,1) :: not null between 1 and 5
- feedback_text :: text :: nullable
- created_at :: timestamptz :: not null default now()
- updated_at :: timestamptz :: not null default now()

## knowledge_cases
- id :: uuid :: primary key default gen_random_uuid()
- worker_id :: uuid :: not null foreign key → public.worker_profiles(user_id) on delete restrict
- experience_id :: uuid :: nullable foreign key → public.experiences(id) on delete set null
- title :: text :: not null
- problem_summary :: text :: not null
- diagnosis_summary :: text :: nullable
- solution_summary :: text :: nullable
- lesson_learned :: text :: nullable
- difficulty_level :: text :: not null default 'intermediate'
- visibility_status :: text :: not null default 'draft'
- is_verified :: boolean :: not null default false
- published_at :: timestamptz :: nullable
- created_at :: timestamptz :: not null default now()
- updated_at :: timestamptz :: not null default now()

## knowledge_case_media
- id :: uuid :: primary key default gen_random_uuid()
- knowledge_case_id :: uuid :: not null foreign key → public.knowledge_cases(id) on delete cascade
- storage_path :: text :: not null
- media_type :: text :: not null
- mime_type :: text :: nullable
- file_name :: text :: nullable
- file_size_bytes :: bigint :: nullable must be >= 0
- media_role :: text :: not null default 'reference'
- caption :: text :: nullable
- created_at :: timestamptz :: not null default now()

## knowledge_case_embeddings
- id :: uuid :: primary key default gen_random_uuid()
- knowledge_case_id :: uuid :: not null unique foreign key → public.knowledge_cases(id) on delete cascade
- embedding :: vector(1536) :: not null
- embedding_version :: text :: not null default 'v1'
- source_text :: text :: not null

## match_results
- id :: uuid :: primary key default gen_random_uuid()
- problem_id :: uuid :: not null foreign key → public.problems(id) on delete cascade
- worker_id :: uuid :: not null foreign key → public.worker_profiles(user_id) on delete restrict
- problem_similarity :: numeric(5,2) :: not null 0 to 100
- context_similarity :: numeric(5,2) :: not null 0 to 100
- verified_experience_confidence :: numeric(5,2) :: not null 0 to 100
- proximity_score :: numeric(5,2) :: not null 0 to 100
- match_score :: numeric(5,2) :: not null 0 to 100
- rank_position :: integer :: not null greater than 0
- explanation :: jsonb :: nullable
- matching_metadata :: jsonb :: nullable
- created_at :: timestamptz :: not null default now()
- updated_at :: timestamptz :: not null default now()

## notifications
- id :: uuid :: primary key default gen_random_uuid()
- user_id :: uuid :: not null foreign key → public.profiles(id) on delete cascade
- notification_type :: text :: not null
- title :: text :: not null
- message :: text :: not null
- related_entity_type :: text :: nullable
- related_entity_id :: uuid :: nullable
- is_read :: boolean :: not null default false
- read_at :: timestamptz :: nullable
- created_at :: timestamptz :: not null default now()
---

## Enumerated (CHECK) values

| Table.column | Allowed |
|---|---|
| profiles.role | customer, worker, admin |
| worker_profiles.availability_status | available, busy, offline |
| worker_skills.proficiency_level | beginner, intermediate, advanced, expert |
| certificates.verification_status | pending, verified, rejected, expired |
| problems.status | open, matched, requested, in_progress, resolved, cancelled |
| problem_media.media_type | image, video, document |
| problem_fingerprints.embedding_status | pending, generated, failed |
| experiences.experience_status | draft, submitted, verified, disputed, archived |
| experience_outcomes.success_status | successful, partially_successful, unsuccessful, unknown |
| experience_skills.proficiency_demonstrated | beginner, intermediate, advanced, expert |
| experience_media.media_type | image, video, document |
| experience_media.media_role | evidence, before, during, after, diagnostic, other |
| service_requests.status | pending, accepted, rejected, cancelled, expired |
| jobs.status | confirmed, in_progress, completed, cancelled, disputed |
| job_status_history.status | confirmed, in_progress, completed, cancelled, disputed |
| verifications.verification_type | customer_confirmation, evidence_review, admin_review, dispute |
| verifications.verification_status | pending, verified, rejected, disputed |
| knowledge_cases.difficulty_level | beginner, intermediate, advanced, expert |
| knowledge_cases.visibility_status | draft, published, archived |

## Embedding columns

`experience_embeddings.embedding` and `knowledge_case_embeddings.embedding` are
`vector(1536)` with HNSW indexes already created by Person 3.

The column default for `embedding_model` is `'text-embedding-3-small'` because the
original spec froze OpenAI. This backend uses Gemini instead and writes the real
model name (`gemini-embedding-001`) explicitly on every insert, so the default is
never relied upon. Dimensionality stays 1536, so no schema or index change is needed.
