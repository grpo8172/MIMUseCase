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



