from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from app.io.storage import StorageIO


class DatasetLoader:
    """Loads CSV, JSON, JSONL, Parquet, or Excel from local disk or GCS."""

    SUPPORTED_EXTENSIONS = {".csv", ".json", ".jsonl", ".parquet", ".xlsx", ".xls"}

    def __init__(self, storage_io: StorageIO) -> None:
        self.storage_io = storage_io

    def load(self, uri: str) -> pd.DataFrame:
        suffix = self._suffix(uri)

        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported input type '{suffix}'. Supported: {sorted(self.SUPPORTED_EXTENSIONS)}"
            )

        raw_bytes = self.storage_io.read_bytes(uri)
        buffer = io.BytesIO(raw_bytes)

        if suffix == ".csv":
            return pd.read_csv(buffer)
        if suffix == ".json":
            return pd.read_json(buffer)
        if suffix == ".jsonl":
            return pd.read_json(buffer, lines=True)
        if suffix == ".parquet":
            return pd.read_parquet(buffer)
        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(buffer)

        raise ValueError(f"Unsupported input type: {suffix}")

    @staticmethod
    def _suffix(uri: str) -> str:
        return Path(uri.split("?")[0]).suffix.lower()
