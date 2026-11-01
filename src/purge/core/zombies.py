"""Cross-platform zombie developer process and port hog hunter."""

import os
from typing import Any, List, Optional, Set

from purge.core.models import ZombieProcess

psutil: Any = None
try:
    import psutil  # type: ignore
except ImportError:
    pass

# Common local development server ports
DEV_PORTS: Set[int] = {
    3000,
    3001,
    3002,
    3003,
    4200,
    5000,
    5173,
    5174,
    5175,
    8000,
    8080,
    8081,
    8888,
    9000,
    9229,  # Node inspector
}

DEV_PROCESS_KEYWORDS: Set[str] = {
    "next-server",
    "vite",
    "webpack",
    "esbuild",
    "nodemon",
    "uvicorn",
    "gunicorn",
    "flask",
    "streamlit",
    "cargo-watch",
    "manage.py",
}


def find_zombies(target_port: Optional[int] = None) -> List[ZombieProcess]:
    """Scan the system for running developer server processes and port hogs."""
    if psutil is None:
        return []

    current_pid = os.getpid()
    zombies: List[ZombieProcess] = []
    seen_pids: Set[int] = set()

    # 1. Check network connections for listening dev ports
    try:
        connections = psutil.net_connections(kind="inet")
        for conn in connections:
            if conn.status == psutil.CONN_LISTEN and conn.laddr:
                port = conn.laddr.port
                if (target_port and port == target_port) or (not target_port and port in DEV_PORTS):
                    if conn.pid and conn.pid != current_pid and conn.pid not in seen_pids:
                        try:
                            proc = psutil.Process(conn.pid)
                            zombie = _extract_zombie_info(proc, port=port)
                            if zombie:
                                zombies.append(zombie)
                                seen_pids.add(conn.pid)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
    except Exception as e:
        # Fallback for systems (e.g. macOS without root) that raise AccessDenied on net_connections
        # We catch Exception here because when mocked in tests, psutil.AccessDenied might not be a class.
        # But specifically checking for the name allows both real and mock psutil to work.
        if type(e).__name__ not in ("AccessDenied", "OSError", "PermissionError"):
            raise e
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.pid == current_pid or proc.pid in seen_pids:
                    continue
                proc_connections = proc.connections(kind="inet")
                for conn in proc_connections:
                    if conn.status == psutil.CONN_LISTEN and conn.laddr:
                        port = conn.laddr.port
                        if (target_port and port == target_port) or (not target_port and port in DEV_PORTS):
                            zombie = _extract_zombie_info(proc, port=port)
                            if zombie:
                                zombies.append(zombie)
                                seen_pids.add(proc.pid)
                            break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    # 2. Check running processes matching dev keywords if no specific port requested
    if not target_port:
        for proc in psutil.process_iter(["pid", "name", "cmdline", "cwd", "create_time"]):
            try:
                pid = proc.info["pid"]
                if pid == current_pid or pid in seen_pids:
                    continue

                name = (proc.info.get("name") or "").lower()
                cmdline_list = proc.info.get("cmdline") or []
                cmdline = " ".join(cmdline_list).lower()

                # Match if name or cmdline matches dev tools
                is_dev = any(k in name for k in DEV_PROCESS_KEYWORDS) or any(
                    k in cmdline for k in DEV_PROCESS_KEYWORDS
                ) or any(
                    f"run {k}" in cmdline or f"bin/{k}" in cmdline for k in ["dev", "start", "serve"]
                )

                if is_dev:
                    zombie = _extract_zombie_info(proc, port=None)
                    if zombie:
                        zombies.append(zombie)
                        seen_pids.add(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    # Sort zombies by memory usage descending
    zombies.sort(key=lambda z: z.memory_mb, reverse=True)
    return zombies


def _extract_zombie_info(proc: Any, port: Optional[int] = None) -> Optional[ZombieProcess]:
    """Extract clean ZombieProcess dataclass from psutil Process."""
    try:
        pid = proc.pid
        name = proc.name()
        cmdline = " ".join(proc.cmdline() or [name])
        cwd = None
        try:
            cwd = proc.cwd()
        except (psutil.AccessDenied, OSError):
            pass

        mem_mb = 0.0
        try:
            mem_info = proc.memory_info()
            mem_mb = mem_info.rss / (1024.0 * 1024.0)
        except (psutil.AccessDenied, OSError):
            pass

        cpu = 0.0
        try:
            cpu = proc.cpu_percent(interval=0.0)
        except (psutil.AccessDenied, OSError):
            pass

        return ZombieProcess(
            pid=pid,
            name=name,
            cmdline=cmdline[:120],
            port=port,
            memory_mb=mem_mb,
            cpu_percent=cpu,
            cwd=cwd,
            create_time=proc.create_time(),
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def kill_zombie(pid: int, force: bool = False) -> bool:
    """Terminate or kill a zombie process safely."""
    if psutil is None:
        return False

    try:
        proc = psutil.Process(pid)
        if force:
            proc.kill()
        else:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except psutil.TimeoutExpired:
                proc.kill()
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
