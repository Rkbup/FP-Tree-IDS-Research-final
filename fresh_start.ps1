# Quick Fresh Start - Run New Experiments
# ========================================

Write-Host ""
Write-Host "FP-Tree IDS - Fresh Experiment Start" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Docker
Write-Host "[Step 1/5] Checking Docker Desktop..." -ForegroundColor Yellow
try {
    docker ps 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "  Docker Desktop is NOT running!" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Quick Fix:" -ForegroundColor Yellow
        Write-Host "  1. Press Windows Key" -ForegroundColor White
        Write-Host "  2. Type 'Docker Desktop'" -ForegroundColor White
        Write-Host "  3. Press Enter" -ForegroundColor White
        Write-Host "  4. Wait for the whale icon to stabilize (bottom-right)" -ForegroundColor White
        Write-Host "  5. Run this script again: .\fresh_start.ps1" -ForegroundColor White
        Write-Host ""
        Write-Host "  Or run this command:" -ForegroundColor Cyan
        Write-Host '  Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"' -ForegroundColor Gray
        Write-Host ""
        exit 1
    }
    Write-Host "  OK - Docker is running" -ForegroundColor Green
} catch {
    Write-Host "  ERROR - Docker not found" -ForegroundColor Red
    exit 1
}

# Step 2: Check Kubernetes
Write-Host ""
Write-Host "[Step 2/5] Checking Kubernetes..." -ForegroundColor Yellow
try {
    kubectl cluster-info 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR - Kubernetes not ready" -ForegroundColor Red
        Write-Host "  Enable in: Docker Desktop > Settings > Kubernetes" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "  OK - Kubernetes is ready" -ForegroundColor Green
} catch {
    Write-Host "  ERROR - kubectl not found" -ForegroundColor Red
    exit 1
}

# Step 3: Clean up old experiments
Write-Host ""
Write-Host "[Step 3/5] Cleaning up old experiments..." -ForegroundColor Yellow
kubectl delete jobs --all -n fp-tree 2>&1 | Out-Null
kubectl delete pods --all -n fp-tree 2>&1 | Out-Null
Start-Sleep -Seconds 3
Write-Host "  Old experiments removed" -ForegroundColor Green

# Step 4: Deploy fresh experiments
Write-Host ""
Write-Host "[Step 4/5] Deploying NEW experiments..." -ForegroundColor Yellow

# Ensure PVC exists
kubectl apply -f k8s/results-pvc.yaml 2>&1 | Out-Null

# Deploy main experiment
Write-Host "  Deploying Main Experiment (CIC-IDS2017)..." -ForegroundColor Cyan
kubectl apply -f k8s/job.yaml
Start-Sleep -Seconds 2

# Deploy synthetic experiment
Write-Host "  Deploying Synthetic Experiment..." -ForegroundColor Cyan
kubectl apply -f k8s/synthetic-job.yaml
Start-Sleep -Seconds 3

Write-Host "  Deployment complete!" -ForegroundColor Green

# Step 5: Verify deployment
Write-Host ""
Write-Host "[Step 5/5] Verifying deployment..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Current Pod Status:" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan
kubectl get pods -n fp-tree -o wide

Write-Host ""
Write-Host "Expected Status:" -ForegroundColor Yellow
Write-Host "  - Pod Status: Running or ContainerCreating" -ForegroundColor White
Write-Host "  - Ready: 0/1 (initially) then 1/1" -ForegroundColor White
Write-Host "  - Restarts: 0" -ForegroundColor White
Write-Host ""

# Show initial logs
Write-Host "Initial Logs (Main Experiment):" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
$mainPod = kubectl get pods -n fp-tree -l job-name=fp-tree-main-experiment --no-headers -o custom-columns=":metadata.name" 2>&1 | Select-Object -First 1
if ($mainPod) {
    kubectl logs --tail=10 -n fp-tree $mainPod 2>&1
} else {
    Write-Host "  Pod not ready yet..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Initial Logs (Synthetic Experiment):" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
$synthPod = kubectl get pods -n fp-tree -l job-name=fp-tree-synthetic-experiment --no-headers -o custom-columns=":metadata.name" 2>&1 | Select-Object -First 1
if ($synthPod) {
    kubectl logs --tail=10 -n fp-tree $synthPod 2>&1
} else {
    Write-Host "  Pod not ready yet..." -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  NEW EXPERIMENTS STARTED!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Estimated Completion Time:" -ForegroundColor Yellow
Write-Host "  Main Experiment: 4-5 hours" -ForegroundColor White
Write-Host "  Synthetic: 2-3 hours" -ForegroundColor White
Write-Host ""
Write-Host "Monitor Progress:" -ForegroundColor Cyan
Write-Host "  .\watch_experiments.ps1" -ForegroundColor White
Write-Host "  OR" -ForegroundColor Gray
Write-Host "  kubectl get pods -n fp-tree -w" -ForegroundColor White
Write-Host ""
Write-Host "Check Logs:" -ForegroundColor Cyan
Write-Host "  kubectl logs -f -n fp-tree $mainPod" -ForegroundColor White
Write-Host "  kubectl logs -f -n fp-tree $synthPod" -ForegroundColor White
Write-Host ""
Write-Host "When Complete:" -ForegroundColor Cyan
Write-Host "  .\extract_results.ps1" -ForegroundColor White
Write-Host ""
