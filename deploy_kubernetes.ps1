# Build and deploy script for running FP-Tree experiments on Kubernetes
# This script sets up the complete pipeline for running experiments in Docker containers

Write-Host "Starting FP-Tree Kubernetes Deployment..." -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

# Step 1: Build Docker image
Write-Host "Building Docker image..." -ForegroundColor Yellow
docker build -t fp-tree-ids:latest .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Docker image built successfully!" -ForegroundColor Green

# Step 2: Create Kubernetes namespace
Write-Host "Setting up Kubernetes namespace..." -ForegroundColor Yellow
kubectl create namespace fp-tree --dry-run=client -o yaml | kubectl apply -f -

# Step 3: Apply ConfigMap
Write-Host "Applying ConfigMap..." -ForegroundColor Yellow
kubectl apply -f k8s/configmap.yaml

# Step 4: Apply PVC
Write-Host "Setting up Persistent Volume..." -ForegroundColor Yellow
kubectl apply -f k8s/pvc.yaml

# Step 5: Deploy the job
Write-Host "Deploying experiment job..." -ForegroundColor Yellow
kubectl apply -f k8s/job.yaml

Write-Host "Kubernetes deployment complete!" -ForegroundColor Green
Write-Host "Monitor progress with:" -ForegroundColor Cyan
Write-Host "   kubectl get pods -n fp-tree -w" -ForegroundColor White
Write-Host "   kubectl logs -n fp-tree -f <pod-name>" -ForegroundColor White
Write-Host "Use the monitoring dashboard in the other terminal for live updates!" -ForegroundColor Magenta