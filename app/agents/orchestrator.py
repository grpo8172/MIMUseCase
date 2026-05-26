from __future__ import annotations

from app.models.inspection import (
    FeatureLabelRecommendation,
    IncidentClassificationFinding,
    InspectionResult,
    UseCaseFinding,
)
from app.models.pipeline import DatasetProfile, PipelineJob


class InspectionOrchestratorAgent:
    """Combines all agent findings into recommended next implementation steps."""

    def run(
        self,
        job: PipelineJob,
        profile: DatasetProfile,
        use_case: UseCaseFinding,
        incident: IncidentClassificationFinding,
        features: FeatureLabelRecommendation,
    ) -> InspectionResult:
        steps: list[str] = []
        notes: list[str] = []

        if profile.warnings:
            steps.append("Fix dataset quality warnings before using this file for recommendations.")

        if incident.seen_before_matching_possible:
            steps.append(
                "Build a similarity index over incident description fields for seen-before matching."
            )
        else:
            steps.append(
                "Add or map an incident description field before building seen-before matching."
            )

        if incident.kba_recommendation_possible:
            steps.append(
                "Create a KBA retrieval index using KBA title, symptoms, causes, resolution steps, and validation steps."
            )
        else:
            steps.append(
                "Create a synthetic KBA database because the current dataset does not contain enough explicit KBA signal."
            )

        if incident.validation_possible:
            steps.append("Extract validation steps into a reusable validation playbook table.")
        else:
            steps.append(
                "Generate validation playbooks from synthetic KBAs and attach them to recommendation output."
            )

        if features.likely_label_columns:
            steps.append(
                "Train small baseline classifiers for resolver group, KBA, severity, or status using the recommended label candidates."
            )
        else:
            steps.append(
                "Start with RAG/similarity retrieval before supervised model training because no clear label was detected."
            )

        if features.leakage_risks:
            notes.append(
                "Some columns may leak post-resolution information and should be excluded from pre-resolution predictions."
            )

        return InspectionResult(
            job_id=job.job_id,
            dataset_profile=profile,
            use_case=use_case,
            incident_classification=incident,
            feature_label_recommendation=features,
            recommended_next_steps=steps,
            agent_notes=notes,
        )
