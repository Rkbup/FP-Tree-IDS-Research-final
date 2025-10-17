# Minimal script to extract results
Write-Host "Extracting results..." -ForegroundColor Cyan
Copy-Item results/tables/* results-final/tables/ -Force
Copy-Item results/figures/* results-final/figures/ -Force
Write-Host "Results copied to results-final folder." -ForegroundColor Green
