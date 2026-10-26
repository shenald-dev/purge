"""Execution engine for safe deletion of developer artifacts and slaying zombies."""

import os
import shutil
import stat
import time
from typing import List, Optional, Tuple

from purge.core.models import Artifact, CleanResult, ZombieProcess
from purge.core.rules import is_protected_path
from purge.core.zombies import kill_zombie


def _remove_readonly(func, path, _exc_info):
    """Clear the readonly bit and re-attempt removal (common on Windows git / read-only files)."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


class PurgeCleaner:
    """Manages the safe removal of disk artifacts and termination of zombie processes."""

    def __init__(self, dry_run: bool = False, to_trash: bool = False):
        self.dry_run = dry_run
        self.to_trash = to_trash

    def delete_artifact(self, artifact: Artifact) -> Tuple[bool, Optional[str]]:
        """Safely delete a single artifact."""
        path = artifact.path.resolve()

        if is_protected_path(path):
            return False, f"Protected path '{path}' cannot be deleted."

        if not path.exists():
            return False, f"Path '{path}' no longer exists."

        if self.dry_run:
            return True, None

        try:
            if self.to_trash:
                try:
                    import send2trash

                    send2trash.send2trash(str(path))
                    return True, None
                except ImportError:
                    pass  # Fallback to standard permanent deletion if send2trash is not installed

            if path.is_file() or path.is_symlink():
                try:
                    path.unlink()
                except PermissionError:
                    os.chmod(str(path), stat.S_IWRITE)
                    path.unlink()
            elif path.is_dir():
                shutil.rmtree(str(path), onerror=_remove_readonly)

            return True, None
        except Exception as e:
            return False, f"Failed to delete '{path}': {e}"

    def purge(
        self,
        artifacts: List[Artifact],
        zombies: Optional[List[ZombieProcess]] = None,
    ) -> CleanResult:
        """Purge selected artifacts and optionally slay zombie processes."""
        start_time = time.time()
        reclaimed_bytes = 0
        deleted_count = 0
        slain_zombies = 0
        errors: List[str] = []

        # 1. Clean Disk Artifacts
        for art in artifacts:
            success, err = self.delete_artifact(art)
            if success:
                reclaimed_bytes += art.size_bytes
                deleted_count += 1
            elif err:
                errors.append(err)

        # 2. Slay Zombie Processes
        if zombies:
            for z in zombies:
                if self.dry_run:
                    slain_zombies += 1
                else:
                    if kill_zombie(z.pid, force=True):
                        slain_zombies += 1
                    else:
                        errors.append(f"Failed to terminate zombie PID {z.pid} ({z.name})")

        duration = time.time() - start_time
        return CleanResult(
            reclaimed_bytes=reclaimed_bytes,
            deleted_artifacts_count=deleted_count,
            slain_zombies_count=slain_zombies,
            duration_seconds=duration,
            errors=errors,
        )
