"""Git repository intelligence for tracking project dormancy and uncommitted changes."""

import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
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


def inspect_git_project(path: Path) -> GitProjectInfo:
    """Inspect the git status and last commit date of a project directory."""
    try:
        # Check if inside git work tree and get root
        res_root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(path),
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
        if res_root.returncode != 0 or not res_root.stdout.strip():
            return GitProjectInfo(is_git=False)

        repo_root = Path(res_root.stdout.strip())

        # Check for uncommitted changes
        res_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
        has_uncommitted = bool(res_status.stdout.strip())

        # Get current branch
        res_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
        current_branch = res_branch.stdout.strip() if res_branch.returncode == 0 else None

        # Get last commit timestamp
        res_log = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )

        last_commit_time = None
        days_since_commit = 0.0
        if res_log.returncode == 0 and res_log.stdout.strip().isdigit():
            epoch = int(res_log.stdout.strip())
            last_commit_time = datetime.fromtimestamp(epoch, tz=timezone.utc)
            days_since_commit = max(0.0, (time.time() - epoch) / 86400.0)

        return GitProjectInfo(
            is_git=True,
            repo_root=repo_root,
            has_uncommitted=has_uncommitted,
            last_commit_time=last_commit_time,
            days_since_last_commit=days_since_commit,
            current_branch=current_branch,
        )
    except (subprocess.SubprocessError, OSError):
        return GitProjectInfo(is_git=False)
