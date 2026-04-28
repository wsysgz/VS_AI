[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
}

function Get-TempTargets {
    param(
        [string]$Root
    )

    $patterns = @(
        ".codex-pytest-temp*",
        ".pytest_cache",
        ".pytest-codex-*",
        ".pytest-tmp",
        "codex_pytest_temp",
        "pytest-tempdir*"
    )

    $names = Get-ChildItem -LiteralPath $Root -Force -Name
    $targets = foreach ($pattern in $patterns) {
        $names | Where-Object { $_ -like $pattern }
    }
    return $targets | Sort-Object -Unique
}

function Remove-Target {
    param(
        [string]$Path
    )

    Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
}

$resolvedRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$targets = Get-TempTargets -Root $resolvedRoot

if ($targets.Count -eq 0) {
    Write-Host "No ignored temp directories found under $resolvedRoot"
    exit 0
}

$isAdmin = Test-IsAdmin
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$removed = New-Object System.Collections.Generic.List[string]
$stubborn = New-Object System.Collections.Generic.List[string]

foreach ($name in $targets) {
    $fullPath = Join-Path $resolvedRoot $name
    if (-not (Test-Path -LiteralPath $fullPath)) {
        continue
    }

    if (-not $PSCmdlet.ShouldProcess($fullPath, "Remove ignored temp directory")) {
        continue
    }

    try {
        Remove-Target -Path $fullPath
        $removed.Add($name)
        continue
    } catch {
        if (-not $isAdmin) {
            $stubborn.Add($name)
            continue
        }
    }

    & takeown.exe /f $fullPath /a /r /d Y | Out-Null
    & icacls.exe $fullPath /inheritance:e /grant:r "${currentUser}:(OI)(CI)F" "Administrators:(OI)(CI)F" "SYSTEM:(OI)(CI)F" /t /c | Out-Null

    try {
        Remove-Target -Path $fullPath
        $removed.Add($name)
    } catch {
        $stubborn.Add($name)
    }
}

if ($removed.Count -gt 0) {
    Write-Host "Removed targets:"
    $removed | ForEach-Object { Write-Host " - $_" }
}

if ($stubborn.Count -eq 0) {
    exit 0
}

Write-Warning "Remaining targets could not be removed:"
$stubborn | ForEach-Object { Write-Warning " - $_" }

if (-not $isAdmin) {
    Write-Warning "Re-run this script from an elevated PowerShell window to take ownership and reset ACLs."
}

exit 1
