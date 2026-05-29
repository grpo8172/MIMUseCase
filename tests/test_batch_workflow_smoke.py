from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.agents.execution_agent import ExecutionAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.workflow_coordinator import WorkflowCoordinatorAgent


def load_payload(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("payload_path", "historical_incidents_path"),
    [
        (
            "fixtures/payloads/incoming-incident-salesforce-sso.json",
            "data/input/incidents.csv",
        ),
        (
            "fixtures/payloads/incoming-incident-vault-key.json",
            "data/input/incidents.csv",
        ),
        (
            "fixtures/payloads/incoming-incident-pipeline-failure.json",
            "data/input/incidents.csv",
        ),
        (
            "fixtures/payloads/incoming-cyber-app-exploit.json",
            "data/generated/cyber_mim_incidents.csv",
        ),
    ],
)
def test_batch_workflow_handles_payloads_and_transformed_datasets(
    payload_path: str,
    historical_incidents_path: str,
) -> None:
    if not Path(payload_path).exists():
        pytest.skip(f"Missing payload fixture: {payload_path}")

    if not Path(historical_incidents_path).exists():
        pytest.skip(f"Missing historical dataset: {historical_incidents_path}")

    payload = load_payload(payload_path)

    coordinator = WorkflowCoordinatorAgent(
        historical_incidents_path=historical_incidents_path,
    )

    state = coordinator.create_workflow(payload)
    state = coordinator.analyse(state)
    state = coordinator.retrieve_dip_context(state)
    state = coordinator.create_action_plan(state)

    assert state.action_plan is not None
    assert state.status in {"awaiting_approval", "action_plan_created"}

    proposed_actions = state.action_plan.get("proposed_actions", [])

    if not proposed_actions:
        assert "Manual review required" in state.action_plan["summary"]
        return

    approved_action_id = proposed_actions[min(2, len(proposed_actions) - 1)]["action_id"]

    state = coordinator.approve_action(state, approved_action_id)
    state = ExecutionAgent().execute_approved_actions(state)
    state = ValidationAgent().validate(state)

    succeeded = [
        result for result in state.execution.results if result["status"] == "succeeded"
    ]

    assert len(succeeded) == 1
    assert succeeded[0]["action_id"] == approved_action_id
    assert state.validation.status == "passed"
    assert state.status == "validated"
