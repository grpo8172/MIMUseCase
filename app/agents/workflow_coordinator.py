from __future__ import annotations

from app.io.dip_repository import DIPRepository
from app.mcp.schemas import MCPIncidentAnalysisRequest
from app.mcp.tools import analyse_incident
from app.models.resolution import IncidentAnalysisResult
from app.models.workflow_state import WorkflowIncident, WorkflowState
from app.io.execution_policy_repository import ExecutionPolicyRepository

class WorkflowCoordinatorAgent:
    """Coordinates MCP-style tools through a shared WorkflowState."""

    def __init__(
        self,
        dip_repository: DIPRepository | None = None,
        execution_policy_repository: ExecutionPolicyRepository | None = None,
        historical_incidents_path: str = "data/input/incidents.csv",
        resolution_db_path: str = "data/resolution_db/incident_resolution_steps.jsonl",
    ) -> None:
        self.dip_repository = dip_repository or DIPRepository()
        self.execution_policy_repository = (
            execution_policy_repository or ExecutionPolicyRepository()
        )
        self.historical_incidents_path = historical_incidents_path
        self.resolution_db_path = resolution_db_path

    def create_workflow(self, incident_payload: dict) -> WorkflowState:
        incident_id = incident_payload.get("incident_id") or incident_payload.get("number")

        symptoms = [
            value
            for value in [
                incident_payload.get("short_description"),
                incident_payload.get("description"),
                incident_payload.get("customer_impact"),
            ]
            if value
        ]

        return WorkflowState(
            workflow_id=f"WF-{incident_id or 'UNKNOWN'}",
            incident=WorkflowIncident(
                incident_id=incident_id,
                service=incident_payload.get("service"),
                short_description=incident_payload.get("short_description"),
                description=incident_payload.get("description"),
                severity=incident_payload.get("severity"),
                priority=incident_payload.get("priority"),
                symptoms=symptoms,
                raw=incident_payload,
            ),
        )

    def analyse(self, state: WorkflowState) -> WorkflowState:
        response = analyse_incident(
            MCPIncidentAnalysisRequest(
                incident=state.incident.raw,
                historical_incidents_path=self.historical_incidents_path,
                resolution_db_path=self.resolution_db_path,
                similarity_limit=5,
            )
        )

        if not response.ok:
            state.status = "failed"
            state.notes.extend(response.errors)
            return state

        analysis = IncidentAnalysisResult.model_validate(response.result)

        state.analysis.mim_classification = analysis.mim_classification
        state.analysis.mim_confidence = analysis.mim_confidence
        state.analysis.seen_before_status = analysis.seen_before_status
        state.analysis.recommended_kba_id = analysis.recommended_kba_id
        state.analysis.recommended_resolver_group = analysis.recommended_resolver_group
        state.analysis.recommended_resolution_steps = analysis.recommended_resolution_steps
        state.analysis.recommended_validation_steps = analysis.recommended_validation_steps
        state.analysis.decision_reasons = analysis.notes
        state.status = "incident_analysed"
        return state

    def retrieve_dip_context(self, state: WorkflowState) -> WorkflowState:
        matched_dips = self.dip_repository.find_by_kba(
            state.analysis.recommended_kba_id
        )

        state.context.matched_dips = matched_dips

        if matched_dips:
            state.notes.append(
                f"Matched {len(matched_dips)} DIP(s) from recommended KBA."
            )
        else:
            state.notes.append("No linked DIP found for recommended KBA.")

        state.status = "context_retrieved"
        return state

    def create_action_plan(self, state: WorkflowState) -> WorkflowState:
        if not state.context.matched_dips:
            state.notes.append("No DIP context available; action plan requires manual drafting.")
            state.status = "action_plan_created"
            state.action_plan = {
                "status": "awaiting_human_approval",
                "summary": "No linked DIP found. Manual review required.",
                "proposed_actions": [],
            }
            return state

        dip = state.context.matched_dips[0]

        policy = self.execution_policy_repository.find_for_service(state.incident.service)
        credential_ref = policy.get("credential_ref") if policy else None
        execution_identity = policy.get("execution_identity") if policy else None

        policy_id = policy.get("policy_id") if policy else None
        gke_cluster = policy.get("gke_cluster") if policy else None
        gke_namespace = policy.get("gke_namespace") if policy else None
        kubernetes_service_account = (
            policy.get("kubernetes_service_account") if policy else None
        )
        ansible_inventory = policy.get("ansible_inventory") if policy else None
        ansible_playbook = policy.get("ansible_playbook") if policy else None
        allowed_kubernetes_resources = (
            policy.get("allowed_kubernetes_resources", []) if policy else []
        )
        allowed_kubernetes_verbs = (
            policy.get("allowed_kubernetes_verbs", []) if policy else []
        )
        target_deployment = (
            policy.get("target_deployment", "fake-auth-service")
            if policy
            else "fake-auth-service"
        )
        desired_replicas = policy.get("desired_replicas", 2) if policy else 2

        proposed_actions = []
        for index, step in enumerate(dip.get("implementation_steps", []), start=1):
            proposed_actions.append(
                {
                    "action_id": f"uat-step-{index}",
                    "action_type": "uat_implementation_step",
                    "title": f"UAT implementation step {index}",
                    "description": step,
                    "environment": "uat",
                    "approval_status": "awaiting_approval",
                    "execution_status": "not_started",
                    "requires_human_approval": True,
                    "risk_level": dip.get("risk_level", "medium"),
                    "source_dip_id": dip.get("dip_id"),
                    "source_kba_id": dip.get("linked_kba_id"),
                    "approval_groups": dip.get("approval_groups", []),
                    "policy_id": policy_id,
                    "execution_identity": execution_identity,
                    "credential_ref": credential_ref,
                    "gke_cluster": gke_cluster,
                    "gke_namespace": gke_namespace,
                    "kubernetes_service_account": kubernetes_service_account,
                    "ansible_inventory": ansible_inventory,
                    "ansible_playbook": ansible_playbook,
                    "allowed_kubernetes_resources": allowed_kubernetes_resources,
                    "allowed_kubernetes_verbs": allowed_kubernetes_verbs,
                    "target_deployment": target_deployment,
                    "desired_replicas": desired_replicas,
                }
            )

        state.action_plan = {
            "status": "awaiting_human_approval",
            "summary": (
                f"Created UAT-first action plan from {dip.get('dip_id')} "
                f"for {state.incident.service}."
            ),
            "source_dip_id": dip.get("dip_id"),
            "source_kba_id": dip.get("linked_kba_id"),
            "risk_level": dip.get("risk_level", "medium"),
            "approval_groups": dip.get("approval_groups", []),
            "target_environment_order": dip.get("target_environment_order", ["uat"]),
            "proposed_actions": proposed_actions,
            "rollback_steps": dip.get("rollback_steps", []),
            "validation_steps": dip.get("validation_steps", []),
        }

        state.validation.checks = dip.get("validation_steps", [])
        state.status = "awaiting_approval"
        state.notes.append(f"Created action plan from {dip.get('dip_id')}.")
        return state

    def approve_action(self, state: WorkflowState, action_id: str) -> WorkflowState:
        if action_id not in state.execution.approved_action_ids:
            state.execution.approved_action_ids.append(action_id)

        if state.action_plan:
            for action in state.action_plan.get("proposed_actions", []):
                if action.get("action_id") == action_id:
                    action["approval_status"] = "approved"
                    break

        state.status = "approved"
        state.notes.append(f"Human approved action {action_id}.")
        return state