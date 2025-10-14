# PowerShell Auto-Approve Configuration
# Add this to your PowerShell profile for permanent settings

# Bypass execution policy restrictions
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser -Force

# Auto-approve all confirmations
$ConfirmPreference = "None"
$VerbosePreference = "SilentlyContinue"
$WarningPreference = "SilentlyContinue"
$ErrorActionPreference = "Continue"

# Auto-approve UAC and system prompts (when possible)
$env:POWERSHELL_TELEMETRY_OPTOUT = 1

Write-Host "PowerShell auto-approve configuration applied!" -ForegroundColor Green