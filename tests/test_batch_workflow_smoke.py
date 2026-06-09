from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.agents.execution_agent import ExecutionAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.workflow_coordinator import WorkflowCoordinatorAgent


def load_payload(path: str) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as payload_file:
        return json.load(payload_file)


def test_salesforce_sso_happy_path_executes_uat_steps_in_order() -> None:
    payload = load_payload("fixtures/payloads/incoming-incident-salesforce-sso.json")

    coordinator = WorkflowCoordinatorAgent(
        dataset_path="data/generated/cyber_mim_incidents.csv",
    )

    state = coordinator.create_workflow(payload)
    state = coordinator.analyse(state)
    state = coordinator.retrieve_dip_context(state)
    state = coordinator.create_action_plan(state)

    for action_id in [
        "uat-step-1",
        "uat-step-2",
        "uat-step-3",
        "uat-step-4",
    ]:
        state = coordinator.approve_action(state, action_id)
        state = ExecutionAgent().execute_approved_actions(state)

    state = ValidationAgent().validate(state)

    results = workflow["execution"]["results"]

    succeeded_action_ids = {
        result["action_id"] for result in results if result["status"] == "succeeded"
    }

    assert {
        "uat-step-1",
        "uat-step-2",
        "uat-step-3",
        "uat-step-4",
    }.issubset(succeeded_action_ids)

    assert state.validation.status == "passed"


def test_salesforce_step_3_can_be_rolled_back_with_separate_approval() -> None:
    payload = load_payload("fixtures/payloads/incoming-incident-salesforce-sso.json")

    coordinator = WorkflowCoordinatorAgent(
        dataset_path="data/generated/cyber_mim_incidents.csv",
    )

    state = coordinator.create_workflow(payload)
    state = coordinator.analyse(state)
    state = coordinator.retrieve_dip_context(state)
    state = coordinator.create_action_plan(state)

    state = coordinator.approve_action(state, "uat-step-3")
    state = ExecutionAgent().execute_approved_actions(state)

    state = coordinator.create_rollback_action_plan(
        state=state,
        action_id="uat-step-3",
    )

    rollback_actions = [
        action
        for action in state.action_plan["proposed_actions"]
        if action["action_id"] == "rollback-uat-step-3"
    ]

    assert len(rollback_actions) == 1
    assert state.status == "awaiting_rollback_approval"

    state = coordinator.approve_action(
        state,
        "rollback-uat-step-3",
    )

    state = ExecutionAgent().execute_approved_actions(state)

    succeeded_action_ids = [
        result["action_id"] for result in state.execution.results if result["status"] == "succeeded"
    ]

    assert "rollback-uat-step-3" in succeeded_action_ids
    assert state.status in {
        "rollback_completed",
        "rollback_validated",
    }


def test_rollback_does_not_reexecute_forward_step_3() -> None:
    coordinator = build_test_coordinator()

    state = build_initial_state()

    # Run the forward UAT workflow first.
    state = coordinator.process(state)

    step_3_results_before = [
        result for result in state.execution.results if result["action_id"] == "uat-step-3"
    ]

    assert len(step_3_results_before) == 1
    assert step_3_results_before[0]["status"] == "succeeded"

    # Approve and execute only the rollback action.
    state.execution.approved_action_ids.append("rollback-uat-step-3")
    state = coordinator.process(state)

    step_3_results_after = [
        result for result in state.execution.results if result["action_id"] == "uat-step-3"
    ]

    rollback_results = [
        result for result in state.execution.results if result["action_id"] == "rollback-uat-step-3"
    ]

    # The original action must not be executed for a second time.
    assert len(step_3_results_after) == len(step_3_results_before)
    assert len(rollback_results) == 1
