from __future__ import annotations

from app.io.playbook_runner import PlaybookRunner
from app.models.workflow_state import WorkflowState


class ExecutionAgent:
    """Executes only manually approved workflow actions."""

    def __init__(self, playbook_runner: PlaybookRunner | None = None) -> None:
        self.playbook_runner = playbook_runner or PlaybookRunner()

    def execute_approved_actions(self, state: WorkflowState) -> WorkflowState:
        if not state.action_plan:
            state.notes.append("No action plan available for execution.")
            state.status = "failed"
            return state

        proposed_actions = state.action_plan.get("proposed_actions", [])
        approved_action_ids = set(state.execution.approved_action_ids)

        for action in proposed_actions:
            action_id = action.get("action_id")

            if action_id not in approved_action_ids:
                state.execution.results.append(
                    {
                        "action_id": action_id,
                        "action_type": action.get("action_type"),
                        "status": "skipped",
                        "message": "Action was not manually approved.",
                    }
                )
                continue

            result = self.playbook_runner.run(action, state)
            state.execution.results.append(result.model_dump())

            action["execution_status"] = result.status

        if state.status != "awaiting_production_approval":
            state.status = "executed"
        state.notes.append("Executed approved actions and skipped unapproved actions.")
        return state
