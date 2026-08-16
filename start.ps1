$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

Get-Content ".env" | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$' -and $_ -notmatch '^\s*#') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}

if (-not $env:HG_COMMUNITY_DATA_DIR) { $env:HG_COMMUNITY_DATA_DIR = Join-Path $Root ".hg_community" }
if (-not $env:HG_CONFIG_PATH) { $env:HG_CONFIG_PATH = Join-Path $env:HG_COMMUNITY_DATA_DIR "config.json" }
if (-not $env:HG_GATEWAY_AUTH_MODE) { $env:HG_GATEWAY_AUTH_MODE = "local-no-key" }
if (-not $env:HG_GATEWAY_STORE -or $env:HG_GATEWAY_STORE -eq "memory") { $env:HG_GATEWAY_STORE = "sqlite" }
if (-not $env:HG_GATEWAY_DB_PATH) { $env:HG_GATEWAY_DB_PATH = Join-Path $env:HG_COMMUNITY_DATA_DIR "gateway.sqlite3" }
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPATH = $Root

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -e ".[dev]"

if (-not (Test-Path $env:HG_CONFIG_PATH)) {
    & $Python -m hg_cli init --mode demo --non-interactive --config $env:HG_CONFIG_PATH --data-dir $env:HG_COMMUNITY_DATA_DIR
}

$RunDir = Join-Path $env:HG_COMMUNITY_DATA_DIR "run"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

$Api = Start-Process -FilePath $Python -ArgumentList @("-m","uvicorn","hg_gateway.main:app","--host","127.0.0.1","--port","8000") -WorkingDirectory $Root -WindowStyle Hidden -PassThru
$Ui = Start-Process -FilePath $Python -ArgumentList @("-m","http.server","4173","--bind","127.0.0.1") -WorkingDirectory (Join-Path $Root "community_ui") -WindowStyle Hidden -PassThru

Set-Content -Path (Join-Path $RunDir "api.pid") -Value $Api.Id
Set-Content -Path (Join-Path $RunDir "ui.pid") -Value $Ui.Id

Write-Host "Hydrogenuine Community is starting."
Write-Host "UI:  http://127.0.0.1:4173"
Write-Host "API: http://127.0.0.1:8000/healthz"
Write-Host "Mode: local demo/mock (no API keys required)"
Write-Host "Check: .\.venv\Scripts\hg.exe doctor --self-test"
Write-Host "Stop: .\stop.ps1"
