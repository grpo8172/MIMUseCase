from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalise raw cyber event data into canonical MIM incidents."
    )
    parser.add_argument(
        "--input",
        default="data/raw/gcs/cyber_events_2026-05-23.csv",
        help="Path to raw cyber events CSV.",
    )
    parser.add_argument(
        "--stream-output",
        default="data/generated/cyber_mim_incident_stream.jsonl",
        help="Path to write normalised incidents for queue replay as JSON Lines.",
    )
    parser.add_argument(
        "--output",
        default="data/generated/cyber_mim_incidents.csv",
        help="Path to write normalised canonical incidents CSV.",
    )
    parser.add_argument(
        "--payload-output",
        default="fixtures/payloads/incoming-cyber-app-exploit.json",
        help="Path to write all incoming cyber payload fixture.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional row limit. Use 0 for all rows.",
    )
    return parser.parse_args()


def text(value: Any) -> str:
    if value is None:
        return ""
    value_str = str(value).strip()
    if value_str.lower() in {"nan", "none", "null"}:
        return ""
    return value_str


def choose_cyber_mapping(row: dict[str, str]) -> dict[str, str]:
    event_type = text(row.get("event_type")).lower()
    event_subtype = text(row.get("event_subtype")).lower()
    description = text(row.get("description")).lower()
    org_data = text(row.get("org_data")).lower()
    cust_data = text(row.get("cust_data")).lower()

    combined = " ".join([event_type, event_subtype, description, org_data, cust_data])

    if "application server" in combined or "server" in event_subtype:
        return {
            "category": "cyber_application_exploitation",
            "assignment_group": "Cyber Incident Response Team",
            "kba_id": "KBA-CYBER-001",
            "dip_id": "DIP-CYBER-001",
            "resolution_notes": (
                "Contain affected application/server, preserve evidence, patch exposed "
                "service, rotate affected credentials, and monitor for persistence."
            ),
            "validation_steps": (
                "Confirmed no new exploit attempts, no persistence indicators, patched "
                "service version, and stable application health."
            ),
        }

    if "end host" in combined or "android" in combined or "malware" in combined:
        return {
            "category": "cyber_endpoint_compromise",
            "assignment_group": "Endpoint Security Team",
            "kba_id": "KBA-CYBER-002",
            "dip_id": "DIP-CYBER-002",
            "resolution_notes": (
                "Isolate affected endpoint, preserve forensic evidence, remove malware, "
                "reset credentials, and validate account activity."
            ),
            "validation_steps": (
                "Confirmed endpoint is clean, credentials reset, suspicious sessions "
                "revoked, and no further malicious activity detected."
            ),
        }

    if (
        "stolen data" in combined
        or "leaked" in combined
        or "exposed" in combined
        or "breach" in combined
        or "data" in combined
    ):
        return {
            "category": "cyber_data_exfiltration",
            "assignment_group": "Cyber Incident Response Team",
            "kba_id": "KBA-CYBER-003",
            "dip_id": "DIP-CYBER-003",
            "resolution_notes": (
                "Confirm exposed data scope, preserve evidence, identify access path, "
                "rotate credentials, and coordinate legal/comms review."
            ),
            "validation_steps": (
                "Confirmed exposure scope, closed access path, completed credential "
                "rotation, and attached evidence for legal/comms review."
            ),
        }

    return {
        "category": "cyber_security_triage",
        "assignment_group": "Security Operations",
        "kba_id": "KBA-CYBER-000",
        "dip_id": "DIP-CYBER-000",
        "resolution_notes": (
            "Triage cyber event, gather evidence, identify affected systems, and route "
            "to the appropriate security resolver group."
        ),
        "validation_steps": (
            "Confirmed event classification, affected asset scope, resolver ownership, "
            "and required follow-up actions."
        ),
    }


def infer_severity_priority(row: dict[str, str]) -> tuple[str, str]:
    motive = text(row.get("motive")).lower()
    event_subtype = text(row.get("event_subtype")).lower()
    description = text(row.get("description")).lower()
    cust_data = text(row.get("cust_data")).lower()
    org_data = text(row.get("org_data")).lower()

    combined = " ".join([motive, event_subtype, description, cust_data, org_data])

    high_impact_terms = [
        "stolen",
        "leaked",
        "exposed",
        "ransom",
        "malware",
        "compromised",
        "credential",
        "payment",
        "bank",
        "financial",
    ]

    if any(term in combined for term in high_impact_terms):
        return "SEV2", "P2"

    if "exploit" in combined or "exploitation" in combined:
        return "SEV2", "P2"

    return "SEV3", "P3"


def normalise_row(row: dict[str, str]) -> dict[str, str]:
    mapping = choose_cyber_mapping(row)
    severity, priority = infer_severity_priority(row)

    source_id = text(row.get("slug"))
    organization = text(row.get("organization")) or "Unknown Organization"
    event_subtype = text(row.get("event_subtype")) or "Cyber security event"
    description = text(row.get("description"))
    org_data = text(row.get("org_data"))
    cust_data = text(row.get("cust_data"))

    details = " ".join(part for part in [description, org_data, cust_data] if part)

    return {
        "incident_id": source_id,
        "source_type": "cyber_events",
        "source_id": source_id,
        "opened_at": text(row.get("event_date")) or text(row.get("reported_date")),
        "service": organization,
        "category": mapping["category"],
        "short_description": event_subtype,
        "description": details or event_subtype,
        "severity": severity,
        "priority": priority,
        "assignment_group": mapping["assignment_group"],
        "kba_id": mapping["kba_id"],
        "dip_id": mapping["dip_id"],
        "resolution_notes": mapping["resolution_notes"],
        "validation_steps": mapping["validation_steps"],
        "actor": text(row.get("actor")),
        "actor_type": text(row.get("actor_type")),
        "motive": text(row.get("motive")),
        "event_type": text(row.get("event_type")),
        "event_subtype": event_subtype,
        "industry": text(row.get("industry")),
        "country": text(row.get("country")),
        "source_url": text(row.get("source_url")),
        "raw_slug": source_id,
    }


def read_rows(path: Path, limit: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for index, row in enumerate(reader):
            if limit and index >= limit:
                break
            rows.append({key: text(value) for key, value in row.items()})

    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        raise RuntimeError("No rows to write.")

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_payload_fixture(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    app_exploit = next(
        (row for row in rows if row["category"] == "cyber_application_exploitation"),
        rows[0],
    )

    payload = {
        "incident_id": f"CYBER-INCOMING-{app_exploit['incident_id']}",
        "source_type": "manual_payload",
        "opened_at": app_exploit["opened_at"],
        "service": app_exploit["service"],
        "short_description": app_exploit["short_description"],
        "description": app_exploit["description"],
        "severity": app_exploit["severity"],
        "priority": app_exploit["priority"],
        "assignment_group": "Unknown",
        "actor_type": app_exploit["actor_type"],
        "motive": app_exploit["motive"],
        "event_type": app_exploit["event_type"],
        "event_subtype": app_exploit["event_subtype"],
        "industry": app_exploit["industry"],
        "country": app_exploit["country"],
    }

    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    payload_output_path = Path(args.payload_output)

    raw_rows = read_rows(input_path, args.limit)
    normalised_rows = [normalise_row(row) for row in raw_rows if text(row.get("slug"))]

    write_csv(output_path, normalised_rows)
    write_payload_fixture(payload_output_path, normalised_rows)

    print(f"Read {len(raw_rows)} raw rows from {input_path}")
    print(f"Wrote {len(normalised_rows)} normalised incidents to {output_path}")
    print(f"Wrote incoming cyber payload fixture to {payload_output_path}")


if __name__ == "__main__":
    main()
