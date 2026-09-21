-- ============================================================================
-- KAUSHALSETU: POSTGRESQL / SUPABASE DATABASE SCHEMA
-- Exactly 25 Tables (Frozen Architecture - Single Source of Truth)
-- ============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Enum Types
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('customer', 'worker', 'admin');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE request_status AS ENUM ('pending', 'accepted', 'rejected', 'expired', 'cancelled');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE job_status AS ENUM ('confirmed', 'in_progress', 'completed', 'cancelled', 'disputed');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE verification_status AS ENUM ('unverified', 'verified', 'disputed');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE media_role AS ENUM ('before', 'during', 'after', 'diagnostic');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- 1. profiles (profiles.id == auth.users.id)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY,
    role user_role NOT NULL DEFAULT 'customer',
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(32),
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. worker_profiles
CREATE TABLE IF NOT EXISTS worker_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    headline VARCHAR(255),
    bio TEXT,
    experience_years INT DEFAULT 0,
    hourly_rate NUMERIC(10, 2),
    service_radius_km NUMERIC(5, 2) DEFAULT 15.00,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    address_line TEXT,
    locality VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    is_available BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    rating NUMERIC(3, 2) DEFAULT 5.00,
    total_reviews INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. skills
CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. worker_skills
CREATE TABLE IF NOT EXISTS worker_skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES worker_profiles(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    proficiency_level VARCHAR(50) DEFAULT 'intermediate',
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(worker_id, skill_id)
);

-- 5. certificates
CREATE TABLE IF NOT EXISTS certificates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES worker_profiles(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    issuing_organization VARCHAR(255) NOT NULL,
    issue_date DATE,
    expiry_date DATE,
    credential_url TEXT,
    storage_path TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. problems
CREATE TABLE IF NOT EXISTS problems (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    address_line TEXT,
    locality VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. problem_media
CREATE TABLE IF NOT EXISTS problem_media (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    storage_path TEXT NOT NULL,
    media_type VARCHAR(50) NOT NULL DEFAULT 'image',
    file_size_bytes BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. problem_fingerprints
CREATE TABLE IF NOT EXISTS problem_fingerprints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id UUID UNIQUE NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    device_type VARCHAR(100),
    brand VARCHAR(100),
    model VARCHAR(100),
    category VARCHAR(100),
    issue VARCHAR(255),
    symptoms JSONB DEFAULT '[]'::jsonb,
    context JSONB DEFAULT '{}'::jsonb,
    suspected_component VARCHAR(255),
    repair_type VARCHAR(100),
    extracted_skills JSONB DEFAULT '[]'::jsonb,
    ai_summary TEXT,
    fingerprint_version INT DEFAULT 1,
    embedding_status VARCHAR(50) DEFAULT 'completed',
    embedding vector(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9. experiences
CREATE TABLE IF NOT EXISTS experiences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES worker_profiles(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    diagnosis TEXT NOT NULL,
    repair_type VARCHAR(100),
    device_category VARCHAR(100),
    brand VARCHAR(100),
    model VARCHAR(100),
    difficulty VARCHAR(50) DEFAULT 'intermediate',
    verification_status verification_status NOT NULL DEFAULT 'unverified',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. experience_contexts
CREATE TABLE IF NOT EXISTS experience_contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experience_id UUID UNIQUE NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
    environment VARCHAR(100),
    usage_history TEXT,
    prior_attempts TEXT,
    symptoms JSONB DEFAULT '[]'::jsonb,
    operational_conditions JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 11. experience_actions
CREATE TABLE IF NOT EXISTS experience_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experience_id UUID NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
    step_number INT NOT NULL,
    action_type VARCHAR(100) NOT NULL,
    action_description TEXT NOT NULL,
    tools_used JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 12. experience_outcomes
CREATE TABLE IF NOT EXISTS experience_outcomes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experience_id UUID NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
    outcome_type VARCHAR(100) NOT NULL,
    outcome_description TEXT NOT NULL,
    success_status VARCHAR(50) NOT NULL DEFAULT 'successful',
    lessons_learned TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 13. experience_skills
CREATE TABLE IF NOT EXISTS experience_skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experience_id UUID NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    relevance_score NUMERIC(3, 2) DEFAULT 1.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(experience_id, skill_id)
);

-- 14. experience_media
CREATE TABLE IF NOT EXISTS experience_media (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experience_id UUID NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
    storage_path TEXT NOT NULL,
    media_type VARCHAR(50) NOT NULL DEFAULT 'image',
    media_role media_role NOT NULL DEFAULT 'after',
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 15. experience_embeddings
CREATE TABLE IF NOT EXISTS experience_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experience_id UUID UNIQUE NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
    embedding vector(384),
    model_version VARCHAR(50) DEFAULT 'all-MiniLM-L6-v2',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 16. service_requests
CREATE TABLE IF NOT EXISTS service_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    worker_id UUID NOT NULL REFERENCES worker_profiles(id) ON DELETE CASCADE,
    match_result_id UUID,
    customer_message TEXT,
    worker_response TEXT,
    status request_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 17. jobs
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_request_id UUID UNIQUE NOT NULL REFERENCES service_requests(id) ON DELETE CASCADE,
    problem_id UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    worker_id UUID NOT NULL REFERENCES worker_profiles(id) ON DELETE CASCADE,
    experience_id UUID REFERENCES experiences(id) ON DELETE SET NULL,
    status job_status NOT NULL DEFAULT 'confirmed',
    notes TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 18. job_status_history
CREATE TABLE IF NOT EXISTS job_status_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    from_status VARCHAR(50),
    to_status VARCHAR(50) NOT NULL,
    changed_by UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 19. verifications
CREATE TABLE IF NOT EXISTS verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID UNIQUE NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    verification_status verification_status NOT NULL DEFAULT 'unverified',
    comments TEXT,
    verified_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 20. feedback
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID UNIQUE NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    worker_id UUID NOT NULL REFERENCES worker_profiles(id) ON DELETE CASCADE,
    rating NUMERIC(2, 1) NOT NULL CHECK (rating >= 1.0 AND rating <= 5.0),
    feedback_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 21. knowledge_cases
CREATE TABLE IF NOT EXISTS knowledge_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES worker_profiles(id) ON DELETE CASCADE,
    experience_id UUID REFERENCES experiences(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    problem_summary TEXT NOT NULL,
    diagnosis TEXT NOT NULL,
    solution TEXT NOT NULL,
    lesson_learned TEXT,
    difficulty VARCHAR(50) DEFAULT 'intermediate',
    device_category VARCHAR(100),
    brand VARCHAR(100),
    model VARCHAR(100),
    is_published BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    view_count INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 22. knowledge_case_media
CREATE TABLE IF NOT EXISTS knowledge_case_media (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knowledge_case_id UUID NOT NULL REFERENCES knowledge_cases(id) ON DELETE CASCADE,
    storage_path TEXT NOT NULL,
    media_type VARCHAR(50) NOT NULL DEFAULT 'image',
    caption TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 23. knowledge_case_embeddings
CREATE TABLE IF NOT EXISTS knowledge_case_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knowledge_case_id UUID UNIQUE NOT NULL REFERENCES knowledge_cases(id) ON DELETE CASCADE,
    embedding vector(384),
    model_version VARCHAR(50) DEFAULT 'all-MiniLM-L6-v2',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 24. match_results
CREATE TABLE IF NOT EXISTS match_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    worker_id UUID NOT NULL REFERENCES worker_profiles(id) ON DELETE CASCADE,
    rank_position INT NOT NULL,
    match_score NUMERIC(5, 4) NOT NULL,
    problem_similarity NUMERIC(5, 4) NOT NULL,
    context_similarity NUMERIC(5, 4) NOT NULL,
    verified_experience_confidence NUMERIC(5, 4) NOT NULL,
    proximity_score NUMERIC(5, 4) NOT NULL,
    explanations JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 25. notifications
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) NOT NULL,
    reference_id UUID,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add Foreign Key from service_requests to match_results (cyclic reference resolved)
ALTER TABLE service_requests
    ADD CONSTRAINT fk_service_requests_match_result
    FOREIGN KEY (match_result_id) REFERENCES match_results(id) ON DELETE SET NULL;

-- Indexes for high performance
CREATE INDEX IF NOT EXISTS idx_worker_profiles_user ON worker_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_problems_customer ON problems(customer_id);
CREATE INDEX IF NOT EXISTS idx_service_requests_worker ON service_requests(worker_id);
CREATE INDEX IF NOT EXISTS idx_service_requests_problem ON service_requests(problem_id);
CREATE INDEX IF NOT EXISTS idx_jobs_customer ON jobs(customer_id);
CREATE INDEX IF NOT EXISTS idx_jobs_worker ON jobs(worker_id);
CREATE INDEX IF NOT EXISTS idx_match_results_problem ON match_results(problem_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
