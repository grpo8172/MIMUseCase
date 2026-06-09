from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ExecutionStatus = Literal["skipped", "succeeded", "failed"]


class ExecutionResult(BaseModel):
    action_id: str
    action_type: str
    status: ExecutionStatus
    message: str
    output: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    return_code: int | None = None
    log_path: str | None = None
    evidence: list[str] = Field(default_factory=list)
