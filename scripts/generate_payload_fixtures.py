from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tests.factories.incident_factory import (
    build_pipeline_failure_payload,
    build_salesforce_sso_payload,
    build_vault_key_payload,
)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    fixture_dir = Path("fixtures/payloads")

    write_json(
        fixture_dir / "incoming-incident-salesforce-sso.json",
        build_salesforce_sso_payload(incident_id="INC9999"),
    )

    write_json(
        fixture_dir / "incoming-incident-vault-key.json",
        build_vault_key_payload(incident_id="INC1000"),
    )

    write_json(
        fixture_dir / "incoming-incident-pipeline-failure.json",
        build_pipeline_failure_payload(incident_id="INC1001"),
    )

    print(f"Wrote payload fixtures to {fixture_dir}")


if __name__ == "__main__":
    main()
