from __future__ import annotations

import re
from typing import Literal

try:
    from google.cloud import pubsub_v1
except ImportError:
    pubsub_v1 = None

from app.models.incident import IncomingIncident
from app.models.resolution import SimilarIncidentMatch

MIMClassification = Literal["normal_mim", "major_mim", "global_major_mim", "not_mim", "unknown"]
SeenBeforeStatus = Literal["seen_before", "possibly_seen_before", "not_seen_before"]


class ResolutionRecommendationAgent:
    """Recommends resolution and validation steps from similar incidents."""

    def recommend(
        self,
        incoming: IncomingIncident,
        matches: list[SimilarIncidentMatch],
    ) -> tuple[str | None, str | None, list[str], list[str]]:
        if not matches:
            return (
                None,
                incoming.assignment_group,
                self._generic_resolution(incoming),
                self._generic_validation(incoming),
            )

        top = matches[0]
        kba_id = top.kba_id
        resolver_group = top.assignment_group or incoming.assignment_group

        resolution_steps = []
        validation_steps = []

        for match in matches:
            resolution_steps.extend(self._split_steps(match.resolution_notes))
            validation_steps.extend(self._split_steps(match.validation_steps))

        if not resolution_steps:
            resolution_steps = self._generic_resolution(incoming)
        if not validation_steps:
            validation_steps = self._generic_validation(incoming)

        return (
            kba_id,
            resolver_group,
            self._dedupe_preserve_order(resolution_steps),
            self._dedupe_preserve_order(validation_steps),
        )

    @staticmethod
    def _split_steps(text: str | None) -> list[str]:
        if not text:
            return []
        parts = re.split(r"(?:\.|;|\n|\|)+", text)
        return [part.strip() for part in parts if part.strip()]

    @staticmethod
    def _dedupe_preserve_order(items: list[str]) -> list[str]:
        seen = set()
        result = []
        for item in items:
            key = item.lower()
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    @staticmethod
    def _generic_resolution(incoming: IncomingIncident) -> list[str]:
        service = incoming.service or "affected service"
        return [
            f"Confirm current impact for {service}.",
            "Check monitoring, recent changes, deployments, and dependency health.",
            "Assign the most likely resolver group based on affected service and symptoms.",
            "Search KBAs and historical incidents for matching symptoms.",
            "Apply the safest known workaround or rollback path if confirmed.",
        ]

    @staticmethod
    def _generic_validation(incoming: IncomingIncident) -> list[str]:
        service = incoming.service or "affected service"
        return [
            f"Confirm {service} health checks return to normal.",
            "Confirm affected users or business owner can complete the impacted workflow.",
            "Check error rate and latency have returned to baseline.",
            "Record the validation evidence before closing the incident.",
        ]
