# Extract Results from Kubernetes Experiments
# This script extracts all results from completed experiment pods

param(
    [string]$OutputDir = ".\results-final"
)

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   FP-Tree IDS - Results Extraction" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check Kubernetes connection
Write-Host "[Step 1/4] Checking Kubernetes connection..." -ForegroundColor Yellow
$pods = kubectl get pods -n fp-tree -o json 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Cannot connect to Kubernetes cluster" -ForegroundColor Red
    Write-Host "  Please ensure Docker Desktop and Kubernetes are running" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Connected to Kubernetes" -ForegroundColor Green
Write-Host ""

# Parse pod information
$podsJson = $pods | ConvertFrom-Json
if ($podsJson.items.Count -eq 0) {
    Write-Host "✗ No pods found in fp-tree namespace" -ForegroundColor Red
    exit 1
}

# Check pod completion status
Write-Host "[Step 2/4] Checking experiment completion status..." -ForegroundColor Yellow
$allCompleted = $true
foreach ($pod in $podsJson.items) {
    $name = $pod.metadata.name
    $status = $pod.status.phase
    
    Write-Host "  Pod: $name" -ForegroundColor Cyan
    Write-Host "    Status: $status" -ForegroundColor $(if ($status -eq "Succeeded") { "Green" } elseif ($status -eq "Running") { "Yellow" } else { "Red" })
    
    if ($status -ne "Succeeded" -and $status -ne "Failed") {
        $allCompleted = $false
    }
}
Write-Host ""

if (-not $allCompleted) {
    Write-Host "⚠️  Warning: Some experiments are still running" -ForegroundColor Yellow
    Write-Host "   Results may be incomplete. Continue anyway? (Y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -ne "Y" -and $response -ne "y") {
        Write-Host "Extraction cancelled" -ForegroundColor Gray
        exit 0
    }
}

# Create output directory
Write-Host "[Step 3/4] Creating output directory..." -ForegroundColor Yellow
if (Test-Path $OutputDir) {
    Write-Host "  Directory already exists: $OutputDir" -ForegroundColor Gray
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupDir = "$OutputDir-backup-$timestamp"
    Write-Host "  Creating backup: $backupDir" -ForegroundColor Yellow
    Move-Item -Path $OutputDir -Destination $backupDir
}
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
Write-Host "✓ Output directory ready: $OutputDir" -ForegroundColor Green
Write-Host ""

# Extract results from each pod
Write-Host "[Step 4/4] Extracting results from pods..." -ForegroundColor Yellow
$successCount = 0
foreach ($pod in $podsJson.items) {
    $podName = $pod.metadata.name
    $expType = if ($podName -match "main") { "main" } else { "synthetic" }
    $podOutputDir = Join-Path $OutputDir $expType
    
    Write-Host "  Extracting from: $podName" -ForegroundColor Cyan
    
    # Create subdirectory for this experiment
    New-Item -ItemType Directory -Path $podOutputDir -Force | Out-Null
    
    # Copy results directory
    Write-Host "    Copying /app/results..." -ForegroundColor Gray
    $copyCmd = "kubectl cp fp-tree/${podName}:/app/results `"$podOutputDir`" 2>&1"
    $result = Invoke-Expression $copyCmd
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✓ Results copied successfully" -ForegroundColor Green
        
        # Count files
        $fileCount = (Get-ChildItem -Path $podOutputDir -Recurse -File).Count
        Write-Host "    Files extracted: $fileCount" -ForegroundColor Gray
        $successCount++
    } else {
        Write-Host "    ✗ Failed to copy results" -ForegroundColor Red
        Write-Host "    Error: $result" -ForegroundColor Red
    }
    
    # Also copy logs
    Write-Host "    Saving pod logs..." -ForegroundColor Gray
    $logFile = Join-Path $podOutputDir "experiment.log"
    kubectl logs -n fp-tree $podName > $logFile 2>&1
    if (Test-Path $logFile) {
        $logSize = (Get-Item $logFile).Length
        Write-Host "    ✓ Logs saved ($([math]::Round($logSize/1KB, 2)) KB)" -ForegroundColor Green
    }
    
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   Extraction Complete!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ Successfully extracted results from $successCount pod(s)" -ForegroundColor Green
Write-Host "📁 Results location: $OutputDir" -ForegroundColor Cyan
Write-Host ""

# Display directory structure
Write-Host "Directory structure:" -ForegroundColor Cyan
Get-ChildItem -Path $OutputDir -Recurse -Directory | ForEach-Object {
    $depth = ($_.FullName.Substring($OutputDir.Length) -split '\\').Count - 1
    $indent = "  " * $depth
    Write-Host "$indent📁 $($_.Name)" -ForegroundColor Gray
}
Write-Host ""

# Display file summary
Write-Host "File summary:" -ForegroundColor Cyan
$allFiles = Get-ChildItem -Path $OutputDir -Recurse -File
$totalSize = ($allFiles | Measure-Object -Property Length -Sum).Sum
Write-Host "  Total files: $($allFiles.Count)" -ForegroundColor Gray
Write-Host "  Total size: $([math]::Round($totalSize/1MB, 2)) MB" -ForegroundColor Gray
Write-Host ""

# Look for key result files
Write-Host "Key result files found:" -ForegroundColor Cyan
$keyFiles = @("*.png", "*.pdf", "*.csv", "*.json", "*.md")
foreach ($pattern in $keyFiles) {
    $files = Get-ChildItem -Path $OutputDir -Recurse -Filter $pattern
    if ($files.Count -gt 0) {
        Write-Host "  $pattern : $($files.Count) file(s)" -ForegroundColor Green
    }
}
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Review results in: $OutputDir" -ForegroundColor Gray
Write-Host "  2. Run cleanup script: .\cleanup.ps1" -ForegroundColor Gray
Write-Host "  3. Archive results: .\archive_results.ps1" -ForegroundColor Gray
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
