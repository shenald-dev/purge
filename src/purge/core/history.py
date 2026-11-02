"""Telemetry and lifetime disk space reclamation statistics tracker for purge."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from purge.core.models import CleanResult, format_bytes

HISTORY_DIR = Path.home() / ".config" / "purge"
HISTORY_FILE = HISTORY_DIR / "history.json"


def _ensure_history_dir():
    try:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def get_lifetime_stats() -> Dict[str, Any]:
    """Retrieve cumulative purge statistics across all cleaning operations."""
    if not HISTORY_FILE.is_file():
        return {
            "total_reclaimed_bytes": 0,
            "human_total_reclaimed": "0 B",
            "total_purges_run": 0,
            "total_artifacts_deleted": 0,
            "total_zombies_slayed": 0,
            "recent_events": [],
        }

    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        data["human_total_reclaimed"] = format_bytes(data.get("total_reclaimed_bytes", 0))
        return data
    except Exception:
        return {
            "total_reclaimed_bytes": 0,
            "human_total_reclaimed": "0 B",
            "total_purges_run": 0,
            "total_artifacts_deleted": 0,
            "total_zombies_slayed": 0,
            "recent_events": [],
        }


def record_clean_event(result: CleanResult) -> Dict[str, Any]:
    """Record a completed purge operation to persistent history."""
    if result.reclaimed_bytes == 0 and result.slain_zombies_count == 0:
        return get_lifetime_stats()

    _ensure_history_dir()
    stats = get_lifetime_stats()

    stats["total_reclaimed_bytes"] = stats.get("total_reclaimed_bytes", 0) + result.reclaimed_bytes
    stats["total_purges_run"] = stats.get("total_purges_run", 0) + 1
    stats["total_artifacts_deleted"] = stats.get("total_artifacts_deleted", 0) + result.deleted_artifacts_count
    stats["total_zombies_slayed"] = stats.get("total_zombies_slayed", 0) + result.slain_zombies_count

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reclaimed_bytes": result.reclaimed_bytes,
        "human_reclaimed": result.human_reclaimed_size,
        "artifacts_count": result.deleted_artifacts_count,
        "zombies_count": result.slain_zombies_count,
        "duration_seconds": round(result.duration_seconds, 2),
    }

    events = stats.get("recent_events", [])
    events.insert(0, event)
    stats["recent_events"] = events[:25]  # Keep last 25 events

    try:
        # Don't persist human_total_reclaimed
        save_data = {k: v for k, v in stats.items() if k != "human_total_reclaimed"}
        HISTORY_FILE.write_text(json.dumps(save_data, indent=2), encoding="utf-8")
    except Exception:
        pass

    stats["human_total_reclaimed"] = format_bytes(stats["total_reclaimed_bytes"])
    return stats
