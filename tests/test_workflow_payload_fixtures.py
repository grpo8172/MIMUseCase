from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.agents.workflow_coordinator import WorkflowCoordinatorAgent


def load_payload_fixture(name: str) -> dict[str, Any]:
    path = Path("fixtures/payloads") / name
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "fixture_name",
    [
        "incoming-incident-salesforce-sso.json",
        "incoming-incident-vault-key.json",
        "incoming-incident-pipeline-failure.json",
    ],
)
def test_workflow_handles_payload_fixture_dynamically(
    fixture_name: str,
) -> None:
    payload = load_payload_fixture(fixture_name)

    coordinator = WorkflowCoordinatorAgent(
        dataset_path="data/generated/cyber_mim_incidents.csv",
    )
    state = coordinator.create_workflow(payload)
    state = coordinator.analyse(state)
    state = coordinator.retrieve_dip_context(state)
    state = coordinator.create_action_plan(state)

    assert state.analysis.mim_classification is not None
    assert state.status in {"awaiting_approval", "action_plan_created"}

    if state.analysis.recommended_kba_id:
        assert state.action_plan is not None

        if state.context.matched_dips:
            assert state.action_plan["status"] == "awaiting_human_approval"
            assert state.action_plan["proposed_actions"]
            assert state.status == "awaiting_approval"
        else:
            assert state.action_plan["status"] == "awaiting_human_approval"
            assert "Manual review required" in state.action_plan["summary"]
            assert state.status == "action_plan_created"
    else:
        assert not state.context.matched_dips
        assert state.action_plan is not None
        assert "Manual review required" in state.action_plan["summary"]
        assert state.status == "action_plan_created"


def test_only_manually_approved_action_executes() -> None:
    from app.agents.execution_agent import ExecutionAgent
    from app.agents.validation_agent import ValidationAgent

    payload = load_payload_fixture("incoming-incident-salesforce-sso.json")

    coordinator = WorkflowCoordinatorAgent()
    state = coordinator.create_workflow(payload)
    state = coordinator.analyse(state)
    state = coordinator.retrieve_dip_context(state)
    state = coordinator.create_action_plan(state)

    state = coordinator.approve_action(state, "uat-step-3")
    state = ExecutionAgent().execute_approved_actions(state)
    state = ValidationAgent().validate(state)

    succeeded = [result for result in state.execution.results if result["status"] == "succeeded"]
    skipped = [result for result in state.execution.results if result["status"] == "skipped"]

    assert len(succeeded) == 1
    assert succeeded[0]["action_id"] == "uat-step-3"
    assert skipped
    assert state.validation.status == "passed"
    assert state.status == "validated"
