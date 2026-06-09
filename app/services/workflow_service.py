from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.agents.workflow_coordinator import WorkflowCoordinatorAgent
from app.io.mongo_mcp_memory_client import MongoMCPMemoryClient
from app.models.workflow_state import WorkflowState


def write_workflow_state(state: WorkflowState) -> None:
    output_dir = Path("data/output/api_workflows")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{state.workflow_id}.json"
    output_path.write_text(
        state.model_dump_json(indent=2),
        encoding="utf-8",
    )


def process_workflow(
    payload: dict[str, Any],
    dataset_path: str,
) -> WorkflowState:
    """Run one normalized incident through the complete analysis workflow."""

    memory_client = (
        MongoMCPMemoryClient() if os.getenv("USE_MONGO_MCP", "false").lower() == "true" else None
    )

    coordinator = WorkflowCoordinatorAgent(
        dataset_path=dataset_path,
        operational_memory_client=memory_client,
    )

    state = coordinator.create_workflow(payload)
    state = coordinator.analyse(state)
    state = coordinator.retrieve_operational_memory(state)
    state = coordinator.retrieve_dip_context(state)
    state = coordinator.create_action_plan(state)

    write_workflow_state(state)

    return state
