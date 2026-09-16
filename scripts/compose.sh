#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# Compatibility alias. From the repository root, use docker compose directly.
compose_options=(compose --project-directory "$repo_dir" --env-file "$repo_dir/.env")
exec docker "${compose_options[@]}" "$@"
