from __future__ import annotations

from app.io.storage import StorageIO
from app.models.pipeline import PipelineJob


class PayloadLoader:
    """Loads a PipelineJob from a JSON payload file, local or GCS."""

    def __init__(self, storage_io: StorageIO) -> None:
        self.storage_io = storage_io

    def load(self, payload_uri: str) -> PipelineJob:
        raw = self.storage_io.read_bytes(payload_uri).decode("utf-8")
        return PipelineJob.model_validate_json(raw)
