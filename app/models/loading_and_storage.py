# -----------------------------------------------------------------------------
# Loading and storage
# -----------------------------------------------------------------------------
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.models.incident import HistoricalIncident, IncomingIncident
from app.models.resolution import ResolutionStepRecord


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

        return [self._to_historical_incident(record) for record in records]

    def _to_historical_incident(self, record: dict[str, Any]) -> HistoricalIncident:
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
        return None


class ResolutionDatabase:
    """Tiny JSONL-backed resolution DB.

    This is the MVP local equivalent of a later database table or vector index.
    It stores reusable resolution records extracted from historical incidents and
    newly processed incoming incidents.
    """

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[ResolutionStepRecord]:
        if not self.path.exists():
            return []
        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(ResolutionStepRecord.model_validate_json(line))
        return records

    def upsert_many(self, new_records: list[ResolutionStepRecord]) -> list[ResolutionStepRecord]:
        existing = self.load()
        by_key: dict[str, ResolutionStepRecord] = {
            self._dedupe_key(record): record for record in existing
        }

        for record in new_records:
            key = self._dedupe_key(record)
            if key in by_key:
                existing_record = by_key[key]
                existing_record.times_seen += 1
                existing_record.last_seen_at = record.last_seen_at
                existing_record.confidence = max(existing_record.confidence, record.confidence)
                existing_record.symptoms = sorted(set(existing_record.symptoms + record.symptoms))
                existing_record.resolution_steps = sorted(
                    set(existing_record.resolution_steps + record.resolution_steps)
                )
                existing_record.validation_steps = sorted(
                    set(existing_record.validation_steps + record.validation_steps)
                )
            else:
                by_key[key] = record

        sorted_records = sorted(
            by_key.values(),
            key=lambda r: (
                r.service or "",
                r.category,
                r.kba_id or "",
                -r.times_seen,
                r.resolution_id,
            ),
        )
        self.path.write_text(
            "\n".join(record.model_dump_json() for record in sorted_records)
            + ("\n" if sorted_records else ""),
            encoding="utf-8",
        )
        return sorted_records

    @staticmethod
    def _dedupe_key(record: ResolutionStepRecord) -> str:
        return "|".join(
            [
                (record.service or "unknown").lower(),
                record.category.lower(),
                (record.kba_id or "no-kba").lower(),
                " ".join(record.resolution_steps).lower()[:120],
            ]
        )
