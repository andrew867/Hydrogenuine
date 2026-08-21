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

foreach ($Port in @(8000, 4173)) {
    $Listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($Listener) {
        throw "Local port $Port is already in use by process $($Listener.OwningProcess). Stop the existing service before starting Hydrogenuine Community."
    }
}

function Wait-HydrogenuineEndpoint {
    param(
        [string]$Name,
        [string]$Uri,
        [System.Diagnostics.Process]$Process
    )

    foreach ($Attempt in 1..40) {
        if ($Process.HasExited) {
            throw "$Name exited before its local endpoint became ready."
        }
        try {
            $Response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 2
            if ($Response.StatusCode -eq 200) { return }
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
    throw "$Name did not become ready at $Uri. Run .\stop.ps1, then review the local terminal output."
}

$Api = Start-Process -FilePath $Python -ArgumentList @("-m","uvicorn","hg_gateway.main:app","--host","127.0.0.1","--port","8000") -WorkingDirectory $Root -WindowStyle Hidden -PassThru
$Ui = Start-Process -FilePath $Python -ArgumentList @("-m","http.server","4173","--bind","127.0.0.1") -WorkingDirectory (Join-Path $Root "community_ui") -WindowStyle Hidden -PassThru

Set-Content -Path (Join-Path $RunDir "api.pid") -Value $Api.Id
Set-Content -Path (Join-Path $RunDir "ui.pid") -Value $Ui.Id

try {
    Wait-HydrogenuineEndpoint -Name "Community API" -Uri "http://127.0.0.1:8000/healthz" -Process $Api
    Wait-HydrogenuineEndpoint -Name "Community UI" -Uri "http://127.0.0.1:4173/" -Process $Ui
} catch {
    & (Join-Path $Root "stop.ps1")
    throw
}

Write-Host "Hydrogenuine Community is ready."
Write-Host "UI:  http://127.0.0.1:4173"
Write-Host "API: http://127.0.0.1:8000/healthz"
Write-Host "Mode: local demo/mock (no API keys required)"
Write-Host "Check: .\.venv\Scripts\hg.exe doctor --self-test"
Write-Host "Stop: .\stop.ps1"
