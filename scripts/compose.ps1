# Compatibility alias. From the repository root, use docker compose directly.
$ErrorActionPreference = 'Stop'
$composeRepo = Split-Path -Parent $PSScriptRoot
$composeOptions = @('compose', '--project-directory', $composeRepo, '--env-file', (Join-Path $composeRepo '.env'))
& docker @composeOptions @args
exit $LASTEXITCODE
