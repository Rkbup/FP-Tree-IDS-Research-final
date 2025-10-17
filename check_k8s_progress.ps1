# K8s Experiment Progress Checker
# Shows real-time updates every 30 seconds

$podName = "fp-tree-main-experiment-cgg55"
$namespace = "fp-tree"
$lastLogCount = 0

Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        K8s Experiment Progress Monitor (Ctrl+C to stop)       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

while ($true) {
    Clear-Host
    Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║        K8s Experiment Progress Monitor (Ctrl+C to stop)       ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan
    
    # Get pod status
    $podStatus = kubectl get pod $podName -n $namespace --no-headers 2>$null
    if ($podStatus) {
        Write-Host "📦 Pod Status:" -ForegroundColor Yellow
        Write-Host "   $podStatus" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host "❌ Pod not found!" -ForegroundColor Red
        break
    }
    
    # Get log count
    $currentLogCount = (kubectl logs $podName -n $namespace 2>$null | Measure-Object -Line).Lines
    
    Write-Host "📊 Activity Monitor:" -ForegroundColor Yellow
    Write-Host "   Log Lines: $currentLogCount" -ForegroundColor White
    if ($lastLogCount -gt 0) {
        $newLines = $currentLogCount - $lastLogCount
        if ($newLines -gt 0) {
            Write-Host "   New Lines: +$newLines (✅ Working!)" -ForegroundColor Green
        } else {
            Write-Host "   New Lines: 0 (⏳ Processing...)" -ForegroundColor Yellow
        }
    }
    $lastLogCount = $currentLogCount
    Write-Host ""
    
    # Get latest logs
    Write-Host "📝 Latest Output:" -ForegroundColor Yellow
    $latestLogs = kubectl logs $podName -n $namespace --tail=10 2>$null
    $latestLogs | ForEach-Object {
        Write-Host "   $_" -ForegroundColor White
    }
    
    # Check for specific phases
    Write-Host "`n🔍 Progress Indicators:" -ForegroundColor Yellow
    $allLogs = kubectl logs $podName -n $namespace 2>$null
    
    if ($allLogs -match "Loaded.*rows") {
        Write-Host "   ✅ Data Loading Complete" -ForegroundColor Green
    }
    if ($allLogs -match "Feature engineering complete") {
        Write-Host "   ✅ Feature Engineering Complete" -ForegroundColor Green
    }
    if ($allLogs -match "Building transactions") {
        Write-Host "   🔄 Transaction Building (may take 15-30 min)" -ForegroundColor Yellow
    }
    if ($allLogs -match "transactions built") {
        Write-Host "   ✅ Transaction Building Complete" -ForegroundColor Green
    }
    if ($allLogs -match "Evaluating") {
        Write-Host "   🔄 Algorithm Evaluation Running" -ForegroundColor Yellow
    }
    
    Write-Host "`n⏰ Next update in 30 seconds..." -ForegroundColor Gray
    Write-Host "   (Press Ctrl+C to stop monitoring)" -ForegroundColor Gray
    
    Start-Sleep -Seconds 30
}
