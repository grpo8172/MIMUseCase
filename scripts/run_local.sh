#!/usr/bin/env bash
set -euo pipefail

python mim_pipeline_inspector.py --payload fixtures/payloads/incoming-incident-salesforce-sso.json
