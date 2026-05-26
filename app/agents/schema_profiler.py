from __future__ import annotations

import json
import statistics
from typing import Any

import pandas as pd

from app.models.pipeline import ColumnProfile, ColumnRole, DatasetProfile


class SchemaProfilerAgent:
    """Deterministically profiles a dataframe before any LLM call."""

    ROLE_KEYWORDS: list[tuple[ColumnRole, list[str]]] = [
        ("incident_id", ["incident", "inc", "ticket", "case", "number"]),
        ("timestamp", ["time", "date", "opened", "created", "updated", "resolved"]),
        ("service", ["service", "application", "system", "platform", "ci", "cmdb"]),
        ("short_description", ["short_description", "summary", "title", "subject"]),
        ("long_description", ["description", "details", "notes", "symptom"]),
        ("severity", ["severity", "sev", "impact"]),
        ("priority", ["priority", "urgency"]),
        ("status", ["status", "state"]),
        ("resolver_group", ["assignment_group", "resolver", "team", "owner"]),
        ("kba_id", ["kba", "kb", "knowledge", "article"]),
        ("root_cause", ["root_cause", "cause", "rca"]),
        ("resolution_notes", ["resolution", "resolved_by", "close_notes", "fix"]),
        ("validation_steps", ["validation", "verify", "verification", "post_check"]),
    ]

    def run(self, df: pd.DataFrame, source_uri: str, sample_rows: int = 5) -> DatasetProfile:
        warnings: list[str] = []

        if df.empty:
            warnings.append("Dataset is empty.")

        if df.shape[1] == 0:
            warnings.append("Dataset has no columns.")

        columns = [self._profile_column(df, column) for column in df.columns]
        sample_records = self._safe_records(df.head(sample_rows))

        return DatasetProfile(
            source_uri=source_uri,
            row_count=int(df.shape[0]),
            column_count=int(df.shape[1]),
            columns=columns,
            sample_records=sample_records,
            warnings=warnings,
        )

    def _profile_column(self, df: pd.DataFrame, column: str) -> ColumnProfile:
        series = df[column]
        non_null = series.dropna()
        row_count = len(series)
        unique_count = int(non_null.nunique(dropna=True))
        null_count = int(series.isna().sum())
        sample_values = [self._stringify(v) for v in non_null.head(5).tolist()]

        min_value = None
        max_value = None
        mean_value = None

        if pd.api.types.is_numeric_dtype(series):
            try:
                min_value = self._stringify(non_null.min()) if not non_null.empty else None
                max_value = self._stringify(non_null.max()) if not non_null.empty else None
                mean_value = float(non_null.mean()) if not non_null.empty else None
            except Exception:
                pass
        elif pd.api.types.is_datetime64_any_dtype(series):
            try:
                min_value = self._stringify(non_null.min()) if not non_null.empty else None
                max_value = self._stringify(non_null.max()) if not non_null.empty else None
            except Exception:
                pass

        suspected_role = self._infer_role(column, series, unique_count, row_count)

        return ColumnProfile(
            name=str(column),
            dtype=str(series.dtype),
            non_null_count=int(non_null.shape[0]),
            null_count=null_count,
            null_ratio=round(null_count / row_count, 4) if row_count else 0.0,
            unique_count=unique_count,
            unique_ratio=round(unique_count / max(row_count, 1), 4),
            sample_values=sample_values,
            min_value=min_value,
            max_value=max_value,
            mean_value=mean_value,
            suspected_role=suspected_role,
        )

    def _infer_role(
        self, column: str, series: pd.Series, unique_count: int, row_count: int
    ) -> ColumnRole:
        col = column.lower().replace(" ", "_").replace("-", "_")

        for role, keywords in self.ROLE_KEYWORDS:
            if any(keyword in col for keyword in keywords):
                return role

        if row_count > 0 and unique_count / row_count > 0.95:
            return "identifier"

        if series.dtype == "object":
            avg_len = self._average_text_length(series.dropna().astype(str).head(50).tolist())
            if avg_len > 80:
                return "free_text"

        return "feature_candidate"

    @staticmethod
    def _average_text_length(values: list[str]) -> float:
        if not values:
            return 0.0
        return statistics.mean(len(v) for v in values)

    @staticmethod
    def _safe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
        clean = df.where(pd.notnull(df), None)
        return json.loads(clean.to_json(orient="records", date_format="iso"))

    @staticmethod
    def _stringify(value: Any) -> str:
        text = str(value)
        return text[:250] + "..." if len(text) > 250 else text
