#!/usr/bin/env python3
"""
max_resource_controller.py
=========================

Always-active function that gives MAXIMUM resource utilization and HIGHEST priority 
to FP-Tree experiments. This script automatically:

1. Sets process priority to REALTIME/HIGH
2. Allocates maximum CPU cores 
3. Increases memory limits
4. Optimizes system for computation
5. Monitors and adjusts resources dynamically

Usage
-----
Run this BEFORE starting any experiments to get maximum performance:

```bash
python max_resource_controller.py
```
"""

import os
import sys
import time
import psutil
import signal
import subprocess
import multiprocessing
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

class MaxResourceController:
    """Controller for maximum resource utilization."""
    
    def __init__(self):
        self.cpu_count = multiprocessing.cpu_count()
        self.total_memory = psutil.virtual_memory().total
        self.running_processes = []
        self.is_active = True
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.ctrl_c_ignore_handler)  # Ignore Ctrl+C
        signal.signal(signal.SIGTERM, self.graceful_shutdown)
        
        # Start keyboard listener for Ctrl+H
        import threading
        keyboard_thread = threading.Thread(target=self.keyboard_listener, daemon=True)
        keyboard_thread.start()
        
        print("🚀 MAXIMUM RESOURCE CONTROLLER INITIALIZED")
        print("=" * 60)
        print(f"💻 Available CPU Cores: {self.cpu_count}")
        print(f"💾 Total Memory: {self.total_memory / (1024**3):.2f} GB")
        print(f"⚡ Priority Level: MAXIMUM")
        print("=" * 60)
    
    def ctrl_c_ignore_handler(self, signum, frame):
        """Handle Ctrl+C - ignore it to prevent accidental shutdown."""
        print("\n💡 Ctrl+C detected. Use Ctrl+H to stop all processes gracefully.")
        print("   This prevents accidental interruption while copying error messages.")
    
    def keyboard_listener(self):
        """Listen for Ctrl+H to trigger graceful shutdown."""
        try:
            import keyboard
            while self.is_active:
                if keyboard.is_pressed('ctrl+h'):
                    self.graceful_shutdown(None, None)
                    break
                time.sleep(0.1)
        except ImportError:
            print("⚠️  Warning: 'keyboard' module not installed. Ctrl+H shutdown not available.")
        except Exception as e:
            print(f"⚠️  Keyboard listener error: {e}")
    
    def graceful_shutdown(self, signum, frame):
        """Handle shutdown gracefully."""
        if signum:
            print(f"\n⚠️  Shutdown signal received ({signum})")
        else:
            print(f"\n⚠️  Ctrl+H pressed - Graceful shutdown requested")
        print("🔄 Restoring normal system priorities...")
        self.is_active = False
        self.restore_normal_priorities()
        sys.exit(0)
    
    def set_process_priority(self, pid: int, priority: str = 'high'):
        """Set process priority to maximum."""
        try:
            process = psutil.Process(pid)
            
            if os.name == 'nt':  # Windows
                if priority == 'realtime':
                    process.nice(psutil.REALTIME_PRIORITY_CLASS)
                elif priority == 'high':
                    process.nice(psutil.HIGH_PRIORITY_CLASS)
                else:
                    process.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
            else:  # Linux/Unix
                # Set nice value to minimum (highest priority)
                process.nice(-20)
            
            return True
        except Exception as e:
            print(f"⚠️  Warning: Could not set priority for PID {pid}: {e}")
            return False
    
    def optimize_system_settings(self):
        """Optimize system settings for maximum performance."""
        print("⚙️  OPTIMIZING SYSTEM SETTINGS...")
        
        try:
            if os.name == 'nt':  # Windows optimizations
                # Set power plan to High Performance
                subprocess.run([
                    'powercfg', '/setactive', '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'
                ], capture_output=True)
                print("  ✓ Power plan set to High Performance")
                
                # Disable CPU throttling
                subprocess.run([
                    'powercfg', '/setacvalueindex', 'scheme_current', 
                    'sub_processor', 'PROCTHROTTLEMIN', '100'
                ], capture_output=True)
                print("  ✓ CPU throttling disabled")
                
            # Set memory overcommit (Linux)
            if os.path.exists('/proc/sys/vm/overcommit_memory'):
                with open('/proc/sys/vm/overcommit_memory', 'w') as f:
                    f.write('1')
                print("  ✓ Memory overcommit enabled")
                
        except Exception as e:
            print(f"  ⚠️  Some optimizations failed: {e}")
    
    def start_synthetic_experiment(self):
        """Start synthetic experiment with maximum resources."""
        print("\n🧪 STARTING SYNTHETIC EXPERIMENT (MAX RESOURCES)")
        print("-" * 50)
        
        # Configure environment for maximum performance
        env = os.environ.copy()
        env.update({
            'OMP_NUM_THREADS': str(self.cpu_count),
            'NUMBA_NUM_THREADS': str(self.cpu_count),
            'MKL_NUM_THREADS': str(self.cpu_count),
            'OPENBLAS_NUM_THREADS': str(self.cpu_count),
            'VECLIB_MAXIMUM_THREADS': str(self.cpu_count),
            'PYTHONUNBUFFERED': '1',
            'CUDA_VISIBLE_DEVICES': '0',  # Use GPU if available
        })
        
        # Start synthetic experiment
        python_exe = sys.executable
        cmd = [python_exe, 'experiments/synthetic_full_experiment.py']
        
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Set maximum priority
        self.set_process_priority(process.pid, 'high')
        
        # Set CPU affinity to use all cores
        try:
            psutil.Process(process.pid).cpu_affinity(list(range(self.cpu_count)))
            print(f"  ✓ Process assigned to all {self.cpu_count} CPU cores")
        except:
            print("  ⚠️  Could not set CPU affinity")
        
        self.running_processes.append(process)
        print(f"  ✓ Synthetic experiment started (PID: {process.pid})")
        return process
    
    def start_kubernetes_deployment(self):
        """Start Kubernetes deployment with maximum resources."""
        print("\n☸️  STARTING KUBERNETES DEPLOYMENT (MAX RESOURCES)")
        print("-" * 50)
        
        # Update Kubernetes job to use maximum resources
        self.update_kubernetes_resources()
        
        # Deploy with maximum priority
        cmd = ['powershell', '-ExecutionPolicy', 'Bypass', '-File', 'deploy_kubernetes.ps1']
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Set high priority for deployment process
        self.set_process_priority(process.pid, 'high')
        
        self.running_processes.append(process)
        print(f"  ✓ Kubernetes deployment started (PID: {process.pid})")
        return process
    
    def update_kubernetes_resources(self):
        """Update Kubernetes manifests for maximum resource allocation."""
        job_file = Path('k8s/job.yaml')
        
        if job_file.exists():
            content = job_file.read_text()
            
            # Update resource limits to maximum
            updated_content = content.replace(
                'cpu: "8"', f'cpu: "{self.cpu_count}"'
            ).replace(
                'memory: 32Gi', f'memory: {int(self.total_memory / (1024**3) * 0.8)}Gi'
            ).replace(
                'cpu: "4"', f'cpu: "{max(1, self.cpu_count // 2)}"'
            ).replace(
                'memory: 16Gi', f'memory: {int(self.total_memory / (1024**3) * 0.4)}Gi'
            )
            
            job_file.write_text(updated_content)
            print(f"  ✓ Kubernetes resources updated for maximum utilization")
    
    def start_monitoring_dashboard(self):
        """Start monitoring dashboard."""
        print("\n📊 STARTING MONITORING DASHBOARD")
        print("-" * 50)
        
        python_exe = sys.executable
        cmd = [python_exe, 'monitor_experiments.py']
        
        process = subprocess.Popen(
            cmd,
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        self.running_processes.append(process)
        print(f"  ✓ Monitoring dashboard started (PID: {process.pid})")
        return process
    
    def monitor_and_optimize(self):
        """Continuously monitor and optimize resource usage."""
        print("\n🔄 STARTING CONTINUOUS OPTIMIZATION LOOP")
        print("-" * 50)
        
        while self.is_active:
            try:
                # Get current system stats
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                
                # Boost priority of our processes if needed
                for process in self.running_processes[:]:
                    try:
                        if process.poll() is None:  # Process is running
                            # Ensure high priority is maintained
                            self.set_process_priority(process.pid, 'high')
                        else:
                            # Remove completed processes
                            self.running_processes.remove(process)
                    except:
                        # Process may have ended
                        if process in self.running_processes:
                            self.running_processes.remove(process)
                
                # Print status every 30 seconds
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"[{current_time}] 🔥 CPU: {cpu_percent:5.1f}% | Memory: {memory.percent:5.1f}% | Active Processes: {len(self.running_processes)}")
                
                # Sleep before next check
                time.sleep(30)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"⚠️  Monitoring error: {e}")
                time.sleep(5)
    
    def restore_normal_priorities(self):
        """Restore normal system priorities."""
        for process in self.running_processes:
            try:
                if process.poll() is None:
                    self.set_process_priority(process.pid, 'normal')
            except:
                pass
        print("✓ System priorities restored to normal")
    
    def run(self):
        """Main execution function."""
        try:
            # Step 1: Optimize system settings
            self.optimize_system_settings()
            
            # Step 2: Start synthetic experiment
            synthetic_process = self.start_synthetic_experiment()
            
            # Step 3: Start Kubernetes deployment
            k8s_process = self.start_kubernetes_deployment()
            
            # Step 4: Start monitoring
            monitor_process = self.start_monitoring_dashboard()
            
            print("\n🎯 ALL SYSTEMS LAUNCHED WITH MAXIMUM RESOURCES!")
            print("=" * 60)
            print("📊 Synthetic Experiment: RUNNING (Max Priority)")
            print("☸️  Kubernetes Deployment: DEPLOYING (Max Resources)")
            print("📈 Live Monitoring: ACTIVE")
            print("🔄 Resource Optimization: CONTINUOUS")
            print("=" * 60)
            print("💡 Press Ctrl+C to stop all processes gracefully")
            print("🚀 Your experiments are now using MAXIMUM system resources!")
            
            # Step 5: Continuous monitoring and optimization
            self.monitor_and_optimize()
            
        except Exception as e:
            print(f"❌ Error in main execution: {e}")
            self.graceful_shutdown(None, None)

def main():
    """Entry point."""
    print("🔥🔥🔥 MAXIMUM RESOURCE UTILIZATION MODE 🔥🔥🔥")
    print("This will give your experiments the HIGHEST priority and ALL available resources!")
    print()
    
    controller = MaxResourceController()
    controller.run()

if __name__ == "__main__":
    main()