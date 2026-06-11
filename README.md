## Local Demo Runbook

The MIM demo uses several independent services which are interconnected and start up at the right queued times.

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
Make sure you have your own credentials and set your project ID:
```bash
gcloud auth application-default login
gcloud config set project your_project_id
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
```

Feed Redis queue to send normalized incidents straight to dashboard. 
```bash
PYTHONPATH=. python scripts/publish_normalized_cyber_events.py   --api-url="${SAFE_API_URL}"   --total-events 12   --min-delay-seconds 0.5   --max-delay-seconds 3   --burst-probability 0.4   --min-burst-size 2   --max-burst-size 4
  '
```

Manually force cert to be stale live on powershell:
```bash
kubectl patch configmap salesforce-saml-active   -n client-a-uat   --type merge   -p '{"data":{"certificate_fingerprint":"11:22:33:44:STALE"}}'
```


Watch live interaction with shell environment:
```bash
kubectl get configmap salesforce-saml-active   -n client-a-uat   --watch   --output-watch-events   -o jsonpath='{.type}{" | "}{.object.metadata.resourceVersion}{" | "}{.object.data.certificate_fingerprint}{" | "}{.object.data.metadata_version}{"\n"}'
```

Start Everything:
```bash
docker compose --profile adk-web up -d --build
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

Use a single-line prompt in the CLI:

```text
I have an incoming Incident ID INC9999, Service Salesforce, Short Description Users unable to login, Description Large group of users seeing SSO redirect loop after SAML certificate change, Severity SEV1, Priority P1. 
```

The GKE node pool may have been scaled to zero to reduce cost and 
if the certificate is fresh it will not trigger drift so set up the
env for demo purposes with this command:
```bash
ansible-playbook playbooks/salesforce/clean_environment_for_demo.yml
```

Run this when done for the day although there is autoscale so some
things may come back up.
```bash
ansible-playbook playbooks/salesforce/shut_down_k8s.yml
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

