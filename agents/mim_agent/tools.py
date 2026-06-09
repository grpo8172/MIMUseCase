from __future__ import annotations

import os
from typing import Any

import httpx

MIM_API_BASE_URL = os.getenv(
    "MIM_API_BASE_URL",
    "http://127.0.0.1:8000",
)


def describe_incident_workflow() -> dict[str, Any]:
    """Describe the controlled incident-remediation workflow."""
    return {
        "status": "success",
        "target_user": "IT major incident manager or operations engineer",
        "workflow": [
            "receive incident payload",
            "analyse the incident",
            "retrieve operational memory through MongoDB MCP",
            "retrieve KBA and DIP context",
            "generate an approval-gated remediation plan",
            "execute only a specifically approved UAT action",
            "validate rollout and write an audit log",
        ],
        "automatic_execution_allowed": False,
    }


def create_incident_workflow(
    incident_id: str,
    service: str,
    short_description: str,
    description: str,
    severity: str,
    priority: str,
    environment: str = "uat",
    dataset_key: str = "it_mim",
) -> dict[str, Any]:
    """
    Create and persist a grounded remediation workflow.

    IMPORTANT:
    - Return the authoritative workflow_id and proposed action IDs.
    - The caller must use the returned identifiers exactly.
    - Never infer, rewrite, or invent workflow IDs or action IDs.
    """
    response = httpx.post(
        f"{MIM_API_BASE_URL}/api/workflows",
        json={
            "payload": {
                "incident_id": incident_id,
                "service": service,
                "short_description": short_description,
                "description": description,
                "severity": severity,
                "priority": priority,
                "environment": environment,
            },
            "dataset_key": dataset_key,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()


def approve_workflow_action(
    workflow_id: str,
    action_id: str,
    human_approved: bool,
) -> dict[str, Any]:
    """
    Approve and execute exactly one persisted workflow action.

    Use only a workflow_id and action_id previously returned by the backend.
    Never generate or infer identifiers from conversational context.
    Call this only after the user explicitly approves the specific action.
    """
    if not human_approved:
        return {
            "status": "blocked",
            "message": "Explicit human approval is required before execution.",
        }

    response = httpx.post(
        f"{MIM_API_BASE_URL}/api/workflows/{workflow_id}/approve",
        json={"action_id": action_id},
        timeout=180.0,
    )
    response.raise_for_status()
    return response.json()


def create_sample_workflow(
    payload_key: str = "salesforce_sso",
    dataset_key: str = "it_mim",
) -> dict[str, Any]:
    """Create a workflow from one of the approved sample payload fixtures."""
    response = httpx.post(
        f"{MIM_API_BASE_URL}/api/workflows",
        json={
            "payload_key": payload_key,
            "dataset_key": dataset_key,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()


def prepare_workflow_rollback(
    workflow_id: str,
    action_id: str,
) -> dict[str, Any]:
    """
    Create an approval-gated rollback action for a completed workflow action.

    Use this when the operator explicitly requests rollback.
    Do not approve or execute the original completed action again.
    """
    response = httpx.post(
        f"{MIM_API_BASE_URL}/api/workflows/{workflow_id}/rollback",
        json={"action_id": action_id},
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()


def get_workflow_action_log(
    workflow_id: str,
    action_id: str,
) -> dict[str, Any]:
    """
    Retrieve the raw captured execution log for a persisted workflow action.

    ALWAYS use this read-only tool when the operator asks to:
    - show the logs
    - display log output
    - inspect execution output
    - show Ansible output
    - retrieve stdout or stderr
    - explain why an action failed
    - provide detailed output for a completed or failed workflow step

    If the operator does not restate the workflow ID or action ID, reuse the
    most recently discussed persisted workflow ID and action ID from the
    conversation. Do not claim that local log files are inaccessible before
    attempting this tool. Do not invent file-system paths or infrastructure
    causes.
    """
    response = httpx.get(
        f"{MIM_API_BASE_URL}/api/workflows/{workflow_id}/logs/{action_id}",
        timeout=30.0,
    )

    if response.is_error:
        return {
            "status": "failed",
            "http_status": response.status_code,
            "message": response.text,
        }

    return response.json()