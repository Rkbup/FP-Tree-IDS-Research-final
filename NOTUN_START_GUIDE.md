# নতুন করে Experiment শুরু করার গাইড
# =====================================

## বর্তমান সমস্যা
Docker Desktop বন্ধ আছে অথবা সঠিকভাবে চলছে না।

## সমাধান (খুব সহজ)

### ১. Docker Desktop চালু করুন

**দ্রুত পদ্ধতি:**
1. `Windows Key` চাপুন
2. টাইপ করুন: `Docker Desktop`
3. `Enter` চাপুন
4. অপেক্ষা করুন ৩০-৬০ সেকেন্ড
5. নিচে ডানদিকে Docker আইকন দেখুন (whale) - সবুজ হলে তৈরি

**অথবা PowerShell দিয়ে:**
```powershell
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Start-Sleep -Seconds 60
```

### ২. Experiment শুরু করুন

Docker Desktop চালু হলে এই কমান্ড চালান:

```powershell
.\fresh_start.ps1
```

এটি স্বয়ংক্রিয়ভাবে করবে:
- ✓ পুরাতন experiments মুছে ফেলবে
- ✓ নতুন experiments deploy করবে
- ✓ Status দেখাবে
- ✓ Logs দেখাবে

### ৩. Monitor করুন

```powershell
# স্বয়ংক্রিয় monitoring
.\watch_experiments.ps1

# অথবা manual
kubectl get pods -n fp-tree -w
```

### ৪. Logs দেখুন

```powershell
# Main experiment
kubectl logs -f -n fp-tree <pod-name>

# Synthetic experiment  
kubectl logs -f -n fp-tree <pod-name>
```

## সময়সীমা

- **Main Experiment:** ৪-৫ ঘন্টা
- **Synthetic Experiment:** ২-৩ ঘন্টা

## সম্পূর্ণ হলে

```powershell
# Results extract করুন
.\extract_results.ps1

# Archive করুন
.\archive_results.ps1 -IncludeCode

# Cleanup করুন
.\cleanup.ps1
```

## সমস্যা হলে

### Docker চালু হচ্ছে না
1. Task Manager খুলুন
2. Docker process kill করুন
3. আবার চালু করুন

### Kubernetes সবুজ হচ্ছে না
1. Docker Desktop → Settings
2. Kubernetes tab
3. "Enable Kubernetes" check করুন
4. Apply & Restart

### Pods শুরু হচ্ছে না
```powershell
# Status check
kubectl get pods -n fp-tree

# Describe pod
kubectl describe pod -n fp-tree <pod-name>

# Delete এবং আবার deploy
kubectl delete jobs --all -n fp-tree
kubectl apply -f k8s/job.yaml
kubectl apply -f k8s/synthetic-job.yaml
```

## Quick Commands

```powershell
# Docker status
docker ps

# Pod status
kubectl get pods -n fp-tree

# Pod logs
kubectl logs -n fp-tree <pod-name>

# Fresh start
.\fresh_start.ps1

# Monitor
.\watch_experiments.ps1

# Extract
.\extract_results.ps1
```

---

## এখনই করুন

1. **Docker Desktop চালু করুন** (Windows Key → "Docker Desktop" → Enter)
2. **৬০ সেকেন্ড অপেক্ষা করুন** (Docker সবুজ হতে দিন)
3. **Experiment শুরু করুন:** `.\fresh_start.ps1`
4. **Monitor করুন:** `.\watch_experiments.ps1`

সব কিছু automatic! 🚀
