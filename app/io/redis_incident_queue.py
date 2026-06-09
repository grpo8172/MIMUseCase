from __future__ import annotations

import json
import os
from typing import Any

import redis


DEFAULT_QUEUE_NAME = "normalized-incidents"


class RedisIncidentQueue:
    """Publishes and consumes normalized incident payloads through Redis."""

    def __init__(
        self,
        redis_url: str | None = None,
        queue_name: str | None = None,
    ) -> None:
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL",
            "redis://localhost:6379/0",
        )
        self.queue_name = queue_name or os.getenv(
            "REDIS_INCIDENT_QUEUE",
            DEFAULT_QUEUE_NAME,
        )

        self.client = redis.Redis.from_url(
            self.redis_url,
            decode_responses=True,
            socket_timeout=None,
        )

    def ping(self) -> bool:
        """Check whether Redis is reachable."""
        return bool(self.client.ping())

    def publish(self, incident: dict[str, Any]) -> int:
        """Append a normalized incident to the FIFO queue."""
        encoded_incident = json.dumps(incident)
        return int(self.client.rpush(self.queue_name, encoded_incident))

    def consume(self, timeout_seconds: int = 5) -> dict[str, Any] | None:
        """
        Wait for the oldest normalized incident.

        Returns None when the timeout expires without a message.
        """
        result = self.client.blpop(
            self.queue_name,
            timeout=timeout_seconds,
        )

        if result is None:
            return None

        _, encoded_incident = result
        return json.loads(encoded_incident)

    def size(self) -> int:
        """Return the number of incidents waiting to be processed."""
        return int(self.client.llen(self.queue_name))
