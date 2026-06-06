from __future__ import annotations

import os
from dataclasses import dataclass

import google.auth
from google.auth.transport.requests import AuthorizedSession


@dataclass(frozen=True)
class GkeSettings:
    project_id: str
    location: str
    cluster_name: str
    node_pool_name: str = "default-pool"

    @classmethod
    def from_env(cls) -> "GkeSettings":
        return cls(
            project_id=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ["GKE_CLUSTER_LOCATION"],
            cluster_name=os.environ["GKE_CLUSTER_NAME"],
            node_pool_name=os.getenv("GKE_NODE_POOL_NAME", "default-pool"),
        )


def _node_pool_name(settings: GkeSettings) -> str:
    return (
        f"projects/{settings.project_id}"
        f"/locations/{settings.location}"
        f"/clusters/{settings.cluster_name}"
        f"/nodePools/{settings.node_pool_name}"
    )


def set_node_pool_size(node_count: int) -> dict:
    if node_count not in {0, 1}:
        raise ValueError("Demo node count must be either 0 or 1.")

    settings = GkeSettings.from_env()
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    session = AuthorizedSession(credentials)

    name = _node_pool_name(settings)
    url = f"https://container.googleapis.com/v1/{name}:setSize"

    response = session.post(
        url,
        json={
            "name": name,
            "nodeCount": node_count,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
