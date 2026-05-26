from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Literal

try:
    from google.cloud import pubsub_v1
except ImportError:
    pubsub_v1 = None

from app.models.incident import IncomingIncident, MIMClassification
from app.models.resolution import ResolutionStepRecord

SeenBeforeStatus = Literal["seen_before", "possibly_seen_before", "not_seen_before"]


class ResolutionDBUpdateAgent:
    """Creates reusable resolution DB records from the processed incident."""

    def build_records(
        self,
        incoming: IncomingIncident,
        mim_level: MIMClassification,
        kba_id: str | None,
        resolver_group: str | None,
        resolution_steps: list[str],
        validation_steps: list[str],
        confidence: float,
    ) -> list[ResolutionStepRecord]:
        now = datetime.now(UTC).isoformat()
        service = incoming.service or "unknown_service"
        source_incident_id = incoming.incident_id or f"incoming-{now}"
        category = self._infer_category(incoming)
        resolution_id = self._resolution_id(service, category, kba_id, resolution_steps)

        symptoms = [
            value
            for value in [
                incoming.short_description,
                incoming.description,
                incoming.customer_impact,
            ]
            if value
        ]

        return [
            ResolutionStepRecord(
                resolution_id=resolution_id,
                source_incident_id=source_incident_id,
                service=service,
                category=category,
                mim_level=mim_level,
                kba_id=kba_id,
                resolver_group=resolver_group,
                symptoms=symptoms,
                resolution_steps=resolution_steps,
                validation_steps=validation_steps,
                confidence=confidence,
                first_seen_at=now,
                last_seen_at=now,
                times_seen=1,
            )
        ]

    @staticmethod
    def _infer_category(incoming: IncomingIncident) -> str:
        text = incoming.searchable_text().lower()
        if any(token in text for token in ["sso", "saml", "login", "auth", "certificate"]):
            return "identity_access_management"
        if any(token in text for token in ["latency", "timeout", "api", "queue"]):
            return "platform_reliability"
        if any(token in text for token in ["mailbox", "email", "exchange"]):
            return "messaging"
        if any(token in text for token in ["dns", "network", "vpn", "firewall"]):
            return "network"
        return "general_it_operations"

    @staticmethod
    def _resolution_id(service: str, category: str, kba_id: str | None, steps: list[str]) -> str:
        base = f"{service}-{category}-{kba_id or 'NO-KBA'}-{' '.join(steps)[:40]}".lower()
        safe = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
        return f"RES-{safe[:80]}"
