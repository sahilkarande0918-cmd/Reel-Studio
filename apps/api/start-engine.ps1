# Keeps the Reel Studio processing engine (API + worker + Dev Tunnel) and Ollama running on this machine.
# Short-lived "ensure" check, run by the task "Reel Studio Engine" at logon and every 2 minutes (and by start-engine.cmd):
#   - Ollama not running            -> start it
#   - engine not running            -> start it in its own hidden console (a Ctrl+C sent to another console, which
#                                      killed the old long-running launcher and engine together, cannot reach it)
#   - engine running but not healthy for 3 minutes -> replace it
# app.serve itself restarts a crashed tunnel or worker. Logs: %LOCALAPPDATA%\reel-studio\logs\engine.log (engine output)
# and engine-launcher.log (starts and replacements).
$api = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $env:LOCALAPPDATA "reel-studio\venv\Scripts\python.exe"
$ollama = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
$logDir = Join-Path $env:LOCALAPPDATA "reel-studio\logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir "engine.log"
$notes = Join-Path $logDir "engine-launcher.log"
function Note($m) { "$(Get-Date -Format s) $m" | Add-Content $notes }

$mutex = New-Object System.Threading.Mutex($false, "Local\ReelStudioEngineEnsure")
if (-not $mutex.WaitOne(0)) { exit 0 }  # another check is already running

if ((Test-Path $ollama) -and -not (Get-Process ollama -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
    Note "started Ollama"
}

$engine = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'app\.serve --tunnel devtunnel' })
$healthy = $false
try { $healthy = (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health -TimeoutSec 10).StatusCode -eq 200 } catch {}

if ($engine.Count -and -not $healthy) {
    $oldest = ($engine | Sort-Object CreationDate | Select-Object -First 1)
    if ($oldest.CreationDate -lt (Get-Date).AddMinutes(-3)) {  # starting engines get time to come up
        Note "engine not answering; replacing it"
        $engine | ForEach-Object { taskkill /PID $_.ProcessId /T /F 2>$null | Out-Null }
        $engine = @()
    }
}
if (-not $engine.Count) {
    # cmd in its own hidden console window: appends output to the log, separate from any other console
    Start-Process -FilePath "cmd.exe" -WorkingDirectory $api -WindowStyle Hidden `
        -ArgumentList "/c", "`"`"$py`" -m app.serve --tunnel devtunnel >> `"$log`" 2>&1`""
    Note "starting engine"
}
