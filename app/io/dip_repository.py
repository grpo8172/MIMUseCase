from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DIPRepository:
    """Loads and searches local DIP/change artefacts.

    Later this can be replaced by MongoDB MCP / MongoDB repository calls.
    """

    def __init__(self, path: str = "data/input/change_repository/dips.json") -> None:
        self.path = Path(path)

    def load_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return raw

        return [raw]

    def find_by_kba(self, kba_id: str | None) -> list[dict[str, Any]]:
        if not kba_id:
            return []

        return [
            dip
            for dip in self.load_all()
            if str(dip.get("linked_kba_id")) == kba_id
        ]

    def find_by_category_or_service(
        self,
        category: str | None = None,
        service: str | None = None,
    ) -> list[dict[str, Any]]:
        dips = self.load_all()
        results: list[dict[str, Any]] = []

        for dip in dips:
            category_match = category and str(dip.get("category")) == category
            service_match = service and str(dip.get("service", "")).lower() in service.lower()

            if category_match or service_match:
                results.append(dip)

        return results
