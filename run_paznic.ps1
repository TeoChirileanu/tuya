# Wrapper cu auto-restart pentru paznic.py (paznic de sarcină).
# Rulat de Scheduled Task "TuyaPaznic" la logon. Log: paznic_run.log.
Set-Location $PSScriptRoot
while ($true) {
    "$(Get-Date -Format o) === paznic start ===" | Add-Content paznic_run.log
    python -u paznic.py 2>&1 | Add-Content paznic_run.log
    "$(Get-Date -Format o) === paznic exit, restart in 10s ===" | Add-Content paznic_run.log
    Start-Sleep -Seconds 10
}
