from __future__ import annotations

from pathlib import Path

try:
    from google.cloud import storage
except ImportError:
    storage = None


class StorageIO:
    """Reads and writes local paths or gs:// URIs."""

    def __init__(self) -> None:
        self._storage_client = None

    def read_bytes(self, uri: str) -> bytes:
        if uri.startswith("gs://"):
            bucket_name, blob_name = self._parse_gcs_uri(uri)
            blob = self._get_bucket(bucket_name).blob(blob_name)
            return blob.download_as_bytes()

        return Path(uri).read_bytes()

    def write_text(self, uri: str, text: str, content_type: str = "application/json") -> None:
        if uri.startswith("gs://"):
            bucket_name, blob_name = self._parse_gcs_uri(uri)
            blob = self._get_bucket(bucket_name).blob(blob_name)
            blob.upload_from_string(text, content_type=content_type)
            return

        output_path = Path(uri)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")

    def _get_bucket(self, bucket_name: str):
        if storage is None:
            raise RuntimeError(
                "google-cloud-storage is not installed. Run: pip install google-cloud-storage"
            )

        if self._storage_client is None:
            self._storage_client = storage.Client()

        return self._storage_client.bucket(bucket_name)

    @staticmethod
    def _parse_gcs_uri(uri: str) -> tuple[str, str]:
        path = uri.removeprefix("gs://")
        bucket_name, _, blob_name = path.partition("/")

        if not bucket_name or not blob_name:
            raise ValueError(f"Invalid GCS URI: {uri}")

        return bucket_name, blob_name
