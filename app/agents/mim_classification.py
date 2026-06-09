from __future__ import annotations

from app.models.incident import IncomingIncident, MIMClassification

try:
    from google.cloud import pubsub_v1
except ImportError:
    pubsub_v1 = None


class MIMClassificationAgent:
    """Determines whether an incoming incident looks like a MIM use case."""

    MAJOR_HINTS = {
        "sev1",
        "sev2",
        "p1",
        "p2",
        "major",
        "outage",
        "unavailable",
        "degraded",
        "multiple users",
        "all users",
        "customer impact",
        "business impact",
        "bridge",
        "regional",
        "region",
        "global",
        "apac",
        "emea",
        "amer",
        "authentication failure",
    }

    GLOBAL_HINTS = {
        "global",
        "multi-region",
        "all regions",
        "worldwide",
        "salesforce",
        "crm",
        "vendor outage",
    }

    def classify(self, incident: IncomingIncident) -> tuple[MIMClassification, float, list[str]]:
        text = incident.searchable_text().lower()
        notes: list[str] = []
        score = 0.0

        if incident.severity and str(incident.severity).lower() in {
            "sev1",
            "sev2",
            "critical",
            "high",
        }:
            score += 0.3
            notes.append("Severity indicates potential MIM handling.")
        if incident.priority and str(incident.priority).lower() in {"p1", "p2", "critical", "high"}:
            score += 0.25
            notes.append("Priority indicates potential MIM handling.")

        matched_major_hints = [hint for hint in self.MAJOR_HINTS if hint in text]
        matched_global_hints = [hint for hint in self.GLOBAL_HINTS if hint in text]

        score += min(len(matched_major_hints) * 0.08, 0.3)
        score += min(len(matched_global_hints) * 0.1, 0.25)

        if matched_major_hints:
            notes.append(
                f"Major incident hints detected: {', '.join(sorted(matched_major_hints)[:5])}."
            )
        if matched_global_hints:
            notes.append(
                f"Global/vendor outage hints detected: {', '.join(sorted(matched_global_hints)[:5])}."
            )

        confidence = min(score, 1.0)

        if confidence < 0.25:
            return "not_mim", round(confidence, 4), notes
        if matched_global_hints and confidence >= 0.55:
            return "global_major_mim", round(confidence, 4), notes
        if confidence >= 0.45:
            return "major_mim", round(confidence, 4), notes
        return "normal_mim", round(confidence, 4), notes
