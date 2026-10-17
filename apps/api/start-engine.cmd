@echo off
rem Double-click to start the Reel Studio engine in the background (it restarts itself if it stops).
start "" /min powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0start-engine.ps1"
