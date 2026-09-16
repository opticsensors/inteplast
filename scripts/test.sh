#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
project="inteplast-tests-$(date +%s)-$$"
compose=(docker compose --env-file "$repo_dir/.env.example" --project-name "$project" --file "$repo_dir/compose.test.yml")
cleanup() { "${compose[@]}" down --remove-orphans; }
trap cleanup EXIT

"${compose[@]}" up --build --wait backend
if [[ "${1:-}" == "--e2e" ]]; then
    shift
    "${compose[@]}" run --build --rm playwright npm test -- "$@"
else
    "${compose[@]}" exec -T backend bash scripts/test.sh "$@"
fi
