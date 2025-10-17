# Cleanup Kubernetes Resources
# This script cleans up experiment pods, jobs, and optionally the namespace

param(
    [switch]$DeleteNamespace = $false,
    [switch]$Force = $false
)

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   FP-Tree IDS - Kubernetes Cleanup" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if (-not $Force) {
    Write-Host "⚠️  WARNING: This will delete Kubernetes resources!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "This will remove:" -ForegroundColor Yellow
    Write-Host "  • Experiment jobs" -ForegroundColor Gray
    Write-Host "  • Experiment pods" -ForegroundColor Gray
    Write-Host "  • PersistentVolumeClaims (data will be lost!)" -ForegroundColor Gray
    if ($DeleteNamespace) {
        Write-Host "  • fp-tree namespace" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Have you extracted the results? (Y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -ne "Y" -and $response -ne "y") {
        Write-Host "Cleanup cancelled. Please extract results first:" -ForegroundColor Gray
        Write-Host "  .\extract_results.ps1" -ForegroundColor Cyan
        exit 0
    }
}

Write-Host ""
Write-Host "[Step 1/5] Deleting jobs..." -ForegroundColor Yellow
kubectl delete job -n fp-tree fp-tree-main-experiment --ignore-not-found=true
kubectl delete job -n fp-tree fp-tree-synthetic-experiment --ignore-not-found=true
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Jobs deleted" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some jobs may not exist" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "[Step 2/5] Deleting pods..." -ForegroundColor Yellow
kubectl delete pods -n fp-tree --all
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Pods deleted" -ForegroundColor Green
} else {
    Write-Host "⚠️  No pods found" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "[Step 3/5] Deleting PersistentVolumeClaims..." -ForegroundColor Yellow
kubectl delete pvc -n fp-tree fp-tree-results --ignore-not-found=true
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ PVCs deleted" -ForegroundColor Green
} else {
    Write-Host "⚠️  No PVCs found" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "[Step 4/5] Checking for remaining resources..." -ForegroundColor Yellow
$remaining = kubectl get all -n fp-tree --no-headers 2>&1
if ($remaining -and $remaining.Count -gt 0) {
    Write-Host "⚠️  Some resources still exist:" -ForegroundColor Yellow
    kubectl get all -n fp-tree
    Write-Host ""
    Write-Host "Delete these manually if needed:" -ForegroundColor Gray
    Write-Host "  kubectl delete all --all -n fp-tree" -ForegroundColor Cyan
} else {
    Write-Host "✓ No resources remaining" -ForegroundColor Green
}
Write-Host ""

if ($DeleteNamespace) {
    Write-Host "[Step 5/5] Deleting namespace..." -ForegroundColor Yellow
    kubectl delete namespace fp-tree
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Namespace deleted" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to delete namespace" -ForegroundColor Red
    }
} else {
    Write-Host "[Step 5/5] Keeping namespace..." -ForegroundColor Yellow
    Write-Host "✓ Namespace 'fp-tree' preserved" -ForegroundColor Green
    Write-Host "  To delete namespace: .\cleanup.ps1 -DeleteNamespace" -ForegroundColor Gray
}
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   Cleanup Complete!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Kubernetes resources have been cleaned up." -ForegroundColor Green
Write-Host ""
Write-Host "What's preserved:" -ForegroundColor Cyan
Write-Host "  ✓ Docker image (fp-tree-ids:latest)" -ForegroundColor Green
Write-Host "  ✓ Local results (if extracted)" -ForegroundColor Green
Write-Host "  ✓ Kubernetes configuration files (k8s/*.yaml)" -ForegroundColor Green
Write-Host ""
Write-Host "To re-run experiments:" -ForegroundColor Cyan
Write-Host "  kubectl apply -f k8s/results-pvc.yaml" -ForegroundColor Gray
Write-Host "  kubectl apply -f k8s/job.yaml" -ForegroundColor Gray
Write-Host "  kubectl apply -f k8s/synthetic-job.yaml" -ForegroundColor Gray
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
