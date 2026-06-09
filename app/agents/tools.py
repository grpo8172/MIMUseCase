from __future__ import annotations

from typing import Any

from app.io.payload_loader import PayloadLoader
from app.io.storage import StorageIO
from app.mcp.schemas import (
    MCPDatasetInspectionRequest,
    MCPIncidentAnalysisRequest,
    MCPToolResponse,
)
from app.models.worker_config import WorkerConfig
from app.services.incident_worker import IncidentWorker
from app.services.pipeline import MIMInspectionPipeline


def analyse_incident(request: MCPIncidentAnalysisRequest) -> MCPToolResponse:
    """Analyse an incoming incident and return a MIM action plan."""

    try:
        config = WorkerConfig(
            dataset_path=request.dataset_path,
            resolution_db=request.resolution_db_path,
            output_file=None,
            similarity_limit=request.similarity_limit,
        )
        worker = IncidentWorker(config)
        result = worker.process(request.incident)

        return MCPToolResponse(result=result.model_dump())

    except Exception as exc:
        return MCPToolResponse(ok=False, errors=[str(exc)])


def inspect_dataset(request: MCPDatasetInspectionRequest) -> MCPToolResponse:
    """Inspect a dataset payload and return schema/use-case recommendations."""

    try:
        storage_io = StorageIO()
        job = PayloadLoader(storage_io).load(request.payload_uri)
        pipeline = MIMInspectionPipeline(storage_io=storage_io, llm=None)
        result = pipeline.run(job)

        return MCPToolResponse(result=result.model_dump())

    except Exception as exc:
        return MCPToolResponse(ok=False, errors=[str(exc)])


def normalise_dynatrace_problem(problem: dict[str, Any]) -> dict[str, Any]:
    """Temporary adapter from Dynatrace-like problem data to incident payload.

    Later this should be fed by the actual Dynatrace MCP server.
    """

    return {
        "incident_id": problem.get("problemId") or problem.get("displayId"),
        "opened_at": problem.get("startTime") or problem.get("created_at"),
        "service": problem.get("affectedService")
        or problem.get("entityName")
        or problem.get("service"),
        "short_description": problem.get("title") or problem.get("displayName"),
        "description": problem.get("impactAnalysis")
        or problem.get("rootCause")
        or problem.get("description"),
        "severity": problem.get("severityLevel") or problem.get("severity"),
        "priority": problem.get("priority"),
        "assignment_group": problem.get("managementZone") or problem.get("owner"),
        "affected_region": problem.get("region"),
        "customer_impact": problem.get("customerImpact") or problem.get("impact"),
    }