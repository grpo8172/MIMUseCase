"""
MIM Pipeline Inspector
======================

Starter Python file for a GCP-based Major Incident Management intelligence pipeline.

Design goal:
    The pipeline does not require the analyst to manually hard-code every dataset shape.
    A job payload tells the service which dataset to ingest from GCS, what context applies,
    and where to write the inspection output.

Current version:
    - Accepts a pipeline job payload as JSON.
    - Loads a dataset from GCS or local disk.
    - Profiles the dataset deterministically.
    - Runs multiple agent-style components:
        1. SchemaProfilerAgent
        2. UseCaseLLMAgent
        3. IncidentClassificationAgent
        4. FeatureLabelAgent
        5. OrchestratorAgent
    - Produces a structured JSON inspection result.

Install:
    pip install pandas pydantic google-cloud-storage google-genai pyarrow openpyxl

GCP auth for local development:
    gcloud auth application-default login
    export GOOGLE_CLOUD_PROJECT="your-project-id"
    export GOOGLE_CLOUD_LOCATION="australia-southeast1"

Example payload file:
    {
      "job_id": "mim-demo-001",
      "dataset_uri": "gs://your-bucket/mim/input/incidents.csv",
      "context": {
        "domain": "major_incident_management",
        "client_size": "enterprise",
        "target_use_cases": [
          "known_issue_matching",
          "kba_recommendation",
          "resolver_group_classification",
          "validation_recommendation"
        ]
      },
      "output_uri": "gs://your-bucket/mim/output/mim-demo-001-inspection.json"
    }

Run with payload:
    python mim_pipeline_inspector.py --payload ./fixtures/payloads/incoming-incident-salesforce-sso.json

Run directly without payload:
    python mim_pipeline_inspector.py \
      --dataset-uri gs://your-bucket/mim/input/incidents.csv \
      --output-uri ./out/inspection.json
"""

from __future__ import annotations

import argparse

try:
    from google.cloud import storage
except ImportError:  # optional for local-only testing
    storage = None

try:
    from google import genai
    from google.genai import types
except ImportError:  # allows deterministic fallback mode
    genai = None
    types = None

from typing import get_args

from app.io.payload_loader import PayloadLoader
from app.io.storage import StorageIO
from app.llm.gemini_client import GeminiClient
from app.models.pipeline import PipelineContext, PipelineJob, TaskType
from app.services.pipeline import MIMInspectionPipeline

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def build_job_from_args(args: argparse.Namespace, storage_io: StorageIO) -> PipelineJob:
    if args.payload:
        return PayloadLoader(storage_io).load(args.payload)

    if not args.dataset_uri:
        raise ValueError("Provide either --payload or --dataset-uri")

    context = PipelineContext(
        domain=args.domain,
        client_size=args.client_size,
        target_use_cases=args.target_use_case or [],
        notes=args.notes or "",
    )

    return PipelineJob(
        job_id=args.job_id,
        dataset_uri=args.dataset_uri,
        output_uri=args.output_uri,
        context=context,
        max_sample_rows=args.max_sample_rows,
        llm_enabled=not args.disable_llm,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect an incident/MIM dataset and infer use case, features, labels, and next steps."
    )

    parser.add_argument("--payload", help="Path or gs:// URI to a JSON PipelineJob payload.")
    parser.add_argument("--job-id", default="manual-run")
    parser.add_argument(
        "--dataset-uri", help="Dataset path or gs:// URI. Used when --payload is not provided."
    )
    parser.add_argument(
        "--output-uri", help="Where to write the inspection JSON. Supports local path or gs:// URI."
    )
    parser.add_argument("--domain", default="major_incident_management")
    parser.add_argument(
        "--client-size", choices=["small", "medium", "enterprise", "unknown"], default="unknown"
    )
    parser.add_argument("--target-use-case", action="append", choices=list(get_args(TaskType)))
    parser.add_argument("--notes", default="")
    parser.add_argument("--max-sample-rows", type=int, default=5)
    parser.add_argument("--disable-llm", action="store_true")
    parser.add_argument("--model", default="gemini-2.5-flash")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    storage_io = StorageIO()
    job = build_job_from_args(args, storage_io)

    llm = None
    if job.llm_enabled:
        llm = GeminiClient(model=args.model)

    pipeline = MIMInspectionPipeline(storage_io=storage_io, llm=llm)
    result = pipeline.run(job)

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
