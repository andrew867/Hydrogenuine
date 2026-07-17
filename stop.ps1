$ErrorActionPreference = "SilentlyContinue"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DataDir = if ($env:HG_COMMUNITY_DATA_DIR) { $env:HG_COMMUNITY_DATA_DIR } else { Join-Path $Root ".hg_community" }
$RunDir = Join-Path $DataDir "run"

foreach ($Name in @("api.pid", "ui.pid")) {
    $Path = Join-Path $RunDir $Name
    if (Test-Path $Path) {
        $PidValue = Get-Content $Path | Select-Object -First 1
        if ($PidValue) { Stop-Process -Id ([int]$PidValue) -Force }
        Remove-Item $Path -Force
    }
}

Write-Host "Hydrogenuine Community services stopped."
