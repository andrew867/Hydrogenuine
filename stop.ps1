$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DataDir = if ($env:HG_COMMUNITY_DATA_DIR) { $env:HG_COMMUNITY_DATA_DIR } else { Join-Path $Root ".hg_community" }
$RunDir = Join-Path $DataDir "run"

function Get-HydrogenuineProcessTree {
    param([int]$RootProcessId)

    $Processes = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue)
    $TreeIds = [System.Collections.Generic.HashSet[int]]::new()
    [void]$TreeIds.Add($RootProcessId)

    do {
        $Added = $false
        foreach ($Process in $Processes) {
            if ($TreeIds.Contains([int]$Process.ParentProcessId) -and $TreeIds.Add([int]$Process.ProcessId)) {
                $Added = $true
            }
        }
    } while ($Added)

    return @($Processes | Where-Object { $TreeIds.Contains([int]$_.ProcessId) })
}

$Services = @{
    "api.pid" = "uvicorn hg_gateway.main:app"
    "ui.pid" = "http.server 4173"
}

foreach ($Name in $Services.Keys) {
    $Path = Join-Path $RunDir $Name
    if (Test-Path $Path) {
        $PidValue = Get-Content $Path | Select-Object -First 1
        if ($PidValue) {
            $Marker = $Services[$Name]
            $Targets = @(
                Get-HydrogenuineProcessTree -RootProcessId ([int]$PidValue) |
                    Where-Object {
                        $_.CommandLine -and
                        $_.CommandLine -like "*$Root*" -and
                        $_.CommandLine -like "*$Marker*"
                    }
            )
            $TargetIds = @($Targets | Select-Object -ExpandProperty ProcessId -Unique)
            if ($TargetIds.Count -gt 0) {
                Stop-Process -Id $TargetIds -Force -ErrorAction SilentlyContinue
                Write-Host "Stopped $Name process tree: $($TargetIds -join ', ')"
            }
        }
        Remove-Item $Path -Force
    }
}

Write-Host "Hydrogenuine Community services stopped."
