# Quick Status Check for FP-Tree Experiments

Write-Host ""
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host " FP-Tree IDS - Quick Status Check" -ForegroundColor Green
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
Write-Host "[1/3] Docker Desktop..." -ForegroundColor Yellow
try {
    docker version --format "{{.Server.Version}}" 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK - Docker is running" -ForegroundColor Green
    } else {
        Write-Host "  ERROR - Docker not responding" -ForegroundColor Red
        Write-Host "  ACTION: Restart Docker Desktop" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "  ERROR - Docker not found" -ForegroundColor Red
    exit 1
}

# Check Kubernetes
Write-Host "[2/3] Kubernetes..." -ForegroundColor Yellow
try {
    kubectl version --client --short 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        kubectl cluster-info 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  OK - Kubernetes is accessible" -ForegroundColor Green
        } else {
            Write-Host "  ERROR - Cannot connect to cluster" -ForegroundColor Red
            Write-Host "  ACTION: Enable Kubernetes in Docker Desktop" -ForegroundColor Yellow
            exit 1
        }
    } else {
        Write-Host "  ERROR - kubectl not installed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ERROR - Kubernetes check failed" -ForegroundColor Red
    exit 1
}

# Check Pods
Write-Host "[3/3] Experiment Pods..." -ForegroundColor Yellow
try {
    $pods = kubectl get pods -n fp-tree --no-headers 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "  Pod Status:" -ForegroundColor Cyan
        kubectl get pods -n fp-tree -o wide
        Write-Host ""
        
        # Show recent logs
        Write-Host "  Recent Activity:" -ForegroundColor Cyan
        $podNames = kubectl get pods -n fp-tree --no-headers -o custom-columns=":metadata.name" 2>&1
        foreach ($pod in $podNames) {
            if ($pod -and $pod.Trim() -ne "") {
                Write-Host "    Pod: $pod" -ForegroundColor White
                kubectl logs --tail=3 -n fp-tree $pod 2>&1 | ForEach-Object { Write-Host "      $_" -ForegroundColor Gray }
                Write-Host ""
            }
        }
    } else {
        Write-Host "  WARNING - Namespace 'fp-tree' not found" -ForegroundColor Yellow
        Write-Host "  ACTION: Deploy experiments with:" -ForegroundColor Yellow
        Write-Host "    kubectl apply -f k8s/" -ForegroundColor White
    }
} catch {
    Write-Host "  ERROR - Cannot check pods" -ForegroundColor Red
}

Write-Host ""
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host " Next Steps" -ForegroundColor Green
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Monitor:  .\watch_experiments.ps1" -ForegroundColor White
Write-Host "  Extract:  .\extract_results.ps1" -ForegroundColor White
Write-Host "  Cleanup:  .\cleanup.ps1" -ForegroundColor White
Write-Host ""
