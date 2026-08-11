# Sync PRICING_MODELS.csv from ops research room into this repo config/
$ErrorActionPreference = "Stop"
$ops = "D:\PROJECT_CENTER\20_PROJECTS\AI_USAGE_COST_TRACKER\data\PRICING_MODELS.csv"
$dst = Join-Path $PSScriptRoot "..\config\PRICING_MODELS.csv"
if (-not (Test-Path $ops)) { throw "Missing ops pricing: $ops" }
Copy-Item -Force $ops $dst
Write-Host "Synced pricing -> $dst"
