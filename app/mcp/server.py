from __future__ import annotations

import json
from pathlib import Path

from app.mcp.schemas import MCPIncidentAnalysisRequest
from app.mcp.tools import analyse_incident


def main() -> None:
    """Local smoke-test entry point for MCP-style tools.

    Later this file can become the actual MCP server registration layer.
    """

    demo_path = Path("fixtures/payloads/incoming-incident-salesforce-sso.json")

    request = MCPIncidentAnalysisRequest(
        incident=json.loads(demo_path.read_text(encoding="utf-8")),
        dataset_path="data/generated/cyber_mim_incidents.csv",
        resolution_db_path="data/resolution_db/incident_resolution_steps.jsonl",
    )

    response = analyse_incident(request)
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    main()