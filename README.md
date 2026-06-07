## Local Demo Runbook

The MIM demo uses several independent services. Starting MongoDB alone is not enough: the MongoDB MCP server, FastAPI backend, and ADK agent must also be running.

### Architecture

```text
ADK agent / React frontend
→ FastAPI backend
→ MongoDB MCP HTTP server
→ MongoDB container

FastAPI approval endpoint
→ PlaybookRunner
→ Ansible
→ GKE control plane
→ fake-auth-service deployment
```

### Ports

| Service              |    Port |
| -------------------- | ------: |
| MongoDB              | `27017` |
| MongoDB MCP server   |  `3000` |
| FastAPI backend      |  `8000` |
| ADK web UI, optional |  `8001` |

---

### Quick Start
Make sure you have your own credentials:
```bash
gcloud auth application-default login
```
It will tell you where the credentials were saved to file. 

Save them to your tmp:
```bash
ADC_SOURCE="your_GCP_credential_directory_location"
ADC_TARGET="your_GCP_credential_directory_location"

sudo rm -rf "$ADC_TARGET"
mkdir -p "$HOME/.config/gcloud"

cp "$ADC_SOURCE" "$ADC_TARGET"
chmod 600 "$ADC_TARGET"

Start Everything:
```bash
docker compose --profile adk-web up -d --build
```
If the agent doesn't know contect seed the DB:
```bash
docker compose --profile seed run --rm mongodb-seed
```
```
Check and confirm:
```bash
docker compose exec mim-api sh -lc '
  ls -ld /tmp/gcp/application_default_credentials.json
  test -f /tmp/gcp/application_default_credentials.json &&
  echo "ADC mount is correct"
'
```
```bash
docker compose up -d --build
```
---

## 1. Start MongoDB

```bash
cd ~/mim-incident-intelligence
docker compose up -d mongodb
docker compose ps
```

---

## 2. Start the MongoDB MCP server

Run this in a separate terminal and leave it open:

```bash
cd ~/mim-incident-intelligence

export MDB_MCP_CONNECTION_STRING="mongodb://127.0.0.1:27017/?directConnection=true"

npx -y mongodb-mcp-server@latest \
  --transport http \
  --httpHost=127.0.0.1 \
  --readOnly
```

Confirm the MCP server is listening:

```bash
ss -ltnp | grep ':3000'
```

---

## 3. Start FastAPI

Run this in a separate terminal:

```bash
cd ~/mim-incident-intelligence
source .venv/bin/activate

export USE_MONGO_MCP=true
export MONGODB_MCP_URL="http://127.0.0.1:3000/mcp"

# Use false for safe local testing.
# Use true only for controlled live GKE execution.
export REAL_EXECUTION=false

PYTHONPATH=. python -m uvicorn app.api.main:app \
  --host 0.0.0.0 \
  --port 8000
```

Confirm the API is reachable:

```bash
curl -s http://127.0.0.1:8000/api/health
```

Expected:

```json
{"status":"ok"}
```

Confirm the execution mode:

```bash
curl -s http://127.0.0.1:8000/api/options | python -m json.tool
```

---

## 4. Run the ADK agent

Run this in a separate terminal:

```bash
cd ~/mim-incident-intelligence
source .venv/bin/activate

export GOOGLE_CLOUD_PROJECT="your_gcp_project_id"
export GOOGLE_CLOUD_LOCATION="global"
export GOOGLE_GENAI_USE_VERTEXAI="True"
export GEMINI_MODEL="gemini-3.1-flash-lite"
export MIM_API_BASE_URL="http://127.0.0.1:8000"

cd agents
adk run mim_agent
```

Use a single-line prompt in the CLI:

```text
Create workflow for Incident ID INC9999, Service Salesforce, Short Description Users unable to login, Description Large group of users seeing SSO redirect loop after SAML certificate change, Severity SEV1, Priority P1. Retrieve operational memory and return the grounded action plan. Do not execute anything.
```

---

## 5. Enable controlled live GKE execution

Restart FastAPI with:

```bash
export REAL_EXECUTION=true
```

Confirm:

```bash
curl -s http://127.0.0.1:8000/api/options | python -m json.tool
```

Expected:

```json
"execution_mode": "real"
```

The GKE node pool may have been scaled to zero to reduce cost. If so, restore one worker node:

```bash
gcloud container clusters resize mim-demo-cluster \
  --zone australia-southeast1-a \
  --node-pool default-pool \
  --num-nodes 1
```

Wait for the node to become ready:

```bash
kubectl get nodes -w
```

Check deployment status:

```bash
kubectl get pods \
  -n client-a-uat \
  -o wide
```

Approve an action using the explicit format:

```text
Approve workflow WF-INC9999 action uat-step-1. Set human_approved to true.
```

---

## Troubleshooting

### `httpx.ConnectError: All connection attempts failed`

MongoDB may be running while the separate MCP HTTP server is stopped.

Check:

```bash
ss -ltnp | grep -E ':27017|:3000|:8000'
```

### `Blocked: GKE location is not whitelisted`

Confirm the execution policy contains:

```json
"gke_location": "australia-southeast1-a"
```

Create a fresh workflow after updating the policy.

### Rollout timeout: `0 of 2 updated replicas are available`

Check:

```bash
kubectl get nodes
kubectl get pods -n client-a-uat -o wide
kubectl get events -n client-a-uat --sort-by='.lastTimestamp' | tail -n 40
```

If there are no worker nodes, resize the GKE node pool from `0` to `1`.

---

## Shut down after the demo

Scale the workload to zero:

```bash
kubectl scale deployment fake-auth-service \
  --replicas=0 \
  -n client-a-uat
```

Scale the node pool to zero:

```bash
gcloud container clusters resize mim-demo-cluster \
  --zone australia-southeast1-a \
  --node-pool default-pool \
  --num-nodes 0
```

Execution logs are written under:

```text
data/output/execution_logs/
```
