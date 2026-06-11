#Requires -Version 7
# Cross-platform dev launcher (PowerShell). Delegates to dev.py.
#   .\dev.ps1            bring everything up (combined logs, Ctrl+C stops all)
#   .\dev.ps1 --skip-sync
#   .\dev.ps1 stop       force-stop anything left running
Set-Location $PSScriptRoot
& uv run python dev.py @args
