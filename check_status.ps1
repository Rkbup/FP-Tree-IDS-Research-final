
ls -la# Quick Recovery Script
# Run this after PC restart to check status and resume experiments

Write-Host "=== FP-Tree IDS Experiment Recovery ===" -ForegroundColor Cyan
Write-Host ("Date: {0}" -f (Get-Date)) -ForegroundColor Gray

# Step 5: Check Pods
Write-Host ""
Write-Host "[5/6] Checking Experiments..." -ForegroundColor Yellow
$pods = kubectl get pods -n fp-tree --no-headers 2>$null
if ($pods) {
    Write-Host "  Pods found:" -ForegroundColor Cyan
    kubectl get pods -n fp-tree
    Write-Host ""
    # Check pod statuses
    $runningPods = kubectl get pods -n fp-tree --field-selector=status.phase=Running --no-headers 2>$null
    $completedPods = kubectl get pods -n fp-tree --field-selector=status.phase=Succeeded --no-headers 2>$null
    $failedPods = kubectl get pods -n fp-tree --field-selector=status.phase=Failed --no-headers 2>$null
    if ($pods) {
        Write-Host "  Pods found:" -ForegroundColor Cyan
        kubectl get pods -n fp-tree
        Write-Host ""
        # Check pod statuses
        $runningPods = kubectl get pods -n fp-tree --field-selector=status.phase=Running --no-headers 2>$null
        $completedPods = kubectl get pods -n fp-tree --field-selector=status.phase=Succeeded --no-headers 2>$null
        $failedPods = kubectl get pods -n fp-tree --field-selector=status.phase=Failed --no-headers 2>$null
        if ($runningPods) {
            Write-Host "  Experiments are RUNNING!" -ForegroundColor Green
            Write-Host "  Monitor with: kubectl logs -f -n fp-tree [pod-name]" -ForegroundColor Cyan
        } elseif ($completedPods) {
            Write-Host "  Experiments COMPLETED!" -ForegroundColor Green
            Write-Host "  Extract results with: kubectl cp fp-tree/[pod-name]:/app/results ./results-final" -ForegroundColor Cyan
        } elseif ($failedPods) {
            Write-Host "  Experiments FAILED" -ForegroundColor Red
            Write-Host "  Check logs: kubectl logs -n fp-tree [pod-name]" -ForegroundColor Yellow
        } else {
            Write-Host "  No pods found - experiments need to be deployed" -ForegroundColor Yellow
            Write-Host "  Deploy with:" -ForegroundColor Cyan
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
        Write-Host ("  PVC 'fp-tree-results' exists (Status: {0})" -f $pvcStatus) -ForegroundColor Green
    } else {
        Write-Host "  PVC 'fp-tree-results' NOT found" -ForegroundColor Yellow
        Write-Host "  Create with: kubectl apply -f k8s/results-pvc.yaml" -ForegroundColor Cyan
    }

    # Summary
    Write-Host ""
    Write-Host "=== Summary ===" -ForegroundColor Cyan
    Write-Host "Docker Desktop: " -NoNewline
    if ($dockerStatus) { Write-Host "Running" -ForegroundColor Green } else { Write-Host "Not Running" -ForegroundColor Red }

    Write-Host "Docker Image:   " -NoNewline
    if ($imageExists) { Write-Host "Available" -ForegroundColor Green } else { Write-Host "Missing" -ForegroundColor Red }

    Write-Host "Kubernetes:     " -NoNewline
    if ($k8sStatus) { Write-Host "Running" -ForegroundColor Green } else { Write-Host "Not Running" -ForegroundColor Red }

    Write-Host "Namespace:      " -NoNewline
    if ($namespaceExists) { Write-Host "Exists" -ForegroundColor Green } else { Write-Host "Missing" -ForegroundColor Yellow }

    Write-Host "Experiments:    " -NoNewline
    if ($runningPods) { 
        Write-Host "Running" -ForegroundColor Green 
    } elseif ($completedPods) { 
        Write-Host "Completed" -ForegroundColor Green 
    } elseif ($failedPods) { 
        Write-Host "Failed" -ForegroundColor Red 
    } else { 
        Write-Host "Not Deployed" -ForegroundColor Yellow 
    }

    Write-Host ""
    Write-Host ""
    } elseif ($failedPods) {
        Write-Host "  Experiments FAILED" -ForegroundColor Red
        Write-Host "  Check logs: kubectl logs -n fp-tree [pod-name]" -ForegroundColor Yellow
    }
} else {
    Write-Host "  No pods found - experiments need to be deployed" -ForegroundColor Yellow
    Write-Host "  Deploy with:" -ForegroundColor Cyan
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
    Write-Host ("  ✅ PVC 'fp-tree-results' exists (Status: {0})" -f $pvcStatus) -ForegroundColor Green
} else {
    Write-Host "  PVC 'fp-tree-results' NOT found" -ForegroundColor Yellow
    Write-Host "  Create with: kubectl apply -f k8s/results-pvc.yaml" -ForegroundColor Cyan
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
if ($namespaceExists) { Write-Host "✅ Exists" -ForegroundColor Green } else { Write-Host "Missing" -ForegroundColor Yellow }
Write-Host "Experiments:    " -NoNewline
if ($runningPods) { 
    Write-Host "✅ Running" -ForegroundColor Green 
} elseif ($completedPods) { 
    Write-Host "🎉 Completed" -ForegroundColor Green 
} elseif ($failedPods) { 
    Write-Host "❌ Failed" -ForegroundColor Red 
} else { 
    Write-Host "Not Deployed" -ForegroundColor Yellow 
}
Write-Host ""

