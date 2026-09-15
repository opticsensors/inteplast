# Local Compose commands, including optional external originals configuration.
$ErrorActionPreference = 'Stop'
$composeRepo = Split-Path -Parent $PSScriptRoot
$composeOptions = @('compose', '--project-directory', $composeRepo, '--env-file', (Join-Path $composeRepo '.env'))
$localConfig = Join-Path $composeRepo '.env.local'
if (Test-Path -LiteralPath $localConfig) {
    $composeOptions += @('--env-file', $localConfig)
}
& docker @composeOptions @args
exit $LASTEXITCODE
