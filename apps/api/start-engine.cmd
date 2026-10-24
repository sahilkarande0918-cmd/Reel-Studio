@echo off
rem Double-click to start the Reel Studio engine in the background (the "Reel Studio Engine" task re-checks it every 2 minutes).
start "" /min powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0start-engine.ps1"
