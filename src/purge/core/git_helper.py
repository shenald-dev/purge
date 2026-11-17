"""Git repository intelligence for tracking project dormancy and uncommitted changes."""

import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional


@dataclass
class GitProjectInfo:
    is_git: bool = False
    repo_root: Optional[Path] = None
    has_uncommitted: bool = False
    last_commit_time: Optional[datetime] = None
    days_since_last_commit: float = 0.0
    current_branch: Optional[str] = None


@lru_cache(maxsize=1024)
def _get_git_root(path: Path) -> Optional[Path]:
    try:
        resolved_path = path.resolve()
        if not resolved_path.is_dir():
            resolved_path = resolved_path.parent

        current = resolved_path
        while True:
            if (current / ".git").exists():
                return current
            if current == current.parent:
                return None
            current = current.parent
    except OSError:
        return None


@lru_cache(maxsize=1024)
def _get_git_info(repo_root: Path) -> GitProjectInfo:
    try:
        env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")

        # One combined call: branch name + last commit timestamp.
        # '%ct' epoch seconds, '%D' ref names; separated by a unit separator
        # so they can be split safely even when branch names contain spaces.
        res_combined = subprocess.run(
            ["git", "log", "-1", "--format=%ct\x1f%D"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
            env=env,
        )
        current_branch = None
        last_commit_time = None
        days_since = 0.0

        if res_combined.returncode == 0 and res_combined.stdout.strip():
            epoch_str, _, ref_info = res_combined.stdout.strip().partition("\x1f")
            try:
                ts = int(epoch_str)
                last_commit_time = datetime.fromtimestamp(ts, tz=timezone.utc)
                days_since = (time.time() - ts) / (24 * 3600)
            except ValueError:
                pass
            # ref_info like 'HEAD -> main, origin/main': take the first branch-ish token
            for token in ref_info.replace("->", " ").split(","):
                token = token.strip()
                if token and token not in ("HEAD", "grafted"):
                    current_branch = token
                    break

        # Check for uncommitted changes (separate call: needs index inspection)
        res_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
            env=env,
        )
        has_uncommitted = bool(res_status.stdout.strip())

        return GitProjectInfo(
            is_git=True,
            repo_root=repo_root,
            has_uncommitted=has_uncommitted,
            last_commit_time=last_commit_time,
            days_since_last_commit=max(0.0, days_since),
            current_branch=current_branch,
        )
    except (subprocess.SubprocessError, OSError):
        return GitProjectInfo(is_git=False)


def inspect_git_project(path: Path, force_refresh: bool = False) -> GitProjectInfo:
    """Inspect the git status and last commit date of a project directory."""
    if force_refresh:
        _get_git_root.cache_clear()
        _get_git_info.cache_clear()

    repo_root = _get_git_root(path)
    if not repo_root:
        return GitProjectInfo(is_git=False)

    return _get_git_info(repo_root)
