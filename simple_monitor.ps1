# Simple K8s Progress Checker
$podName = "fp-tree-main-experiment-cgg55"
$namespace = "fp-tree"

Write-Host "`n=== K8s Experiment Progress Monitor ===" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Gray

while ($true) {
    $timestamp = Get-Date -Format "HH:mm:ss"
    
    Write-Host "`n[$timestamp] Checking status..." -ForegroundColor Yellow
    
    # Pod status
    $status = kubectl get pod $podName -n $namespace --no-headers 2>$null
    if ($status) {
        Write-Host "Pod: $status" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Pod not found!" -ForegroundColor Red
        break
    }
    
    # Latest 5 log lines
    Write-Host "`nLatest logs:" -ForegroundColor Cyan
    kubectl logs $podName -n $namespace --tail=5 2>$null | ForEach-Object {
        Write-Host "  $_" -ForegroundColor White
    }
    
    Write-Host "`n---" -ForegroundColor Gray
    Start-Sleep -Seconds 30
}
