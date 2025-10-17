# Linux VM Setup Guide for FP-Tree-IDS-Research-final

## 1. Create a Linux VM (Ubuntu recommended)
- Use VirtualBox, VMware, or a cloud provider (AWS EC2, GCP, Azure, etc.)
- Recommended: Ubuntu 22.04 LTS, 4+ CPU, 16GB+ RAM, 50GB+ disk

## 2. Update and Install Essentials
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget build-essential python3.13 python3.13-venv python3-pip docker.io docker-compose make
```

## 3. Add User to Docker Group
```bash
sudo usermod -aG docker $USER
newgrp docker
```

## 4. Install Minikube (Kubernetes, optional)
```bash
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
minikube start --driver=docker
```

## 5. Clone the Project
```bash
git clone <your-repo-url>
cd FP-Tree-IDS-Research-final
```

## 6. Python Environment Setup
```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 7. Build Docker Image (optional)
```bash
docker build -t fp-tree-ids:latest .
```

## 8. Run Experiments (see Makefile or bash scripts)

---

# For full automation, use the provided Makefile or bash scripts.
