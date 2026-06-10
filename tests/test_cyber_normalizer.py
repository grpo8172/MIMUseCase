from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from scripts.normalize_cyber_events import main as normalize_cyber_events_main


def load_payload(path: str) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as payload_file:
        return json.load(payload_file)

def test_cyber_normalizer_creates_canonical_incidents_and_payload(
    tmp_path,
    monkeypatch,
) -> None:
    output_path = tmp_path / "cyber_mim_incidents.csv"
    payload_path = tmp_path / "incoming-cyber-app-exploit.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "normalize_cyber_events.py",
            "--input",
            "data/raw/gcs/cyber_events_2026-05-23.csv",
            "--output",
            str(output_path),
            "--payload-output",
            str(payload_path),
            "--limit",
            "50",
        ],
    )

    normalize_cyber_events_main()

    assert output_path.exists()
    assert payload_path.exists()

    with output_path.open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    assert rows
    assert len(rows) <= 50

    required_columns = {
        "incident_id",
        "source_type",
        "source_id",
        "opened_at",
        "service",
        "category",
        "short_description",
        "description",
        "severity",
        "priority",
        "assignment_group",
        "kba_id",
        "dip_id",
        "resolution_notes",
        "validation_steps",
    }

    assert required_columns.issubset(rows[0].keys())

    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    assert payload["incident_id"].startswith("CYBER-INCOMING-")
    assert payload["service"]
    assert payload["description"]
    assert payload["severity"] in {"SEV1", "SEV2", "SEV3"}
    assert payload["priority"] in {"P1", "P2", "P3"}
