# -----------------------------------------------------------------------------
# Pipeline service
# -----------------------------------------------------------------------------
from __future__ import annotations

from app.agents.feature_label import FeatureLabelAgent
from app.agents.incident_classification import IncidentClassificationAgent
from app.agents.orchestrator import InspectionOrchestratorAgent
from app.agents.schema_profiler import SchemaProfilerAgent
from app.agents.use_case_llm import UseCaseLLMAgent
from app.io.dataset_loader import DatasetLoader
from app.io.storage import StorageIO
from app.llm.gemini_client import GeminiClient
from app.models.inspection import InspectionResult
from app.models.pipeline import PipelineJob


class MIMInspectionPipeline:
    def __init__(
        self, storage_io: StorageIO | None = None, llm: GeminiClient | None = None
    ) -> None:
        self.storage_io = storage_io or StorageIO()
        self.dataset_loader = DatasetLoader(self.storage_io)
        self.schema_agent = SchemaProfilerAgent()
        self.llm = llm
        self.use_case_agent = UseCaseLLMAgent(self.llm)
        self.incident_agent = IncidentClassificationAgent()
        self.feature_label_agent = FeatureLabelAgent()
        self.orchestrator_agent = InspectionOrchestratorAgent()

    def run(self, job: PipelineJob) -> InspectionResult:
        df = self.dataset_loader.load(job.dataset_uri)
        profile = self.schema_agent.run(
            df, source_uri=job.dataset_uri, sample_rows=job.max_sample_rows
        )

        use_case = self.use_case_agent.run(profile, job.context)
        incident = self.incident_agent.run(profile)
        features = self.feature_label_agent.run(profile)

        result = self.orchestrator_agent.run(job, profile, use_case, incident, features)

        if job.output_uri:
            self.storage_io.write_text(job.output_uri, result.model_dump_json(indent=2))

        return result
