param(
    [string]$EnvFile = "config/litellm/litellm.env.local",
    [string]$RootEnvFile = ".env",
    [string]$GatewayConfigPath = "",
    [string]$GatewaySmokeModel = "vs-ai-analysis",
    [string]$RepoModel = "vs-ai-default",
    [string]$PublicationMode = "reviewed",
    [int]$GatewayReadyTimeoutSeconds = 60,
    [switch]$KeepGatewayRunning
)

$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot

function Resolve-WorkspacePath {
    param([string]$Path)

    if (-not $Path) {
        return ""
    }

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }

    return [System.IO.Path]::GetFullPath((Join-Path $workspace $Path))
}

function Import-KeyValueFile {
    param([string]$Path)

    $resolved = Resolve-WorkspacePath -Path $Path
    if (-not $resolved -or -not (Test-Path -LiteralPath $resolved)) {
        return
    }

    Get-Content -LiteralPath $resolved | ForEach-Object {
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

function Wait-ForTcpPort {
    param(
        [string]$TcpHost,
        [int]$Port,
        [int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $client = $null
        try {
            $client = [System.Net.Sockets.TcpClient]::new()
            $async = $client.BeginConnect($TcpHost, $Port, $null, $null)
            if ($async.AsyncWaitHandle.WaitOne(1000) -and $client.Connected) {
                $client.EndConnect($async) | Out-Null
                return $true
            }
        } catch {
            # Keep waiting for the gateway to accept connections.
        } finally {
            if ($client) {
                $client.Dispose()
            }
        }
        Start-Sleep -Milliseconds 500
    }

    return $false
}

function Show-LogTail {
    param(
        [string]$Label,
        [string]$Path
    )

    if (Test-Path -LiteralPath $Path) {
        Write-Host ("--- {0} ---" -f $Label)
        Get-Content -LiteralPath $Path -Tail 80
    }
}

function Get-ListenerProcessId {
    param([int]$Port)

    return Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty OwningProcess
}

function Set-StageAliasEnv {
    param(
        [string]$Prefix,
        [string]$BaseUrl,
        [string]$Model
    )

    Set-Item -Path ("Env:{0}_AI_PROVIDER" -f $Prefix) -Value "litellm_proxy"
    Set-Item -Path ("Env:{0}_AI_BASE_URL" -f $Prefix) -Value $BaseUrl
    Set-Item -Path ("Env:{0}_AI_MODEL" -f $Prefix) -Value $Model
}

Import-KeyValueFile -Path $RootEnvFile
Import-KeyValueFile -Path $EnvFile

if (-not $env:LITELLM_DEEPSEEK_API_KEY -and $env:DEEPSEEK_API_KEY) {
    $env:LITELLM_DEEPSEEK_API_KEY = $env:DEEPSEEK_API_KEY
}

if (-not $env:LITELLM_MINIMAX_API_KEY -and $env:AI_API_KEY) {
    $env:LITELLM_MINIMAX_API_KEY = $env:AI_API_KEY
}

if (-not $env:LITELLM_DEEPSEEK_API_KEY) {
    throw "LITELLM_DEEPSEEK_API_KEY is required. Set it in config/litellm/litellm.env.local or provide DEEPSEEK_API_KEY in the repo root .env."
}

$hasMiniMaxKey = [bool]$env:LITELLM_MINIMAX_API_KEY
$useStageAliases = $hasMiniMaxKey

$resolvedEnvFile = Resolve-WorkspacePath -Path $EnvFile
$resolvedRootEnvFile = Resolve-WorkspacePath -Path $RootEnvFile
$resolvedConfigPath = if ($GatewayConfigPath) {
    Resolve-WorkspacePath -Path $GatewayConfigPath
} elseif ($useStageAliases) {
    Resolve-WorkspacePath -Path "config/litellm/litellm-config.example.yaml"
} elseif ($env:LITELLM_CONFIG_PATH) {
    Resolve-WorkspacePath -Path $env:LITELLM_CONFIG_PATH
} else {
    Resolve-WorkspacePath -Path "config/litellm/litellm-config.local.example.yaml"
}

$resolvedHost = if ($env:LITELLM_HOST) { $env:LITELLM_HOST } else { "127.0.0.1" }
$resolvedPort = if ($env:LITELLM_PORT) { [int]$env:LITELLM_PORT } else { 4000 }
$resolvedBaseUrl = "http://$resolvedHost`:$resolvedPort"
$resolvedMasterKey = if ($env:LITELLM_MASTER_KEY) { $env:LITELLM_MASTER_KEY } else { "sk-local-smoke" }
$env:LITELLM_MASTER_KEY = $resolvedMasterKey

$stdoutLog = Join-Path $env:TEMP "vs-ai-litellm-smoke.out.log"
$stderrLog = Join-Path $env:TEMP "vs-ai-litellm-smoke.err.log"
Remove-Item $stdoutLog, $stderrLog -Force -ErrorAction SilentlyContinue

$gatewayProcess = $null
$preExistingListenerPid = Get-ListenerProcessId -Port $resolvedPort

if ($preExistingListenerPid) {
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$preExistingListenerPid"
    throw "Port $resolvedPort is already in use by process $preExistingListenerPid ($($processInfo.Name)). Stop it or choose another LiteLLM port."
}

try {
    Write-Host "[LiteLLM] Starting gateway..."
    $gatewayProcess = Start-Process pwsh `
        -ArgumentList @(
            "-NoProfile",
            "-File",
            (Join-Path $workspace "scripts/start-litellm-gateway.ps1"),
            "-EnvFile",
            $resolvedEnvFile,
            "-RootEnvFile",
            $resolvedRootEnvFile,
            "-ConfigPath",
            $resolvedConfigPath,
            "-BindHost",
            $resolvedHost,
            "-Port",
            "$resolvedPort"
        ) `
        -WorkingDirectory $workspace `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru

    if (-not (Wait-ForTcpPort -TcpHost $resolvedHost -Port $resolvedPort -TimeoutSeconds $GatewayReadyTimeoutSeconds)) {
        Show-LogTail -Label "LiteLLM stdout" -Path $stdoutLog
        Show-LogTail -Label "LiteLLM stderr" -Path $stderrLog
        throw "LiteLLM gateway did not start listening on $resolvedBaseUrl within $GatewayReadyTimeoutSeconds seconds."
    }

    Write-Host "[LiteLLM] Gateway port is ready."
    if ($useStageAliases) {
        Write-Host "[LiteLLM] Stage alias mode enabled (DeepSeek + MiniMax)."
    } else {
        Write-Host "[LiteLLM] Stage alias mode disabled (DeepSeek-only fallback)."
        Write-Host "[LiteLLM] To verify summary/prefilter aliases, set AI_API_KEY in .env or LITELLM_MINIMAX_API_KEY in config/litellm/litellm.env.local."
    }

    & (Join-Path $workspace "scripts/smoke-litellm-gateway.ps1") `
        -EnvFile $resolvedEnvFile `
        -RootEnvFile $resolvedRootEnvFile `
        -BaseUrl $resolvedBaseUrl `
        -Model $GatewaySmokeModel

    $runStatusPath = Join-Path $workspace "data/state/run-status.json"
    $beforeGeneratedAt = ""
    if (Test-Path -LiteralPath $runStatusPath) {
        $beforePayload = Get-Content -LiteralPath $runStatusPath -Raw | ConvertFrom-Json
        $beforeGeneratedAt = [string]$beforePayload.generated_at
    }

    $env:PYTHONPATH = "src"
    $env:AUTO_PUSH_ENABLED = "false"
    $env:PUBLICATION_MODE = $PublicationMode
    $env:AI_PROVIDER = "litellm_proxy"
    $env:AI_BASE_URL = $resolvedBaseUrl
    $env:AI_MODEL = $RepoModel
    $env:LITELLM_MASTER_KEY = $resolvedMasterKey

    foreach ($prefix in @("ANALYSIS", "SUMMARY", "FORECAST", "PREFILTER", "DISCOVERY", "SEARCH")) {
        foreach ($suffix in @("AI_PROVIDER", "AI_BASE_URL", "AI_MODEL", "AI_API_KEY", "LITELLM_MASTER_KEY")) {
            Remove-Item ("Env:{0}_{1}" -f $prefix, $suffix) -ErrorAction SilentlyContinue
        }
    }

    if ($useStageAliases) {
        Set-StageAliasEnv -Prefix "ANALYSIS" -BaseUrl $resolvedBaseUrl -Model "vs-ai-analysis"
        Set-StageAliasEnv -Prefix "SUMMARY" -BaseUrl $resolvedBaseUrl -Model "vs-ai-summary"
        Set-StageAliasEnv -Prefix "FORECAST" -BaseUrl $resolvedBaseUrl -Model "vs-ai-forecast"
        Set-StageAliasEnv -Prefix "PREFILTER" -BaseUrl $resolvedBaseUrl -Model "vs-ai-prefilter"
        Set-StageAliasEnv -Prefix "DISCOVERY" -BaseUrl $resolvedBaseUrl -Model "vs-ai-discovery"
        Set-StageAliasEnv -Prefix "SEARCH" -BaseUrl $resolvedBaseUrl -Model "vs-ai-search"
    }

    $pythonCmd = if (Test-Path -LiteralPath (Join-Path $workspace ".venv/Scripts/python.exe")) {
        Join-Path $workspace ".venv/Scripts/python.exe"
    } else {
        "python"
    }

    Write-Host "[VS_AI] Running repo smoke via LiteLLM gateway..."
    & $pythonCmd -m auto_report.cli run-once --publication-mode $PublicationMode

    if (-not (Test-Path -LiteralPath $runStatusPath)) {
        throw "run-status.json was not generated."
    }

    $status = Get-Content -LiteralPath $runStatusPath -Raw | ConvertFrom-Json
    if (-not $status.generated_at -or $status.generated_at -eq $beforeGeneratedAt) {
        throw "run-status.json did not update during the smoke run."
    }
    if ([string]$status.publication_mode -ne $PublicationMode) {
        throw "Expected publication_mode=$PublicationMode, got $($status.publication_mode)."
    }
    foreach ($stageName in @("analysis", "summary", "forecast")) {
        if ([string]$status.stage_status.$stageName -ne "ok") {
            throw "Stage '$stageName' did not finish with ok status."
        }
    }
    if ([string]$status.ai_metrics.provider -ne "litellm_proxy") {
        throw "Expected ai_metrics.provider=litellm_proxy, got $($status.ai_metrics.provider)."
    }
    if ($useStageAliases) {
        $stageBreakdown = $status.ai_metrics.stage_breakdown
        $expectedStageModels = [ordered]@{
            prefilter = "vs-ai-prefilter"
            analysis = "vs-ai-analysis"
            summary = "vs-ai-summary"
            forecast = "vs-ai-forecast"
        }

        foreach ($stageName in $expectedStageModels.Keys) {
            if (-not $stageBreakdown.$stageName) {
                throw "Expected ai_metrics.stage_breakdown.$stageName to exist."
            }
            if ([string]$stageBreakdown.$stageName.model -ne $expectedStageModels[$stageName]) {
                throw "Expected $stageName model=$($expectedStageModels[$stageName]), got $($stageBreakdown.$stageName.model)."
            }
        }
        if ([string]$status.ai_metrics.provider -ne "litellm_proxy") {
            throw "Expected ai_metrics.provider=litellm_proxy in stage alias mode, got $($status.ai_metrics.provider)."
        }
        if ([string]$status.ai_metrics.model -ne "mixed") {
            throw "Expected ai_metrics.model=mixed in stage alias mode, got $($status.ai_metrics.model)."
        }
    } elseif ([string]$status.ai_metrics.model -ne $RepoModel) {
        throw "Expected ai_metrics.model=$RepoModel, got $($status.ai_metrics.model)."
    }

    Write-Host "[VS_AI] Repo smoke OK"
    Write-Host ("[VS_AI] generated_at:      {0}" -f $status.generated_at)
    Write-Host ("[VS_AI] publication_mode: {0}" -f $status.publication_mode)
    Write-Host ("[VS_AI] report_topics:    {0}" -f $status.source_stats.report_topics)
    Write-Host ("[VS_AI] ai_provider:      {0}" -f $status.ai_metrics.provider)
    Write-Host ("[VS_AI] ai_model:         {0}" -f $status.ai_metrics.model)
    if ($useStageAliases) {
        Write-Host ("[VS_AI] prefilter_model:  {0}" -f $status.ai_metrics.stage_breakdown.prefilter.model)
        Write-Host ("[VS_AI] analysis_model:   {0}" -f $status.ai_metrics.stage_breakdown.analysis.model)
        Write-Host ("[VS_AI] summary_model:    {0}" -f $status.ai_metrics.stage_breakdown.summary.model)
        Write-Host ("[VS_AI] forecast_model:   {0}" -f $status.ai_metrics.stage_breakdown.forecast.model)
    }
}
finally {
    if ($gatewayProcess -and -not $gatewayProcess.HasExited -and -not $KeepGatewayRunning) {
        Stop-Process -Id $gatewayProcess.Id -Force -ErrorAction SilentlyContinue
    }

    if (-not $KeepGatewayRunning) {
        Start-Sleep -Seconds 2
        $remainingListenerPid = Get-ListenerProcessId -Port $resolvedPort
        if ($remainingListenerPid -and $remainingListenerPid -ne $preExistingListenerPid) {
            Stop-Process -Id $remainingListenerPid -Force -ErrorAction SilentlyContinue
        }
    }

    if ($KeepGatewayRunning) {
        Write-Host "[LiteLLM] Gateway left running on request."
    }
}
