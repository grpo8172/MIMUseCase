from __future__ import annotations

from app.models.inspection import FeatureLabelRecommendation
from app.models.pipeline import DatasetProfile


class FeatureLabelAgent:
    """Suggests feature/label columns for downstream classifiers or retrieval tasks."""

    LABEL_ROLES = {"severity", "priority", "resolver_group", "kba_id", "root_cause", "status"}
    FEATURE_ROLES = {
        "service",
        "short_description",
        "long_description",
        "free_text",
        "timestamp",
        "feature_candidate",
    }
    EXCLUDE_ROLES = {"identifier"}

    def run(self, profile: DatasetProfile) -> FeatureLabelRecommendation:
        likely_labels: list[str] = []
        likely_features: list[str] = []
        likely_text: list[str] = []
        exclude: list[str] = []
        leakage: list[str] = []

        for column in profile.columns:
            if column.suspected_role in self.LABEL_ROLES:
                likely_labels.append(column.name)
            if column.suspected_role in self.FEATURE_ROLES:
                likely_features.append(column.name)
            if column.suspected_role in {
                "short_description",
                "long_description",
                "free_text",
                "resolution_notes",
            }:
                likely_text.append(column.name)
            if column.suspected_role in self.EXCLUDE_ROLES:
                exclude.append(column.name)

            lower_name = column.name.lower()
            if any(
                token in lower_name
                for token in ["resolution", "root_cause", "kba", "resolved", "close"]
            ):
                leakage.append(
                    f"{column.name}: may leak outcome information if used to predict severity, resolver group, or KBA before resolution."
                )

        if not likely_labels:
            reason = "No strong supervised label found. Start with retrieval/similarity matching and optional clustering."
        else:
            reason = "Candidate labels and features identified from MIM-oriented schema roles. Validate against the business objective before training."

        return FeatureLabelRecommendation(
            likely_label_columns=likely_labels,
            likely_feature_columns=likely_features,
            likely_text_columns=likely_text,
            columns_to_exclude=exclude,
            leakage_risks=leakage,
            reason=reason,
        )
