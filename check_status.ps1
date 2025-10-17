# Quick Recovery Script
# Run this after PC restart to check status and resume experiments

Write-Host "=== FP-Tree IDS Experiment Recovery ===" -ForegroundColor Cyan
Write-Host "Date: $(Get-Date)" -ForegroundColor Gray
Write-Host ""

# Step 1: Check Docker
Write-Host "[1/6] Checking Docker Desktop..." -ForegroundColor Yellow
$dockerStatus = docker version 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Docker Desktop is running" -ForegroundColor Green
} else {
    Write-Host "  ❌ Docker Desktop is NOT running" -ForegroundColor Red
    Write-Host "  → Start Docker Desktop and run this script again" -ForegroundColor Yellow
    exit 1
}

# Step 2: Check Docker Image
Write-Host ""
Write-Host "[2/6] Checking Docker Image..." -ForegroundColor Yellow
$imageExists = docker images fp-tree-ids:latest --format "{{.Repository}}:{{.Tag}}" 2>$null
if ($imageExists -eq "fp-tree-ids:latest") {
    Write-Host "  ✅ Docker image 'fp-tree-ids:latest' exists" -ForegroundColor Green
    $imageSize = docker images fp-tree-ids:latest --format "{{.Size}}"
    Write-Host "  📦 Size: $imageSize" -ForegroundColor Gray
} else {
    Write-Host "  ❌ Docker image NOT found" -ForegroundColor Red
    Write-Host "  → Need to rebuild image (see RECOVERY_INSTRUCTIONS.md)" -ForegroundColor Yellow
    Write-Host "  → Command: docker build -t fp-tree-ids:latest ." -ForegroundColor Cyan
}

# Step 3: Check Kubernetes
Write-Host ""
Write-Host "[3/6] Checking Kubernetes Cluster..." -ForegroundColor Yellow
$k8sStatus = kubectl cluster-info 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Kubernetes cluster is running" -ForegroundColor Green
} else {
    Write-Host "  ❌ Kubernetes cluster is NOT running" -ForegroundColor Red
    Write-Host "  → Check Docker Desktop → Settings → Kubernetes" -ForegroundColor Yellow
    exit 1
}

# Step 4: Check Namespace
Write-Host ""
Write-Host "[4/6] Checking fp-tree namespace..." -ForegroundColor Yellow
$namespaceExists = kubectl get namespace fp-tree -o name 2>$null
if ($namespaceExists -eq "namespace/fp-tree") {
    Write-Host "  ✅ Namespace 'fp-tree' exists" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Namespace 'fp-tree' NOT found" -ForegroundColor Yellow
    Write-Host "  → Creating namespace..." -ForegroundColor Cyan
    kubectl create namespace fp-tree
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Namespace created" -ForegroundColor Green
    }
}

# Step 5: Check Jobs and Pods
Write-Host ""
Write-Host "[5/6] Checking Experiments..." -ForegroundColor Yellow
$jobs = kubectl get jobs -n fp-tree -o name 2>$null
$pods = kubectl get pods -n fp-tree --no-headers 2>$null

if ($pods) {
    Write-Host "  📊 Pods found:" -ForegroundColor Cyan
    kubectl get pods -n fp-tree
    Write-Host ""
    
    # Check pod statuses
    $runningPods = kubectl get pods -n fp-tree --field-selector=status.phase=Running --no-headers 2>$null
    $completedPods = kubectl get pods -n fp-tree --field-selector=status.phase=Succeeded --no-headers 2>$null
    $failedPods = kubectl get pods -n fp-tree --field-selector=status.phase=Failed --no-headers 2>$null
    
    if ($runningPods) {
        Write-Host "  ✅ Experiments are RUNNING!" -ForegroundColor Green
        Write-Host "  → Monitor with: kubectl logs -f -n fp-tree <pod-name>" -ForegroundColor Cyan
    } elseif ($completedPods) {
        Write-Host "  🎉 Experiments COMPLETED!" -ForegroundColor Green
        Write-Host "  → Extract results with: kubectl cp fp-tree/<pod-name>:/app/results ./results-final" -ForegroundColor Cyan
    } elseif ($failedPods) {
        Write-Host "  ❌ Experiments FAILED" -ForegroundColor Red
        Write-Host "  → Check logs: kubectl logs -n fp-tree <pod-name>" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠️  No pods found - experiments need to be deployed" -ForegroundColor Yellow
    Write-Host "  → Deploy with:" -ForegroundColor Cyan
    Write-Host "     kubectl apply -f k8s/results-pvc.yaml" -ForegroundColor Gray
    Write-Host "     kubectl apply -f k8s/job.yaml" -ForegroundColor Gray
    Write-Host "     kubectl apply -f k8s/synthetic-job.yaml" -ForegroundColor Gray
}

# Step 6: Check PVC
Write-Host ""
Write-Host "[6/6] Checking Storage..." -ForegroundColor Yellow
$pvcExists = kubectl get pvc fp-tree-results -n fp-tree -o name 2>$null
if ($pvcExists -eq "persistentvolumeclaim/fp-tree-results") {
    $pvcStatus = kubectl get pvc fp-tree-results -n fp-tree -o jsonpath='{.status.phase}' 2>$null
    Write-Host "  ✅ PVC 'fp-tree-results' exists (Status: $pvcStatus)" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  PVC 'fp-tree-results' NOT found" -ForegroundColor Yellow
    Write-Host "  → Create with: kubectl apply -f k8s/results-pvc.yaml" -ForegroundColor Cyan
}

# Summary
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "Docker Desktop: " -NoNewline
if ($dockerStatus) { Write-Host "✅ Running" -ForegroundColor Green } else { Write-Host "❌ Not Running" -ForegroundColor Red }

Write-Host "Docker Image:   " -NoNewline
if ($imageExists) { Write-Host "✅ Available" -ForegroundColor Green } else { Write-Host "❌ Missing" -ForegroundColor Red }

Write-Host "Kubernetes:     " -NoNewline
if ($k8sStatus) { Write-Host "✅ Running" -ForegroundColor Green } else { Write-Host "❌ Not Running" -ForegroundColor Red }

Write-Host "Namespace:      " -NoNewline
if ($namespaceExists) { Write-Host "✅ Exists" -ForegroundColor Green } else { Write-Host "⚠️  Missing" -ForegroundColor Yellow }

Write-Host "Experiments:    " -NoNewline
if ($runningPods) { 
    Write-Host "✅ Running" -ForegroundColor Green 
} elseif ($completedPods) { 
    Write-Host "🎉 Completed" -ForegroundColor Green 
} elseif ($failedPods) { 
    Write-Host "❌ Failed" -ForegroundColor Red 
} else { 
    Write-Host "⚠️  Not Deployed" -ForegroundColor Yellow 
}

Write-Host ""
Write-Host "📖 For detailed instructions, see: RECOVERY_INSTRUCTIONS.md" -ForegroundColor Cyan
Write-Host ""
