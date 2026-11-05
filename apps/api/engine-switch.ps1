# One-click on/off for the Reel Studio engine (API + worker + Dev Tunnel). Used by the desktop button
# "Reel Studio Engine (on-off)"; also: powershell -File engine-switch.ps1 -Action start|stop|toggle|status
#   start : enables the "Reel Studio Engine" task (logon + every 2 min ensure check) and starts it now
#   stop  : disables that task so nothing restarts the engine, then stops only Reel Studio's engine processes
#           (python -m app.serve / app.workers.run and their children); Ollama and other projects are untouched
#   toggle: stop when it is running, otherwise start
# A small pop-up (closes itself after a few seconds) says what happened.
param([ValidateSet("start", "stop", "toggle", "status")][string]$Action = "toggle", [switch]$Quiet)

$task = "Reel Studio Engine"
$api = Split-Path -Parent $MyInvocation.MyCommand.Path
$notes = Join-Path $env:LOCALAPPDATA "reel-studio\logs\engine-launcher.log"
function Note($m) { "$(Get-Date -Format s) [switch] $m" | Add-Content $notes -ErrorAction SilentlyContinue }
function Say($msg, $icon = 64) {
    if ($Quiet) { Write-Output $msg; return }
    (New-Object -ComObject WScript.Shell).Popup($msg, 6, "Reel Studio Engine", $icon) | Out-Null
}
function Healthy { try { (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health -TimeoutSec 4).StatusCode -eq 200 } catch { $false } }
function EngineProcs {
    @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {
        $_.CommandLine -match '-m app\.serve --tunnel' -or $_.CommandLine -match '-m app\.workers\.run'
    })
}

if ($Action -eq "toggle") { $Action = if ((EngineProcs).Count -or (Healthy)) { "stop" } else { "start" } }

switch ($Action) {
    "status" {
        $state = (Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue).State
        Say ("Engine is " + $(if (Healthy) { "ON (healthy)" } else { "OFF" }) + ". Auto-start task: $state.")
    }
    "stop" {
        Disable-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue | Out-Null
        EngineProcs | ForEach-Object { taskkill /PID $_.ProcessId /T /F 2>$null | Out-Null }
        Start-Sleep -Seconds 2
        EngineProcs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Note "engine stopped by the on/off button"
        if (Healthy) { Say "Could not stop the engine completely. Try the button again." 48 }
        else { Say "Engine is OFF. It will stay off (also after a restart) until you press the button again." }
    }
    "start" {
        Enable-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue | Out-Null
        if (Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue) { Start-ScheduledTask -TaskName $task }
        else { & (Join-Path $api "start-engine.ps1") }  # no task on this machine: start once directly
        Note "engine started by the on/off button"
        $up = $false
        for ($i = 0; $i -lt 45; $i++) { if (Healthy) { $up = $true; break }; Start-Sleep -Seconds 2 }
        if ($up) { Say "Engine is ON. The website can process and render again." }
        else { Say "Engine is starting (the first start after a reboot can take a few minutes). Press the button again only to turn it off." 48 }
    }
}
