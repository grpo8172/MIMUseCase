# -----------------------------------------------------------------------------
# Types and structured models
# -----------------------------------------------------------------------------
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

try:
    from google.cloud import pubsub_v1
except ImportError:
    pubsub_v1 = None


MIMLevel = Literal["normal_mim", "major_mim", "global_major_mim", "unknown"]
ClientSize = Literal["small", "medium", "enterprise", "unknown"]
TaskType = Literal[
    "known_issue_matching",
    "kba_recommendation",
    "resolver_group_classification",
    "severity_classification",
    "root_cause_assistance",
    "validation_recommendation",
    "data_quality_only",
    "unknown",
]
ColumnRole = Literal[
    "incident_id",
    "timestamp",
    "service",
    "short_description",
    "long_description",
    "severity",
    "priority",
    "status",
    "resolver_group",
    "kba_id",
    "root_cause",
    "resolution_notes",
    "validation_steps",
    "label_candidate",
    "feature_candidate",
    "identifier",
    "free_text",
    "ignore",
    "unknown",
]


class PipelineContext(BaseModel):
    domain: str = "major_incident_management"
    client_size: ClientSize = "unknown"
    target_use_cases: list[TaskType] = Field(default_factory=list)
    notes: str = ""


class PipelineJob(BaseModel):
    job_id: str = "manual-run"
    dataset_uri: str
    output_uri: str | None = None
    context: PipelineContext = Field(default_factory=PipelineContext)
    max_sample_rows: int = 5
    llm_enabled: bool = True


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    non_null_count: int
    null_count: int
    null_ratio: float
    unique_count: int
    unique_ratio: float
    sample_values: list[str] = Field(default_factory=list)
    min_value: str | None = None
    max_value: str | None = None
    mean_value: float | None = None
    suspected_role: ColumnRole = "unknown"


class DatasetProfile(BaseModel):
    source_uri: str
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    sample_records: list[dict[str, Any]]
    warnings: list[str] = Field(default_factory=list)


class UseCaseFinding(BaseModel):
    use_case_name: str = "unknown"
    mim_level: MIMLevel = "unknown"
    task_type: TaskType = "unknown"
    business_context: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""


class FeatureLabelRecommendation(BaseModel):
    likely_label_columns: list[str] = Field(default_factory=list)
    likely_feature_columns: list[str] = Field(default_factory=list)
    likely_text_columns: list[str] = Field(default_factory=list)
    columns_to_exclude: list[str] = Field(default_factory=list)
    leakage_risks: list[str] = Field(default_factory=list)
    reason: str = ""
