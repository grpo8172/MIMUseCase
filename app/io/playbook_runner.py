from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.models.execution import ExecutionResult


class PlaybookRunner:
    """Safe demo runner for approved UAT actions."""

    def __init__(self, log_dir: str = "data/output/execution_logs") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def run(self, action: dict[str, Any]) -> ExecutionResult:
        action_id = str(action.get("action_id"))
        action_type = str(action.get("action_type"))
        description = str(action.get("description", ""))
        environment = str(action.get("environment", "uat"))
        source_dip_id = action.get("source_dip_id")
        source_kba_id = action.get("source_kba_id")
        credential_ref = action.get("credential_ref")
        execution_identity = action.get("execution_identity")
        policy_id = action.get("policy_id")

        if environment != "uat":
            result = ExecutionResult(
                action_id=action_id,
                action_type=action_type,
                status="failed",
                message="Only UAT execution is allowed in the MVP demo.",
                stderr="Blocked: non-UAT execution requested.",
                return_code=1,
            )
            return self._write_log(action, result)

        if action_type != "uat_implementation_step":
            result = ExecutionResult(
                action_id=action_id,
                action_type=action_type,
                status="failed",
                message=f"Unsupported action type: {action_type}",
                stderr=f"Blocked: unsupported action_type={action_type}",
                return_code=1,
            )
            return self._write_log(action, result)

        stdout = "\n".join(
            [
                "=== Simulated Ansible UAT Execution ===",
                f"Action ID: {action_id}",
                f"Source DIP: {source_dip_id}",
                f"Source KBA: {source_kba_id}",
                f"Target environment: {environment}",
                f"Step: {description}",
                "Credential handling: credential_ref would be resolved by execution layer.",
                "Secret exposure: no secret values exposed to LLM or workflow state.",
                "Result: simulated playbook execution succeeded.",
            ]
        )

        result = ExecutionResult(
            action_id=action_id,
            action_type=action_type,
            status="succeeded",
            message="Simulated approved UAT playbook execution completed.",
            output=(
                f"Would run whitelisted Ansible workflow for {source_dip_id} / "
                f"{source_kba_id}: {description}"
            ),
            stdout=stdout,
            stderr="",
            return_code=0,
            evidence=[
                "No secret values exposed to LLM or workflow state.",
                "Credential reference would be resolved by execution layer at runtime.",
                "Execution limited to UAT environment.",
            ],
        )
        return self._write_log(action, result)

    def _write_log(self, action: dict[str, Any], result: ExecutionResult) -> ExecutionResult:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        safe_action_id = result.action_id.replace("/", "_").replace(" ", "_")
        log_path = self.log_dir / f"{timestamp}-{safe_action_id}.log"

        policy_id = action.get("policy_id")
        execution_identity = action.get("execution_identity")
        credential_ref = action.get("credential_ref")

        content = "\n".join(
            [
                "MIM Agent Execution Log",
                "=======================",
                f"Timestamp: {timestamp}",
                f"Action ID: {result.action_id}",
                f"Action type: {result.action_type}",
                f"Status: {result.status}",
                f"Message: {result.message}",
                "",
                "Approved action:",
                str(action),
                "",
                "Execution controls:",
                f"Execution policy: {policy_id}",
                f"Execution identity: {execution_identity}",
                f"Credential reference: {credential_ref}",
                "Credential handling: credential_ref would be resolved by the execution identity at runtime.",
                "",
                "STDOUT:",
                result.stdout or "",
                "",
                "STDERR:",
                result.stderr or "",
                "",
                f"Return code: {result.return_code}",
            ]
        )

        log_path.write_text(content, encoding="utf-8")
        result.log_path = str(log_path)
        return result