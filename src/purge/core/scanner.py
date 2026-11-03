"""High-performance parallel disk scanner for developer bloat and global caches."""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from purge.core.git_helper import inspect_git_project
from purge.core.models import Artifact, PurgeReport
from purge.core.rules import (
    PROTECTED_DIR_NAMES,
    get_global_cache_targets,
    identify_artifact_category,
    is_protected_path,
)
from purge.core.scoring import calculate_purge_score


def get_path_stats(path: Path) -> Tuple[int, int, Optional[datetime], float]:
    """Calculate (total_bytes, file_count, last_modified, days_stale) for a file or directory."""
    total_bytes = 0
    file_count = 0
    latest_mtime = 0.0

    now_ts = time.time()

    if path.is_symlink():
        try:
            stat = path.lstat()
            latest_mtime = stat.st_mtime
            total_bytes = stat.st_size
            file_count = 1
        except (OSError, PermissionError):
            pass
    elif path.is_file():
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
    """Recursively scans projects for reclaimable developer bloat and global caches."""

    def __init__(
        self,
        max_workers: int = 8,
        categories: Optional[List[str]] = None,
        min_stale_days: float = 0.0,
        min_size_bytes: int = 0,
        min_score: float = 0.0,
        sort_by: str = "size",
        top: Optional[int] = None,
        git_aware: bool = True,
        custom_rules: Optional[Dict[str, List[str]]] = None,
        ignore_paths: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ):
        self.max_workers = max_workers
        self.categories = categories
        self.min_stale_days = min_stale_days
        self.min_size_bytes = min_size_bytes
        self.min_score = min_score
        self.sort_by = sort_by.lower()
        self.top = top
        self.git_aware = git_aware
        self.custom_rules = custom_rules
        self.ignore_paths = [p.replace("\\", "/").rstrip("/") for p in (ignore_paths or [])]
        self.progress_callback = progress_callback

    def _is_ignored(self, p: Path) -> bool:
        str_p = str(p).replace("\\", "/").rstrip("/")
        for ign in self.ignore_paths:
            if ign in str_p:
                return True
        return False

    def scan_global_caches(self) -> List[Artifact]:
        """Scan system for global developer package manager caches (npm, pip, uv, cargo, etc.)."""
        global_targets = get_global_cache_targets()
        global_artifacts = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_cand = {
                executor.submit(get_path_stats, path): (path, cat, desc)
                for path, cat, desc in global_targets
                if not self._is_ignored(path)
            }

            for future in as_completed(future_to_cand):
                path, cat, desc = future_to_cand[future]
                try:
                    bytes_size, f_count, last_mod, days_stale = future.result()
                    if bytes_size > 0:
                        score_info = calculate_purge_score(
                            size_bytes=bytes_size,
                            days_stale=days_stale,
                            category=cat,
                            artifact_name=path.name,
                            is_global_cache=True,
                        )
                        global_artifacts.append(
                            Artifact(
                                path=path,
                                category=cat,
                                size_bytes=bytes_size,
                                file_count=f_count,
                                last_modified=last_mod,
                                days_stale=days_stale,
                                is_global_cache=True,
                                description=desc,
                                purge_score=score_info.total_score,
                                safety_level=score_info.safety_level.value,
                                score_recommendation=score_info.recommendation,
                            )
                        )
                except Exception:
                    continue

        global_artifacts.sort(key=lambda x: x.size_bytes, reverse=True)
        return global_artifacts

    def scan(
        self,
        root_path: Path,
        max_depth: int = 10,
        include_global_caches: bool = False,
    ) -> PurgeReport:
        """Scan root_path recursively and return PurgeReport."""
        start_time = time.time()
        root = root_path.resolve()

        if is_protected_path(root, allow_home=True):
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
                            entry_name = entry.name
                            if entry_name in PROTECTED_DIR_NAMES:
                                continue

                            entry_path = Path(entry.path)
                            if self._is_ignored(entry_path):
                                continue

                            # Check if this matches a bloat artifact
                            category = identify_artifact_category(
                                entry_name, current_dir, custom_rules=self.custom_rules
                            )
                            if category:
                                if not self.categories or any(
                                    c.lower() in category.lower() for c in self.categories
                                ):
                                    discovered_candidates.append((entry_path, category))
                                # CRITICAL: Do NOT recurse into artifact folders like node_modules!
                                continue

                            if entry.is_symlink():
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
        uncommitted_repos = 0
        seen_repo_roots = set()

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

                    # Filter by minimum size bytes
                    if self.min_size_bytes > 0 and bytes_size < self.min_size_bytes:
                        continue

                    is_git = False
                    has_uncommitted = False
                    last_commit_time = None
                    days_since_commit = 0.0

                    if self.git_aware:
                        git_info = inspect_git_project(cand_path.parent)
                        if git_info.is_git:
                            is_git = True
                            has_uncommitted = git_info.has_uncommitted
                            last_commit_time = git_info.last_commit_time
                            days_since_commit = git_info.days_since_last_commit
                            if has_uncommitted and git_info.repo_root:
                                r_str = str(git_info.repo_root)
                                if r_str not in seen_repo_roots:
                                    seen_repo_roots.add(r_str)
                                    uncommitted_repos += 1

                    score_info = calculate_purge_score(
                        size_bytes=bytes_size,
                        days_stale=days_stale,
                        category=category,
                        artifact_name=cand_path.name,
                        is_git_repo=is_git,
                        has_uncommitted=has_uncommitted,
                        days_since_commit=days_since_commit,
                    )

                    if self.min_score > 0 and score_info.total_score < self.min_score:
                        continue

                    art = Artifact(
                        path=cand_path,
                        category=category,
                        size_bytes=bytes_size,
                        file_count=f_count,
                        last_modified=last_mod,
                        days_stale=days_stale,
                        is_git_repo=is_git,
                        has_uncommitted=has_uncommitted,
                        last_commit_time=last_commit_time,
                        days_since_commit=days_since_commit,
                        purge_score=score_info.total_score,
                        safety_level=score_info.safety_level.value,
                        score_recommendation=score_info.recommendation,
                    )
                    artifacts.append(art)
                    total_bytes += bytes_size
                    total_files += f_count
                except Exception:
                    continue

        # Sort artifacts according to sort_by strategy
        if self.sort_by == "score":
            artifacts.sort(key=lambda x: (x.purge_score, x.size_bytes), reverse=True)
        elif self.sort_by == "stale":
            artifacts.sort(key=lambda x: x.days_stale, reverse=True)
        elif self.sort_by == "name":
            artifacts.sort(key=lambda x: str(x.path).lower())
        else:  # default: "size"
            artifacts.sort(key=lambda x: x.size_bytes, reverse=True)

        if self.top and self.top > 0:
            artifacts = artifacts[: self.top]

        high_priority_count = sum(1 for a in artifacts if a.purge_score >= 65.0)

        global_caches = []
        if include_global_caches:
            global_caches = self.scan_global_caches()
            total_bytes += sum(gc.size_bytes for gc in global_caches)
            total_files += sum(gc.file_count for gc in global_caches)

        duration = time.time() - start_time
        return PurgeReport(
            scan_path=root,
            artifacts=artifacts,
            global_caches=global_caches,
            total_bytes=total_bytes,
            total_files=total_files,
            scanned_dirs_count=scanned_dirs_count,
            duration_seconds=duration,
            uncommitted_repos_count=uncommitted_repos,
            high_priority_count=high_priority_count,
        )
