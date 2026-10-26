"""High-performance parallel disk scanner for developer artifacts."""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from purge.core.models import Artifact, PurgeReport
from purge.core.rules import (
    PROTECTED_DIR_NAMES,
    identify_artifact_category,
    is_protected_path,
)


def get_path_stats(path: Path) -> Tuple[int, int, Optional[datetime], float]:
    """Calculate (total_bytes, file_count, last_modified, days_stale) for a file or directory."""
    total_bytes = 0
    file_count = 0
    latest_mtime = 0.0

    now_ts = time.time()

    if path.is_file():
        try:
            stat = path.stat()
            latest_mtime = stat.st_mtime
            total_bytes = stat.st_size
            file_count = 1
        except (OSError, PermissionError):
            pass
    else:
        # Directory traversal using os.scandir for raw speed
        stack = [str(path)]
        while stack:
            current_dir = stack.pop()
            try:
                with os.scandir(current_dir) as it:
                    for entry in it:
                        try:
                            # Avoid following symlinks to prevent infinite cycles or external loops
                            if entry.is_symlink():
                                continue
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                stat = entry.stat(follow_symlinks=False)
                                total_bytes += stat.st_size
                                file_count += 1
                                if stat.st_mtime > latest_mtime:
                                    latest_mtime = stat.st_mtime
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                continue

    last_mod = datetime.fromtimestamp(latest_mtime, tz=timezone.utc) if latest_mtime > 0 else None
    days_stale = max(0.0, (now_ts - latest_mtime) / 86400.0) if latest_mtime > 0 else 0.0

    return total_bytes, file_count, last_mod, days_stale


class DiskScanner:
    """Recursively scans projects for reclaimable developer bloat."""

    def __init__(
        self,
        max_workers: int = 8,
        categories: Optional[List[str]] = None,
        min_stale_days: float = 0.0,
        progress_callback: Optional[Callable[[str], None]] = None,
    ):
        self.max_workers = max_workers
        self.categories = categories
        self.min_stale_days = min_stale_days
        self.progress_callback = progress_callback

    def scan(self, root_path: Path, max_depth: int = 10) -> PurgeReport:
        """Scan root_path recursively and return PurgeReport."""
        start_time = time.time()
        root = root_path.resolve()

        if is_protected_path(root):
            raise ValueError(f"Target path '{root}' is a protected system directory.")

        discovered_candidates: List[Tuple[Path, str]] = []
        scanned_dirs_count = 0

        # Phase 1: Rapid discovery walk (prunes traversal at candidate artifact folders)
        stack: List[Tuple[Path, int]] = [(root, 0)]

        while stack:
            current_dir, depth = stack.pop()
            scanned_dirs_count += 1

            if self.progress_callback and scanned_dirs_count % 100 == 0:
                self.progress_callback(str(current_dir))

            if depth > max_depth:
                continue

            try:
                with os.scandir(str(current_dir)) as it:
                    for entry in it:
                        try:
                            if entry.is_symlink():
                                continue

                            entry_name = entry.name
                            if entry_name in PROTECTED_DIR_NAMES:
                                continue

                            entry_path = Path(entry.path)

                            # Check if this matches a bloat artifact
                            category = identify_artifact_category(entry_name, current_dir)
                            if category:
                                if not self.categories or any(
                                    c.lower() in category.lower() for c in self.categories
                                ):
                                    discovered_candidates.append((entry_path, category))
                                # CRITICAL: Do NOT recurse into artifact folders like node_modules!
                                continue

                            if entry.is_dir(follow_symlinks=False):
                                stack.append((entry_path, depth + 1))
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                continue

        # Phase 2: Parallel stat computation for all discovered candidates
        artifacts: List[Artifact] = []
        total_bytes = 0
        total_files = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_cand = {
                executor.submit(get_path_stats, cand_path): (cand_path, cat)
                for cand_path, cat in discovered_candidates
            }

            for future in as_completed(future_to_cand):
                cand_path, category = future_to_cand[future]
                try:
                    bytes_size, f_count, last_mod, days_stale = future.result()

                    # Filter by minimum stale days if requested
                    if self.min_stale_days > 0 and days_stale < self.min_stale_days:
                        continue

                    art = Artifact(
                        path=cand_path,
                        category=category,
                        size_bytes=bytes_size,
                        file_count=f_count,
                        last_modified=last_mod,
                        days_stale=days_stale,
                    )
                    artifacts.append(art)
                    total_bytes += bytes_size
                    total_files += f_count
                except Exception:
                    continue

        # Sort artifacts descending by size (largest targets first)
        artifacts.sort(key=lambda x: x.size_bytes, reverse=True)

        duration = time.time() - start_time
        return PurgeReport(
            scan_path=root,
            artifacts=artifacts,
            total_bytes=total_bytes,
            total_files=total_files,
            scanned_dirs_count=scanned_dirs_count,
            duration_seconds=duration,
        )
