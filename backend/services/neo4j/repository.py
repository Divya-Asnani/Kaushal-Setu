from typing import Any

from .client import neo4j_client


class Neo4jRepository:
    """
    Repository for graph operations used by Kaushal Setu.

    Neo4j is a projection of PostgreSQL/Supabase.
    PostgreSQL remains the source of truth.
    """

    def __init__(self) -> None:
        self.client = neo4j_client

    # ---------------------------------------------------------
    # Worker
    # ---------------------------------------------------------

    def upsert_worker(
        self,
        worker: dict[str, Any],
    ) -> dict[str, Any]:
        query = """
        MERGE (w:Worker {id: $id})
        SET
            w.user_id = $user_id,
            w.full_name = $full_name,
            w.headline = $headline,
            w.bio = $bio,
            w.experience_years = $experience_years,
            w.hourly_rate = $hourly_rate,
            w.service_radius_km = $service_radius_km,
            w.latitude = $latitude,
            w.longitude = $longitude,
            w.locality = $locality,
            w.city = $city,
            w.state = $state,
            w.is_available = $is_available,
            w.is_verified = $is_verified,
            w.rating = $rating,
            w.total_reviews = $total_reviews
        RETURN w
        """

        return self.client.execute(query, worker)

    # ---------------------------------------------------------
    # Skill
    # ---------------------------------------------------------
        # ---------------------------------------------------------
    # Knowledge Case
    # ---------------------------------------------------------

    def upsert_knowledge_case(
        self,
        knowledge_case: dict[str, Any],
    ) -> dict[str, Any]:
        query = """
        MERGE (k:KnowledgeCase {id: $id})
        SET
            k.worker_id = $worker_id,
            k.experience_id = $experience_id,
            k.title = $title,
            k.problem_summary = $problem_summary,
            k.diagnosis = $diagnosis,
            k.solution = $solution,
            k.lesson_learned = $lesson_learned,
            k.difficulty = $difficulty,
            k.device_category = $device_category,
            k.brand = $brand,
            k.model = $model,
            k.is_published = $is_published,
            k.is_verified = $is_verified,
            k.view_count = $view_count

        WITH k

        MATCH (w:Worker {id: $worker_id})
        MERGE (k)-[:CREATED_BY]->(w)

        RETURN k
        """

        return self.client.execute(query, knowledge_case)

    def link_knowledge_case_issue(
        self,
        knowledge_case_id: str,
        issue_id: str,
    ) -> dict[str, Any]:
        query = """
        MATCH (k:KnowledgeCase {id: $knowledge_case_id})
        MATCH (i:Issue {id: $issue_id})
        MERGE (k)-[:ABOUT]->(i)
        RETURN k, i
        """

        return self.client.execute(
            query,
            {
                "knowledge_case_id": knowledge_case_id,
                "issue_id": issue_id,
            },
        )

    def link_knowledge_case_skill(
        self,
        knowledge_case_id: str,
        skill_id: str,
    ) -> dict[str, Any]:
        query = """
        MATCH (k:KnowledgeCase {id: $knowledge_case_id})
        MATCH (s:Skill {id: $skill_id})
        MERGE (k)-[:REQUIRES_SKILL]->(s)
        RETURN k, s
        """

        return self.client.execute(
            query,
            {
                "knowledge_case_id": knowledge_case_id,
                "skill_id": skill_id,
            },
        )

    def upsert_skill(
        self,
        skill: dict[str, Any],
    ) -> dict[str, Any]:
        query = """
        MERGE (s:Skill {id: $id})
        SET
            s.name = $name,
            s.category = $category,
            s.description = $description
        RETURN s
        """

        return self.client.execute(query, skill)

    def link_worker_skill(
        self,
        worker_id: str,
        skill_id: str,
        proficiency_level: str | None = None,
        verified: bool = False,
    ) -> dict[str, Any]:
        query = """
        MATCH (w:Worker {id: $worker_id})
        MATCH (s:Skill {id: $skill_id})
        MERGE (w)-[r:HAS_SKILL]->(s)
        SET
            r.proficiency_level = $proficiency_level,
            r.verified = $verified
        RETURN w, r, s
        """

        return self.client.execute(
            query,
            {
                "worker_id": worker_id,
                "skill_id": skill_id,
                "proficiency_level": proficiency_level,
                "verified": verified,
            },
        )

    # ---------------------------------------------------------
    # Experience
    # ---------------------------------------------------------

    def upsert_experience(
        self,
        experience: dict[str, Any],
    ) -> dict[str, Any]:
        query = """
        MERGE (e:Experience {id: $id})
        SET
            e.worker_id = $worker_id,
            e.title = $title,
            e.diagnosis = $diagnosis,
            e.repair_type = $repair_type,
            e.device_category = $device_category,
            e.brand = $brand,
            e.model = $model,
            e.difficulty = $difficulty,
            e.verification_status = $verification_status
        WITH e
        MATCH (w:Worker {id: $worker_id})
        MERGE (w)-[:SOLVED]->(e)
        RETURN e
        """

        return self.client.execute(query, experience)

    # ---------------------------------------------------------
    # Device
    # ---------------------------------------------------------

    def upsert_device(
        self,
        device: dict[str, Any],
    ) -> dict[str, Any]:
        query = """
        MERGE (d:Device {id: $id})
        SET
            d.device_type = $device_type,
            d.brand = $brand,
            d.model = $model
        RETURN d
        """

        return self.client.execute(query, device)

    def link_experience_device(
        self,
        experience_id: str,
        device_id: str,
    ) -> dict[str, Any]:
        query = """
        MATCH (e:Experience {id: $experience_id})
        MATCH (d:Device {id: $device_id})
        MERGE (e)-[:INVOLVES]->(d)
        RETURN e, d
        """

        return self.client.execute(
            query,
            {
                "experience_id": experience_id,
                "device_id": device_id,
            },
        )

    # ---------------------------------------------------------
    # Issue
    # ---------------------------------------------------------

    def upsert_issue(
        self,
        issue: dict[str, Any],
    ) -> dict[str, Any]:
        query = """
        MERGE (i:Issue {id: $id})
        SET
            i.canonical_name = $canonical_name
        RETURN i
        """

        return self.client.execute(query, issue)

    def link_experience_issue(
        self,
        experience_id: str,
        issue_id: str,
    ) -> dict[str, Any]:
        query = """
        MATCH (e:Experience {id: $experience_id})
        MATCH (i:Issue {id: $issue_id})
        MERGE (e)-[:HAS_ISSUE]->(i)
        RETURN e, i
        """

        return self.client.execute(
            query,
            {
                "experience_id": experience_id,
                "issue_id": issue_id,
            },
        )

    # ---------------------------------------------------------
    # Context
    # ---------------------------------------------------------

    def upsert_context(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        query = """
        MERGE (c:Context {id: $id})
        SET
            c.canonical_name = $canonical_name,
            c.description = $description
        RETURN c
        """

        return self.client.execute(query, context)

    def link_experience_context(
        self,
        experience_id: str,
        context_id: str,
    ) -> dict[str, Any]:
        query = """
        MATCH (e:Experience {id: $experience_id})
        MATCH (c:Context {id: $context_id})
        MERGE (e)-[:OCCURRED_IN]->(c)
        RETURN e, c
        """

        return self.client.execute(
            query,
            {
                "experience_id": experience_id,
                "context_id": context_id,
            },
        )

    # ---------------------------------------------------------
    # Outcome
    # ---------------------------------------------------------

    def upsert_outcome(
        self,
        outcome: dict[str, Any],
    ) -> dict[str, Any]:
        query = """
        MERGE (o:Outcome {id: $id})
        SET
            o.outcome_type = $outcome_type,
            o.outcome_description = $outcome_description,
            o.success_status = $success_status,
            o.lessons_learned = $lessons_learned
        RETURN o
        """

        return self.client.execute(query, outcome)

    def link_experience_outcome(
        self,
        experience_id: str,
        outcome_id: str,
    ) -> dict[str, Any]:
        query = """
        MATCH (e:Experience {id: $experience_id})
        MATCH (o:Outcome {id: $outcome_id})
        MERGE (e)-[:RESULTED_IN]->(o)
        RETURN e, o
        """

        return self.client.execute(
            query,
            {
                "experience_id": experience_id,
                "outcome_id": outcome_id,
            },
        )

    # ---------------------------------------------------------
    # Graph matching
    # ---------------------------------------------------------

    def find_workers_by_experience(
        self,
        brand: str | None = None,
        model: str | None = None,
        issue: str | None = None,
    ) -> dict[str, Any]:
        query = """
        MATCH (w:Worker)-[:SOLVED]->(e:Experience)
        OPTIONAL MATCH (e)-[:INVOLVES]->(d:Device)
        OPTIONAL MATCH (e)-[:HAS_ISSUE]->(i:Issue)

        WHERE
            ($brand IS NULL OR d.brand = $brand OR e.brand = $brand)
            AND
            ($model IS NULL OR d.model = $model OR e.model = $model)
            AND
            ($issue IS NULL OR i.canonical_name = $issue)

        RETURN DISTINCT
            w.id AS worker_id,
            w.full_name AS full_name,
            w.rating AS rating,
            w.is_verified AS worker_verified,
            e.id AS experience_id,
            e.title AS experience_title,
            e.diagnosis AS diagnosis,
            e.verification_status AS verification_status,
            d.brand AS device_brand,
            d.model AS device_model,
            i.canonical_name AS issue
        ORDER BY
            CASE
                WHEN e.verification_status = 'verified' THEN 1
                ELSE 0
            END DESC,
            w.rating DESC
        """

        return self.client.execute(
            query,
            {
                "brand": brand,
                "model": model,
                "issue": issue,
            },
        )


neo4j_repository = Neo4jRepository()

