from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.models.incident import HistoricalIncident, IncomingIncident


class HistoricalIncidentLoader:
    """Loads historical incidents from CSV/JSON/JSONL."""

    def load(self, path: str) -> list[HistoricalIncident]:
        suffix = Path(path).suffix.lower()

        if suffix == ".csv":
            df = pd.read_csv(path)
            records = df.where(pd.notnull(df), None).to_dict(orient="records")
        elif suffix == ".json":
            records = json.loads(Path(path).read_text(encoding="utf-8"))
            if isinstance(records, dict):
                records = records.get("incidents", [records])
        elif suffix == ".jsonl":
            records = [
                json.loads(line)
                for line in Path(path).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        else:
            raise ValueError(f"Unsupported historical incident file type: {suffix}")

        return [self._to_incoming_incident(record) for record in records]

    def _to_incoming_incident(self, record: dict[str, Any]) -> HistoricalIncident:
        incident = IncomingIncident.from_any_payload(record)

        return HistoricalIncident(
            incident_id=incident.incident_id
            or str(record.get("incident_id") or record.get("number") or "UNKNOWN"),
            service=incident.service,
            short_description=incident.short_description,
            description=incident.description,
            severity=incident.severity,
            priority=incident.priority,
            assignment_group=incident.assignment_group,
            kba_id=self._first_present(record, ["kba_id", "kb_article", "knowledge_article", "kb"]),
            resolution_notes=self._first_present(
                record, ["resolution_notes", "resolution", "close_notes", "fix"]
            ),
            validation_steps=self._first_present(
                record, ["validation_steps", "validation", "post_checks", "verification"]
            ),
            raw=record,
        )

    @staticmethod
    def _first_present(record: dict[str, Any], keys: list[str]) -> str | None:
        lower_record = {str(k).lower(): v for k, v in record.items()}

        for key in keys:
            value = lower_record.get(key.lower())
            if value is not None and str(value).strip():
                return str(value)
