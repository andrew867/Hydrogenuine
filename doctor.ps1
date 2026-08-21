$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPATH = $Root
if (-not $env:HG_COMMUNITY_DATA_DIR) { $env:HG_COMMUNITY_DATA_DIR = Join-Path $Root ".hg_community" }
if (-not $env:HG_CONFIG_PATH) { $env:HG_CONFIG_PATH = Join-Path $env:HG_COMMUNITY_DATA_DIR "config.json" }
$Python = if (Test-Path ".venv\Scripts\python.exe") { Join-Path $Root ".venv\Scripts\python.exe" } else { "python" }

& $Python --version
& $Python -m hg_cli doctor --config $env:HG_CONFIG_PATH --self-test

try {
    $Health = Invoke-WebRequest -Uri "http://127.0.0.1:8000/healthz" -UseBasicParsing -TimeoutSec 2
    Write-Host "running api health:" $Health.StatusCode
} catch {
    Write-Host "api health: not running"
}
