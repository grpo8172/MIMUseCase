from __future__ import annotations

from typing import Any
from app.io.dip_repository import DIPRepository
from app.mcp.schemas import MCPIncidentAnalysisRequest
from app.mcp.tools import analyse_incident
from app.models.resolution import IncidentAnalysisResult
from app.models.workflow_state import WorkflowIncident, WorkflowState
from app.io.execution_policy_repository import ExecutionPolicyRepository
from app.io.mongo_mcp_memory_client import MongoMCPMemoryClient


class WorkflowCoordinatorAgent:
    """Coordinates MCP-style tools through a shared WorkflowState."""

    def __init__(
        self,
        dip_repository: DIPRepository | None = None,
        execution_policy_repository: ExecutionPolicyRepository | None = None,
        operational_memory_client: MongoMCPMemoryClient | None = None,
        dataset_path: str = "data/generated/cyber_mim_incidents.csv",
        resolution_db_path: str = "data/resolution_db/incident_resolution_steps.jsonl",
    ) -> None:
        self.dip_repository = dip_repository or DIPRepository()
        self.execution_policy_repository = (
            execution_policy_repository or ExecutionPolicyRepository()
        )
        self.operational_memory_client = operational_memory_client
        self.dataset_path= dataset_path
        self.resolution_db_path = resolution_db_path
    
    @staticmethod
    def _get_action_adapter(
        *,
        policy: dict | None,
        action_id: str,
    ) -> dict:
        if not policy:
            return {}

        adapters = policy.get("action_adapters", {})

        adapter = adapters.get(action_id)

        if not isinstance(adapter, dict):
            return {}

        return adapter

    @staticmethod
    def _build_shared_policy_fields(
        policy: dict | None,
    ) -> dict:
        if not policy:
            return {
                "policy_id": None,
                "execution_identity": None,
                "credential_ref": None,
                "gke_cluster": None,
                "gke_location": None,
                "gke_namespace": None,
                "kubernetes_service_account": None,
                "ansible_inventory": None,
                "preflight_playbook": None,
                "allowed_kubernetes_resources": [],
                "allowed_kubernetes_verbs": [],
            }

        return {
            "policy_id": policy.get("policy_id"),
            "execution_identity": policy.get("execution_identity"),
            "credential_ref": policy.get("credential_ref"),
            "gke_cluster": policy.get("gke_cluster"),
            "gke_location": policy.get("gke_location"),
            "gke_namespace": policy.get("gke_namespace"),
            "kubernetes_service_account": policy.get(
                "kubernetes_service_account"
            ),
            "ansible_inventory": policy.get("ansible_inventory"),
            "preflight_playbook": policy.get("preflight_playbook"),
            "allowed_kubernetes_resources": policy.get(
                "allowed_kubernetes_resources",
                [],
            ),
            "allowed_kubernetes_verbs": policy.get(
                "allowed_kubernetes_verbs",
                [],
            ),
        }

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
                dataset_path=self.dataset_path,
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
            state.notes.append(
                "No DIP context available; action plan requires manual drafting."
            )
            state.status = "action_plan_created"
            state.action_plan = {
                "status": "awaiting_human_approval",
                "summary": "No linked DIP found. Manual review required.",
                "proposed_actions": [],
            }
            return state

        dip = state.context.matched_dips[0]

        policy = self.execution_policy_repository.find_for_service(
            state.incident.service
        )

        shared_policy_fields = self._build_shared_policy_fields(policy)

        proposed_actions = []

        for index, step in enumerate(
            dip.get("implementation_steps", []),
            start=1,
        ):
            action_id = f"uat-step-{index}"

            adapter = self._get_action_adapter(
                policy=policy,
                action_id=action_id,
            )

            proposed_actions.append(
                {
                    "action_id": action_id,
                    "action_type": adapter.get(
                        "action_type",
                        "advisory_only",
                    ),
                    "title": f"UAT implementation step {index}",
                    "description": adapter.get(
                        "description",
                        step,
                    ),
                    "environment": "uat",
                    "approval_status": "awaiting_approval",
                    "execution_status": "not_started",
                    "requires_human_approval": True,
                    "risk_level": dip.get("risk_level", "medium"),
                    "source_dip_id": dip.get("dip_id"),
                    "source_kba_id": dip.get("linked_kba_id"),
                    "approval_groups": dip.get("approval_groups", []),
                    "ansible_playbook": adapter.get("ansible_playbook"),
                    "live_execution_supported": bool(adapter),
                    **shared_policy_fields,
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
            "target_environment_order": dip.get(
                "target_environment_order",
                ["uat"],
            ),
            "proposed_actions": proposed_actions,
            "rollback_steps": dip.get("rollback_steps", []),
            "validation_steps": dip.get("validation_steps", []),
        }

        state.validation.checks = dip.get("validation_steps", [])
        state.status = "awaiting_approval"
        state.notes.append(
            f"Created action plan from {dip.get('dip_id')}."
        )

        return state


    def retrieve_operational_memory(self, state: WorkflowState) -> WorkflowState:
        if not self.operational_memory_client:
            state.notes.append("MongoDB MCP memory retrieval not enabled.")
            return state

        memory = self.operational_memory_client.retrieve_context(
            service=state.incident.service,
            symptoms=state.incident.symptoms,
            description=state.incident.description,
        )

        state.context.matched_change_records.append(memory)

        similar_incidents = memory.get("similar_incidents", [])

        if (
            not state.analysis.recommended_kba_id
            and similar_incidents
            and similar_incidents[0].get("kba_id")
        ):
            state.analysis.recommended_kba_id = similar_incidents[0]["kba_id"]
            state.notes.append(
                "Applied KBA recommendation from MongoDB MCP operational memory."
            )

        state.notes.append("Retrieved operational memory through MongoDB MCP.")
        state.status = "operational_memory_retrieved"
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