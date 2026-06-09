from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MCPIncidentPayload(BaseModel):
    """Incident payload accepted by the MCP-facing tool.

    This intentionally allows extra/raw fields because client incident data
    may use different names.
    """

    incident_id: str | None = None
    opened_at: str | None = None
    service: str | None = None
    short_description: str | None = None
    description: str | None = None
    severity: str | None = None
    priority: str | None = None
    assignment_group: str | None = None
    affected_region: str | None = None
    customer_impact: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class MCPIncidentAnalysisRequest(BaseModel):
    incident: dict[str, Any]
    dataset_path: str = "data/generated/cyber_mim_incidents.csv"
    resolution_db_path: str = "data/resolution_db/incident_resolution_steps.jsonl"
    similarity_limit: int = 5


class MCPDatasetInspectionRequest(BaseModel):
    payload_uri: str = "fixtures/payloads/incoming-incident-salesforce-sso.json"


class MCPToolResponse(BaseModel):
    ok: bool = True
    result: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)