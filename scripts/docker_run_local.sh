#!/usr/bin/env bash
set -euo pipefail

docker compose --profile local-file run --rm mim-inspector-local-file
