"""Data models for purge artifacts, zombie processes, and scan reports."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string (KB, MB, GB, TB)."""
    if num_bytes < 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} PB"


@dataclass
class Artifact:
    """Represents a reclaimable developer artifact on disk."""

    path: Path
    category: str  # e.g., 'Node.js', 'Python', 'Rust', 'Build Cache'
    size_bytes: int = 0
    file_count: int = 0
    last_modified: Optional[datetime] = None
    days_stale: float = 0.0

    @property
    def human_size(self) -> str:
        return format_bytes(self.size_bytes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": str(self.path),
            "category": self.category,
            "size_bytes": self.size_bytes,
            "human_size": self.human_size,
            "file_count": self.file_count,
            "days_stale": round(self.days_stale, 1),
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
        }


@dataclass
class ZombieProcess:
    """Represents a background developer process hogging ports or memory."""

    pid: int
    name: str
    cmdline: str
    port: Optional[int] = None
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    cwd: Optional[str] = None
    create_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "cmdline": self.cmdline,
            "port": self.port,
            "memory_mb": round(self.memory_mb, 1),
            "cpu_percent": round(self.cpu_percent, 1),
            "cwd": self.cwd,
        }


@dataclass
class PurgeReport:
    """Summary of a scan cycle."""

    scan_path: Path
    artifacts: List[Artifact] = field(default_factory=list)
    zombies: List[ZombieProcess] = field(default_factory=list)
    total_bytes: int = 0
    total_files: int = 0
    scanned_dirs_count: int = 0
    duration_seconds: float = 0.0

    @property
    def human_total_size(self) -> str:
        return format_bytes(self.total_bytes)

    @property
    def category_breakdown(self) -> Dict[str, int]:
        breakdown: Dict[str, int] = {}
        for a in self.artifacts:
            breakdown[a.category] = breakdown.get(a.category, 0) + a.size_bytes
        return breakdown

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_path": str(self.scan_path),
            "total_bytes": self.total_bytes,
            "human_total_size": self.human_total_size,
            "total_artifacts": len(self.artifacts),
            "total_zombies": len(self.zombies),
            "scanned_dirs_count": self.scanned_dirs_count,
            "duration_seconds": round(self.duration_seconds, 3),
            "artifacts": [a.to_dict() for a in self.artifacts],
            "zombies": [z.to_dict() for z in self.zombies],
            "category_breakdown": {
                k: {"bytes": v, "human_size": format_bytes(v)}
                for k, v in self.category_breakdown.items()
            },
        }


@dataclass
class CleanResult:
    """Outcome of a purge cleaning operation."""

    reclaimed_bytes: int = 0
    deleted_artifacts_count: int = 0
    slain_zombies_count: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)

    @property
    def human_reclaimed_size(self) -> str:
        return format_bytes(self.reclaimed_bytes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reclaimed_bytes": self.reclaimed_bytes,
            "human_reclaimed_size": self.human_reclaimed_size,
            "deleted_artifacts_count": self.deleted_artifacts_count,
            "slain_zombies_count": self.slain_zombies_count,
            "duration_seconds": round(self.duration_seconds, 3),
            "errors": self.errors,
        }
