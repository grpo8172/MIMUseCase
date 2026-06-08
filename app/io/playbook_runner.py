from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.models.execution import ExecutionResult
from app.models.workflow_state import WorkflowState

import os
import subprocess

class PlaybookRunner:
    """Safe demo runner for approved UAT actions."""

    def __init__(self, log_dir: str = "data/output/execution_logs") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def execute_action(
        self,
        action: dict[str, Any],
        workflow: WorkflowState | None = None,
    ) -> ExecutionResult:
        """Execute one explicitly approved UAT action."""

        action_id = str(action.get("action_id"))
        action_type = str(action.get("action_type", "ansible_playbook"))
        environment = str(action.get("environment", "uat"))

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

        if action_type == "approval_transition":
            if workflow is None:
                result = ExecutionResult(
                    action_id=action_id,
                    action_type=action_type,
                    status="failed",
                    message="Blocked: workflow transition requires workflow context.",
                    stderr="Workflow object was not supplied to the runner.",
                    return_code=1,
                )
                return self._write_log(action, result)

            return self._execute_approval_transition(action, workflow)

        return self._run_real_gke_action(action)


    def run(
        self,
        action: dict[str, Any],
        workflow: WorkflowState | None = None,
    ) -> ExecutionResult:
        """Compatibility wrapper for existing callers."""
        return self.execute_action(action, workflow)

    def _execute_approval_transition(self, action: dict[str, Any], workflow: WorkflowState,) -> ExecutionResult:
        action_id = action["action_id"]
        action_type = action["action_type"]

        transition = action.get("transition", {})
        expected_from = transition.get("from")
        target_state = transition.get("to")

        if not target_state:
            result = ExecutionResult(
                action_id=action_id,
                action_type=action_type,
                status="failed",
                message="Blocked: workflow transition target is missing.",
                stderr="Expected action.transition.to to be configured.",
                return_code=1,
            )
            return self._write_log(action, result)

        current_state = workflow.status

        if expected_from and current_state != expected_from:
            result = ExecutionResult(
                action_id=action_id,
                action_type=action_type,
                status="failed",
                message="Blocked: workflow is not in the expected state.",
                stderr=(
                    f"Expected workflow status '{expected_from}', "
                    f"found '{current_state}'."
                ),
                return_code=1,
            )
            return self._write_log(action, result)

        workflow.status = target_state

        result = ExecutionResult(
            action_id=action_id,
            action_type=action_type,
            status="succeeded",
            message=(
                "UAT validation recorded successfully. "
                f"Workflow transitioned to '{target_state}'."
            ),
            return_code=0,
        )

        self._persist_workflow(workflow)

        return self._write_log(action, result)

    def _run_real_gke_action(
        self,
        action: dict[str, Any],
    ) -> ExecutionResult:
        action_id = str(action.get("action_id"))
        action_type = str(action.get("action_type"))

        ansible_playbook = str(action.get("ansible_playbook") or "")
        ansible_inventory = str(action.get("ansible_inventory") or "")
        gke_cluster = str(action.get("gke_cluster") or "")
        gke_location = str(action.get("gke_location") or "")
        gke_namespace = str(action.get("gke_namespace") or "")
        target_deployment = str(action.get("target_deployment") or "")
        desired_replicas = str(action.get("desired_replicas") or "2")

        allowed_clusters = {
            "mim-demo-cluster",
        }

        allowed_locations = {
            "australia-southeast1-a",
        }

        allowed_playbooks = {
            "playbooks/ensure_remediation_capacity.yml",
            "playbooks/salesforce/detect_certificate_drift.yml",
            "playbooks/salesforce/compare_saml_metadata.yml",
            "playbooks/salesforce/apply_uat_metadata.yml",
            "playbooks/salesforce/validate_uat_remediation.yml",
        }

        allowed_namespaces = {
            "client-a-uat",
        }
        if ansible_playbook not in allowed_playbooks:
            result = ExecutionResult(
                action_id=action_id,
                action_type=action_type,
                status="failed",
                message="Blocked: Ansible playbook is not whitelisted.",
                stderr=f"Blocked playbook: {ansible_playbook}",
                return_code=1,
            )
            return self._write_log(action, result)

        if gke_namespace not in allowed_namespaces:
            result = ExecutionResult(
                action_id=action_id,
                action_type=action_type,
                status="failed",
                message="Blocked: Kubernetes namespace is not whitelisted.",
                stderr=f"Blocked namespace: {gke_namespace}",
                return_code=1,
            )
            return self._write_log(action, result)

        if gke_cluster not in allowed_clusters:
            result = ExecutionResult(
                action_id=action_id,
                action_type=action_type,
                status="failed",
                message="Blocked: GKE cluster is not whitelisted.",
                stderr=f"Blocked cluster: {gke_cluster}",
                return_code=1,
            )
            return self._write_log(action, result)

        if gke_location not in allowed_locations:
            result = ExecutionResult(
                action_id=action_id,
                action_type=action_type,
                status="failed",
                message="Blocked: GKE location is not whitelisted.",
                stderr=f"Blocked location: {gke_location}",
                return_code=1,
            )
            return self._write_log(action, result)

        if not Path(ansible_playbook).exists():
            result = ExecutionResult(
                action_id=action_id,
                action_type=action_type,
                status="failed",
                message="Ansible playbook file was not found.",
                stderr=f"Missing playbook: {ansible_playbook}",
                return_code=1,
            )
            return self._write_log(action, result)

        env = os.environ.copy()
        env["TARGET_NAMESPACE"] = gke_namespace
        env["TARGET_DEPLOYMENT"] = target_deployment
        env["DESIRED_REPLICAS"] = desired_replicas

        credentials_result = subprocess.run(
            [
                "gcloud",
                "container",
                "clusters",
                "get-credentials",
                gke_cluster,
                "--zone",
                gke_location,
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

        if credentials_result.returncode != 0:
            result = ExecutionResult(
                action_id=action_id,
                action_type=action_type,
                status="failed",
                message="Failed to obtain credentials for the approved GKE cluster.",
                stdout=credentials_result.stdout,
                stderr=credentials_result.stderr,
                return_code=credentials_result.returncode,
            )
            return self._write_log(action, result)

        completed = subprocess.run(
            [
                "ansible-playbook",
                "-i",
                ansible_inventory or "localhost,",
                ansible_playbook,
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )


        result = ExecutionResult(
            action_id=action_id,
            action_type=action_type,
            status="succeeded" if completed.returncode == 0 else "failed",
            message=(
                "Approved Ansible/GKE execution completed."
                if completed.returncode == 0
                else "Approved Ansible/GKE execution failed."
            ),
            stdout=completed.stdout,
            stderr=completed.stderr,
            return_code=completed.returncode,
            evidence=[
                "Execution mode: real_gke",
                f"Namespace: {gke_namespace}",
                f"Deployment: {target_deployment}",
                f"Desired replicas: {desired_replicas}",
                f"Playbook: {ansible_playbook}",
                f"Inventory: {ansible_inventory or 'localhost,'}",
                "Credential reference remained unresolved in workflow state.",
                f"GKE cluster: {gke_cluster}",
                f"GKE location: {gke_location}",
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