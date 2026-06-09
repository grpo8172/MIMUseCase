"""
MIM Incident Pub/Sub Worker
===========================

CLI entry point for the MIM incident worker.

The actual worker logic lives under app/.
This file only parses command-line arguments, builds WorkerConfig, and starts
either a local incoming-incident run or a Pub/Sub consumer.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.io.pubsub_consumer import PubSubIncidentConsumer
from app.models.worker_config import WorkerConfig
from app.services.incident_worker import IncidentWorker


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify incoming incidents and recommend MIM/KBA resolution steps."
    )
    parser.add_argument(
        "--incoming-file",
        help="Local JSON file containing a single incoming incident payload.",
    )
    parser.add_argument(
        "--subscription",
        help="Pub/Sub subscription path for incoming incident messages.",
    )
    parser.add_argument("--historical-incidents", default="data/generated/cyber_mim_incidents.csv")
    parser.add_argument(
        "--resolution-db",
        default="data/resolution_db/incident_resolution_steps.jsonl",
    )
    parser.add_argument("--output-file", default="data/output/incoming-incident-analysis.json")
    parser.add_argument("--similarity-limit", type=int, default=5)
    return parser.parse_args()


def load_incoming_file(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()

    if not args.incoming_file and not args.subscription:
        raise SystemExit(
            "Provide either --incoming-file for local testing or --subscription for Pub/Sub polling."
        )

    config = WorkerConfig(
        historical_incidents=args.historical_incidents,
        resolution_db=args.resolution_db,
        output_file=args.output_file,
        similarity_limit=args.similarity_limit,
    )
    worker = IncidentWorker(config)

    if args.incoming_file:
        payload = load_incoming_file(args.incoming_file)
        result = worker.process(payload)
        print(result.model_dump_json(indent=2))
        return

    consumer = PubSubIncidentConsumer(args.subscription, worker)
    consumer.run_forever()


if __name__ == "__main__":
    main()
