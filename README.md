# MIM Incident Intelligence

AI-assisted Major Incident Management pipeline for inspecting incident datasets,
identifying likely use cases, matching known issues, recommending KBAs, routing
resolver groups, and producing validation steps.

## MVP flow

```text
Job payload
  -> dataset selected from local path or GCS
  -> schema profiling
  -> LLM/use-case inspection
  -> classification/recommendation agents
  -> structured inspection result
```

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run locally

```bash
python mim_pipeline_inspector.py --payload fixtures/payloads/incoming-incident-salesforce-sso.json
```

## Run with Docker

```bash
docker compose build mim-inspector
docker compose run --rm mim-inspector
```
