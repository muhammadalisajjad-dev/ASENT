$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
py -3.12 -m venv .venv
& .venv\Scripts\python.exe -m pip install -r requirements.lock.txt
npm --prefix frontend ci
npm --prefix frontend run build
Write-Output "Use WSL2/Linux for native tracing, or build the Docker sandbox. Start with scripts/start.ps1."
