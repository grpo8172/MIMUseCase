from __future__ import annotations

import json

from app.llm.gemini_client import GeminiClient
from app.models.inspection import UseCaseFinding
from app.models.pipeline import DatasetProfile, MIMLevel, PipelineContext, TaskType


class UseCaseLLMAgent:
    """LLM agent that interprets the dataset's likely MIM use case."""

    def __init__(self, llm: GeminiClient | None):
        self.llm = llm

    def run(self, profile: DatasetProfile, context: PipelineContext) -> UseCaseFinding:
        if self.llm and self.llm.available:
            prompt = self._build_prompt(profile, context)
            try:
                return self.llm.generate_json(prompt, UseCaseFinding)  # type: ignore[return-value]
            except Exception as exc:
                return self._fallback(profile, context, note=f"LLM failed: {exc}")

        return self._fallback(
            profile, context, note="LLM unavailable; used deterministic fallback."
        )

    def _build_prompt(self, profile: DatasetProfile, context: PipelineContext) -> str:
        compact_profile = profile.model_dump(exclude={"sample_records"})
        compact_samples = profile.sample_records[:5]

        return f"""
    You are a Major Incident Management data analyst.

    Your task is to inspect an unknown client dataset and infer the most likely use case.
    The dataset may have arbitrary column names, incomplete fields, or messy operational data.

    Focus on:
    - what business process the dataset appears to describe
    - whether it looks like incident, problem, KBA, monitoring, service desk, or operational data
    - whether it supports normal MIM, major MIM, or global major incident management
    - whether it can support known-issue matching, KBA recommendation, resolver routing, severity classification, root-cause assistance, or validation recommendation
    - whether the dataset appears too incomplete and should be treated as data-quality-only

    Return only valid structured JSON matching the schema.

    Pipeline context:
    {context.model_dump_json(indent=2)}

    Dataset profile:
    {json.dumps(compact_profile, indent=2)}

    Sample records:
    {json.dumps(compact_samples, indent=2)}
    """.strip()

    def _fallback(
        self, profile: DatasetProfile, context: PipelineContext, note: str
    ) -> UseCaseFinding:
        column_roles = {column.suspected_role for column in profile.columns}
        names = " ".join(column.name.lower() for column in profile.columns)
        target_use_cases = set(context.target_use_cases)

        if (
            "kba_recommendation" in target_use_cases
            or {"kba_id", "resolution_notes"} & column_roles
        ):
            task: TaskType = "kba_recommendation"
        elif (
            "resolver_group_classification" in target_use_cases or "resolver_group" in column_roles
        ):
            task = "resolver_group_classification"
        elif "validation_recommendation" in target_use_cases or "validation_steps" in column_roles:
            task = "validation_recommendation"
        elif "severity" in column_roles or "priority" in column_roles:
            task = "severity_classification"
        else:
            task = "known_issue_matching"

        if context.client_size == "enterprise" or any(
            token in names for token in ["global", "region", "outage", "salesforce", "crm"]
        ):
            mim_level: MIMLevel = "global_major_mim"
        elif any(token in names for token in ["major", "sev1", "severity", "impact"]):
            mim_level = "major_mim"
        else:
            mim_level = "normal_mim"

        return UseCaseFinding(
            use_case_name="MIM incident intelligence",
            mim_level=mim_level,
            task_type=task,
            business_context="Dataset appears to support incident triage, known issue matching, KBA recommendation, resolver routing, or validation planning.",
            confidence=0.55,
            reason=note,
        )
