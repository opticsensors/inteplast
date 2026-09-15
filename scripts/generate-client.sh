#! /usr/bin/env bash

set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir/backend"
# The test-only API is included in the SDK for E2E provisioning. No DB is opened.
ENABLE_TEST_ROUTES=true ENVIRONMENT=local POSTGRES_DB=app_test \
  uv run python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > ../frontend/openapi.json
cd "$repo_dir"
npm run generate-client --workspace frontend
