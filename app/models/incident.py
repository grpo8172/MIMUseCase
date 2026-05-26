# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

MIMClassification = Literal[
    "normal_mim",
    "major_mim",
    "global_major_mim",
    "not_mim",
    "unknown",
]

SeenBeforeStatus = Literal[
    "seen_before",
    "possibly_seen_before",
    "not_seen_before",
]


class IncomingIncident(BaseModel):
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

    @classmethod
    def from_any_payload(cls, payload: dict[str, Any]) -> IncomingIncident:
        """Maps common incident field aliases into the normalised model."""
        aliases = {
            "incident_id": ["incident_id", "number", "ticket_number", "case_id", "id"],
            "opened_at": [
                "opened_at",
                "created_at",
                "created",
                "opened",
                "timestamp",
                "event_time",
            ],
            "service": [
                "service",
                "business_service",
                "application",
                "app",
                "system",
                "cmdb_ci",
                "ci_name",
            ],
            "short_description": [
                "short_description",
                "summary",
                "title",
                "subject",
                "alert_title",
            ],
            "description": ["description", "details", "notes", "alert_description", "symptoms"],
            "severity": ["severity", "sev", "impact", "criticality"],
            "priority": ["priority", "urgency"],
            "assignment_group": ["assignment_group", "resolver_group", "team", "owner_group"],
            "affected_region": ["affected_region", "region", "geo", "location"],
            "customer_impact": ["customer_impact", "impact_summary", "business_impact"],
        }

        normalised: dict[str, Any] = {"raw": payload}
        lower_payload = {str(k).lower(): v for k, v in payload.items()}

        for target, source_names in aliases.items():
            for source_name in source_names:
                if source_name.lower() in lower_payload:
                    normalised[target] = lower_payload[source_name.lower()]
                    break

        return cls.model_validate(normalised)

    def searchable_text(self) -> str:
        parts = [
            self.service,
            self.short_description,
            self.description,
            self.severity,
            self.priority,
            self.affected_region,
            self.customer_impact,
        ]
        return " ".join(str(part) for part in parts if part)


class HistoricalIncident(BaseModel):
    incident_id: str
    service: str | None = None
    short_description: str | None = None
    description: str | None = None
    severity: str | None = None
    priority: str | None = None
    assignment_group: str | None = None
    kba_id: str | None = None
    resolution_notes: str | None = None
    validation_steps: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
    affected_region: str | None = None
    customer_impact: str | None = None

    def searchable_text(self) -> str:
        parts = [
            self.service,
            self.short_description,
            self.description,
            self.severity,
            self.priority,
        ]
        return " ".join(str(part) for part in parts if part)


class SimilarIncidentMatch(BaseModel):
    incident_id: str
    similarity_score: float
    service: str | None = None
    short_description: str | None = None
    severity: str | None = None
    priority: str | None = None
    assignment_group: str | None = None
    kba_id: str | None = None
    resolution_notes: str | None = None
    validation_steps: str | None = None


class ResolutionStepRecord(BaseModel):
    resolution_id: str
    source_incident_id: str
    service: str | None = None
    category: str = "general_it_operations"
    mim_level: MIMClassification = "unknown"
    kba_id: str | None = None
    resolver_group: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    resolution_steps: list[str] = Field(default_factory=list)
    validation_steps: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    first_seen_at: str
    last_seen_at: str
    times_seen: int = 1


class IncidentAnalysisResult(BaseModel):
    incoming_incident: IncomingIncident
    mim_classification: MIMClassification
    mim_confidence: float
    seen_before_status: SeenBeforeStatus
    similar_incidents: list[SimilarIncidentMatch]
    recommended_kba_id: str | None = None
    recommended_resolver_group: str | None = None
    recommended_resolution_steps: list[str]
    recommended_validation_steps: list[str]
    resolution_db_updates: list[ResolutionStepRecord]
    notes: list[str] = Field(default_factory=list)
