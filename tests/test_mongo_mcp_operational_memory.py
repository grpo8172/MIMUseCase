from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.agents.workflow_coordinator import WorkflowCoordinatorAgent
from app.io.mongo_mcp_memory_client import MongoMCPMemoryClient


def load_payload(path: str) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as payload_file:
        return json.load(payload_file)

class StubMongoMCPMemoryClient:
    """Deterministic test double for MongoDB MCP retrieval."""

    def retrieve_context(
        self,
        *,
        service: str | None,
        symptoms: list[str],
        description: str | None,
    ) -> dict[str, Any]:
        return {
            "source": "mongodb_mcp",
            "query": {
                "service": service,
                "symptoms": symptoms,
                "description": description,
            },
            "similar_incidents": [
                {
                    "incident_id": "INC-MCP-001",
                    "service": "Salesforce",
                    "category": "identity_access_management",
                    "short_description": "Users unable to login",
                    "description": "SSO redirect loop after SAML certificate change",
                    "kba_id": "KBA-MIM-001",
                    "dip_id": "DIP-001",
                    "validation_status": "passed",
                }
            ],
            "similar_incident_count": 1,
        }


def test_coordinator_retrieves_operational_memory_through_mongo_mcp() -> None:
    payload = {
        "incident_id": "INC9999",
        "service": "Salesforce",
        "short_description": "Users unable to login",
        "description": "SSO redirect loop after SAML certificate change",
        "severity": "SEV1",
        "priority": "P1",
        "assignment_group": "Unknown",
    }

    coordinator = WorkflowCoordinatorAgent(
        operational_memory_client=StubMongoMCPMemoryClient(),
    )

    state = coordinator.create_workflow(payload)
    state = coordinator.retrieve_operational_memory(state)

    assert state.status == "operational_memory_retrieved"
    assert "Retrieved operational memory through MongoDB MCP." in state.notes

    assert len(state.context.matched_change_records) == 1

    memory = state.context.matched_change_records[0]

    assert memory["source"] == "mongodb_mcp"
    assert memory["similar_incident_count"] == 1
    assert memory["similar_incidents"][0]["incident_id"] == "INC-MCP-001"
    assert memory["similar_incidents"][0]["kba_id"] == "KBA-MIM-001"
    assert memory["similar_incidents"][0]["dip_id"] == "DIP-001"


def test_coordinator_skips_mongo_mcp_when_client_is_not_enabled() -> None:
    payload = {
        "incident_id": "INC9999",
        "service": "Salesforce",
        "short_description": "Users unable to login",
        "description": "SSO redirect loop after SAML certificate change",
        "severity": "SEV1",
        "priority": "P1",
        "assignment_group": "Unknown",
    }

    coordinator = WorkflowCoordinatorAgent()

    state = coordinator.create_workflow(payload)
    state = coordinator.retrieve_operational_memory(state)

    assert not state.context.matched_change_records
    assert "MongoDB MCP memory retrieval not enabled." in state.notes
