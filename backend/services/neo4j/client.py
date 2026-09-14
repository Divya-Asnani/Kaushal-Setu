import os
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()


class Neo4jClient:
    """
    Lightweight Neo4j Aura client using the HTTPS Query API.

    PostgreSQL/Supabase remains the source of truth.
    Neo4j is used as a graph projection for relationship/context queries.
    """

    def __init__(self) -> None:
        uri = os.getenv("NEO4J_URI")
        username = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")

        if not uri:
            raise RuntimeError("NEO4J_URI is missing from environment")

        if not username:
            raise RuntimeError("NEO4J_USERNAME is missing from environment")

        if not password:
            raise RuntimeError("NEO4J_PASSWORD is missing from environment")

        self.username = username
        self.password = password
        self.database = username

        hostname = uri.replace("neo4j+s://", "").rstrip("/")

        self.query_url = (
            f"https://{hostname}/db/{self.database}/query/v2"
        )

    def execute(
        self,
        statement: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute one Cypher statement through the Neo4j Aura Query API.
        """

        response = requests.post(
            self.query_url,
            auth=(self.username, self.password),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "statement": statement,
                "parameters": parameters or {},
            },
            timeout=30,
        )

        if not response.ok:
            raise RuntimeError(
                f"Neo4j query failed "
                f"(HTTP {response.status_code}): {response.text}"
            )

        return response.json()

    def health_check(self) -> bool:
        """Check whether Neo4j is reachable and can execute Cypher."""

        result = self.execute("RETURN 1 AS health")

        values = result.get("data", {}).get("values", [])

        return bool(values and values[0][0] == 1)


neo4j_client = Neo4jClient()