from __future__ import annotations

import json
import logging
import os
import signal
from typing import Any

from app.io.redis_incident_queue import RedisIncidentQueue
from app.services.workflow_service import process_workflow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

LOGGER = logging.getLogger("normalized-incident-worker")

SHUTDOWN_REQUESTED = False


def request_shutdown(*_: Any) -> None:
    global SHUTDOWN_REQUESTED
    SHUTDOWN_REQUESTED = True
    LOGGER.info("Shutdown requested. Finishing current operation.")

def process_incident(incident: dict[str, Any]) -> None:
    incident_id = incident.get("incident_id", "unknown")

    LOGGER.info("Processing normalized incident: %s", incident_id)
    LOGGER.info("Payload: %s", incident)

    state = process_workflow(
        payload=incident,
        dataset_path=os.getenv(
            "dataset_path",
            "/app/data/generated/cyber_mim_incidents.csv",
        ),
    )

    LOGGER.info(
        "Workflow result:\n%s",
        json.dumps(
            state.model_dump(mode="json"),
            indent=2,
            default=str,
        ),
    )

def main() -> None:
    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    queue = RedisIncidentQueue()
    queue.ping()

    LOGGER.info(
        "Connected to Redis. Waiting on queue: %s",
        queue.queue_name,
    )

    while not SHUTDOWN_REQUESTED:
        incident = queue.consume(timeout_seconds=5)

        if incident is None:
            continue

        try:
            process_incident(incident)
        except Exception:
            LOGGER.exception("Incident processing failed: %s", incident)


if __name__ == "__main__":
    main()
