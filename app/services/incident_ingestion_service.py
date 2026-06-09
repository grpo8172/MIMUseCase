from __future__ import annotations

from typing import Any

from app.io.redis_incident_queue import RedisIncidentQueue
from app.services.normalized_cyber_events import CyberEventNormalizer


class IncidentIngestionService:
    """Normalizes incoming cyber events and publishes them to Redis."""

    def __init__(
        self,
        normalizer: CyberEventNormalizer | None = None,
        incident_queue: RedisIncidentQueue | None = None,
    ) -> None:
        self.normalizer = normalizer or CyberEventNormalizer()
        self.incident_queue = incident_queue or RedisIncidentQueue()

    def ingest(self, raw_event: dict[str, Any]) -> dict[str, Any]:
        normalized_event = self.normalizer.normalize(raw_event)

        if hasattr(normalized_event, "model_dump"):
            queue_payload = normalized_event.model_dump(mode="json")
        else:
            queue_payload = normalized_event

        queue_length = self.incident_queue.publish(queue_payload)

        return {
            "incident_id": queue_payload["incident_id"],
            "status": "queued",
            "queue_name": self.incident_queue.queue_name,
            "queue_length": queue_length,
        }
