from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from app.io.redis_incident_queue import RedisIncidentQueue


def publish_events(
    input_file: str,
    delay_seconds: float,
    limit: int | None,
) -> None:
    queue = RedisIncidentQueue()
    source = Path(input_file)

    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)

        for index, incident in enumerate(reader, start=1):
            if limit is not None and index > limit:
                break

            queue_length = queue.publish(incident)

            print(
                f"Queued {index}: "
                f"{incident.get('incident_id', 'unknown')} "
                f"(queue_length={queue_length})"
            )

            if delay_seconds > 0:
                time.sleep(delay_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish normalized cyber incidents to Redis."
    )

    parser.add_argument(
        "--input-file",
        default="data/generated/cyber_mim_incidents.csv",
    )

    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=1.0,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
    )

    args = parser.parse_args()

    publish_events(
        input_file=args.input_file,
        delay_seconds=args.delay_seconds,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
