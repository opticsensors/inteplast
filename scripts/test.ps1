param(
    [switch]$E2E,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$TestArgs
)
$ErrorActionPreference = 'Stop'
$testRepo = Split-Path -Parent $PSScriptRoot
$testProject = "inteplast-tests-$PID-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
$composeArgs = @('compose', '--env-file', (Join-Path $testRepo '.env.example'), '--project-name', $testProject, '--file', (Join-Path $testRepo 'compose.test.yml'))
$testExit = 1
try {
    & docker @composeArgs up --build --wait backend
    if ($LASTEXITCODE -ne 0) { throw 'Could not start isolated test stack' }
    if ($E2E) {
        & docker @composeArgs run --build --rm playwright npm test -- @TestArgs
    } else {
        & docker @composeArgs exec -T backend bash scripts/test.sh @TestArgs
    }
    $testExit = $LASTEXITCODE
} finally {
    & docker @composeArgs down --remove-orphans
}
exit $testExit
