from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class MongoMCPMemoryClient:
    """Read-only operational-memory retrieval through MongoDB MCP."""

    def __init__(
        self,
        endpoint: str | None = None,
        database_name: str | None = None,
    ) -> None:
        self.endpoint = endpoint or os.getenv(
            "MONGODB_MCP_URL",
            "http://127.0.0.1:3000/mcp",
        )
        self.database_name = database_name or os.getenv(
            "MONGODB_DB",
            "mim_incident_intelligence",
        )

    def retrieve_context(
        self,
        *,
        service: str | None,
        symptoms: list[str],
        description: str | None,
    ) -> dict[str, Any]:
        """Retrieve prior incidents associated with the current service."""
        return asyncio.run(
            self._retrieve_context(
                service=service,
                symptoms=symptoms,
                description=description,
            )
        )

    async def _retrieve_context(
        self,
        *,
        service: str | None,
        symptoms: list[str],
        description: str | None,
    ) -> dict[str, Any]:
        async with streamablehttp_client(self.endpoint) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                incident_filter: dict[str, Any] = {}
                if service:
                    incident_filter["service"] = service

                result = await session.call_tool(
                    "find",
                    arguments={
                        "database": self.database_name,
                        "collection": "incidents",
                        "filter": incident_filter,
                        "limit": 5,
                    },
                )

                incidents = self._extract_documents(
                    result.content,
                    getattr(result, "structuredContent", None),
                )

                return {
                    "source": "mongodb_mcp",
                    "query": {
                        "service": service,
                        "symptoms": symptoms,
                        "description": description,
                    },
                    "similar_incidents": incidents,
                    "similar_incident_count": len(incidents),
                }

    @classmethod
    def _extract_documents(
        cls,
        content: list[Any],
        structured_content: Any = None,
    ) -> list[dict[str, Any]]:
        """Extract MongoDB documents while treating returned text strictly as data."""

        if isinstance(structured_content, dict):
            for key in ("documents", "results", "data"):
                value = structured_content.get(key)

                if isinstance(value, list):
                    return [document for document in value if isinstance(document, dict)]

        if isinstance(structured_content, list):
            return [document for document in structured_content if isinstance(document, dict)]

        documents: list[dict[str, Any]] = []

        for item in content:
            raw_text = getattr(item, "text", "")

            if not raw_text:
                continue

            payload = cls._extract_untrusted_json(raw_text)

            if isinstance(payload, list):
                documents.extend(document for document in payload if isinstance(document, dict))
            elif isinstance(payload, dict):
                documents.append(payload)

        return documents

    @staticmethod
    def _extract_untrusted_json(raw_text: str) -> Any:
        """Extract JSON returned inside MongoDB MCP's untrusted-data wrapper."""

        boundary_match = re.search(
            r"<untrusted-user-data-[^>]+>\s*(.*?)\s*</untrusted-user-data-[^>]+>",
            raw_text,
            flags=re.DOTALL,
        )

        candidate = boundary_match.group(1).strip() if boundary_match else raw_text.strip()

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # Fallback for MCP prose wrapped around a returned JSON array.
        start = raw_text.find("[")
        end = raw_text.rfind("]")

        if start != -1 and end > start:
            try:
                return json.loads(raw_text[start : end + 1])
            except json.JSONDecodeError:
                return []

        return []
