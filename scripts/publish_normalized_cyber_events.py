from __future__ import annotations

import argparse
import csv
import json
import random
import time
import urllib.request
from pathlib import Path
from typing import Any

from app.io.redis_incident_queue import RedisIncidentQueue


def load_events(input_file: str) -> list[dict[str, Any]]:
    source = Path(input_file)

    with source.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def publish_event(
    queue: RedisIncidentQueue | None,
    incident: dict[str, Any],
    *,
    sequence_number: int,
    api_url: str | None,
    burst_id: str | None = None,
) -> None:
    if api_url:
        body = json.dumps({"payload": incident}).encode("utf-8")

        request = urllib.request.Request(
            f"{api_url.rstrip('/')}/api/workflows",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status not in {200, 201}:
                raise RuntimeError(
                    f"Hosted API returned HTTP {response.status}"
                )

        print(
            f"Published {sequence_number}: "
            f"{incident.get('incident_id')} "
            f"(target=hosted-api, burst_id={burst_id or 'none'})"
        )
        return

    if queue is None:
        raise RuntimeError(
            "Redis queue is required when --api-url is not set."
        )

    queue_length = queue.publish(incident)

    print(
        f"Queued {sequence_number}: "
        f"{incident.get('incident_id')} "
        f"(queue_length={queue_length}, burst_id={burst_id or 'none'})"
    )


def publish_random_stream(
    *,
    input_file: str,
    total_events: int,
    min_delay_seconds: float,
    max_delay_seconds: float,
    burst_probability: float,
    min_burst_size: int,
    max_burst_size: int,
    seed: int | None,
    api_url: str | None,
) -> None:
    rng = random.Random(seed)
    queue = None if api_url else RedisIncidentQueue()
    events = load_events(input_file)

    if not events:
        raise ValueError(f"No incidents found in {input_file}")

    published_count = 0
    burst_counter = 0

    while published_count < total_events:
        should_send_burst = rng.random() < burst_probability

        if should_send_burst:
            burst_counter += 1
            burst_id = f"BURST-{burst_counter:03d}"

            remaining = total_events - published_count
            burst_size = min(
                rng.randint(min_burst_size, max_burst_size),
                remaining,
            )

            print(f"\nStarting {burst_id} with {burst_size} events")

            for _ in range(burst_size):
                incident = rng.choice(events)
                published_count += 1

                publish_event(
                    queue,
                    incident,
                    sequence_number=published_count,
                    api_url=api_url,
                    burst_id=burst_id,
                )

                # Small jitter inside a burst so events arrive almost together.
                time.sleep(rng.uniform(0.05, 0.3))

        else:
            incident = rng.choice(events)
            published_count += 1

            publish_event(
                queue,
                incident,
                sequence_number=published_count,
                api_url=api_url,
            )

        if published_count < total_events:
            delay = rng.uniform(
                min_delay_seconds,
                max_delay_seconds,
            )

            print(f"Waiting {delay:.2f} seconds\n")
            time.sleep(delay)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish a randomized stream of normalized cyber incidents."
    )

    parser.add_argument(
        "--api-url",
        help=(
            "Optional hosted API base URL. "
            "When set, publish via POST /api/workflows instead of Redis."
        ),
    )

    parser.add_argument(
        "--input-file",
        default="data/generated/cyber_mim_incidents.csv",
    )

    parser.add_argument(
        "--total-events",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--min-delay-seconds",
        type=float,
        default=0.5,
    )

    parser.add_argument(
        "--max-delay-seconds",
        type=float,
        default=4.0,
    )

    parser.add_argument(
        "--burst-probability",
        type=float,
        default=0.35,
    )

    parser.add_argument(
        "--min-burst-size",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--max-burst-size",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--seed",
        type=int,
    )

    args = parser.parse_args()

    publish_random_stream(
        input_file=args.input_file,
        total_events=args.total_events,
        min_delay_seconds=args.min_delay_seconds,
        max_delay_seconds=args.max_delay_seconds,
        burst_probability=args.burst_probability,
        min_burst_size=args.min_burst_size,
        max_burst_size=args.max_burst_size,
        seed=args.seed,
        api_url=args.api_url,
    )


if __name__ == "__main__":
    main()
