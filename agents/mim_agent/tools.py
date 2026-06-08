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


def approve_workflow_action(
    workflow_id: str,
    action_id: str,
    human_approved: bool,
) -> dict[str, Any]:
    """Execute one workflow action only after explicit human approval."""
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
