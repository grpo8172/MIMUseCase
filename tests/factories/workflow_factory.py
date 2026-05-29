from __future__ import annotations

from typing import Any

from app.models.workflow_state import (
    WorkflowAnalysis,
    WorkflowContext,
    WorkflowIncident,
    WorkflowState,
)
from tests.factories.incident_factory import build_incident_payload


def build_workflow_state(
    workflow_id: str = "WF-INC9999",
    incident_payload: dict[str, Any] | None = None,
    status: str = "created",
) -> WorkflowState:
    """Build a basic workflow state from an incident payload."""

    payload = incident_payload or build_incident_payload()

    symptoms = [
        value
        for value in [
            payload.get("short_description"),
            payload.get("description"),
            payload.get("customer_impact"),
        ]
        if isinstance(value, str) and value
    ]

    return WorkflowState(
        workflow_id=workflow_id,
        status=status,  # type: ignore[arg-type]
        incident=WorkflowIncident(
            incident_id=payload.get("incident_id"),  # type: ignore[arg-type]
            service=payload.get("service"),  # type: ignore[arg-type]
            short_description=payload.get("short_description"),  # type: ignore[arg-type]
            description=payload.get("description"),  # type: ignore[arg-type]
            severity=payload.get("severity"),  # type: ignore[arg-type]
            priority=payload.get("priority"),  # type: ignore[arg-type]
            symptoms=symptoms,
            raw=payload,
        ),
    )


def build_analysed_workflow_state(
    recommended_kba_id: str = "KBA-MIM-001",
    recommended_resolver_group: str = "IAM Platform Team",
    mim_classification: str = "global_major_mim",
    mim_confidence: float = 0.81,
    seen_before_status: str = "seen_before",
) -> WorkflowState:
    """Build a workflow state as if incident analysis has already completed."""

    state = build_workflow_state(status="incident_analysed")
    state.analysis = WorkflowAnalysis(
        mim_classification=mim_classification,
        mim_confidence=mim_confidence,
        seen_before_status=seen_before_status,
        recommended_kba_id=recommended_kba_id,
        recommended_resolver_group=recommended_resolver_group,
        recommended_resolution_steps=[
            "Updated SAML metadata and activated correct certificate"
        ],
        recommended_validation_steps=[
            "Confirmed pilot login and auth failure rate returned to baseline"
        ],
        decision_reasons=[
            "Severity indicates potential MIM handling.",
            "Incoming incident strongly matches at least one historical incident.",
        ],
    )
    return state


def build_dip_record(
    dip_id: str = "DIP-001",
    linked_kba_id: str = "KBA-MIM-001",
    service: str = "Salesforce",
    category: str = "identity_access_management",
    risk_level: str = "medium",
) -> dict[str, Any]:
    """Build a DIP/change implementation plan record."""

    return {
        "dip_id": dip_id,
        "linked_kba_id": linked_kba_id,
        "title": "Salesforce SAML certificate metadata correction",
        "service": service,
        "category": category,
        "risk_level": risk_level,
        "approval_groups": ["IAM Platform Team", "Change Enablement Team"],
        "target_environment_order": ["uat", "production"],
        "implementation_steps": [
            "Confirm active IdP signing certificate fingerprint.",
            "Compare vendor SAML metadata with approved IdP metadata.",
            "Apply corrected metadata in UAT.",
            "Run pilot login validation.",
            "Request production approval if UAT succeeds.",
        ],
        "rollback_steps": [
            "Restore previous vendor metadata snapshot.",
            "Re-enable previous known-good signing certificate if approved.",
        ],
        "validation_steps": [
            "Pilot login succeeds.",
            "SSO redirect loop no longer occurs.",
            "Authentication failure rate returns to baseline.",
        ],
    }


def build_workflow_with_dip_context() -> WorkflowState:
    """Build a workflow state as if KBA → DIP retrieval has completed."""

    state = build_analysed_workflow_state()
    state.context = WorkflowContext(
        matched_dips=[build_dip_record()],
        matched_kbas=[],
        matched_change_records=[],
        matched_validation_plans=[],
    )
    state.status = "context_retrieved"
    state.notes.append("Matched 1 DIP(s) from recommended KBA.")
    return state


def build_workflow_with_action_plan() -> WorkflowState:
    """Build a workflow state with a simple awaiting-approval action plan."""

    state = build_workflow_with_dip_context()
    dip = state.context.matched_dips[0]

    proposed_actions = []
    for index, step in enumerate(dip["implementation_steps"], start=1):
        proposed_actions.append(
            {
                "action_id": f"uat-step-{index}",
                "action_type": "uat_implementation_step",
                "title": f"UAT implementation step {index}",
                "description": step,
                "environment": "uat",
                "approval_status": "awaiting_approval",
                "execution_status": "not_started",
                "requires_human_approval": True,
                "risk_level": dip["risk_level"],
                "source_dip_id": dip["dip_id"],
                "source_kba_id": dip["linked_kba_id"],
                "approval_groups": dip["approval_groups"],
                "target_service": state.incident.service,
                "policy_id": "EXEC-POLICY-SALESFORCE-UAT",
                "execution_identity": "mim-executor-iam-uat",
                "credential_ref": "secret-manager://mim-demo/uat/iam-ansible-runner",
            }
        )

    state.action_plan = {
        "status": "awaiting_human_approval",
        "summary": "Created UAT-first action plan from DIP-001 for Salesforce.",
        "source_dip_id": dip["dip_id"],
        "source_kba_id": dip["linked_kba_id"],
        "risk_level": dip["risk_level"],
        "approval_groups": dip["approval_groups"],
        "target_environment_order": dip["target_environment_order"],
        "proposed_actions": proposed_actions,
        "rollback_steps": dip["rollback_steps"],
        "validation_steps": dip["validation_steps"],
    }
    state.validation.checks = dip["validation_steps"]
    state.status = "awaiting_approval"
    return state
