from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.agents.execution_agent import ExecutionAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.workflow_coordinator import WorkflowCoordinatorAgent


def load_payload(path: str) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as payload_file:
        return json.load(payload_file)

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

