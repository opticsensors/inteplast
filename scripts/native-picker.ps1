# ASCII source: this script also runs under Windows PowerShell 5.1.
# Paths arrive through the environment, never through evaluated shell text.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -Path (Join-Path $PSScriptRoot 'native-picker.cs') -ReferencedAssemblies System.Windows.Forms,System.Drawing
$result = [NativePicker]::Show($env:INTEPLAST_PICKER_ROOT, $env:INTEPLAST_PICKER_KIND)
# PowerShell 5.1 emits no output for ConvertTo-Json -InputObject $null.
# Closing with X, Escape or Cancel is a successful, explicit null result.
if ($null -eq $result) { [Console]::WriteLine('null') }
else { [Console]::WriteLine((ConvertTo-Json -InputObject $result -Compress)) }
