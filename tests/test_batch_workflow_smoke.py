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


def build_test_coordinator() -> WorkflowCoordinatorAgent:
    return WorkflowCoordinatorAgent(
        dataset_path="data/generated/cyber_mim_incidents.csv",
    )


def build_initial_state():
    payload = load_payload(
        "fixtures/payloads/incoming-incident-salesforce-sso.json"
    )

    coordinator = build_test_coordinator()

    state = coordinator.create_workflow(payload)
    state = coordinator.analyse(state)
    state = coordinator.retrieve_dip_context(state)
    state = coordinator.create_action_plan(state)

    return coordinator, state


def test_salesforce_sso_happy_path_executes_uat_steps_in_order() -> None:
    coordinator, state = build_initial_state()
    execution_agent = ExecutionAgent()

    for action_id in [
        "uat-step-1",
        "uat-step-2",
        "uat-step-3",
        "uat-step-4",
    ]:
        state = coordinator.approve_action(state, action_id)
        state = execution_agent.execute_approved_actions(state)

    state = ValidationAgent().validate(state)

    succeeded_action_ids = {
        result["action_id"]
        for result in state.execution.results
        if result["status"] == "succeeded"
    }

    assert {
        "uat-step-1",
        "uat-step-2",
        "uat-step-3",
        "uat-step-4",
    }.issubset(succeeded_action_ids)

    assert state.validation.status == "passed"


def test_salesforce_step_3_can_be_rolled_back_with_separate_approval() -> None:
    coordinator, state = build_initial_state()
    execution_agent = ExecutionAgent()

    state = coordinator.approve_action(state, "uat-step-3")
    state = execution_agent.execute_approved_actions(state)

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

    state = coordinator.approve_action(state, "rollback-uat-step-3")
    state = execution_agent.execute_approved_actions(state)

    succeeded_action_ids = {
        result["action_id"]
        for result in state.execution.results
        if result["status"] == "succeeded"
    }

    assert "rollback-uat-step-3" in succeeded_action_ids
    assert state.status in {
        "rollback_completed",
        "rollback_validated",
    }


def test_rollback_does_not_reexecute_forward_step_3() -> None:
    coordinator, state = build_initial_state()
    execution_agent = ExecutionAgent()

    # Execute the forward action once.
    state = coordinator.approve_action(state, "uat-step-3")
    state = execution_agent.execute_approved_actions(state)

    step_3_results_before = [
        result
        for result in state.execution.results
        if result["action_id"] == "uat-step-3"
        and result["status"] == "succeeded"
    ]

    assert len(step_3_results_before) == 1

    # Create, approve, and execute the separate rollback action.
    state = coordinator.create_rollback_action_plan(
        state=state,
        action_id="uat-step-3",
    )
    state = coordinator.approve_action(state, "rollback-uat-step-3")
    state = execution_agent.execute_approved_actions(state)

    step_3_results_after = [
        result
        for result in state.execution.results
        if result["action_id"] == "uat-step-3"
        and result["status"] == "succeeded"
    ]

    rollback_results = [
        result
        for result in state.execution.results
        if result["action_id"] == "rollback-uat-step-3"
        and result["status"] == "succeeded"
    ]

    # The forward action must not run again during rollback.
    assert len(step_3_results_after) == len(step_3_results_before)
    assert len(rollback_results) == 1