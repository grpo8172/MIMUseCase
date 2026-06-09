from __future__ import annotations

from app.agents.incident_similarity import SimilarityAgent
from app.agents.mim_classification import MIMClassificationAgent
from app.agents.resolution_db_update import ResolutionDBUpdateAgent
from app.agents.resolution_recommendation import ResolutionRecommendationAgent
from app.io.historical_incidents import HistoricalIncidentLoader
from app.io.resolution_database import ResolutionDatabase
from app.models.resolution import IncidentAnalysisResult
from app.models.worker_config import WorkerConfig


class IncidentWorker:
    def __init__(self, config: WorkerConfig) -> None:
        self.config = config
        self.historical_loader = HistoricalIncidentLoader()
        self.resolution_db = ResolutionDatabase(config.resolution_db)
        self.similarity_agent = SimilarityAgent()
        self.mim_agent = MIMClassificationAgent()
        self.resolution_agent = ResolutionRecommendationAgent()
        self.db_update_agent = ResolutionDBUpdateAgent()

    def process(self, incoming_payload: dict) -> IncidentAnalysisResult:
        historical = self.historical_loader.load(self.config.dataset_path)
        incoming = self.historical_loader._to_incoming_incident(incoming_payload)

        mim_level, mim_confidence, mim_notes = self.mim_agent.classify(incoming)

        seen_status, matches = self.similarity_agent.find_matches(
            incoming,
            historical,
            limit=self.config.similarity_limit,
        )

        kba_id, resolver_group, resolution_steps, validation_steps = (
            self.resolution_agent.recommend(incoming, matches)
        )

        update_records = self.db_update_agent.build_records(
            incoming=incoming,
            mim_level=mim_level,
            kba_id=kba_id,
            resolver_group=resolver_group,
            resolution_steps=resolution_steps,
            validation_steps=validation_steps,
            confidence=max(
                mim_confidence,
                matches[0].similarity_score if matches else 0.0,
            ),
        )

        self.resolution_db.upsert_many(update_records)

        notes = list(mim_notes)
        if seen_status == "seen_before":
            notes.append("Incoming incident strongly matches at least one historical incident.")
        elif seen_status == "possibly_seen_before":
            notes.append(
                "Incoming incident partially matches historical incidents; human validation recommended."
            )
        else:
            notes.append(
                "No similar incident found above threshold; use generic triage and append learnings."
            )

        result = IncidentAnalysisResult(
            incoming_incident=incoming,
            mim_classification=mim_level,
            mim_confidence=mim_confidence,
            seen_before_status=seen_status,
            similar_incidents=matches,
            recommended_kba_id=kba_id,
            recommended_resolver_group=resolver_group,
            recommended_resolution_steps=resolution_steps,
            recommended_validation_steps=validation_steps,
            resolution_db_updates=update_records,
            notes=notes,
        )

        if self.config.output_file:
            from pathlib import Path

            output_path = Path(self.config.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

        return result
