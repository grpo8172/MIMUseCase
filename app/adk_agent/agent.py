from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

from app.api.workflow_service import (
    create_workflow_for_payload,
    get_workflow_by_id,
    approve_and_execute_action,
)


def create_incident_workflow(
    payload_key: str,
    dataset_key: str = "it_mim",
) -> dict[str, Any]:
    """Create an incident workflow, retrieve operational memory, and generate a plan."""
    return create_workflow_for_payload(
        payload_key=payload_key,
        dataset_key=dataset_key,
    )


def inspect_incident_workflow(workflow_id: str) -> dict[str, Any]:
    """Return the current workflow, memory matches, proposed actions, and status."""
    return get_workflow_by_id(workflow_id)


def execute_explicitly_approved_action(
    workflow_id: str,
    action_id: str,
    human_approved: bool,
) -> dict[str, Any]:
    """Execute one action only when the user explicitly confirms approval."""
    if not human_approved:
        return {
            "status": "blocked",
            "message": "Human approval is required before execution.",
        }

    return approve_and_execute_action(
        workflow_id=workflow_id,
        action_id=action_id,
    )


root_agent = LlmAgent(
    name="mim_incident_response_agent",
    model="gemini-3.1-flash-lite-preview",
    description=(
        "Investigates major incidents, retrieves MongoDB MCP operational memory, "
        "creates approval-gated remediation plans, and executes only explicitly "
        "approved UAT actions."
    ),
    instruction="""
You are an incident-response workflow agent.

For each incident:
1. Create or inspect the workflow.
2. Retrieve and explain relevant operational memory.
3. Present the KBA, DIP, and proposed remediation steps.
4. Never execute a remediation unless the user explicitly approves a specific action.
5. Keep credential values out of the response. Credential references may be shown.
6. Restrict execution to policy-approved UAT targets.
""",
    tools=[
        create_incident_workflow,
        inspect_incident_workflow,
        execute_explicitly_approved_action,
    ],
)
