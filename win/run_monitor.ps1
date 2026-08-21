# Wrapper cu auto-restart pentru src\monitor_local.py.
# Inregistrat ca Scheduled Task "TuyaMonitor" de win\install.ps1. Log: logs\mon_run.log.
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force -Path logs | Out-Null
$log = "logs\mon_run.log"
while ($true) {
    "$(Get-Date -Format o) === monitor start ===" | Add-Content $log
    python -u src\monitor_local.py 2>&1 | Add-Content $log
    "$(Get-Date -Format o) === monitor exit, restart in 10s ===" | Add-Content $log
    Start-Sleep -Seconds 10
}
