from __future__ import annotations

from pathlib import Path

from app.models.resolution import ResolutionStepRecord


class ResolutionDatabase:
    """JSONL-backed storage for reusable incident resolution records.

    This is the local MVP version of what could later become Firestore,
    BigQuery, Cloud SQL, MongoDB, or a vector database.
    """

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[ResolutionStepRecord]:
        """Load all known resolution records from the JSONL file."""
        if not self.path.exists():
            return []

        records: list[ResolutionStepRecord] = []

        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(ResolutionStepRecord.model_validate_json(line))

        return records

    def upsert_many(self, new_records: list[ResolutionStepRecord]) -> list[ResolutionStepRecord]:
        """Insert or merge resolution records, then persist the sorted DB."""
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
            key=lambda record: (
                record.service or "",
                record.category,
                record.kba_id or "",
                -record.times_seen,
                record.resolution_id,
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
        """Build a rough stable key so repeated incidents update the same resolution record."""
        return "|".join(
            [
                (record.service or "unknown").lower(),
                record.category.lower(),
                (record.kba_id or "no-kba").lower(),
                " ".join(record.resolution_steps).lower()[:120],
            ]
        )
