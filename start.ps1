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

if (-not $env:HG_GATEWAY_API_KEY) { $env:HG_GATEWAY_API_KEY = "oss-demo-key" }
if (-not $env:HG_COMMUNITY_DATA_DIR) { $env:HG_COMMUNITY_DATA_DIR = Join-Path $Root ".hg_community" }
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPATH = $Root

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -e ".[dev]"

$RunDir = Join-Path $env:HG_COMMUNITY_DATA_DIR "run"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

$Api = Start-Process -FilePath $Python -ArgumentList @("-m","uvicorn","hg_gateway.main:app","--host","127.0.0.1","--port","8000") -WorkingDirectory $Root -WindowStyle Hidden -PassThru
$Ui = Start-Process -FilePath $Python -ArgumentList @("-m","http.server","4173","--bind","127.0.0.1") -WorkingDirectory (Join-Path $Root "community_ui") -WindowStyle Hidden -PassThru

Set-Content -Path (Join-Path $RunDir "api.pid") -Value $Api.Id
Set-Content -Path (Join-Path $RunDir "ui.pid") -Value $Ui.Id

Write-Host "Hydrogenuine Community is starting."
Write-Host "UI:  http://127.0.0.1:4173"
Write-Host "API: http://127.0.0.1:8000/healthz"
Write-Host "API key: $env:HG_GATEWAY_API_KEY"
Write-Host "Stop: .\stop.ps1"
