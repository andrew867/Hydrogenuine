$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPATH = $Root
$env:HG_COMMUNITY_DATA_DIR = if ($env:HG_COMMUNITY_DATA_DIR) { $env:HG_COMMUNITY_DATA_DIR } else { Join-Path $Root ".hg_community_demo" }
$env:HG_GATEWAY_STORE = "memory"
$Python = if (Test-Path ".venv\Scripts\python.exe") { Join-Path $Root ".venv\Scripts\python.exe" } else { "python" }

& $Python -m hg_cli demo
