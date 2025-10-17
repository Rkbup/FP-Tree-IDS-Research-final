# Docker Desktop Startup Wait Script
# Waits for Docker Desktop to be fully ready

param(
    [int]$MaxWaitSeconds = 300
)

Write-Host ""
Write-Host "Waiting for Docker Desktop to start..." -ForegroundColor Yellow
Write-Host "Maximum wait time: $MaxWaitSeconds seconds" -ForegroundColor Gray
Write-Host ""

$waited = 0
$checkInterval = 5

while ($waited -lt $MaxWaitSeconds) {
    # Try Docker command
    try {
        $null = docker version --format "{{.Server.Version}}" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "Docker Desktop is READY!" -ForegroundColor Green
            Write-Host "Total wait time: $waited seconds" -ForegroundColor Cyan
            
            # Now check Kubernetes
            Write-Host ""
            Write-Host "Checking Kubernetes..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
            
            $k8sWaited = 0
            $k8sMaxWait = 120
            
            while ($k8sWaited -lt $k8sMaxWait) {
                try {
                    kubectl cluster-info 2>&1 | Out-Null
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "Kubernetes is READY!" -ForegroundColor Green
                        Write-Host ""
                        Write-Host "System is fully ready!" -ForegroundColor Green
                        Write-Host ""
                        Write-Host "Next steps:" -ForegroundColor Cyan
                        Write-Host "  .\quick_status.ps1       - Check experiment status" -ForegroundColor White
                        Write-Host "  .\run_all.ps1            - Run all automation tasks" -ForegroundColor White
                        Write-Host "  .\watch_experiments.ps1  - Monitor experiments" -ForegroundColor White
                        Write-Host ""
                        exit 0
                    }
                } catch {}
                
                Write-Host "  Waiting for Kubernetes... ($k8sWaited seconds)" -ForegroundColor Gray
                Start-Sleep -Seconds 5
                $k8sWaited += 5
            }
            
            Write-Host ""
            Write-Host "WARNING: Kubernetes not ready after $k8sMaxWait seconds" -ForegroundColor Yellow
            Write-Host "Docker is running but Kubernetes needs manual enablement" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Enable Kubernetes:" -ForegroundColor Cyan
            Write-Host "  1. Open Docker Desktop" -ForegroundColor White
            Write-Host "  2. Settings (gear icon)" -ForegroundColor White
            Write-Host "  3. Kubernetes tab" -ForegroundColor White
            Write-Host "  4. Check 'Enable Kubernetes'" -ForegroundColor White
            Write-Host "  5. Apply and Restart" -ForegroundColor White
            Write-Host ""
            exit 1
        }
    } catch {}
    
    # Show progress
    $dots = "." * (($waited / $checkInterval) % 4)
    Write-Host ("  Waiting{0,-4} ({1} seconds)" -f $dots, $waited) -ForegroundColor Gray
    
    Start-Sleep -Seconds $checkInterval
    $waited += $checkInterval
}

Write-Host ""
Write-Host "ERROR: Docker Desktop did not start within $MaxWaitSeconds seconds" -ForegroundColor Red
Write-Host ""
Write-Host "Troubleshooting:" -ForegroundColor Yellow
Write-Host "  1. Check if Docker Desktop is running (system tray)" -ForegroundColor White
Write-Host "  2. Try manually starting Docker Desktop" -ForegroundColor White
Write-Host "  3. Check Windows Task Manager for stuck Docker processes" -ForegroundColor White
Write-Host "  4. Restart your computer if Docker won't start" -ForegroundColor White
Write-Host ""
Write-Host "Manual start:" -ForegroundColor Cyan
Write-Host '  Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"' -ForegroundColor White
Write-Host ""
exit 1
