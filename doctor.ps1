$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPATH = $Root
if (-not $env:HG_GATEWAY_API_KEY) { $env:HG_GATEWAY_API_KEY = "oss-demo-key" }
if (-not $env:HG_COMMUNITY_DATA_DIR) { $env:HG_COMMUNITY_DATA_DIR = Join-Path $Root ".hg_community" }

python --version
python -c "import hg_gateway.main; import hg_gateway.community; print('imports ok')"
python -m pytest tests/test_community_backend_acceptance.py -q
python -m pytest tests/test_public_packaging_docs.py -q

try {
    $Health = Invoke-WebRequest -Uri "http://127.0.0.1:8000/healthz" -UseBasicParsing -TimeoutSec 2
    Write-Host "running api health:" $Health.StatusCode
} catch {
    Write-Host "api health: not running"
}
