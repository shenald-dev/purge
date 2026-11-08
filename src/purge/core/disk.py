"""Disk health, drive partition analysis, and bloat percentage telemetry."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from purge.core.models import format_bytes

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore


@dataclass
class PartitionInfo:
    """Disk partition usage and developer bloat footprint."""

    mountpoint: str
    device: str
    fstype: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent_used: float
    bloat_bytes: int = 0

    @property
    def human_total(self) -> str:
        return format_bytes(self.total_bytes)

    @property
    def human_used(self) -> str:
        return format_bytes(self.used_bytes)

    @property
    def human_free(self) -> str:
        return format_bytes(self.free_bytes)

    @property
    def human_bloat(self) -> str:
        return format_bytes(self.bloat_bytes)

    @property
    def bloat_percent_of_total(self) -> float:
        if self.total_bytes <= 0:
            return 0.0
        return round((self.bloat_bytes / self.total_bytes) * 100.0, 2)

    @property
    def bloat_percent_of_used(self) -> float:
        if self.used_bytes <= 0:
            return 0.0
        return round((self.bloat_bytes / self.used_bytes) * 100.0, 2)

    @property
    def potential_free_gain_percent(self) -> float:
        if self.free_bytes <= 0:
            return 0.0
        return round((self.bloat_bytes / self.free_bytes) * 100.0, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mountpoint": self.mountpoint,
            "device": self.device,
            "fstype": self.fstype,
            "total_bytes": self.total_bytes,
            "human_total": self.human_total,
            "used_bytes": self.used_bytes,
            "human_used": self.human_used,
            "free_bytes": self.free_bytes,
            "human_free": self.human_free,
            "percent_used": round(self.percent_used, 1),
            "bloat_bytes": self.bloat_bytes,
            "human_bloat": self.human_bloat,
            "bloat_percent_of_total": self.bloat_percent_of_total,
            "bloat_percent_of_used": self.bloat_percent_of_used,
            "potential_free_gain_percent": self.potential_free_gain_percent,
        }


def list_system_partitions() -> list[PartitionInfo]:
    """Backward-compatible wrapper to list all system partitions."""
    if psutil is None:
        return []
    partitions = []
    try:
        for part in psutil.disk_partitions(all=False):
            p_info = get_partition_for_path(Path(part.mountpoint))
            if p_info:
                partitions.append(p_info)
    except Exception:
        pass
    return partitions


def get_partition_for_path(path: Path, bloat_bytes: int = 0) -> Optional[PartitionInfo]:
    """Retrieve the partition information for a specific directory or file path."""
    if psutil is None:
        return None

    try:
        resolved_path = str(path.resolve())
    except Exception:
        try:
            resolved_path = str(path.absolute())
        except Exception:
            resolved_path = str(path)

    # Fallback disk usage for the path with ancestor traversal if path does not exist
    try:
        curr = Path(resolved_path)
        if curr.is_file():
            curr = curr.parent
        usage = psutil.disk_usage(str(curr))
    except Exception:
        try:
            curr = Path(resolved_path)
            while not curr.is_dir() and curr != curr.parent:
                curr = curr.parent
            usage = psutil.disk_usage(str(curr))
        except Exception:
            return None

    mount = resolved_path
    device = resolved_path
    fstype = ""

    try:
        partitions = psutil.disk_partitions(all=False)
        best_match = None
        best_len = -1
        import ntpath
        import posixpath

        p_drive, p_tail = os.path.splitdrive(resolved_path)

        for part in partitions:
            m = part.mountpoint
            m_drive, m_tail = os.path.splitdrive(m)

            if m_drive or (p_drive and "\\" in m):
                # Windows drive partition matching
                if p_drive.lower() == m_drive.lower():
                    path_mod = ntpath
                    p_norm_str = (
                        resolved_path
                        if resolved_path.endswith(("\\", "/"))
                        else resolved_path + "\\"
                    )
                    m_norm_str = m if m.endswith(("\\", "/")) else m + "\\"
                    path_norm = path_mod.normcase(path_mod.normpath(p_norm_str))
                    mount_norm = path_mod.normcase(path_mod.normpath(m_norm_str))
                    try:
                        cp = path_mod.commonpath([path_norm, mount_norm])
                        if cp == mount_norm or cp.rstrip("\\") == mount_norm.rstrip("\\"):
                            if len(m) > best_len:
                                best_len = len(m)
                                best_match = part
                    except ValueError:
                        pass
            else:
                # POSIX mountpoint matching (handles cross-platform paths on Windows)
                posix_target = p_tail.replace("\\", "/")
                if not posix_target.startswith("/"):
                    posix_target = "/" + posix_target
                path_mod = posixpath
                path_norm = path_mod.normcase(path_mod.normpath(posix_target))
                mount_norm = path_mod.normcase(path_mod.normpath(m))
                try:
                    if path_mod.commonpath([path_norm, mount_norm]) == mount_norm:
                        if len(m) > best_len:
                            best_len = len(m)
                            best_match = part
                except ValueError:
                    pass

        if best_match:
            mount = best_match.mountpoint
            device = best_match.device
            fstype = best_match.fstype
    except Exception:
        pass

    return PartitionInfo(
        mountpoint=mount,
        device=device,
        fstype=fstype,
        total_bytes=usage.total,
        used_bytes=usage.used,
        free_bytes=usage.free,
        percent_used=usage.percent,
        bloat_bytes=bloat_bytes,
    )
