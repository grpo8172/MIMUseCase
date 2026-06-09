from __future__ import annotations

import os

from google.adk.agents import Agent

from .tools import (
    approve_workflow_action,
    create_incident_workflow,
    create_sample_workflow,
    describe_incident_workflow,
    get_workflow_action_log,
    prepare_workflow_rollback,
)

root_agent = Agent(
    name="mim_incident_agent",
    model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
    description=(
        "Major Incident Management agent that retrieves operational memory, "
        "creates approval-gated remediation plans, and executes only explicitly "
        "approved UAT actions."
    ),
    instruction=(
        "You assist IT major incident managers and operations engineers. "
        "Use only the registered tools. "
        "When the user requests the Salesforce demo fixture, call "
        "create_sample_workflow. "
        "When the user supplies incident details, call create_incident_workflow. "
        "When the user explicitly approves a specific workflow ID and action ID, "
        "call approve_workflow_action. "
        "Do not call get_incident_details because that tool does not exist. "
        "Never claim that you queried memory, retrieved logs, inspected "
        "configuration, executed remediation, or validated an outcome unless a "
        "registered tool returned that exact evidence. "
        "Never invent Salesforce API results. "
        "Never expose passwords, tokens, private keys, or secret values."
    ),
    tools=[
        describe_incident_workflow,
        create_incident_workflow,
        create_sample_workflow,
        approve_workflow_action,
        prepare_workflow_rollback,
        get_workflow_action_log,
    ],
)
