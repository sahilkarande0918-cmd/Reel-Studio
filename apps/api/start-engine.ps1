# Keeps the Reel Studio processing engine (API + worker + Dev Tunnel) running on this machine.
# If it ever stops, it is started again after 5 s. Only one copy can run (a second start just exits).
# Log: %LOCALAPPDATA%\reel-studio\logs\engine.log
$api = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $env:LOCALAPPDATA "reel-studio\venv\Scripts\python.exe"
$logDir = Join-Path $env:LOCALAPPDATA "reel-studio\logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir "engine.log"

$mutex = New-Object System.Threading.Mutex($false, "Local\ReelStudioEngine")
if (-not $mutex.WaitOne(0)) { "$(Get-Date -Format s) engine already running; not starting a second copy" | Add-Content $log; exit 0 }

Set-Location $api
while ($true) {
    "$(Get-Date -Format s) starting engine" | Add-Content $log
    # cmd redirection keeps native stderr as plain text in the log.
    cmd /c "`"$py`" -m app.serve --tunnel devtunnel >> `"$log`" 2>&1"
    "$(Get-Date -Format s) engine stopped (exit $LASTEXITCODE); restarting in 5 s" | Add-Content $log
    Start-Sleep -Seconds 5
}
