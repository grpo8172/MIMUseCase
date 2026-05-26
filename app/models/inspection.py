# from __future__ import annotations

# from pydantic import BaseModel, Field

# from app.models.pipeline import DatasetProfile


# class InspectionResult(BaseModel):
#     job_id: str
#     dataset_profile: DatasetProfile
#     use_case: UseCaseFinding
#     incident_classification: IncidentClassificationFinding
#     feature_label_recommendation: FeatureLabelRecommendation
#     recommended_next_steps: list[str]
#     agent_notes: list[str] = Field(default_factory=list)

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.pipeline import DatasetProfile, MIMLevel, TaskType


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


class InspectionResult(BaseModel):
    job_id: str
    dataset_profile: DatasetProfile
    use_case: UseCaseFinding
    incident_classification: IncidentClassificationFinding
    feature_label_recommendation: FeatureLabelRecommendation
    recommended_next_steps: list[str]
    agent_notes: list[str] = Field(default_factory=list)
