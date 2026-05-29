from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.agents.execution_agent import ExecutionAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.workflow_coordinator import WorkflowCoordinatorAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full MIM workflow smoke test."
    )
    parser.add_argument(
        "--payload",
        default="fixtures/payloads/incoming-incident-salesforce-sso.json",
        help="Path to incoming incident payload JSON.",
    )
    parser.add_argument(
        "--historical-incidents",
        default="data/input/incidents.csv",
        help="Path to canonical historical incidents CSV.",
    )
    parser.add_argument(
        "--resolution-db",
        default="data/resolution_db/incident_resolution_steps.jsonl",
        help="Path to local resolution memory JSONL.",
    )
    parser.add_argument(
        "--approve-action-id",
        default="uat-step-3",
        help="Action ID to simulate as manually approved.",
    )
    parser.add_argument(
        "--output-file",
        default="data/output/full-workflow-state.json",
        help="Where to write the final workflow state.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))

    coordinator = WorkflowCoordinatorAgent(
        historical_incidents_path=args.historical_incidents,
        resolution_db_path=args.resolution_db,
    )

    state = coordinator.create_workflow(payload)
    state = coordinator.analyse(state)
    state = coordinator.retrieve_dip_context(state)
    state = coordinator.create_action_plan(state)

    state = coordinator.approve_action(state, args.approve_action_id)

    state = ExecutionAgent().execute_approved_actions(state)
    state = ValidationAgent().validate(state)

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    print(state.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
