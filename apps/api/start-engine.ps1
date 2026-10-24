# Keeps the Reel Studio processing engine (API + worker + Dev Tunnel) running on this machine.
# If it ever stops, it is started again after 5 s. Only one copy can run (a second start just exits).
# Logs: %LOCALAPPDATA%\reel-studio\logs\engine.log (engine) and engine-launcher.log (starts/stops)
$api = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $env:LOCALAPPDATA "reel-studio\venv\Scripts\python.exe"
$logDir = Join-Path $env:LOCALAPPDATA "reel-studio\logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir "engine.log"           # engine output (held open while it runs)
$notes = Join-Path $logDir "engine-launcher.log" # starts, stops, duplicate-start refusals

$mutex = New-Object System.Threading.Mutex($false, "Local\ReelStudioEngine")
if (-not $mutex.WaitOne(0)) { "$(Get-Date -Format s) engine already running; not starting a second copy" | Add-Content $notes; exit 0 }

Set-Location $api
$ollama = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
while ($true) {
    # the AI director and campaign planner need the local model server; it does not start by itself after a reboot
    if ((Test-Path $ollama) -and -not (Get-Process ollama -ErrorAction SilentlyContinue)) {
        Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
        "$(Get-Date -Format s) started Ollama" | Add-Content $notes
    }
    "$(Get-Date -Format s) starting engine" | Add-Content $notes
    # cmd redirection keeps native stderr as plain text in the log.
    cmd /c "`"$py`" -m app.serve --tunnel devtunnel >> `"$log`" 2>&1"
    "$(Get-Date -Format s) engine stopped (exit $LASTEXITCODE); restarting in 5 s" | Add-Content $notes
    Start-Sleep -Seconds 5
}
