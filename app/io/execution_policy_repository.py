from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ExecutionPolicyRepository:
    """Loads execution policies.

    Later this can come from MongoDB, GCS, or Terraform-managed policy files.
    """

    def __init__(self, path: str = "data/input/policies/execution_policies.json") -> None:
        self.path = Path(path)

    def load_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else [raw]

    def find_for_service(self, service: str | None) -> dict[str, Any] | None:
        policies = self.load_all()

        if service:
            for policy in policies:
                if str(policy.get("service", "")).lower() == service.lower():
                    return policy

        for policy in policies:
            if policy.get("service") == "*":
                return policy

        return None
