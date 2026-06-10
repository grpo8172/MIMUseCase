from __future__ import annotations

import json
from pathlib import Path

from app.agents.workflow_coordinator import WorkflowCoordinatorAgent


def load_payload(path: str) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as payload_file:
        return json.load(payload_file)

def test_unknown_service_requires_manual_review() -> None:
    payload = {
        "incident_id": "INC-UNKNOWN-001",
        "opened_at": "2026-05-29T00:00:00Z",
        "service": "Unknown Service",
        "short_description": "Generic incident requiring manual triage",
        "description": "Generic outage with insufficient context",
        "severity": "SEV2",
        "priority": "P2",
        "assignment_group": "Unknown",
    }

    coordinator = WorkflowCoordinatorAgent()
    state = coordinator.create_workflow(payload)
    state = coordinator.analyse(state)
    state = coordinator.retrieve_dip_context(state)
    state = coordinator.create_action_plan(state)

    assert state.action_plan is not None
    assert not state.action_plan.get("proposed_actions")
    assert "Manual review required" in state.action_plan["summary"]
    assert state.status == "action_plan_created"