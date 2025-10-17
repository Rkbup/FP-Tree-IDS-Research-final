# Minimal script to start both experiments locally
Write-Host "Starting main and synthetic experiments..." -ForegroundColor Cyan
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "experiments/main_experiment.py" -WindowStyle Hidden -PassThru | Out-Null
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "experiments/synthetic_full_experiment.py" -WindowStyle Hidden -PassThru | Out-Null
Write-Host "Experiments started in background. Monitor with watch_experiments.ps1." -ForegroundColor Green
