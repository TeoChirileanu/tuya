# Wrapper cu auto-restart pentru src\paznic.py (paznic de sarcină).
# Inregistrat ca Scheduled Task "TuyaPaznic" de win\install.ps1. Log: logs\paznic_run.log.
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force -Path logs | Out-Null
$log = "logs\paznic_run.log"
while ($true) {
    "$(Get-Date -Format o) === paznic start ===" | Add-Content $log
    python -u src\paznic.py 2>&1 | Add-Content $log
    "$(Get-Date -Format o) === paznic exit, restart in 10s ===" | Add-Content $log
    Start-Sleep -Seconds 10
}
