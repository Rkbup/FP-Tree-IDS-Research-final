# Quick Deploy Script
# Use this to redeploy experiments if they were lost after restart

param(
    [switch]$SkipCleanup = $false
)

Write-Host "=== FP-Tree IDS Experiment Deployment ===" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "[Prerequisite Check]" -ForegroundColor Yellow
$dockerRunning = docker version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Docker is running" -ForegroundColor Green

$imageExists = docker images fp-tree-ids:latest --format "{{.Repository}}:{{.Tag}}" 2>$null
if ($imageExists -ne "fp-tree-ids:latest") {
    Write-Host "❌ Docker image 'fp-tree-ids:latest' not found!" -ForegroundColor Red
    Write-Host "   Please rebuild the image first:" -ForegroundColor Yellow
    Write-Host "   docker build -t fp-tree-ids:latest ." -ForegroundColor Cyan
    exit 1
}
Write-Host "✅ Docker image exists" -ForegroundColor Green

$k8sRunning = kubectl cluster-info 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Kubernetes is not running. Check Docker Desktop settings." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Kubernetes is running" -ForegroundColor Green
Write-Host ""

# Step 1: Cleanup old jobs (if not skipped)
if (-not $SkipCleanup) {
    Write-Host "[1/5] Cleaning up old jobs..." -ForegroundColor Yellow
    kubectl delete job --all -n fp-tree --ignore-not-found=true 2>$null
    Start-Sleep -Seconds 2
    Write-Host "✅ Cleanup complete" -ForegroundColor Green
} else {
    Write-Host "[1/5] Skipping cleanup (--SkipCleanup flag)" -ForegroundColor Gray
}

# Step 2: Ensure namespace exists
Write-Host ""
Write-Host "[2/5] Ensuring namespace exists..." -ForegroundColor Yellow
$namespaceExists = kubectl get namespace fp-tree -o name 2>$null
if ($namespaceExists -ne "namespace/fp-tree") {
    kubectl create namespace fp-tree
    Write-Host "✅ Namespace 'fp-tree' created" -ForegroundColor Green
} else {
    Write-Host "✅ Namespace 'fp-tree' already exists" -ForegroundColor Green
}

# Step 3: Ensure PVC exists
Write-Host ""
Write-Host "[3/5] Ensuring storage (PVC) exists..." -ForegroundColor Yellow
$pvcExists = kubectl get pvc fp-tree-results -n fp-tree -o name 2>$null
if ($pvcExists -ne "persistentvolumeclaim/fp-tree-results") {
    if (Test-Path "k8s/results-pvc.yaml") {
        kubectl apply -f k8s/results-pvc.yaml
        Write-Host "✅ PVC 'fp-tree-results' created" -ForegroundColor Green
        Start-Sleep -Seconds 3
    } else {
        Write-Host "⚠️  k8s/results-pvc.yaml not found, creating PVC inline..." -ForegroundColor Yellow
        @"
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: fp-tree-results
  namespace: fp-tree
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
"@ | kubectl apply -f -
        Write-Host "✅ PVC created" -ForegroundColor Green
        Start-Sleep -Seconds 3
    }
} else {
    Write-Host "✅ PVC 'fp-tree-results' already exists" -ForegroundColor Green
}

# Step 4: Deploy Main Experiment
Write-Host ""
Write-Host "[4/5] Deploying Main Experiment..." -ForegroundColor Yellow
if (Test-Path "k8s/job.yaml") {
    kubectl apply -f k8s/job.yaml
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Main experiment job deployed" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to deploy main experiment" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "❌ k8s/job.yaml not found!" -ForegroundColor Red
    exit 1
}

# Step 5: Deploy Synthetic Experiment
Write-Host ""
Write-Host "[5/5] Deploying Synthetic Experiment..." -ForegroundColor Yellow
if (Test-Path "k8s/synthetic-job.yaml") {
    kubectl apply -f k8s/synthetic-job.yaml
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Synthetic experiment job deployed" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to deploy synthetic experiment" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "❌ k8s/synthetic-job.yaml not found!" -ForegroundColor Red
    exit 1
}

# Wait for pods to be created
Write-Host ""
Write-Host "Waiting for pods to be created..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

# Show status
Write-Host ""
Write-Host "=== Current Status ===" -ForegroundColor Cyan
kubectl get jobs -n fp-tree
Write-Host ""
kubectl get pods -n fp-tree

Write-Host ""
Write-Host "🎉 Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Monitor pods: kubectl get pods -n fp-tree -w" -ForegroundColor Gray
Write-Host "  2. View logs: kubectl logs -f -n fp-tree <pod-name>" -ForegroundColor Gray
Write-Host "  3. Expected duration: Main (4-5 hours), Synthetic (2-3 hours)" -ForegroundColor Gray
Write-Host ""
