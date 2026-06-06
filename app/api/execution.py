from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from app.services.gke_scaling import set_node_pool_size

router = APIRouter(prefix="/api/execution", tags=["execution"])


def _real_execution_enabled() -> bool:
    return os.getenv("REAL_EXECUTION", "false").lower() == "true"


@router.post("/enable")
def enable_live_execution() -> dict:
    if not _real_execution_enabled():
        raise HTTPException(
            status_code=403,
            detail="Live execution is disabled. Enable REAL_EXECUTION first.",
        )

    operation = set_node_pool_size(1)

    return {
        "execution_mode": "real",
        "capacity_status": "requested",
        "operation": operation.get("name"),
    }


@router.post("/disable")
def disable_live_execution() -> dict:
    operation = set_node_pool_size(0)

    return {
        "execution_mode": "simulation",
        "capacity_status": "scale_down_requested",
        "operation": operation.get("name"),
    }
