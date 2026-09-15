#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
compose_options=(compose --project-directory "$repo_dir" --env-file "$repo_dir/.env")
if [[ -f "$repo_dir/.env.local" ]]; then
  compose_options+=(--env-file "$repo_dir/.env.local")
fi
exec docker "${compose_options[@]}" "$@"
