from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.agents.execution_agent import ExecutionAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.workflow_coordinator import WorkflowCoordinatorAgent
from app.models.workflow_state import WorkflowState
from app.services.workflow_service import process_workflow

import os

from app.api.execution import router as execution_router

app = FastAPI(
    title="MIM Incident Intelligence API",
    description="API wrapper for payload analysis, KBA/DIP retrieval, approval, execution, and validation.",
    version="0.1.0",
)

WORKFLOW_STORE: dict[str, WorkflowState] = {}

app.include_router(execution_router)

PAYLOAD_OPTIONS = {
    "salesforce_sso": "fixtures/payloads/incoming-incident-salesforce-sso.json",
    "vault_key": "fixtures/payloads/incoming-incident-vault-key.json",
    "pipeline_failure": "fixtures/payloads/incoming-incident-pipeline-failure.json",
    "cyber_app_exploit": "fixtures/payloads/incoming-cyber-app-exploit.json",
}


DATASET_OPTIONS = {
    "it_mim": "data/generated/cyber_mim_incidents.csv",
    "cyber_mim": "data/generated/cyber_mim_incidents.csv",
}


class CreateWorkflowRequest(BaseModel):
    payload_key: str | None = Field(
        default=None,
        description="Known payload fixture key, such as salesforce_sso or cyber_app_exploit.",
    )
    payload_path: str | None = Field(
        default=None,
        description="Direct path to an incoming payload JSON file.",
    )
    payload: dict[str, Any] | None = Field(
        default=None,
        description="Inline incident payload. Takes precedence over payload_key/path.",
    )
    dataset_key: str | None = Field(
        default="it_mim",
        description="Known historical dataset key, such as it_mim or cyber_mim.",
    )
    dataset_path: str | None = Field(
        default=None,
        description="Direct path to canonical historical incidents CSV.",
    )


class ApproveWorkflowRequest(BaseModel):
    action_id: str = Field(description="Action ID to approve and execute.")


def load_json(path: str) -> dict[str, Any]:
    file_path = Path(path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    return json.loads(file_path.read_text(encoding="utf-8"))


def resolve_payload(request: CreateWorkflowRequest) -> dict[str, Any]:
    if request.payload is not None:
        return request.payload

    if request.payload_path:
        return load_json(request.payload_path)

    if request.payload_key:
        path = PAYLOAD_OPTIONS.get(request.payload_key)
        if not path:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown payload_key: {request.payload_key}",
            )
        return load_json(path)

    raise HTTPException(
        status_code=400,
        detail="Provide payload, payload_path, or payload_key.",
    )


def resolve_dataset_path(request: CreateWorkflowRequest) -> str:
    if request.dataset_path:
        path = request.dataset_path
    else:
        dataset_key = request.dataset_key or "it_mim"
        path = DATASET_OPTIONS.get(dataset_key)
        if not path:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown dataset_key: {dataset_key}",
            )

    if not Path(path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"Historical incidents dataset not found: {path}",
        )

    return path


def write_workflow_state(state: WorkflowState) -> None:
    output_dir = Path("data/output/api_workflows")
    output_dir.mkdir(parents=True, exist_ok=True)

    path = output_dir / f"{state.workflow_id}.json"
    path.write_text(state.model_dump_json(indent=2), encoding="utf-8")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/options")
def options() -> dict[str, Any]:
    return {
        "payloads": PAYLOAD_OPTIONS,
        "datasets": DATASET_OPTIONS,
        "execution_mode": "real" if __import__("os").getenv("REAL_EXECUTION", "false").lower() == "true" else "simulated",
    }

@app.post("/api/workflows")
def create_workflow(request: CreateWorkflowRequest) -> dict[str, Any]:
    payload = resolve_payload(request)
    dataset_path = resolve_dataset_path(request)

    state = process_workflow(
        payload=payload,
        dataset_path=dataset_path,
    )

    WORKFLOW_STORE[state.workflow_id] = state

    return state.model_dump()


@app.get("/api/workflows/{workflow_id}")
def get_workflow(workflow_id: str) -> dict[str, Any]:
    state = WORKFLOW_STORE.get(workflow_id)

    if state:
        return state.model_dump()

    path = Path("data/output/api_workflows") / f"{workflow_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")


@app.post("/api/workflows/{workflow_id}/approve")
def approve_and_execute(
    workflow_id: str,
    request: ApproveWorkflowRequest,
) -> dict[str, Any]:
    state = WORKFLOW_STORE.get(workflow_id)

    if not state:
        path = Path("data/output/api_workflows") / f"{workflow_id}.json"
        if path.exists():
            state = WorkflowState.model_validate_json(path.read_text(encoding="utf-8"))
        else:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    coordinator = WorkflowCoordinatorAgent()
    state = coordinator.approve_action(state, request.action_id)
    state = ExecutionAgent().execute_approved_actions(state)
    state = ValidationAgent().validate(state)

    WORKFLOW_STORE[state.workflow_id] = state
    write_workflow_state(state)

    return state.model_dump()
