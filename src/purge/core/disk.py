"""Disk health, drive partition analysis, and bloat percentage telemetry."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def get_partition_for_path(path: Path, bloat_bytes: int = 0) -> Optional[PartitionInfo]:
    """Retrieve the partition information for a specific directory or file path."""
    if psutil is None:
        return None

    resolved_path = str(path.resolve())

    # Fallback disk usage for the path
    try:
        usage = psutil.disk_usage(resolved_path)
    except Exception:
        return None

    mount = resolved_path
    device = resolved_path
    fstype = ""

    try:
        partitions = psutil.disk_partitions(all=False)
        best_match = None
        best_len = -1
        for part in partitions:
            m = part.mountpoint
            if os.path.splitdrive(resolved_path)[0].lower() == os.path.splitdrive(m)[0].lower():
                if len(m) > best_len:
                    best_len = len(m)
                    best_match = part
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


def list_system_partitions() -> List[PartitionInfo]:
    """List all mounted physical partitions with disk usage statistics."""
    if psutil is None:
        return []

    results = []
    try:
        partitions = psutil.disk_partitions(all=False)
        for part in partitions:
            try:
                usage = psutil.disk_usage(part.mountpoint)
                results.append(
                    PartitionInfo(
                        mountpoint=part.mountpoint,
                        device=part.device,
                        fstype=part.fstype,
                        total_bytes=usage.total,
                        used_bytes=usage.used,
                        free_bytes=usage.free,
                        percent_used=usage.percent,
                    )
                )
            except (PermissionError, OSError):
                continue
    except Exception:
        pass

    return results
