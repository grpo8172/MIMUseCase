from __future__ import annotations

from app.io.playbook_runner import PlaybookRunner
from app.models.workflow_state import WorkflowState


class ExecutionAgent:
    """Executes only manually approved workflow actions."""

    def __init__(
        self,
        playbook_runner: PlaybookRunner | None = None,
    ) -> None:
        self.playbook_runner = playbook_runner or PlaybookRunner()

    def execute_approved_actions(
        self,
        state: WorkflowState,
    ) -> WorkflowState:
        if not state.action_plan:
            state.notes.append("No action plan available for execution.")
            state.status = "failed"
            return state

        proposed_actions = state.action_plan.get(
            "proposed_actions",
            [],
        )

        approved_action_ids = set(
            state.execution.approved_action_ids
        )

        for action in proposed_actions:
            action_id = action.get("action_id")
            action_type = action.get(
                "action_type",
                "advisory_only",
            )
            execution_status = action.get(
                "execution_status",
                "not_started",
            )

            # Only run explicitly approved actions.
            if action_id not in approved_action_ids:
                continue

            # Never silently rerun an action that already reached a terminal state.
            if execution_status in {
                "succeeded",
                "failed",
                "blocked",
                "awaiting_manual_intervention",
            }:
                continue

            if action_type == "manual_intervention":
                action["execution_status"] = "awaiting_manual_intervention"

                state.execution.results.append(
                    {
                        "action_id": action_id,
                        "action_type": action_type,
                        "operation": action.get(
                            "operation",
                            "manual_intervention",
                        ),
                        "rolls_back_action_id": action.get(
                            "rolls_back_action_id"
                        ),
                        "status": "awaiting_manual_intervention",
                        "message": (
                            "This action requires manual technical intervention."
                        ),
                        "log_path": None,
                    }
                )

                state.status = "awaiting_manual_intervention"
                state.notes.append(
                    f"Manual intervention required for action {action_id}."
                )
                continue

            result = self.playbook_runner.execute_action(
                action,
                state.model_dump(),
            )

            action["execution_status"] = result.status

            state.execution.results.append(
                {
                    "action_id": action_id,
                    "action_type": action_type,
                    "operation": action.get(
                        "operation",
                        "remediation",
                    ),
                    "rolls_back_action_id": action.get(
                        "rolls_back_action_id"
                    ),
                    "status": result.status,
                    "message": result.message,
                    "log_path": getattr(
                        result,
                        "log_path",
                        None,
                    ),
                }
            )

            if result.status != "succeeded":
                state.status = "failed"
                state.notes.append(
                    f"Execution failed for action {action_id}."
                )
                continue

            if action.get("operation") == "rollback":
                state.status = "rollback_completed"
                state.notes.append(
                    f"Rollback completed for "
                    f"{action.get('rolls_back_action_id')}."
                )
            else:
                state.status = "executed"
                state.notes.append(
                    f"Execution completed for action {action_id}."
                )

        return state