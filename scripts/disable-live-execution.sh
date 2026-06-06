#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../infra"

terraform apply \
  -auto-approve \
  -var="real_execution=false" \
  -var="gke_worker_nodes=0"