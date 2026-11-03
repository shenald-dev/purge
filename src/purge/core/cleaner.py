"""Execution engine for safe deletion of developer artifacts and slaying zombies."""

import os
import shutil
import stat
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Tuple

from purge.core.history import record_clean_event
from purge.core.models import Artifact, CleanResult, ZombieProcess
from purge.core.rules import is_protected_path
from purge.core.vault import QuarantineVault, VaultItem, VaultSession
from purge.core.zombies import kill_zombie_tree


def _remove_readonly(func, path, _exc_info):
    """Clear the readonly bit and re-attempt removal (common on Windows git / read-only files)."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


class PurgeCleaner:
    """Manages the safe removal of disk artifacts and termination of zombie processes."""

    def __init__(
        self,
        dry_run: bool = False,
        to_trash: bool = False,
        to_vault: bool = False,
        vault_root: Optional[Path] = None,
        record_history: bool = True,
        workers: int = 4,
    ):
        self.dry_run = dry_run
        self.to_trash = to_trash
        self.to_vault = to_vault
        self.record_history = record_history
        self.workers = max(1, workers)
        self.vault = QuarantineVault(vault_root=vault_root) if to_vault else None

    def delete_artifact(
        self, artifact: Artifact, vault_session_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[VaultItem]]:
        """Safely delete or quarantine a single artifact."""
        path = artifact.path

        if is_protected_path(path):
            return False, f"Protected path '{path}' cannot be deleted.", None

        if not path.exists() and not path.is_symlink():
            return False, f"Path '{path}' no longer exists.", None

        if self.dry_run:
            return True, None, None

        # Quarantine mode
        if self.to_vault and self.vault and vault_session_id:
            ok, item, err = self.vault.quarantine(path, vault_session_id, size_bytes=artifact.size_bytes)
            return ok, err, item

        try:
            if self.to_trash:
                try:
                    import send2trash

                    send2trash.send2trash(str(path))
                    return True, None, None
                except ImportError:
                    return (
                        False,
                        "The 'send2trash' package is required for trash functionality. Install it via 'pip install send2trash'.",
                        None,
                    )

            if path.is_file() or path.is_symlink():
                try:
                    path.unlink()
                except PermissionError:
                    os.chmod(str(path), stat.S_IWRITE)
                    path.unlink()
            elif path.is_dir():
                # Attempt rmtree with readonly handler and retry for Windows locking
                attempts = 2
                for attempt in range(attempts):
                    try:
                        shutil.rmtree(str(path), onerror=_remove_readonly)
                        break
                    except OSError:
                        if attempt == attempts - 1:
                            raise
                        time.sleep(0.05)

            return True, None, None
        except Exception as e:
            return False, f"Failed to delete '{path}': {e}", None

    def purge(
        self,
        artifacts: List[Artifact],
        zombies: Optional[List[ZombieProcess]] = None,
    ) -> CleanResult:
        """Purge selected artifacts and optionally slay zombie processes."""
        start_time = time.time()
        reclaimed_bytes = 0
        deleted_count = 0
        quarantined_count = 0
        slain_zombies = 0
        errors: List[str] = []

        vault_session_id = None
        vault_items: List[VaultItem] = []
        if self.to_vault and self.vault and not self.dry_run:
            vault_session_id = self.vault.create_session()

        # 1. Clean / Quarantine Disk Artifacts
        if len(artifacts) > 1 and self.workers > 1 and not self.dry_run and not self.to_trash:
            # Parallel execution for pure disk deletion
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                future_to_art = {
                    executor.submit(self.delete_artifact, art, vault_session_id): art
                    for art in artifacts
                }
                for future in as_completed(future_to_art):
                    art = future_to_art[future]
                    try:
                        success, err, item = future.result()
                        if success:
                            reclaimed_bytes += art.size_bytes
                            if item:
                                quarantined_count += 1
                                vault_items.append(item)
                            else:
                                deleted_count += 1
                        elif err:
                            errors.append(err)
                    except Exception as exc:
                        errors.append(f"Error purging '{art.path}': {exc}")
        else:
            for art in artifacts:
                success, err, item = self.delete_artifact(art, vault_session_id)
                if success:
                    reclaimed_bytes += art.size_bytes
                    if item:
                        quarantined_count += 1
                        vault_items.append(item)
                    else:
                        deleted_count += 1
                elif err:
                    errors.append(err)

        # Save vault manifest if quarantined items exist
        if vault_session_id and self.vault and vault_items:
            session = VaultSession(
                vault_id=vault_session_id,
                created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                total_bytes=reclaimed_bytes,
                total_items=len(vault_items),
                items=vault_items,
            )
            self.vault.save_session_manifest(session)

        # 2. Slay Zombie Processes (including process trees)
        if zombies:
            for z in zombies:
                if self.dry_run:
                    slain_zombies += 1
                else:
                    killed_count = kill_zombie_tree(z.pid, force=True)
                    if killed_count > 0:
                        slain_zombies += 1
                    else:
                        errors.append(f"Failed to terminate zombie PID {z.pid} ({z.name})")

        duration = time.time() - start_time
        result = CleanResult(
            reclaimed_bytes=reclaimed_bytes,
            deleted_artifacts_count=deleted_count,
            slain_zombies_count=slain_zombies,
            duration_seconds=duration,
            quarantined_count=quarantined_count,
            vault_session_id=vault_session_id,
            errors=errors,
        )

        if not self.dry_run and self.record_history:
            record_clean_event(result)

        return result
