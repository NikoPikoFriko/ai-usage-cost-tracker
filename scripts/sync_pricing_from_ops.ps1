# Optional: copy a PRICING_MODELS.csv from elsewhere into config/
# Usage:
#   pwsh -File scripts/sync_pricing_from_ops.ps1 -Source "C:\path\to\PRICING_MODELS.csv"

param(
  [Parameter(Mandatory = $true)]
  [string]$Source
)

$ErrorActionPreference = "Stop"
$dst = Join-Path $PSScriptRoot "..\config\PRICING_MODELS.csv"
if (-not (Test-Path $Source)) { throw "Missing source: $Source" }
Copy-Item -Force $Source $dst
Write-Host "Synced pricing -> $dst"
