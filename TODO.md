# TODO

titulo oficial: gestor de conocimiento de modificaciones de molde

- [ ] asistente: ollama run qwen3.5:2b --think=false
- [ ] test de preguntas para el asistente
  1. Busca el feature Bolt Eye. ¿Qué advertencias y lecciones aprendidas tiene registradas?
  2. En la pieza 3212, revisión 06, ¿qué mediciones y tolerancias hay para N170? Indica el muestreo, la cavidad y la fuente.
  3. que correcion tiene la n170 del bold eye de la pieza pump housing?
      La pieza Pump Housing (3212) no tiene el feature "Nervios" ni ninguna característica de refuerzo. El error indica que no existe un registro para esa descripción específica en la base de datos del sistema.

- [ ] solucionar que el molde tarda mucho en cargar, (pregunatr si realmente le sinetersa que se ueda ver en la web....)

- [ ] añadir la foto de la pieza de verdad en ficheros vinculados a una pieza. 


PRUEBA POSTMAN ANGEL:

PS C:\Users\eduard.almar>  & {
>>       $ErrorActionPreference = 'Stop'
>>       [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
>>       Add-Type -AssemblyName System.Web
>>
>>       # Leer las credenciales que ya tenemos.
>>       $config = @{}
>>       $envPath = 'C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\repos\inteplast\.env'
>>
>>       foreach ($line in Get-Content -LiteralPath $envPath -Encoding UTF8) {
>>           if ($line -match '^\s*(MICROSOFT_CLIENT_ID|MICROSOFT_CLIENT_SECRET)\s*=\s*(.*?)\s*$') {
>>               $config[$Matches[1]] = $Matches[2].Trim().Trim('"').Trim("'")
>>           }
>>       }
>>
>>       if (!$config.MICROSOFT_CLIENT_ID -or !$config.MICROSOFT_CLIENT_SECRET) {
>>           throw 'Faltan las credenciales en .env.'
>>       }
>>
>>       $tenant = '1d4fdb5e-586f-414c-a0f7-93f631b65591'
>>       $authority = "https://login.microsoftonline.com/$tenant/oauth2/v2.0"
>>       $redirectUri = 'https://oauth.pstmn.io/v1/browser-callback'
>>       $scope = 'https://graph.microsoft.com/.default'
>>       $loginState = [guid]::NewGuid().ToString('N')
>>
>>       # Proteger el intercambio de autorización con PKCE.
>>       $randomBytes = New-Object byte[] 32
>>       $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
>>       $rng.GetBytes($randomBytes)
>>       $rng.Dispose()
>>
>>       $verifier = [Convert]::ToBase64String($randomBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
>>       $sha = [Security.Cryptography.SHA256]::Create()
>>       $digest = $sha.ComputeHash([Text.Encoding]::ASCII.GetBytes($verifier))
>>       $challenge = [Convert]::ToBase64String($digest).TrimEnd('=').Replace('+', '-').Replace('/', '_')
>>       $sha.Dispose()
>>
>>       # Abrir Microsoft para iniciar sesión con tu cuenta.
>>       $authParams = @{
>>           client_id             = $config.MICROSOFT_CLIENT_ID
>>           response_type         = 'code'
>>           redirect_uri          = $redirectUri
>>           response_mode         = 'query'
>>           scope                 = $scope
>>           state                 = $loginState
>>           code_challenge        = $challenge
>>           code_challenge_method = 'S256'
>>           prompt                = 'select_account'
>>       }
>>
>>       $query = ($authParams.GetEnumerator() | ForEach-Object {
>>           '{0}={1}' -f $_.Key, [Uri]::EscapeDataString([string]$_.Value)
>>       }) -join '&'
>>
>>       Start-Process -FilePath "$authority/authorize?$query"
>>
>>       $returnedUrl = Read-Host 'Cuando aparezca Authentication complete, pega la URL completa del navegador'
>>       $returnedUri = [Uri]$returnedUrl.Trim()
>>
>>       if ($returnedUri.GetLeftPart([UriPartial]::Path) -cne $redirectUri) {
>>           throw 'La URL pegada no corresponde a la página de retorno.'
>>       }
>>
>>       $reply = [Web.HttpUtility]::ParseQueryString($returnedUri.Query)
>>
>>       if ($reply['state'] -cne $loginState) {
>>           throw 'La respuesta no corresponde a este intento de login.'
>>       }
>>       if ($reply['error']) {
>>           throw $reply['error_description']
>>       }
>>       if (!$reply['code']) {
>>           throw 'La URL no contiene el código. Copia la dirección completa de la barra del navegador.'
>>       }
>>
>>       # Combinar la autorización de tu usuario con las claves de la aplicación.
>>       $token = Invoke-RestMethod -Method Post `
>>           -Uri "$authority/token" `
>>           -ContentType 'application/x-www-form-urlencoded' `
>>           -Body @{
>>               client_id     = $config.MICROSOFT_CLIENT_ID
>>               client_secret = $config.MICROSOFT_CLIENT_SECRET
>>               grant_type    = 'authorization_code'
>>               code          = $reply['code']
>>               redirect_uri  = $redirectUri
>>               code_verifier = $verifier
>>               scope         = $scope
>>           }
>>
>>       if (!$token.access_token) {
>>           throw 'Microsoft no ha devuelto un token.'
>>       }
>>
>>       Write-Host 'Token obtenido con tu usuario y la aplicación.' -ForegroundColor Green
>>
>>       # Consultar Exemples en el OneDrive del usuario conectado.
>>       $headers = @{ Authorization = "Bearer $($token.access_token)" }
>>       $url = 'https://graph.microsoft.com/v1.0/me/drive/root:/Escritorio/proyectos/11.%20inteplast/Exemples:/children'
>>
>>       $result = Invoke-RestMethod -Method Get -Uri $url -Headers $headers
>>       $result.value | Select-Object name, size | Format-Table -AutoSize
>>
>>       Write-Host 'OK: acceso a Exemples confirmado.' -ForegroundColor Green
>>   }
Cuando aparezca Authentication complete, pega la URL completa del navegador: https://oauth.pstmn.io/v1/browser-callback?code=1.AYIAXttPHW9YTEGg95P2MbZVkQqpV-ZwGU5KtZogR5Jz8zkAAKCCAA.BQABBAIAAAADAOz_BQD0_0V2b1N0c0FydGlmYWN0cwIAAAAAAJJe1nMqj1fTDfikYciIe_6PgNvlgPIPfF3OcU6zwAIT87KCpdYQfCjzpKbc1aGAFESsLWO3IAKbiUuDdk0RAmZJscI8dvuXcw_c3rkYcdRQbytT3LPRx-Z6LuR330R8grPmeUGJWoyjsea9NaArcQwZRg0NtmAZbec6oCbcyv44KvgzTsiwRfAM5sjNAxNgy5ulwEoBEtSuqPMe-mXWG6ge9mgZk4bV3FMghdOY7GcQqJK5B38UvMMFLpYQekLWYKmdmdfXacXQUoj2kyxBQwEnlyx1gU4YQBwxpPh-ZT_655VSQzGv0jn-9UnN_bb4A7l0YcBEQMs42-oL1TQNYZbRzl7y8m_0_ztxqogbi5qY6wSG5Z72NuaXPvGpWP2FAvDEulWeOAD7mWMHgxQEZakF_DQCrKjRHb44M60dxSc80xazDiCcDPTZziAE_GA3Lq8qpcfAcpH-FKti180wxTiBNCk5Fj8i94JEMmn7wnTZ1O61jyoSU0nWTqZcnXkcaMR6iP24UemPCaHPKCkGQWKPspYmQlUeShWce1xtoLcvSxtvykqs8neUOcD5TbpQCto5Q1WSDAl4Gr-dDfWbJycZntzhP_0u-5PxCq0hK9Dn2472-dFF9i0ngekvKGy4pKZeE4OkvQHjCYVJxwFBU3Z0QtRIF_okmWQmMp_KQCFjiHCLDPIQFUwblnRYkXJf-MEbtA_90F5zEdig2jJRRoQF7-snXzWtBQSeGWhsBQDnL3T4MntimJ8wOtJ9fvXjBPGHKGhwKDuBMBCc-ApUQypjKqVwUOxD5V9V2C912xRJ-zsPjw8PlprW-IycCzBa2V0khdYHkzlvsi7IbJ-LQU09iApVbjWm68yl31j34L-TF0zCMhSrdTXl0ixX-xY-Fg_0OPl3238MtfwLOGGDQqkJF5CW1qyIdudYQeDnwLLzbD316d5IfWBYNN1YxbdpBIm_dMkfdOyVC9Glbfe-7nzoMN9A6c5hT5m_JlQHjCPI4wr190-H414_6pEn7UheN4fW9QsjDJQBgcrwJkI1PUMQ5FHd0YWpGLW5OLur96mCTwEBBpiFhLndntABSm-fgt7I_N_cyIXkaKJHVUrDOeFRE3VVuNe-zDwIVg3WNp1WBkZUWT09iicQEQDhClSOMmmJ_kb9yPGNguVlJl5o6fUf-Lyf4CXpXkgkvala3wR21wKujaKOyRUTx56HrFf9TuJ9EghVMusd9trVHI6sef-9MsCxnkm33ENZTd6SzmEZHYCJ6ovU1oQDADGwDdbXyLXvg39K7VzdBOz5nBarzx1129XLRlwgKaOAMqL9eV4pR1veYarEqMWFWJyS3FGs5Xv2oZCGCmWd7_CrwC3Rn4qxevKcjl57pH12cs57pb_1uXO9NnkVZdGnHMIaA_Sjkl_VWV0K6qKdp9s2cpQYEOGlklG-svZz1bB3k7HBejPbmdu7IzyfYAxIbpnCuWVj-eDR&state=0673d4299cd348679b86f76b4eae91c4&session_state=008bcd2a-396f-6391-057b-62cf49bba782
Token obtenido con tu usuario y la aplicación.

name                   size
----                   ----
2820 Pump Housing   6069725
3051 Pump Housing 620433472
3197 Pot          857145038
3212 Pump Housing 874496260


OK: acceso a Exemples confirmado.







