# Run from the PC. The remote checkout always follows the published main branch.
[CmdletBinding(DefaultParameterSetName = 'Deploy')]
param(
    [ValidatePattern('^[a-zA-Z0-9][a-zA-Z0-9.-]*$')]
    [string]$Server = 'euredinteplast.local.eurecat.org',
    [ValidatePattern('^[a-zA-Z0-9_][a-zA-Z0-9_.-]*$')]
    [string]$User = $env:USERNAME,
    [Parameter(ParameterSetName = 'Deploy')]
    [string]$ConfigDirectory,
    [Parameter(Mandatory, ParameterSetName = 'Prepare')]
    [switch]$PrepareOnly
)

$ErrorActionPreference = 'Stop'
$destination = "$User@$Server"
$sshOptions = @('-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=30')
$stage = '-'
$mode = if ($PrepareOnly) { 'prepare' } else { 'deploy' }
$files = @('.env.production', 'fullchain.pem', 'privkey.pem')

if ($ConfigDirectory) {
    $paths = foreach ($file in $files) {
        $path = Get-Item -LiteralPath (Join-Path $ConfigDirectory $file)
        if ($path.PSIsContainer -or $path.Length -eq 0) { throw "Fichero vacio o no valido: $file" }
        $path.FullName
    }
    $stage = '.config/.inteplast-setup-' + [guid]::NewGuid().ToString('N')
    $existing = & ssh @sshOptions $destination "umask 077 && mkdir -p .config && if test -d .config/inteplast; then echo installed; else mkdir $stage && echo upload; fi"
    if ($LASTEXITCODE -ne 0) { throw 'Fallo al preparar la configuracion por SSH.' }
    if ($existing -contains 'installed') {
        Write-Host 'Se conserva la configuracion privada existente del servidor.'
        $stage = '-'
    } elseif ($existing -contains 'upload') {
        & scp @sshOptions @paths "${destination}:$stage/"
        if ($LASTEXITCODE -ne 0) {
            & ssh @sshOptions $destination "cd $stage && rm -f -- .env.production fullchain.pem privkey.pem && cd .. && rmdir -- $(Split-Path -Leaf $stage)"
            throw 'Transferencia incompleta. Vuelve a ejecutar el comando.'
        }
    } else {
        throw 'Respuesta inesperada al preparar la configuracion remota.'
    }
}

# Send the LF script as a single SSH command, leaving the terminal available
# for SSH and sudo password prompts (including in Windows PowerShell 5.1).
$script = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'deploy-server.sh')).Replace("`r`n", "`n")
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
& ssh @sshOptions -t $destination "printf %s $payload | base64 -d | bash -s -- $mode $stage $Server"
if ($LASTEXITCODE -ne 0) { throw 'El despliegue remoto no se ha completado. Revisa el mensaje anterior.' }
if ($PrepareOnly) { return }

$origin = "https://$Server"
$health = Invoke-RestMethod -Uri "$origin/api/v1/utils/health-check/" -TimeoutSec 30
if ($health -isnot [bool] -or !$health) { throw "La API no ha pasado la comprobacion HTTPS en $origin." }
$page = Invoke-WebRequest -UseBasicParsing -Uri "$origin/" -TimeoutSec 30
if ($page.Content -notmatch 'id="root"') { throw "No se ha encontrado la web de INTEPLAST en $origin." }
Write-Host "Despliegue verificado desde el PC: $origin"
