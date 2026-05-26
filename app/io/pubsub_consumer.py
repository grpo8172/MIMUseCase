# -----------------------------------------------------------------------------
# Pub/Sub integration
# -----------------------------------------------------------------------------

from __future__ import annotations

import json
import sys
from typing import Any

try:
    from google.cloud import pubsub_v1
except ImportError:
    pubsub_v1 = None


class PubSubIncidentConsumer:
    def __init__(self, subscription: str, worker: Any) -> None:
        if pubsub_v1 is None:
            raise RuntimeError(
                "google-cloud-pubsub is not installed. Run: pip install google-cloud-pubsub"
            )

        self.subscription = subscription
        self.worker = worker
        self.subscriber = pubsub_v1.SubscriberClient()

    def run_forever(self) -> None:
        def callback(message: Any) -> None:
            try:
                payload = json.loads(message.data.decode("utf-8"))
                result = self.worker.process(payload)
                print(result.model_dump_json(indent=2))
                message.ack()
            except Exception as exc:
                print(f"Failed to process message: {exc}", file=sys.stderr)
                message.nack()

        future = self.subscriber.subscribe(self.subscription, callback=callback)
        print(f"Listening for incident messages on {self.subscription}...")

        try:
            future.result()
        except KeyboardInterrupt:
            future.cancel()
            print("Stopped Pub/Sub consumer.")
