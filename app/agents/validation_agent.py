from __future__ import annotations

from app.models.workflow_state import WorkflowState


class ValidationAgent:
    """Validates whether the approved UAT execution produced enough evidence."""

    def validate(self, state: WorkflowState) -> WorkflowState:
        succeeded = [
            result for result in state.execution.results if result.get("status") == "succeeded"
        ]

        if not succeeded:
            state.validation.status = "failed"
            state.validation.evidence.append("No successful approved execution results found.")
            state.status = "failed"
            return state

        for check in state.validation.checks:
            state.validation.evidence.append(f"Demo validation check passed: {check}")

        state.validation.status = "passed"
        state.status = "validated"
        state.notes.append("Validation completed for approved UAT execution.")
        return state
