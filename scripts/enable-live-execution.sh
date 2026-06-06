#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../infra"

terraform init

terraform apply \
  -auto-approve \
  -var="real_execution=true" \
  -var="gke_worker_nodes=1"

gcloud container clusters get-credentials mim-demo-cluster \
  --zone australia-southeast1-a

echo "Waiting for the GKE node..."
kubectl wait \
  --for=condition=Ready \
  node \
  --all \
  --timeout=300s

echo "Current workload status:"
kubectl get pods \
  -n client-a-uat \
  -o wide