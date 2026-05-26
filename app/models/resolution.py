from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.incident import MIMClassification, SeenBeforeStatus


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
    incoming_incident: object
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


class IncidentClassificationFinding(BaseModel):
    likely_incident_domain: str = "unknown"
    likely_service_columns: list[str] = Field(default_factory=list)
    likely_kba_columns: list[str] = Field(default_factory=list)
    likely_resolver_group_columns: list[str] = Field(default_factory=list)
    likely_resolution_columns: list[str] = Field(default_factory=list)
    seen_before_matching_possible: bool = False
    kba_recommendation_possible: bool = False
    validation_possible: bool = False
    gaps: list[str] = Field(default_factory=list)
