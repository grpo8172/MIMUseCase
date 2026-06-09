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


def test_cyber_transformed_dataset_creates_kba_dip_action_plan() -> None:
    payload_path = Path("fixtures/payloads/incoming-cyber-app-exploit.json")
    dataset_path = Path("data/generated/cyber_mim_incidents.csv")

    if not payload_path.exists():
        pytest.skip("Cyber payload fixture has not been generated yet.")

    if not dataset_path.exists():
        pytest.skip("Cyber normalised dataset has not been generated yet.")

    payload = load_payload(str(payload_path))

    coordinator = WorkflowCoordinatorAgent(
        dataset_path=str(dataset_path),
    )

    state = coordinator.create_workflow(payload)
    state = coordinator.analyse(state)
    state = coordinator.retrieve_dip_context(state)
    state = coordinator.create_action_plan(state)

    assert state.analysis.recommended_kba_id is not None
    assert state.analysis.recommended_kba_id.startswith("KBA-CYBER-")
    assert state.context.matched_dips
    assert state.context.matched_dips[0]["dip_id"].startswith("DIP-CYBER-")
    assert state.action_plan is not None
    assert state.action_plan["proposed_actions"]
    assert state.status == "awaiting_approval"


def test_cyber_transformed_dataset_executes_only_approved_action() -> None:
    payload_path = Path("fixtures/payloads/incoming-cyber-app-exploit.json")
    dataset_path = Path("data/generated/cyber_mim_incidents.csv")

    if not payload_path.exists():
        pytest.skip("Cyber payload fixture has not been generated yet.")

    if not dataset_path.exists():
        pytest.skip("Cyber normalised dataset has not been generated yet.")

    payload = load_payload(str(payload_path))

    coordinator = WorkflowCoordinatorAgent(
        dataset_path=str(dataset_path),
    )

    state = coordinator.create_workflow(payload)
    state = coordinator.analyse(state)
    state = coordinator.retrieve_dip_context(state)
    state = coordinator.create_action_plan(state)

    assert state.action_plan is not None
    assert state.action_plan["proposed_actions"]

    approved_action_id = state.action_plan["proposed_actions"][2]["action_id"]

    state = coordinator.approve_action(state, approved_action_id)
    state = ExecutionAgent().execute_approved_actions(state)
    state = ValidationAgent().validate(state)

    succeeded = [
        result for result in state.execution.results if result["status"] == "succeeded"
    ]
    skipped = [
        result for result in state.execution.results if result["status"] == "skipped"
    ]

    assert len(succeeded) == 1
    assert succeeded[0]["action_id"] == approved_action_id
    assert skipped
    assert state.validation.status == "passed"
    assert state.status == "validated"
