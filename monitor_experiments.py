#!/usr/bin/env python3
"""
monitor_experiments.py
=====================

Static, non-flickering monitoring dashboard using Rich.
Only numeric values update; the layout stays fixed for easy reading.

Controls:
- Ctrl+M: Stop monitoring gracefully (recommended)
- Ctrl+C: Ignored (safe for copying errors)
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import psutil
from rich.console import Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Global flag
stop_monitoring = False


def get_system_stats() -> Dict:
    """Return system and FP-Tree process stats (stable ordering, robust)."""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    fp_procs: List[Dict] = []
    total_fp_cpu = 0.0
    total_fp_mem = 0.0

    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info.get('cmdline') or [])
                if any(k in cmdline.lower() for k in ['fp-tree', 'synthetic_full', 'main_experiment', 'max_resource']):
                    try:
                        cpu_p = proc.cpu_percent(interval=None)
                        mem_p = proc.memory_percent()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        cpu_p, mem_p = 0.0, 0.0
                    fp_procs.append({
                        'pid': proc.info.get('pid'),
                        'name': proc.info.get('name') or 'proc',
                        'cpu_percent': cpu_p,
                        'memory_percent': mem_p,
                    })
                    total_fp_cpu += cpu_p
                    total_fp_mem += mem_p
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass

    # Stable order by PID to avoid row jumping
    fp_procs.sort(key=lambda p: (p['pid'] is None, p['pid']))

    return {
        'cpu_percent': cpu_percent,
        'memory_percent': mem.percent,
        'memory_available_gb': mem.available / (1024 ** 3),
        'disk_percent': disk.percent,
        'disk_free_gb': disk.free / (1024 ** 3),
        'fp_tree_processes': fp_procs[:5],
        'total_fp_cpu': total_fp_cpu,
        'total_fp_memory': total_fp_mem,
    }


def check_synthetic_progress() -> Dict:
    """Read synthetic checkpoints; provide stable, minimal fields."""
    ck_dir = Path('results/checkpoints')
    algos: List[Dict] = []
    if ck_dir.exists():
        for f in sorted(ck_dir.glob('synthetic_*_checkpoint.json')):
            name = f.stem.replace('synthetic_', '').replace('_checkpoint', '')
            try:
                data = json.loads(f.read_text())
                total = 5000
                current = int(data.get('last_index', -1)) + 1
                progress = max(0.0, min(100.0, (current / total) * 100))
                algos.append({
                    'name': name,
                    'display_name': name,
                    'progress': progress,
                    'current': current,
                    'total': total,
                    'speed': 0.0,
                    'eta': '-',
                })
            except Exception:
                continue
    status = 'Running' if algos else 'Not Started'
    return {'status': status, 'algorithms': algos}


def check_kubernetes_status() -> Dict:
    """Return Kubernetes pods state (if available)."""
    try:
        res = subprocess.run([
            'kubectl', 'get', 'pods', '-n', 'fp-tree', '-o', 'json'
        ], capture_output=True, text=True, timeout=8)
        if res.returncode != 0:
            return {'status': 'Unavailable', 'error': res.stderr.strip()[:120]}
        pods_json = json.loads(res.stdout)
        pods = []
        for it in pods_json.get('items', []):
            meta = it.get('metadata', {})
            st = it.get('status', {})
            cs = (st.get('containerStatuses') or [{}])[0]
            pods.append({
                'name': meta.get('name', ''),
                'status': st.get('phase', ''),
                'ready': cs.get('ready', False),
                'restart_count': cs.get('restartCount', 0),
            })
        return {'status': 'Running' if pods else 'No Pods', 'pods': pods}
    except FileNotFoundError:
        return {'status': 'kubectl not found'}
    except subprocess.TimeoutExpired:
        return {'status': 'Timeout'}
    except Exception as e:
        return {'status': 'Error', 'error': str(e)[:120]}


def check_results_files() -> Dict:
    """Summarize result files without causing layout churn."""
    root = Path('results')
    files: List[Dict] = []
    summary = {'csv_files': 0, 'images': 0, 'checkpoints': 0, 'total_size_mb': 0.0, 'latest_file': None}
    latest_time = 0.0

    if not root.exists():
        return {'status': 'No Results', 'files': [], 'summary': summary}

    def add_file(path: Path, t: str):
        nonlocal latest_time
        st = path.stat()
        size_mb = st.st_size / (1024 ** 2)
        files.append({
            'name': path.name,
            'type': t,
            'size_mb': size_mb,
            'modified': datetime.fromtimestamp(st.st_mtime).strftime('%H:%M:%S'),
        })
        summary['total_size_mb'] += size_mb
        if st.st_mtime > latest_time:
            latest_time = st.st_mtime
            summary['latest_file'] = {'name': path.name, 'time': datetime.fromtimestamp(st.st_mtime).strftime('%H:%M:%S')}

    tdir = root / 'tables'
    if tdir.exists():
        csvs = list(tdir.glob('*.csv'))
        summary['csv_files'] = len(csvs)
        for p in csvs:
            add_file(p, 'CSV Table')

    fdir = root / 'figures'
    if fdir.exists():
        imgs = list(fdir.glob('*.png')) + list(fdir.glob('*.jpg')) + list(fdir.glob('*.pdf'))
        summary['images'] = len(imgs)
        for p in imgs:
            add_file(p, 'Figure/Plot')

    cdir = root / 'checkpoints'
    if cdir.exists():
        chks = list(cdir.glob('*.json'))
        summary['checkpoints'] = len(chks)
        for p in chks:
            add_file(p, 'Checkpoint')

    files.sort(key=lambda d: d['modified'], reverse=True)
    return {'status': 'Found Results' if files else 'No Results', 'files': files[:6], 'summary': summary}


def build_layout(sys_stats: Dict, syn: Dict, k8s: Dict, res: Dict) -> Layout:
    """Create a fixed layout; only cell text changes between refreshes."""
    layout = Layout()
    layout.split_column(
        Layout(name='header', size=3),
        Layout(name='body', ratio=1),
        Layout(name='footer', size=3),
    )

    # Header
    head = Text(justify='center')
    head.append(' FP-TREE EXPERIMENT LIVE MONITOR ', style='bold white on blue')
    head.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    layout['header'].update(head)

    # Body split
    layout['body'].split_row(
        Layout(name='system', ratio=1),
        Layout(name='synthetic', ratio=1),
        Layout(name='k8s_results', ratio=1),
    )

    # System panel (stable order, minimal fields)
    sys_tbl = Table(show_header=False, expand=True)
    sys_tbl.add_row(f"CPU: {sys_stats['cpu_percent']:5.1f}%", f"Mem: {sys_stats['memory_percent']:5.1f}% ({sys_stats['memory_available_gb']:4.1f} GB free)")
    sys_tbl.add_row(f"Disk: {sys_stats['disk_percent']:5.1f}%", f"FP CPU: {sys_stats['total_fp_cpu']:5.1f}% | FP Mem: {sys_stats['total_fp_memory']:5.1f}%")
    if sys_stats['fp_tree_processes']:
        procs = Table(show_header=True, header_style='bold magenta')
        procs.add_column('PID', justify='right')
        procs.add_column('CPU%', justify='right')
        procs.add_column('MEM%', justify='right')
        procs.add_column('NAME', justify='left')
        for p in sys_stats['fp_tree_processes']:
            procs.add_row(str(p['pid']), f"{p['cpu_percent']:4.1f}", f"{p['memory_percent']:4.1f}", p['name'])
        sys_panel = Panel(Group(sys_tbl, procs), title='System', border_style='cyan')
    else:
        sys_panel = Panel(sys_tbl, title='System', border_style='cyan')
    layout['system'].update(sys_panel)

    # Synthetic panel (stable sorted rows)
    syn_tbl = Table(show_header=True, header_style='bold green', expand=True)
    syn_tbl.add_column('Algorithm')
    syn_tbl.add_column('Progress', justify='right')
    syn_tbl.add_column('Speed (tx/min)', justify='right')
    syn_tbl.add_column('ETA', justify='right')
    if syn.get('algorithms'):
        for a in sorted(syn['algorithms'], key=lambda x: x.get('display_name', '')):
            syn_tbl.add_row(
                a.get('display_name', a.get('name', '')),
                f"{a.get('progress', 0):6.2f}% ({a.get('current', 0)}/{a.get('total', 0)})",
                f"{a.get('speed', 0):6.1f}",
                a.get('eta', '-')
            )
    else:
        syn_tbl.add_row('No checkpoints', '-', '-', '-')
    syn_status_icon = '🟢' if syn.get('status') == 'Running' else ('✅' if syn.get('status') == 'Complete' else '⚪')
    layout['synthetic'].update(Panel(Group(Text(f"Status: {syn_status_icon} {syn.get('status', 'N/A')}"), syn_tbl), title='Synthetic', border_style='green'))

    # Kubernetes + Results panel
    k8s_tbl = Table(show_header=True, header_style='bold yellow', expand=True)
    k8s_tbl.add_column('Pod')
    k8s_tbl.add_column('Status')
    k8s_tbl.add_column('Restarts', justify='right')
    if 'pods' in k8s:
        for p in k8s['pods']:
            kicon = '🟢' if p.get('ready') else '🔴'
            k8s_tbl.add_row(f"{kicon} {p.get('name', '')}", p.get('status', ''), str(p.get('restart_count', 0)))
    else:
        k8s_tbl.add_row(k8s.get('status', 'Unknown'), k8s.get('error', ''), '-')

    res_tbl = Table(show_header=True, header_style='bold blue', expand=True)
    res_tbl.add_column('File')
    res_tbl.add_column('Type')
    res_tbl.add_column('Size (MB)', justify='right')
    res_tbl.add_column('Modified')
    for f in res.get('files', [])[:6]:
        res_tbl.add_row(f['name'], f['type'], f"{f['size_mb']:.2f}", f['modified'])
    layout['k8s_results'].update(Panel(Group(k8s_tbl, res_tbl), title='K8s & Results', border_style='yellow'))

    # Footer
    layout['footer'].update(Text('Ctrl+M to stop • Ctrl+C allowed for copying', justify='center'))
    return layout


def display_dashboard():
    """Run the Rich Live dashboard with Ctrl+M stop and no flicker."""
    global stop_monitoring
    stop_monitoring = False

    # Ctrl+M listener (best-effort) with file-based fallback
    import threading

    def key_listener():
        global stop_monitoring
        try:
            import keyboard  # type: ignore
            while not stop_monitoring:
                if keyboard.is_pressed('ctrl+m'):
                    stop_monitoring = True
                    break
                time.sleep(0.1)
        except Exception:
            sentinel = Path('.stop_monitor')
            while not stop_monitoring:
                if sentinel.exists():
                    stop_monitoring = True
                    break
                time.sleep(0.5)

    threading.Thread(target=key_listener, daemon=True).start()

    with Live(refresh_per_second=2, screen=False) as live:
        while not stop_monitoring:
            sys_stats = get_system_stats()
            syn = check_synthetic_progress()
            k8s = check_kubernetes_status()
            res = check_results_files()
            live.update(build_layout(sys_stats, syn, k8s, res))
            try:
                time.sleep(1.0)
            except KeyboardInterrupt:
                # Ignore Ctrl+C to allow copying output
                continue
    print('\nMonitoring stopped.')


if __name__ == '__main__':
    display_dashboard()
#!/usr/bin/env python3
"""
monitor_experiments.py
=====================

Static, non-flickering monitoring dashboard using Rich.
Only numerical values update; layout stays fixed for easy reading.
Controls: Ctrl+M to stop (Ctrl+C is ignored for safe copy).
"""

import os
import sys
import time
import json
import psutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.console import Group

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Global flag for monitoring control
stop_monitoring = False

def get_system_stats() -> Dict:
    """Get current system resource usage with robust error handling."""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    fp_tree_processes: List[Dict] = []
    total_fp_cpu = 0.0
    total_fp_memory = 0.0

    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info.get('cmdline') or [])
                if any(k in cmdline.lower() for k in ['fp-tree', 'synthetic_full', 'main_experiment', 'max_resource']):
                    try:
                        cpu_p = proc.cpu_percent(interval=None)
                        mem_p = proc.memory_percent()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        cpu_p, mem_p = 0.0, 0.0
                    fp_tree_processes.append({
                        'pid': proc.info.get('pid'),
                        'name': proc.info.get('name') or 'proc',
                        'cpu_percent': cpu_p,
                        'memory_percent': mem_p,
                    })
                    total_fp_cpu += cpu_p
                    total_fp_memory += mem_p
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass

    return {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'memory_available_gb': memory.available / (1024**3),
        'disk_percent': disk.percent,
        'disk_free_gb': disk.free / (1024**3),
        'fp_tree_processes': sorted(fp_tree_processes, key=lambda p: p['cpu_percent'], reverse=True)[:5],
        'total_fp_cpu': total_fp_cpu,
        'total_fp_memory': total_fp_memory,
    }
    
    result_files: List[Dict] = []
    summary = {
        'csv_files': 0,
        'images': 0,
        'checkpoints': 0,
        'total_size_mb': 0,
        'latest_file': None
    }
    
    latest_time = 0
    
    # Check tables
    tables_dir = results_dir / "tables"
    if tables_dir.exists():
        csv_files = list(tables_dir.glob("*.csv"))
        summary['csv_files'] = len(csv_files)
        for csv_file in csv_files:
            stat = csv_file.stat()
            size_mb = stat.st_size / (1024**2)
            summary['total_size_mb'] += size_mb
            
            if stat.st_mtime > latest_time:
                latest_time = stat.st_mtime
                summary['latest_file'] = {
                    'name': csv_file.name,
                    'time': datetime.fromtimestamp(stat.st_mtime).strftime('%H:%M:%S')
                }
            
            result_files.append({
                'name': csv_file.name,
                'type': 'CSV Table',
                'size_mb': size_mb,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%H:%M:%S'),
                'path': str(csv_file)
            })
    
    # Check figures
    figures_dir = results_dir / "figures"
    if figures_dir.exists():
        img_files = list(figures_dir.glob("*.png")) + list(figures_dir.glob("*.jpg")) + list(figures_dir.glob("*.pdf"))
        summary['images'] = len(img_files)
        for img_file in img_files:
            stat = img_file.stat()
            size_mb = stat.st_size / (1024**2)
            summary['total_size_mb'] += size_mb
            
            if stat.st_mtime > latest_time:
                latest_time = stat.st_mtime
                summary['latest_file'] = {
                    'name': img_file.name,
                    'time': datetime.fromtimestamp(stat.st_mtime).strftime('%H:%M:%S')
                }
            
            result_files.append({
                'name': img_file.name,
                'type': 'Figure/Plot',
                'size_mb': size_mb,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%H:%M:%S'),
                'path': str(img_file)
            })
    
    # Check checkpoints
    checkpoints_dir = results_dir / "checkpoints"
    if checkpoints_dir.exists():
        checkpoint_files = list(checkpoints_dir.glob("*.json"))
        summary['checkpoints'] = len(checkpoint_files)
        for checkpoint_file in checkpoint_files:
            stat = checkpoint_file.stat()
            size_mb = stat.st_size / (1024**2)
            summary['total_size_mb'] += size_mb
            
            result_files.append({
                'name': checkpoint_file.name,
                'type': 'Checkpoint',
                'size_mb': size_mb,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%H:%M:%S'),
                'path': str(checkpoint_file)
            })
    
    # Sort by modification time (newest first)
    result_files.sort(key=lambda x: x['modified'], reverse=True)
    
    return {"status": "Found Results" if result_files else "No Results", "files": result_files, "summary": summary}

def check_kubernetes_status() -> Dict:
    """Return Kubernetes job/pod status if kubectl is available."""
    try:
        result = subprocess.run([
            "kubectl", "get", "pods", "-n", "fp-tree", "-o", "json"
        ], capture_output=True, text=True, timeout=8)
        if result.returncode != 0:
            return {"status": "Unavailable", "error": result.stderr.strip()[:120]}
        pods_json = json.loads(result.stdout)
        pods = []
        for item in pods_json.get('items', []):
            meta = item.get('metadata', {})
            status = item.get('status', {})
            cs = (status.get('containerStatuses') or [{}])[0]
            pods.append({
                'name': meta.get('name', ''),
                'status': status.get('phase', ''),
                'ready': cs.get('ready', False),
                'restart_count': cs.get('restartCount', 0)
            })
        return {"status": "Running" if pods else "No Pods", "pods": pods}
    except FileNotFoundError:
        return {"status": "kubectl not found"}
    except subprocess.TimeoutExpired:
        return {"status": "Timeout"}
    except Exception as e:
        return {"status": "Error", "error": str(e)[:120]}

def _build_layout(sys_stats: Dict, synthetic_status: Dict, k8s_status: Dict, results_status: Dict) -> Layout:
    """Build a fixed Rich layout; only cell text updates each refresh."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=3),
    )

    # Header
    header = Text(justify="center")
    header.append(" FP-TREE EXPERIMENT LIVE MONITOR ", style="bold white on blue")
    header.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    layout["header"].update(header)

    # Body split
    layout["body"].split_row(
        Layout(name="system", ratio=1),
        Layout(name="synthetic", ratio=1),
        Layout(name="k8s_results", ratio=1),
    )

    # System panel (stable rows)
    sys_table = Table(show_header=False, expand=True)
    sys_table.add_row(f"CPU: {sys_stats['cpu_percent']:5.1f}%", f"Mem: {sys_stats['memory_percent']:5.1f}% ({sys_stats['memory_available_gb']:4.1f} GB free)")
    sys_table.add_row(f"Disk: {sys_stats['disk_percent']:5.1f}%", f"FP CPU: {sys_stats['total_fp_cpu']:5.1f}% | FP Mem: {sys_stats['total_fp_memory']:5.1f}%")
    if sys_stats['fp_tree_processes']:
        procs = Table(show_header=True, header_style="bold magenta")
        procs.add_column("PID", justify="right")
        procs.add_column("CPU%", justify="right")
        procs.add_column("MEM%", justify="right")
        procs.add_column("NAME", justify="left")
        for p in sys_stats['fp_tree_processes']:
            procs.add_row(str(p['pid']), f"{p['cpu_percent']:4.1f}", f"{p['memory_percent']:4.1f}", p['name'])
        sys_panel = Panel(Group(sys_table, procs), title="System", border_style="cyan")
    else:
        sys_panel = Panel(sys_table, title="System", border_style="cyan")
    layout["system"].update(sys_panel)

    # Synthetic panel (stable table)
    syn_table = Table(show_header=True, header_style="bold green", expand=True)
    syn_table.add_column("Algorithm", justify="left")
    syn_table.add_column("Progress", justify="right")
    syn_table.add_column("Speed (tx/min)", justify="right")
    syn_table.add_column("ETA", justify="right")
    if synthetic_status.get('algorithms'):
        # Sort by algorithm name for stable order
        for algo in sorted(synthetic_status['algorithms'], key=lambda a: a.get('display_name', '')):
            syn_table.add_row(
                algo.get('display_name', algo.get('name','')),
                f"{algo.get('progress',0):6.2f}% ({algo.get('current',0)}/{algo.get('total',0)})",
                f"{algo.get('speed',0):6.1f}",
                algo.get('eta','-')
            )
    else:
        syn_table.add_row("No checkpoints", "-", "-", "-")
    syn_status_icon = "🟢" if synthetic_status.get('status') == "Running" else ("✅" if synthetic_status.get('status') == "Complete" else "⚪")
    layout["synthetic"].update(Panel(Group(Text(f"Status: {syn_status_icon} {synthetic_status.get('status','N/A')}"), syn_table), title="Synthetic", border_style="green"))

    # Kubernetes + Results panel
    k8s_table = Table(show_header=True, header_style="bold yellow", expand=True)
    k8s_table.add_column("Pod")
    k8s_table.add_column("Status")
    k8s_table.add_column("Restarts", justify="right")
    if 'pods' in k8s_status:
        for pod in k8s_status['pods']:
            kicon = "🟢" if pod.get('ready') else "🔴"
            k8s_table.add_row(f"{kicon} {pod.get('name','')}", pod.get('status',''), str(pod.get('restart_count',0)))
    else:
        k8s_table.add_row(k8s_status.get('status','Unknown'), k8s_status.get('error',''), '-')

    res_table = Table(show_header=True, header_style="bold blue", expand=True)
    res_table.add_column("File")
    res_table.add_column("Type")
    res_table.add_column("Size (MB)", justify="right")
    res_table.add_column("Modified")
    for f in results_status.get('files', [])[:6]:
        res_table.add_row(f['name'], f['type'], f"{f['size_mb']:.2f}", f['modified'])
    layout["k8s_results"].update(Panel(Group(k8s_table, res_table), title="K8s & Results", border_style="yellow"))

    # Footer
    layout["footer"].update(Text("Ctrl+M to stop • Ctrl+C is safe for copying", justify="center"))
    return layout

def check_synthetic_progress() -> Dict:
    """Check progress of synthetic dataset experiment from checkpoints."""
    checkpoint_dir = Path("results/checkpoints")
    algorithms: List[Dict] = []
    if checkpoint_dir.exists():
        for f in checkpoint_dir.glob("synthetic_*_checkpoint.json"):
            name = f.stem.replace("synthetic_", "").replace("_checkpoint", "")
            try:
                with open(f, 'r') as fh:
                    data = json.load(fh)
                total = 5000
                current = int(data.get('last_index', -1)) + 1
                progress = max(0.0, min(100.0, (current/total)*100))
                algorithms.append({
                    'name': name,
                    'display_name': name,
                    'progress': progress,
                    'current': current,
                    'total': total,
                    'speed': 0.0,
                    'eta': '-',
                })
            except Exception:
                continue
    status = "Running" if algorithms else "Not Started"
    return {"status": status, "algorithms": algorithms}

def display_dashboard():
    """Display the Rich Live dashboard; static layout, updated values."""
    global stop_monitoring
    stop_monitoring = False

    # Ctrl+M listener (best-effort)
    import threading
    def key_listener():
        global stop_monitoring
        try:
            import keyboard  # type: ignore
            while not stop_monitoring:
                if keyboard.is_pressed('ctrl+m'):
                    stop_monitoring = True
                    break
                time.sleep(0.1)
        except Exception:
            # Fallback: stop if a sentinel file exists
            sentinel = Path('.stop_monitor')
            while not stop_monitoring:
                if sentinel.exists():
                    stop_monitoring = True
                    break
                time.sleep(0.5)

    threading.Thread(target=key_listener, daemon=True).start()

    with Live(refresh_per_second=4, screen=False) as live:
        while not stop_monitoring:
            sys_stats = get_system_stats()
            syn = check_synthetic_progress()
            k8s = check_kubernetes_status()
            res = check_results_files()
            live.update(_build_layout(sys_stats, syn, k8s, res))
            try:
                time.sleep(1.0)
            except KeyboardInterrupt:
                # Ignore Ctrl+C to allow safe copying
                continue
    print("\nMonitoring stopped.")

def display_dashboard():
    """Display the live monitoring dashboard."""
    
    # Global flag for stopping monitoring
    global stop_monitoring
    stop_monitoring = False
    
    # Start keyboard listener for Ctrl+M in separate thread
    import threading
    
    def keyboard_listener():
        """Listen for Ctrl+M to stop monitoring."""
        global stop_monitoring
        try:
            import keyboard
            print("🎯 Keyboard listener started. Press Ctrl+M to stop monitoring safely.")
            while not stop_monitoring:
                if keyboard.is_pressed('ctrl+m'):
                    print("\n\n✅ Ctrl+M pressed - Stopping monitoring gracefully...")
                    stop_monitoring = True
                    break
                time.sleep(0.1)
        except ImportError:
            print("⚠️  Warning: 'keyboard' module not available. Use terminal Ctrl+C as fallback.")
        except Exception as e:
            print(f"⚠️  Keyboard listener error: {e}")
    
    # Start keyboard listener thread
    keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
    keyboard_thread.start()
    
    while not stop_monitoring:
        clear_screen()
        
        # Header
        print("=" * 80)
        print("🔥 FP-TREE EXPERIMENT LIVE MONITOR 🔥")
        print("=" * 80)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # System Resources
        print("💻 SYSTEM RESOURCES & PROCESS STATUS")
        print("-" * 60)
        sys_stats = get_system_stats()
        
        # Overall system stats
        cpu_bar = "█" * int(sys_stats['cpu_percent'] / 5) + "░" * (20 - int(sys_stats['cpu_percent'] / 5))
        mem_bar = "█" * int(sys_stats['memory_percent'] / 5) + "░" * (20 - int(sys_stats['memory_percent'] / 5))
        
        print(f"� Total CPU:    [{cpu_bar}] {sys_stats['cpu_percent']:5.1f}%")
        print(f"� Total Memory: [{mem_bar}] {sys_stats['memory_percent']:5.1f}% ({sys_stats['memory_available_gb']:4.1f} GB free)")
        print(f"� Disk Space: {sys_stats['disk_percent']:5.1f}% used ({sys_stats['disk_free_gb']:6.1f} GB free)")
        
        # FP-Tree specific processes
        if sys_stats['fp_tree_processes']:
            print(f"\n🚀 FP-Tree Processes: {len(sys_stats['fp_tree_processes'])} active")
            print(f"   📊 FP-Tree CPU Usage: {sys_stats['total_fp_cpu']:.1f}%")
            print(f"   💾 FP-Tree Memory Usage: {sys_stats['total_fp_memory']:.1f}%")
            print("   Active Processes:")
            for proc in sys_stats['fp_tree_processes'][:5]:  # Show top 5
                print(f"     🔄 PID {proc['pid']:>6} | CPU {proc['cpu_percent']:5.1f}% | Mem {proc['memory_percent']:5.1f}% | {proc['name']}")
        else:
            print("\n⚠️  No active FP-Tree processes detected")
        print()
        
        # Synthetic Dataset Experiment
        print("🧪 SYNTHETIC DATASET EXPERIMENT (LOCAL)")
        print("-" * 60)
        synthetic_status = check_synthetic_progress()
        
        # Show overall status with process info
        status_icon = "🟢" if synthetic_status['status'] == "Running" else ("✅" if synthetic_status['status'] == "Complete" else "⚪")
        print(f"Status: {status_icon} {synthetic_status['status']}")
        
        if synthetic_status.get('active_processes'):
            print(f"Active Processes: {len(synthetic_status['active_processes'])} running")
            for proc in synthetic_status['active_processes']:
                print(f"  🔄 PID {proc['pid']} ({proc['name']})")
        
        if synthetic_status['algorithms']:
            print(f"\nAlgorithm Progress:")
            for algo in synthetic_status['algorithms']:
                # Enhanced progress bar with colors
                progress_filled = int(algo['progress'] / 5)
                progress_bar = "█" * progress_filled + "░" * (20 - progress_filled)
                
                # Status icons
                if algo['status'] == 'Complete':
                    status_icon = "✅"
                elif algo['status'] == 'Running':
                    status_icon = "🔄"
                elif 'Error' in algo['status']:
                    status_icon = "❌"
                else:
                    status_icon = "⏸️"
                
                # Format display
                print(f"  {status_icon} {algo['display_name']:<25}")
                print(f"     [{progress_bar}] {algo['progress']:6.2f}% ({algo['current']:>4}/{algo['total']})")
                print(f"     Speed: {algo['speed']:>6.1f} tx/min | ETA: {algo['eta']:<8} | Updated: {algo['last_update']}")
                print()
        else:
            print("  📝 No checkpoints found - experiment may not have started yet")
        print()
        
        # Kubernetes Real Dataset Experiment
        print("☸️  REAL DATASET EXPERIMENT (KUBERNETES)")
        print("-" * 40)
        k8s_status = check_kubernetes_status()
        print(f"Status: {k8s_status['status']}")
        
        if 'pods' in k8s_status:
            for pod in k8s_status['pods']:
                status_icon = "🟢" if pod['ready'] else "🔴"
                print(f"  {status_icon} {pod['name']:<30} {pod['status']:<10} (Restarts: {pod['restart_count']})")
        elif 'error' in k8s_status:
            print(f"  ❌ {k8s_status['error']}")
        print()
        
        # Results Files
        print("📊 GENERATED RESULTS & OUTPUT")
        print("-" * 60)
        results_status = check_results_files()
        summary = results_status.get('summary', {})
        
        # Show summary statistics
        print(f"Status: 📈 {results_status['status']}")
        if summary:
            print(f"Summary: {summary['csv_files']} CSV files | {summary['images']} Images | {summary['checkpoints']} Checkpoints")
            print(f"Total Size: {summary['total_size_mb']:.2f} MB")
            if summary.get('latest_file'):
                print(f"Latest: {summary['latest_file']['name']} (at {summary['latest_file']['time']})")
        
        print()
        if results_status['files']:
            print("Recent Files:")
            for file_info in results_status['files'][:8]:  # Show most recent 8 files
                # File type icons
                if file_info['type'] == 'CSV Table':
                    icon = "📊"
                elif file_info['type'] == 'Figure/Plot':
                    icon = "📈"
                elif file_info['type'] == 'Checkpoint':
                    icon = "💾"
                else:
                    icon = "📄"
                
                print(f"  {icon} {file_info['name']:<35} {file_info['size_mb']:>6.2f} MB  {file_info['modified']}")
        else:
            print("  📝 No result files generated yet - experiments may still be starting")
        print()
        
        # Instructions
        print("⌨️  CONTROLS")
        print("-" * 60)
        print("  💡 Press Ctrl+M to stop monitoring (Ctrl+C is safe for copying errors)")
        print("  🔄 This dashboard updates every 5 seconds automatically")
        print("  📋 Feel free to use Ctrl+C to copy any error messages!")
        print("=" * 80)
        
        # Wait for next update
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            # Ignore Ctrl+C - user might be copying errors
            print("\n💡 Ctrl+C detected - continuing monitoring. Use Ctrl+M to stop.")
            time.sleep(1)  # Brief pause to show the message
    
    print("\n\n👋 Monitoring stopped gracefully. Goodbye!")

if __name__ == "__main__":
    display_dashboard()