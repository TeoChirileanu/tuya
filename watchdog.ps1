# Watchdog: verifică monitor + paznic și repornește ce e mort/înțepenit.
# Rulat de Scheduled Task "TuyaWatchdog" la fiecare 5 minute.
Set-Location $PSScriptRoot
$log = "watchdog.log"
$now = Get-Date -Format o

function Restart-Stack {
    param([string]$reason)
    "$((Get-Date -Format o)) RESTART: $reason" | Add-Content $log
    Stop-ScheduledTask -TaskName "TuyaMonitor" -ErrorAction SilentlyContinue
    Stop-ScheduledTask -TaskName "TuyaPaznic" -ErrorAction SilentlyContinue
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -match "monitor_local|paznic" } |
        ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -Confirm:$false } catch {} }
    Start-Sleep -Seconds 45   # lasă contorul să-și închidă sesiunile TCP stale
    Start-ScheduledTask -TaskName "TuyaMonitor"
    Start-Sleep -Seconds 15   # monitorul primul (singura conexiune la contor)
    Start-ScheduledTask -TaskName "TuyaPaznic"
}

$procs = (Get-CimInstance Win32_Process -Filter "Name='python.exe'").CommandLine
$monitorAlive = ($procs | Where-Object { $_ -match "monitor_local" }) -ne $null
$paznicAlive  = ($procs | Where-Object { $_ -match "paznic" }) -ne $null

# centrala scrie rânduri la 10s -> fișierul zilei trebuie să fie proaspăt
$centralaCsv = "centrala_$(Get-Date -Format yyyyMMdd).csv"
$fresh = (Test-Path $centralaCsv) -and
         ((Get-Date) - (Get-Item $centralaCsv).LastWriteTime).TotalMinutes -lt 5

if (-not $monitorAlive)   { Restart-Stack "monitor mort" }
elseif (-not $fresh)      { Restart-Stack "date stale (centrala CSV vechi/absent)" }
elseif (-not $paznicAlive) { Restart-Stack "paznic mort" }
else { "$now OK" | Add-Content $log }

# taie logul dacă crește prea mult
if ((Get-Item $log -ErrorAction SilentlyContinue).Length -gt 1MB) {
    Get-Content $log -Tail 200 | Set-Content $log
}
