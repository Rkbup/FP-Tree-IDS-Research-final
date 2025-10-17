# FP-Tree IDS Experiment - Complete Status Report
# Generated on runtime

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   FP-Tree IDS Research - Experiment Status Report" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check Docker status
Write-Host "[1/5] Checking Docker Desktop..." -ForegroundColor Yellow
$dockerRunning = $false
try {
    docker ps > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Docker Desktop is running" -ForegroundColor Green
        $dockerRunning = $true
    } else {
        Write-Host "  ✗ Docker Desktop is not responding" -ForegroundColor Red
        Write-Host "    Please start Docker Desktop and wait for it to fully initialize" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ Docker Desktop is not running" -ForegroundColor Red
    Write-Host "    Please start Docker Desktop" -ForegroundColor Yellow
}
Write-Host ""

# Check Kubernetes cluster
Write-Host "[2/5] Checking Kubernetes cluster..." -ForegroundColor Yellow
$k8sRunning = $false
if ($dockerRunning) {
    try {
        $clusterInfo = kubectl cluster-info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Kubernetes cluster is accessible" -ForegroundColor Green
            $k8sRunning = $true
        } else {
            Write-Host "  ✗ Cannot connect to Kubernetes cluster" -ForegroundColor Red
            Write-Host "    Enable Kubernetes in Docker Desktop Settings" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ✗ kubectl not available" -ForegroundColor Red
    }
} else {
    Write-Host "  ⊘ Skipped (Docker not running)" -ForegroundColor Gray
}
Write-Host ""

# Check namespace
Write-Host "[3/5] Checking fp-tree namespace..." -ForegroundColor Yellow
if ($k8sRunning) {
    $ns = kubectl get namespace fp-tree 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Namespace exists" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Namespace not found" -ForegroundColor Red
    }
} else {
    Write-Host "  ⊘ Skipped (Kubernetes not running)" -ForegroundColor Gray
}
Write-Host ""

# Check pods
Write-Host "[4/5] Checking experiment pods..." -ForegroundColor Yellow
if ($k8sRunning) {
    $pods = kubectl get pods -n fp-tree --no-headers 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Pods found:" -ForegroundColor Green
        Write-Host ""
        kubectl get pods -n fp-tree -o wide
        Write-Host ""
        
        # Check pod status details
        $podsJson = kubectl get pods -n fp-tree -o json | ConvertFrom-Json
        foreach ($pod in $podsJson.items) {
            $podName = $pod.metadata.name
            $status = $pod.status.phase
            
            Write-Host "  Pod: $podName" -ForegroundColor Cyan
            Write-Host "    Status: $status" -ForegroundColor $(if ($status -eq "Running") { "Green" } elseif ($status -eq "Succeeded") { "Green" } else { "Yellow" })
            
            if ($status -eq "Running" -or $status -eq "Succeeded") {
                Write-Host "    Recent logs:" -ForegroundColor DarkCyan
                $logs = kubectl logs -n fp-tree $podName --tail=5 2>&1
                foreach ($line in $logs) {
                    Write-Host "      $line" -ForegroundColor Gray
                }
            }
            Write-Host ""
        }
    } else {
        Write-Host "  ✗ No pods found or cannot access" -ForegroundColor Red
    }
} else {
    Write-Host "  ⊘ Skipped (Kubernetes not running)" -ForegroundColor Gray
}
Write-Host ""

# Check results
Write-Host "[5/5] Checking results..." -ForegroundColor Yellow
if (Test-Path ".\results-final") {
    Write-Host "  ✓ Results directory exists" -ForegroundColor Green
    $fileCount = (Get-ChildItem -Path ".\results-final" -Recurse -File).Count
    Write-Host "    Files found: $fileCount" -ForegroundColor Gray
} else {
    Write-Host "  ⊘ Results not yet extracted" -ForegroundColor Gray
}
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   Summary and Next Steps" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if ($k8sRunning) {
    Write-Host "✓ System Status: READY" -ForegroundColor Green
    Write-Host ""
    Write-Host "Available Commands:" -ForegroundColor Cyan
    Write-Host "  Monitor pods:      kubectl get pods -n fp-tree -w" -ForegroundColor Gray
    Write-Host "  Check main logs:   kubectl logs -f -n fp-tree fp-tree-main-experiment-rhxql" -ForegroundColor Gray
    Write-Host "  Check synth logs:  kubectl logs -f -n fp-tree fp-tree-synthetic-experiment-qdnbd" -ForegroundColor Gray
    Write-Host "  Quick status:      .\check_status.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "When experiments complete:" -ForegroundColor Cyan
    Write-Host "  Extract results:   .\extract_results.ps1" -ForegroundColor Gray
    Write-Host "  Clean up:          .\cleanup.ps1" -ForegroundColor Gray
} else {
    Write-Host "✗ System Status: NEEDS ATTENTION" -ForegroundColor Red
    Write-Host ""
    Write-Host "Required Actions:" -ForegroundColor Yellow
    Write-Host "  1. Start Docker Desktop" -ForegroundColor Gray
    Write-Host "  2. Enable Kubernetes in Docker Desktop Settings" -ForegroundColor Gray
    Write-Host "  3. Wait for Kubernetes to be ready (green indicator)" -ForegroundColor Gray
    Write-Host "  4. Run this script again to verify" -ForegroundColor Gray
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
