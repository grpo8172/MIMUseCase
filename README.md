# MIM Incident Intelligence

AI-assisted Major Incident Management pipeline for inspecting incident datasets, normalising raw incident/event data, matching known issues, recommending KBAs, retrieving DIPs, producing approval-gated action plans, and validating execution outcomes.

## MVP flow

```text
Incoming payload
  -> normalise / inspect incident context
  -> compare against historical incident memory
  -> recommend KBA / resolver group
  -> retrieve linked DIP
  -> create approval-gated action plan
  -> execute only manually approved actions
  -> write execution log and validation evidence
```

## Repository structure

```text
fixtures/payloads/
  Static incoming incident payload examples.

data/input/
  Runtime seed data such as incidents, DIPs, and execution policies.

data/generated/
  Generated or normalised datasets, such as transformed cyber incident memory.

scripts/
  Dataset generation, normalisation, and MongoDB seeding scripts.

playbooks/
  Placeholder and real Ansible playbooks for approved execution.

tests/
  Pytest coverage for payloads, transformed datasets, workflow behaviour, and policy metadata propagation.
```

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run tests

```bash
PYTHONPATH=. pytest tests -q
```

## Run the pipeline inspector locally

```bash
python mim_pipeline_inspector.py \
  --payload fixtures/payloads/incoming-incident-salesforce-sso.json
```

## Run the workflow smoke test

Simulated execution is the default.

```bash
PYTHONPATH=. python mim_workflow_smoke.py \
  --payload fixtures/payloads/incoming-incident-salesforce-sso.json \
  --historical-incidents data/input/incidents.csv \
  --approve-action-id uat-step-3
```

## Run the cyber workflow smoke test

First ensure the transformed cyber dataset exists:

```bash
PYTHONPATH=. python scripts/normalize_cyber_events.py
```

Then run:

```bash
PYTHONPATH=. python mim_workflow_smoke.py \
  --payload fixtures/payloads/incoming-cyber-app-exploit.json \
  --historical-incidents data/generated/cyber_mim_incidents.csv \
  --approve-action-id uat-step-3
```

## Run with Docker

Build the image:

```bash
docker compose build
```

Start MongoDB if using local memory storage:

```bash
docker compose up -d mongodb
```

Run the inspector container:

```bash
docker compose run --rm mim-inspector
```

Run the workflow smoke container:

```bash
docker compose run --rm mim-workflow
```

## Optional: MongoDB memory layer

The workflow can use local files for development, but MongoDB is used as the intended operational memory layer for KBAs, DIPs, workflow states, execution metadata, and future incident learnings.

Start local MongoDB:

```bash
docker compose up -d mongodb
```

Set environment variables:

```bash
export MONGODB_URI="mongodb://localhost:27017"
export MONGODB_DB="mim_incident_intelligence"
export USE_MONGO=true
```

Seed MongoDB:

```bash
PYTHONPATH=. python scripts/seed_mongo.py
```

## Optional: Real GKE execution mode

Check existing clusters:
```bash
gcloud container clusters list
```

Create nodal zones:
```bash
gcloud container clusters create mim-demo-cluster \
  --zone australia-southeast1-a \
  --num-nodes 1 \
  --machine-type e2-small \
  --disk-size 20GB \
  --enable-ip-alias
```

Restore kubectl access:
```bash
gcloud container clusters get-credentials mim-demo-cluster \
  --zone australia-southeast1-a
```

View nodes:
```bash
kubectl get nodes
```

By default, the workflow uses simulated execution. This keeps local tests safe and does not require cloud infrastructure.

To run approved actions against a real GKE cluster, configure `kubectl` first:

```bash
gcloud container clusters get-credentials mim-demo-cluster \
  --zone australia-southeast1-a

kubectl get nodes
kubectl get pods -n client-a-uat
```

Create the target namespace and fake service:

```bash
kubectl create namespace client-a-uat --dry-run=client -o yaml | kubectl apply -f -

kubectl create deployment fake-auth-service \
  --image=nginx:alpine \
  --replicas=1 \
  -n client-a-uat \
  --dry-run=client -o yaml | kubectl apply -f -
```

Run the workflow in safe simulated mode:

```bash
PYTHONPATH=. python mim_workflow_smoke.py \
  --payload fixtures/payloads/incoming-incident-salesforce-sso.json \
  --historical-incidents data/input/incidents.csv \
  --approve-action-id uat-step-3
```

Run the workflow with real execution enabled:

```bash
REAL_EXECUTION=true \
PYTHONPATH=. python mim_workflow_smoke.py \
  --payload fixtures/payloads/incoming-incident-salesforce-sso.json \
  --historical-incidents data/input/incidents.csv \
  --approve-action-id uat-step-3
```

The approved action uses execution policy metadata to determine the target namespace, deployment, playbook, and execution identity. Secrets are not exposed to the workflow state; only credential references are passed through.

The GKE cluster is not required for local development. The repository includes the policy metadata and Ansible playbooks needed to target GKE, but users must configure their own cluster, namespace, `kubectl` credentials, and RBAC bindings.

## Execution policy metadata

Execution policies are stored in:

```text
data/input/policies/execution_policies.json
```

Policy metadata is propagated into workflow actions:

```text
policy_id
execution_identity
credential_ref
gke_cluster
gke_namespace
kubernetes_service_account
ansible_inventory
ansible_playbook
allowed_kubernetes_resources
allowed_kubernetes_verbs
target_deployment
desired_replicas
```

This allows the workflow to separate:

```text
MIM policy
  Decides whether the action should be allowed.

Identity / credential policy
  Decides which credential reference and execution identity are used.

GKE / Kubernetes policy
  Enforces what the runner can technically do in the target namespace.
```

## Typical demo order

```text
1. Run pytest.
2. Normalise the cyber dataset.
3. Run the IT/MIM workflow smoke test.
4. Run the cyber workflow smoke test.
5. Start MongoDB and seed memory data.
6. Optionally configure GKE.
7. Run the approved action in simulated mode.
8. Optionally run the approved action with REAL_EXECUTION=true.
9. Inspect execution logs and validation evidence.
```
## Run API and React frontend locally

Start the FastAPI backend:

```bash
cd ~/mim-incident-intelligence
PYTHONPATH=. uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

In a second terminal, start the React/Vite frontend:

```bash
cd ~/mim-incident-intelligence/frontend
npm install
npm run dev -- --host 0.0.0.0
```

Open the frontend on port `5173`.

The frontend calls the API through the Vite proxy. The API must be running on port `8000`.

Useful checks:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/options
```

## Known workflow behaviour

The system does not always create an executable remediation plan. If no matching KBA/DIP is found, it falls back to manual review.

When a matching KBA/DIP and execution policy are available, the workflow can create an approval-gated action plan and execute only the manually approved action.

This is intentional. The workflow is designed to accelerate known or well-matched incident patterns, while safely routing unknown or ambiguous incidents to manual review.

## Run API and React frontend locally

Start the FastAPI backend:

```bash
cd ~/mim-incident-intelligence
PYTHONPATH=. uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

In a second terminal, start the React/Vite frontend:

```bash
cd ~/mim-incident-intelligence/frontend
npm install
npm run dev -- --host 0.0.0.0
```

Open the frontend on port `5173`.

The frontend calls the API through the Vite proxy. The API must be running on port `8000`.

Useful checks:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/options
```

## Known workflow behaviour

The system does not always create an executable remediation plan. If no matching KBA/DIP is found, it falls back to manual review.

When a matching KBA/DIP and execution policy are available, the workflow can create an approval-gated action plan and execute only the manually approved action.

This is intentional. The workflow is designed to accelerate known or well-matched incident patterns, while safely routing unknown or ambiguous incidents to manual review.


Compose up MongoDB to use MongoDB MCP:

cd ~/mim-incident-intelligence

docker compose config --services
docker compose up -d mongodb
docker compose ps


