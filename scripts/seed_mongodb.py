from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pymongo import MongoClient


MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "mim")

DATA_ROOT = Path("/app/data")
FIXTURES_ROOT = Path("/app/fixtures")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def upsert_documents(
    collection,
    documents: list[dict[str, Any]],
    key: str,
) -> int:
    count = 0

    for document in documents:
        if key not in document:
            raise ValueError(f"Missing required key '{key}' in document: {document}")

        collection.update_one(
            {key: document[key]},
            {"$set": document},
            upsert=True,
        )
        count += 1

    return count


def main() -> None:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")

    database = client[MONGODB_DATABASE]

    similar_incidents = [
        {
            "incident_id": "INC-MCP-001",
            "service": "Salesforce",
            "category": "identity_access_management",
            "short_description": "Users unable to login",
            "description": "SSO redirect loop after SAML certificate change",
            "dip_id": "DIP-001",
            "kba_id": "KBA-MIM-001",
            "validation_status": "passed",
        }
    ]

    dips_path = DATA_ROOT / "input" / "change_repository" / "dips.json"
    kbas_path = DATA_ROOT / "kbas" / "kba_seed.json"
    policies_path = DATA_ROOT / "input" / "policies" / "execution_policies.json"
    playbooks_path = DATA_ROOT / "playbooks" / "validation_playbooks.json"

    dips = load_json(dips_path) if dips_path.exists() else []
    kbas = load_json(kbas_path) if kbas_path.exists() else []
    policies = load_json(policies_path) if policies_path.exists() else []
    validation_playbooks = (
        load_json(playbooks_path)
        if playbooks_path.exists()
        else []
    )

    results = {
        "similar_incidents": upsert_documents(
            database["similar_incidents"],
            similar_incidents,
            "incident_id",
        ),
        "dips": upsert_documents(
            database["dips"],
            dips,
            "dip_id",
        ) if dips else 0,
        "kbas": upsert_documents(
            database["kbas"],
            kbas,
            "kba_id",
        ) if kbas else 0,
        "execution_policies": upsert_documents(
            database["execution_policies"],
            policies,
            "policy_id",
        ) if policies else 0,
        "validation_playbooks": upsert_documents(
            database["validation_playbooks"],
            validation_playbooks,
            "playbook_id",
        ) if validation_playbooks else 0,
    }

    print("MongoDB seed completed successfully.")
    for collection, count in results.items():
        print(f"{collection}: {count}")


if __name__ == "__main__":
    main()
