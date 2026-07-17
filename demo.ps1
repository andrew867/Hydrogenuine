$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPATH = $Root
$env:HG_GATEWAY_API_KEY = if ($env:HG_GATEWAY_API_KEY) { $env:HG_GATEWAY_API_KEY } else { "oss-demo-key" }
$env:HG_COMMUNITY_DATA_DIR = if ($env:HG_COMMUNITY_DATA_DIR) { $env:HG_COMMUNITY_DATA_DIR } else { Join-Path $Root ".hg_community_demo" }
$env:HG_GATEWAY_STORE = "memory"

python examples\offline_demo.py
