from __future__ import annotations

from app.models.inspection import IncidentClassificationFinding
from app.models.pipeline import DatasetProfile


class IncidentClassificationAgent:
    """Determines what MIM decisions are possible from the available fields."""

    def run(self, profile: DatasetProfile) -> IncidentClassificationFinding:
        role_to_columns: dict[str, list[str]] = {}
        for column in profile.columns:
            role_to_columns.setdefault(column.suspected_role, []).append(column.name)

        service_cols = role_to_columns.get("service", [])
        kba_cols = role_to_columns.get("kba_id", [])
        resolver_cols = role_to_columns.get("resolver_group", [])
        resolution_cols = role_to_columns.get("resolution_notes", []) + role_to_columns.get(
            "root_cause", []
        )
        validation_cols = role_to_columns.get("validation_steps", [])
        text_cols = (
            role_to_columns.get("short_description", [])
            + role_to_columns.get("long_description", [])
            + role_to_columns.get("free_text", [])
        )

        gaps: list[str] = []
        if not text_cols:
            gaps.append("No obvious incident description/text column found.")
        if not service_cols:
            gaps.append("No obvious service/application/CMDB CI column found.")
        if not resolution_cols:
            gaps.append("No obvious resolution or root cause column found.")
        if not kba_cols:
            gaps.append("No obvious KBA/knowledge article column found.")
        if not validation_cols:
            gaps.append(
                "No explicit validation steps column found; validation may need to come from KBA/playbook retrieval."
            )

        return IncidentClassificationFinding(
            likely_incident_domain=self._infer_domain(profile),
            likely_service_columns=service_cols,
            likely_kba_columns=kba_cols,
            likely_resolver_group_columns=resolver_cols,
            likely_resolution_columns=resolution_cols,
            seen_before_matching_possible=bool(text_cols),
            kba_recommendation_possible=bool(text_cols and (kba_cols or resolution_cols)),
            validation_possible=bool(resolution_cols or validation_cols),
            gaps=gaps,
        )

    @staticmethod
    def _infer_domain(profile: DatasetProfile) -> str:
        text = " ".join(
            [column.name.lower() for column in profile.columns]
            + [" ".join(column.sample_values).lower() for column in profile.columns]
        )

        domain_keywords = {
            "identity_access_management": [
                "sso",
                "saml",
                "oauth",
                "login",
                "auth",
                "okta",
                "entra",
                "ping",
            ],
            "salesforce_crm": ["salesforce", "crm", "case", "opportunity"],
            "network": ["dns", "latency", "packet", "bgp", "router", "firewall", "vpn"],
            "database": ["database", "sql", "connection pool", "deadlock", "replica"],
            "cloud_platform": [
                "gcp",
                "aws",
                "azure",
                "region",
                "cloud run",
                "kubernetes",
                "cluster",
            ],
        }

        scores = {
            domain: sum(1 for keyword in keywords if keyword in text)
            for domain, keywords in domain_keywords.items()
        }
        best_domain, best_score = max(scores.items(), key=lambda item: item[1])
        return best_domain if best_score > 0 else "general_it_operations"
