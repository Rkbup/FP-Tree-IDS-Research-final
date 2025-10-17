# Complete Automation - Run All Tasks
# This script executes all pending tasks with your permission

param(
    [switch]$SkipConfirmation
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  FP-Tree IDS - Complete Automation Suite" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Wait for Docker Desktop
Write-Host "[1/6] Waiting for Docker Desktop to be ready..." -ForegroundColor Yellow
$maxWait = 120
$waited = 0
$dockerReady = $false

while ($waited -lt $maxWait) {
    try {
        docker ps 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Docker Desktop is ready!" -ForegroundColor Green
            $dockerReady = $true
            break
        }
    } catch {}
    
    Write-Host "  Waiting... ($waited seconds)" -ForegroundColor Gray
    Start-Sleep -Seconds 10
    $waited += 10
}

if (-not $dockerReady) {
    Write-Host "  ERROR: Docker Desktop did not start in time" -ForegroundColor Red
    Write-Host "  Please start Docker Desktop manually and run this script again" -ForegroundColor Yellow
    exit 1
}

Start-Sleep -Seconds 5

# Wait for Kubernetes
Write-Host ""
Write-Host "[2/6] Waiting for Kubernetes to be ready..." -ForegroundColor Yellow
$maxWait = 120
$waited = 0
$k8sReady = $false

while ($waited -lt $maxWait) {
    try {
        kubectl cluster-info 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Kubernetes is ready!" -ForegroundColor Green
            $k8sReady = $true
            break
        }
    } catch {}
    
    Write-Host "  Waiting... ($waited seconds)" -ForegroundColor Gray
    Start-Sleep -Seconds 10
    $waited += 10
}

if (-not $k8sReady) {
    Write-Host "  ERROR: Kubernetes did not start in time" -ForegroundColor Red
    Write-Host "  Please enable Kubernetes in Docker Desktop settings" -ForegroundColor Yellow
    exit 1
}

# Check experiment status
Write-Host ""
Write-Host "[3/6] Checking experiment status..." -ForegroundColor Yellow

$pods = kubectl get pods -n fp-tree --no-headers 2>&1
if ($LASTEXITCODE -eq 0 -and $pods) {
    Write-Host "  Experiments found!" -ForegroundColor Green
    Write-Host ""
    kubectl get pods -n fp-tree -o wide
    Write-Host ""
    
    # Check if any pods are completed
    $completedPods = kubectl get pods -n fp-tree --field-selector=status.phase=Succeeded --no-headers 2>&1
    $runningPods = kubectl get pods -n fp-tree --field-selector=status.phase=Running --no-headers 2>&1
    
    if ($completedPods) {
        Write-Host "  Some experiments have COMPLETED!" -ForegroundColor Green
        Write-Host "  Proceeding to extract results..." -ForegroundColor Cyan
        $extractResults = $true
    } elseif ($runningPods) {
        Write-Host "  Experiments are RUNNING" -ForegroundColor Cyan
        Write-Host "  Estimated completion: 2-5 hours" -ForegroundColor Yellow
        $extractResults = $false
    } else {
        Write-Host "  Experiments in unknown state" -ForegroundColor Yellow
        $extractResults = $false
    }
} else {
    Write-Host "  No experiments found in namespace 'fp-tree'" -ForegroundColor Yellow
    Write-Host "  Deploying experiments now..." -ForegroundColor Cyan
    
    # Deploy experiments
    Write-Host ""
    Write-Host "[4/6] Deploying experiments to Kubernetes..." -ForegroundColor Yellow
    
    # Create namespace and PVC
    kubectl apply -f k8s/results-pvc.yaml
    Start-Sleep -Seconds 2
    
    # Deploy jobs
    kubectl apply -f k8s/job.yaml
    kubectl apply -f k8s/synthetic-job.yaml
    
    Write-Host "  Deployment initiated!" -ForegroundColor Green
    Start-Sleep -Seconds 5
    
    Write-Host ""
    Write-Host "  Current pod status:" -ForegroundColor Cyan
    kubectl get pods -n fp-tree -o wide
    
    $extractResults = $false
}

# Monitor experiments
Write-Host ""
Write-Host "[5/6] Monitoring setup..." -ForegroundColor Yellow
Write-Host "  You can monitor experiments with these commands:" -ForegroundColor Cyan
Write-Host "    .\quick_status.ps1" -ForegroundColor White
Write-Host "    .\watch_experiments.ps1" -ForegroundColor White
Write-Host "    kubectl get pods -n fp-tree -w" -ForegroundColor White
Write-Host ""

# Extract results if completed
if ($extractResults) {
    Write-Host "[6/6] Extracting results..." -ForegroundColor Yellow
    
    if (Test-Path ".\extract_results.ps1") {
        Write-Host "  Running extraction script..." -ForegroundColor Cyan
        & .\extract_results.ps1
    } else {
        Write-Host "  Manual extraction required:" -ForegroundColor Yellow
        Write-Host "    kubectl cp fp-tree/<pod-name>:/app/results ./results-final/" -ForegroundColor White
    }
} else {
    Write-Host "[6/6] Results extraction..." -ForegroundColor Yellow
    Write-Host "  Experiments still running - extraction will be available when complete" -ForegroundColor Cyan
    Write-Host "  Run this when experiments finish:" -ForegroundColor Yellow
    Write-Host "    .\extract_results.ps1" -ForegroundColor White
}

# Final summary
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Docker Desktop: READY" -ForegroundColor Green
Write-Host "  Kubernetes:     READY" -ForegroundColor Green

$currentPods = kubectl get pods -n fp-tree --no-headers 2>&1
if ($LASTEXITCODE -eq 0 -and $currentPods) {
    $podCount = ($currentPods | Measure-Object -Line).Lines
    Write-Host "  Experiments:    $podCount pods active" -ForegroundColor Green
} else {
    Write-Host "  Experiments:    Not deployed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Next Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Monitor progress:" -ForegroundColor White
Write-Host "     .\watch_experiments.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. When complete, extract results:" -ForegroundColor White
Write-Host "     .\extract_results.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Archive results:" -ForegroundColor White
Write-Host "     .\archive_results.ps1 -IncludeCode" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Clean up resources:" -ForegroundColor White
Write-Host "     .\cleanup.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Show current pod status one more time
Write-Host "Current Pod Status:" -ForegroundColor Cyan
kubectl get pods -n fp-tree 2>&1

Write-Host ""
Write-Host "All permitted tasks have been executed!" -ForegroundColor Green
Write-Host ""
