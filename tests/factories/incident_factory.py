from __future__ import annotations

from datetime import UTC, datetime


def build_incident_payload(
    incident_id: str = "INC9999",
    opened_at: str | None = None,
    service: str = "Salesforce",
    short_description: str = "Users unable to login",
    description: str = (
        "Large group of users seeing SSO redirect loop after SAML certificate change"
    ),
    severity: str = "SEV1",
    priority: str = "P1",
    assignment_group: str = "Unknown",
    affected_region: str | None = None,
    customer_impact: str | None = None,
    **extra_fields: object,
) -> dict[str, object]:
    """Build an incoming incident payload with sensible defaults.

    Tests can override only the fields that matter for a scenario.
    """

    payload: dict[str, object] = {
        "incident_id": incident_id,
        "opened_at": opened_at or datetime.now(UTC).isoformat(),
        "service": service,
        "short_description": short_description,
        "description": description,
        "severity": severity,
        "priority": priority,
        "assignment_group": assignment_group,
    }

    if affected_region is not None:
        payload["affected_region"] = affected_region

    if customer_impact is not None:
        payload["customer_impact"] = customer_impact

    payload.update(extra_fields)
    return payload


def build_historical_incident_row(
    incident_id: str = "INC0001",
    opened_at: str = "2026-05-26T05:00:00Z",
    service: str = "Salesforce",
    category: str = "identity_access_management",
    short_description: str = "Users unable to login",
    description: str = "Users seeing SSO redirect loop after SAML certificate change",
    severity: str = "SEV1",
    priority: str = "P1",
    assignment_group: str = "IAM Platform Team",
    kba_id: str = "KBA-MIM-001",
    resolution_notes: str = "Updated SAML metadata and activated correct certificate",
    validation_steps: str = ("Confirmed pilot login and auth failure rate returned to baseline"),
    **extra_fields: object,
) -> dict[str, object]:
    """Build one historical incident row for CSV-style test data."""

    row: dict[str, object] = {
        "incident_id": incident_id,
        "opened_at": opened_at,
        "service": service,
        "category": category,
        "short_description": short_description,
        "description": description,
        "severity": severity,
        "priority": priority,
        "assignment_group": assignment_group,
        "kba_id": kba_id,
        "resolution_notes": resolution_notes,
        "validation_steps": validation_steps,
    }

    row.update(extra_fields)
    return row


def build_salesforce_sso_payload(**overrides: object) -> dict[str, object]:
    return build_incident_payload(
        service="Salesforce",
        short_description="Users unable to login",
        description=("Large group of users seeing SSO redirect loop after SAML certificate change"),
        severity="SEV1",
        priority="P1",
        **overrides,
    )


def build_vault_key_payload(**overrides: object) -> dict[str, object]:
    return build_incident_payload(
        service="Payments API",
        short_description="Application authentication failures",
        description="401 errors after vault key rotation and stale secret reference",
        severity="SEV2",
        priority="P2",
        **overrides,
    )


def build_pipeline_failure_payload(**overrides: object) -> dict[str, object]:
    return build_incident_payload(
        service="Deployment Pipeline",
        short_description="Change request pipeline failed",
        description="Change request pipeline failed during UAT deployment",
        severity="SEV2",
        priority="P2",
        **overrides,
    )
