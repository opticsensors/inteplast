param(
    [string]$Model = 'gpt-reserve',
    [ValidateSet('low', 'medium', 'high')][string]$Effort = 'low',
    [int]$Port = 11435,
    [switch]$Background,
    [string]$StateDirectory = (Join-Path $env:LOCALAPPDATA 'INTEPLAST/codex-bridge')
)

$ErrorActionPreference = 'Stop'
$nodeCommand = Get-Command node -ErrorAction Stop
$codexCommand = Get-Command codex -ErrorAction Stop
$bridgeState = [System.IO.Path]::GetFullPath($StateDirectory)
New-Item -ItemType Directory -Path $bridgeState -Force | Out-Null
$bridgeTokenFile = Join-Path $bridgeState 'bridge.token'
if (-not (Test-Path -LiteralPath $bridgeTokenFile)) {
    $randomBytes = New-Object byte[] 48
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($randomBytes) } finally { $generator.Dispose() }
    [System.IO.File]::WriteAllText($bridgeTokenFile, [Convert]::ToBase64String($randomBytes))
}

# Process-local configuration only. The application .env is never read or edited.
$env:CODEX_BRIDGE_TOKEN_FILE = $bridgeTokenFile
$env:CODEX_BRIDGE_RUNTIME_DIR = Join-Path $bridgeState 'runtime'
$env:CODEX_BRIDGE_EXECUTABLE = $codexCommand.Source
$env:CODEX_BRIDGE_MODEL = $Model
$env:CODEX_BRIDGE_EFFORT = $Effort
$env:CODEX_BRIDGE_PORT = [string]$Port
$env:CODEX_BRIDGE_HOST = '127.0.0.1'
if ($Background) {
    $bridgeScript = Join-Path $PSScriptRoot 'server.mjs'
    $bridgeProcess = Start-Process -FilePath $nodeCommand.Source -ArgumentList ('"' + $bridgeScript + '"') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $bridgeState 'bridge.log') -RedirectStandardError (Join-Path $bridgeState 'bridge-error.log')
    [System.IO.File]::WriteAllText((Join-Path $bridgeState 'bridge.pid'), [string]$bridgeProcess.Id)
    Write-Output ('Codex bridge started in background (PID ' + $bridgeProcess.Id + ').')
    exit 0
}
& $nodeCommand.Source (Join-Path $PSScriptRoot 'server.mjs')
exit $LASTEXITCODE
