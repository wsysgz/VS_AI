$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$env:PYTHONPATH = "src"

python -m auto_report.workflow_guard --root $repoRoot
