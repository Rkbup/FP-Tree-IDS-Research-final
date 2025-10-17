# Minimal script to cleanup resources
Write-Host "Cleaning up logs and temp files..." -ForegroundColor Cyan
Remove-Item logs/*.log -Force -ErrorAction SilentlyContinue
Remove-Item results-final/* -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Cleanup complete." -ForegroundColor Green
