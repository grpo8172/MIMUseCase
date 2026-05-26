from __future__ import annotations

import math
import re
from collections import Counter

from app.models.incident import (
    HistoricalIncident,
    IncomingIncident,
    SeenBeforeStatus,
)
from app.models.resolution import SimilarIncidentMatch

try:
    from google.cloud import pubsub_v1
except ImportError:
    pubsub_v1 = None


class SimilarityAgent:
    """Deterministic bag-of-words similarity for MVP seen-before matching."""

    def __init__(self, seen_threshold: float = 0.62, possible_threshold: float = 0.35) -> None:
        self.seen_threshold = seen_threshold
        self.possible_threshold = possible_threshold

    def find_matches(
        self,
        incoming: IncomingIncident,
        historical: list[HistoricalIncident],
        limit: int = 5,
    ) -> tuple[SeenBeforeStatus, list[SimilarIncidentMatch]]:
        incoming_text = incoming.searchable_text()
        scored: list[SimilarIncidentMatch] = []

        for incident in historical:
            score = self._cosine_similarity(incoming_text, incident.searchable_text())
            if self._same_service(incoming, incident):
                score = min(score + 0.12, 1.0)
            if self._same_priority_or_severity(incoming, incident):
                score = min(score + 0.08, 1.0)

            if score >= self.possible_threshold:
                scored.append(
                    SimilarIncidentMatch(
                        incident_id=incident.incident_id,
                        similarity_score=round(score, 4),
                        service=incident.service,
                        short_description=incident.short_description,
                        severity=incident.severity,
                        priority=incident.priority,
                        assignment_group=incident.assignment_group,
                        kba_id=incident.kba_id,
                        resolution_notes=incident.resolution_notes,
                        validation_steps=incident.validation_steps,
                    )
                )

        scored.sort(key=lambda item: item.similarity_score, reverse=True)
        matches = scored[:limit]

        if matches and matches[0].similarity_score >= self.seen_threshold:
            return "seen_before", matches
        if matches:
            return "possibly_seen_before", matches
        return "not_seen_before", []

    @staticmethod
    def _same_service(incoming: IncomingIncident, historical: HistoricalIncident) -> bool:
        if not incoming.service or not historical.service:
            return False
        return incoming.service.strip().lower() == historical.service.strip().lower()

    @staticmethod
    def _same_priority_or_severity(
        incoming: IncomingIncident, historical: HistoricalIncident
    ) -> bool:
        incoming_tokens = {
            str(incoming.priority or "").lower(),
            str(incoming.severity or "").lower(),
        }
        historical_tokens = {
            str(historical.priority or "").lower(),
            str(historical.severity or "").lower(),
        }
        return bool((incoming_tokens - {""}) & (historical_tokens - {""}))

    def _cosine_similarity(self, left: str, right: str) -> float:
        left_vector = self._term_vector(left)
        right_vector = self._term_vector(right)
        if not left_vector or not right_vector:
            return 0.0

        terms = set(left_vector) | set(right_vector)
        dot = sum(left_vector.get(term, 0) * right_vector.get(term, 0) for term in terms)
        left_norm = math.sqrt(sum(value * value for value in left_vector.values()))
        right_norm = math.sqrt(sum(value * value for value in right_vector.values()))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)

    @staticmethod
    def _term_vector(text: str) -> Counter[str]:
        tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "to",
            "of",
            "in",
            "on",
            "for",
            "with",
            "after",
            "before",
            "user",
            "users",
            "issue",
            "incident",
            "multiple",
        }
        return Counter(token for token in tokens if token not in stop_words and len(token) > 2)
