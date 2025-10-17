# Minimal script to monitor experiment progress
Write-Host "Monitoring experiment logs..." -ForegroundColor Cyan
Get-ChildItem logs/*.log | ForEach-Object { Write-Host "`n=== $($_.Name) ===" -ForegroundColor Yellow; Get-Content $_.FullName -Tail 30 }
