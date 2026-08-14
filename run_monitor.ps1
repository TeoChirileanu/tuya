# Wrapper cu auto-restart pentru monitor_local.py.
# Rulat de Scheduled Task "TuyaMonitor" la logon. Log: mon_run.log.
Set-Location $PSScriptRoot
while ($true) {
    "$(Get-Date -Format o) === monitor start ===" | Add-Content mon_run.log
    python -u monitor_local.py 2>&1 | Add-Content mon_run.log
    "$(Get-Date -Format o) === monitor exit, restart in 10s ===" | Add-Content mon_run.log
    Start-Sleep -Seconds 10
}
