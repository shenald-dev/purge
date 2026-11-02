"""Cross-platform zombie developer process, port hog hunter, and process tree slayer."""

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
    "python",
    "node",
}


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

        children_count = 0
        try:
            children_count = len(proc.children(recursive=True))
        except (psutil.AccessDenied, OSError):
            pass

        url = f"http://localhost:{port}" if port else None

        return ZombieProcess(
            pid=pid,
            name=name,
            cmdline=cmdline[:140],
            port=port,
            memory_mb=mem_mb,
            cpu_percent=cpu,
            cwd=cwd,
            create_time=proc.create_time(),
            children_count=children_count,
            url=url,
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


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
    except (psutil.AccessDenied, OSError):
        pass

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

                is_dev = any(k in name for k in DEV_PROCESS_KEYWORDS) or any(
                    f"run {k}" in cmdline or f"bin/{k}" in cmdline for k in ["dev", "start", "serve"]
                )

                if is_dev:
                    zombie = _extract_zombie_info(proc, port=None)
                    if zombie:
                        zombies.append(zombie)
                        seen_pids.add(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    zombies.sort(key=lambda z: z.memory_mb, reverse=True)
    return zombies


def get_process_on_port(port: int) -> Optional[ZombieProcess]:
    """Find the specific process listening on a given port."""
    zombies = find_zombies(target_port=port)
    return zombies[0] if zombies else None


def kill_zombie_tree(pid: int, force: bool = True) -> int:
    """Recursively terminate a process and all its spawned children to avoid orphaned zombies.

    Returns the total count of processes terminated.
    """
    if psutil is None:
        return 0

    try:
        parent = psutil.Process(pid)
        children = []
        try:
            children = parent.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        count = 0
        # Terminate all child processes first
        for child in children:
            try:
                if force:
                    child.kill()
                else:
                    child.terminate()
                count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Terminate parent process
        try:
            if force:
                parent.kill()
            else:
                parent.terminate()
                try:
                    parent.wait(timeout=2.0)
                except psutil.TimeoutExpired:
                    parent.kill()
            count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        return count
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0


def kill_zombie(pid: int, force: bool = False) -> bool:
    """Terminate or kill a zombie process safely (backward-compatible wrapper)."""
    return kill_zombie_tree(pid, force=force) > 0
