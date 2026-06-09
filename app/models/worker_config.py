# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------
from dataclasses import dataclass


@dataclass
class WorkerConfig:
    dataset_path: str
    resolution_db: str
    output_file: str | None = None
    similarity_limit: int = 5
