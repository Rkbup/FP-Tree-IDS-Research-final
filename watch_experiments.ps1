# Simple Experiment Monitor Dashboard
param([int]$RefreshSeconds = 10)

function Get-PodAge {
    param($startTime)
    if ([string]::IsNullOrEmpty($startTime)) { return "N/A" }
    $start = [DateTime]::Parse($startTime)
    $now = [DateTime]::UtcNow
    $age = ($now - $start).TotalSeconds
    $ts = [TimeSpan]::FromSeconds($age)
    if ($ts.TotalHours -ge 1) {
        return "{0:D2}h {1:D2}m {2:D2}s" -f [Math]::Floor($ts.TotalHours), $ts.Minutes, $ts.Seconds
    } else {
        return "{0:D2}m {2}s" -f $ts.Minutes, $ts.Seconds
    }
}

$iteration = 0
while ($true) {
    $iteration++
    Clear-Host
    
    Write-Host "=" * 70 -ForegroundColor Cyan
    Write-Host "FP-Tree IDS Experiment Monitor - $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Green
    Write-Host "=" * 70 -ForegroundColor Cyan
    Write-Host ""
    
    # Get pods
    $pods = kubectl get pods -n fp-tree -o json | ConvertFrom-Json
    
    if ($pods.items.Count -eq 0) {
        Write-Host "[WARNING] No pods found" -ForegroundColor Yellow
    } else {
        foreach ($pod in $pods.items) {
            $name = $pod.metadata.name
            $status = $pod.status.phase
            $age = Get-PodAge $pod.status.startTime
            
            $type = if ($name -match "main") { "MAIN-CIC2017" } else { "SYNTHETIC" }
            
            Write-Host "[$type]" -ForegroundColor Cyan -NoNewline
            Write-Host " $status " -ForegroundColor $(if ($status -eq "Running") { "Green" } elseif ($status -eq "Succeeded") { "Green" } else { "Yellow" }) -NoNewline
            Write-Host "| Runtime: $age" -ForegroundColor Gray
            Write-Host "  Pod: $name" -ForegroundColor DarkGray
            
            # Get last few log lines
            if ($status -eq "Running") {
                $logs = kubectl logs -n fp-tree $name --tail=3 2>&1
                Write-Host "  Latest:" -ForegroundColor DarkCyan
                foreach ($line in $logs[-3..-1]) {
                    if ($line.Length -gt 65) { $line = $line.Substring(0, 65) + "..." }
                    Write-Host "    $line" -ForegroundColor Gray
                }
            }
            Write-Host ""
        }
        
        # Summary
        $running = ($pods.items | Where-Object { $_.status.phase -eq "Running" }).Count
        $succeeded = ($pods.items | Where-Object { $_.status.phase -eq "Succeeded" }).Count
        
        Write-Host "SUMMARY: " -NoNewline -ForegroundColor White
        Write-Host "Running: $running | Succeeded: $succeeded | Total: $($pods.items.Count)" -ForegroundColor Gray
        
        if ($succeeded -eq $pods.items.Count) {
            Write-Host ""
            Write-Host "[SUCCESS] All experiments completed!" -ForegroundColor Green
            break
        }
    }
    
    Write-Host ""
    Write-Host "=" * 70 -ForegroundColor Cyan
    Write-Host "Refreshing in $RefreshSeconds seconds... (Iteration: $iteration)" -ForegroundColor DarkGray
    Write-Host "Press Ctrl+C to exit" -ForegroundColor DarkGray
    
    Start-Sleep -Seconds $RefreshSeconds
}
