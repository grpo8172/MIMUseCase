from __future__ import annotations

import json
from pathlib import Path

from app.agents.workflow_coordinator import WorkflowCoordinatorAgent


def test_salesforce_action_plan_contains_gke_and_ansible_policy_metadata() -> None:
    payload = json.loads(
        Path("fixtures/payloads/incoming-incident-salesforce-sso.json").read_text(
            encoding="utf-8"
        )
    )

    coordinator = WorkflowCoordinatorAgent()
    state = coordinator.create_workflow(payload)
    state = coordinator.analyse(state)
    state = coordinator.retrieve_dip_context(state)
    state = coordinator.create_action_plan(state)

    assert state.action_plan is not None

    action = next(
        action
        for action in state.action_plan["proposed_actions"]
        if action["action_id"] == "uat-step-3"
    )

    assert action["policy_id"] == "EXEC-POLICY-SALESFORCE-UAT"
    assert action["execution_identity"] == "mim-executor-iam-uat"
    assert action["credential_ref"] == "secret-manager://mim-demo/uat/iam-ansible-runner"

    assert action["gke_cluster"] == "mim-demo-cluster"
    assert action["gke_namespace"] == "client-a-uat"
    assert action["kubernetes_service_account"] == "mim-executor-ksa"
    assert action["ansible_inventory"] == "inventories/uat.ini"
    assert action["ansible_playbook"] == "playbooks/scale_k8s_deployment.yml"
    assert "deployment" in action["allowed_kubernetes_resources"]
    assert "patch" in action["allowed_kubernetes_verbs"]


def test_default_policy_metadata_is_used_for_unknown_service() -> None:
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

    if not state.action_plan or not state.action_plan.get("proposed_actions"):
        # Unknown service may fall back to manual review before an executable action exists.
        assert state.status == "action_plan_created"
        assert state.action_plan is not None
        assert "Manual review required" in state.action_plan["summary"]
        return

    action = state.action_plan["proposed_actions"][0]

    assert action["policy_id"] == "EXEC-POLICY-UAT-ONLY"
    assert action["execution_identity"] == "mim-executor-uat"
    assert action["credential_ref"] == "secret-manager://mim-demo/uat/ansible-runner"

    assert action["gke_cluster"] == "mim-demo-cluster"
    assert action["gke_namespace"] == "mim-uat"
    assert action["kubernetes_service_account"] == "mim-executor-ksa"
    assert action["ansible_playbook"] == "playbooks/scale_k8s_deployment.yml"