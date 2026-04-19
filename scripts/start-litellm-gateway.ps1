param(
    [string]$EnvFile = "config/litellm/litellm.env.local",
    [string]$RootEnvFile = ".env",
    [string]$ConfigPath = "",
    [string]$BindHost = "",
    [int]$Port = 0
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

if (-not $env:LITELLM_DEEPSEEK_API_KEY -and $env:DEEPSEEK_API_KEY) {
    $env:LITELLM_DEEPSEEK_API_KEY = $env:DEEPSEEK_API_KEY
}

if (-not $env:LITELLM_MINIMAX_API_KEY -and $env:AI_API_KEY) {
    $env:LITELLM_MINIMAX_API_KEY = $env:AI_API_KEY
}

$resolvedConfig = if ($ConfigPath) {
    $ConfigPath
} elseif ($env:LITELLM_CONFIG_PATH) {
    $env:LITELLM_CONFIG_PATH
} else {
    "config/litellm/litellm-config.local.example.yaml"
}

$resolvedHost = if ($BindHost) {
    $BindHost
} elseif ($env:LITELLM_HOST) {
    $env:LITELLM_HOST
} else {
    "127.0.0.1"
}

$resolvedPort = if ($Port -gt 0) {
    $Port
} elseif ($env:LITELLM_PORT) {
    [int]$env:LITELLM_PORT
} else {
    4000
}

if (-not $env:LITELLM_MASTER_KEY) {
    throw "LITELLM_MASTER_KEY is required. Copy config/litellm/litellm.env.local.example to config/litellm/litellm.env.local and set it first."
}

if (-not (Test-Path -LiteralPath $resolvedConfig)) {
    throw "LiteLLM config file not found: $resolvedConfig"
}

if (-not $env:LITELLM_DEEPSEEK_API_KEY) {
    throw "LITELLM_DEEPSEEK_API_KEY is required for the local bootstrap aliases."
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install it first, then rerun this script."
}

Write-Host "[LiteLLM] Config: $resolvedConfig"
Write-Host "[LiteLLM] Host:   $resolvedHost"
Write-Host "[LiteLLM] Port:   $resolvedPort"
Write-Host "[LiteLLM] Model smoke default: vs-ai-analysis"
Write-Host "[LiteLLM] Stop with Ctrl+C"

uv tool run --from "litellm[proxy]" litellm --config $resolvedConfig --host $resolvedHost --port $resolvedPort
