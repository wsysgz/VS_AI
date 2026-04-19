param(
    [string]$EnvFile = "config/litellm/litellm.env.local",
    [string]$RootEnvFile = ".env",
    [string]$BaseUrl = "",
    [string]$Model = "vs-ai-analysis",
    [string]$Prompt = "Reply with the active model alias and the word OK."
)

$ErrorActionPreference = "Stop"

function Import-KeyValueFile {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }

        $parts = $line -split "=", 2
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        Set-Item -Path ("Env:{0}" -f $name) -Value $value
    }
}

Import-KeyValueFile -Path $RootEnvFile
Import-KeyValueFile -Path $EnvFile

$resolvedHost = if ($env:LITELLM_HOST) { $env:LITELLM_HOST } else { "127.0.0.1" }
$resolvedPort = if ($env:LITELLM_PORT) { [int]$env:LITELLM_PORT } else { 4000 }
$resolvedBaseUrl = if ($BaseUrl) { $BaseUrl.TrimEnd("/") } else { "http://$resolvedHost`:$resolvedPort" }
$resolvedKey = if ($env:LITELLM_MASTER_KEY) { $env:LITELLM_MASTER_KEY } else { "" }

if (-not $resolvedKey) {
    throw "LITELLM_MASTER_KEY is required for the smoke call."
}

$body = @{
    model = $Model
    messages = @(
        @{
            role = "user"
            content = $Prompt
        }
    )
} | ConvertTo-Json -Depth 6

$response = Invoke-RestMethod `
    -Uri "$resolvedBaseUrl/chat/completions" `
    -Method POST `
    -Headers @{
        "Authorization" = "Bearer $resolvedKey"
        "Content-Type" = "application/json"
    } `
    -Body $body

$content = $response.choices[0].message.content
Write-Host "[LiteLLM] Smoke call OK"
Write-Host "[LiteLLM] Base URL: $resolvedBaseUrl"
Write-Host "[LiteLLM] Model:    $Model"
Write-Host "[LiteLLM] Reply:    $content"
