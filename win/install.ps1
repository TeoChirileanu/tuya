# Înregistrează cele 3 Scheduled Tasks care rulează monitorizarea pe Windows.
# Echivalentul lui pi/install.sh. Rulează: pwsh -File win\install.ps1
# Idempotent: -Force înlocuiește taskurile existente (inclusiv căi vechi).
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited

function New-TuyaAction([string]$script) {
    New-ScheduledTaskAction -Execute "pwsh.exe" `
        -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$root\win\$script`""
}

# monitor + paznic: pornesc la logon, rulează la nesfârșit (wrapperele au bucla de restart)
$loopSettings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName "TuyaMonitor" -Force `
    -Action (New-TuyaAction "run_monitor.ps1") `
    -Trigger (New-ScheduledTaskTrigger -AtLogOn) `
    -Settings $loopSettings -Principal $principal | Out-Null

Register-ScheduledTask -TaskName "TuyaPaznic" -Force `
    -Action (New-TuyaAction "run_paznic.ps1") `
    -Trigger (New-ScheduledTaskTrigger -AtLogOn) `
    -Settings $loopSettings -Principal $principal | Out-Null

# watchdog: la 5 minute, cu limită de execuție ca să nu se suprapună
Register-ScheduledTask -TaskName "TuyaWatchdog" -Force `
    -Action (New-TuyaAction "watchdog.ps1") `
    -Trigger (New-ScheduledTaskTrigger -Once -At (Get-Date) `
        -RepetitionInterval (New-TimeSpan -Minutes 5)) `
    -Settings (New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 4)) `
    -Principal $principal | Out-Null

Get-ScheduledTask -TaskName Tuya* | Select-Object TaskName, State

Write-Host @"

Taskurile sunt inregistrate. Comenzi utile:
  Start-ScheduledTask   TuyaMonitor    # porneste acum
  Disable-ScheduledTask TuyaMonitor    # opreste monitorizarea (nu mai porneste la logon)
  Enable-ScheduledTask  TuyaMonitor
  Get-Content logs\mon_run.log -Tail 20 -Wait
"@
