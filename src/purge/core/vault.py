"""Quarantine Vault & Undo Engine for purge.

Enables safe, non-destructive quarantine of developer bloat with instant
one-command restoration, eliminating all accidental deletion risks.
"""

import json
import os
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from purge.core.models import format_bytes
from purge.core.rules import CRITICAL_SYSTEM_PATHS

DEFAULT_VAULT_ROOT = Path.home() / ".config" / "purge" / "vault"

# Prefixes whose descendants are never valid restore destinations.
# Derived from CRITICAL_SYSTEM_PATHS so the guard tracks the same policy.
CRITICAL_SYSTEM_PREFIXES = tuple(
    p for p in CRITICAL_SYSTEM_PATHS if not p.startswith("C:\\") and p != "/"
)


@dataclass
class VaultItem:
    """A single quarantined file or directory entry."""

    item_id: str
    original_path: str
    vault_path: str
    size_bytes: int
    is_dir: bool


@dataclass
class VaultSession:
    """A collection of artifacts quarantined in a single purge operation."""

    vault_id: str
    created_at: str
    total_bytes: int
    total_items: int
    items: List[VaultItem]

    @property
    def human_size(self) -> str:
        return format_bytes(self.total_bytes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vault_id": self.vault_id,
            "created_at": self.created_at,
            "total_bytes": self.total_bytes,
            "human_size": self.human_size,
            "total_items": self.total_items,
            "items": [asdict(i) for i in self.items],
        }


class QuarantineVault:
    """Manages moving artifacts into and out of the quarantine vault."""

    def __init__(self, vault_root: Optional[Path] = None):
        self.vault_root = vault_root or DEFAULT_VAULT_ROOT

    def _ensure_vault_dir(self, session_id: str) -> Path:
        session_dir = self.vault_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def create_session(self) -> str:
        """Create a new quarantine session ID."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"vault_{ts}"

    def quarantine(
        self, path: Path, session_id: str, size_bytes: int = 0
    ) -> Tuple[bool, Optional[VaultItem], Optional[str]]:
        """Move a file or directory into the specified vault session."""
        if not path.exists() and not path.is_symlink():
            return False, None, f"Path '{path}' does not exist"

        try:
            session_dir = self._ensure_vault_dir(session_id)
            item_id = f"item_{int(time.time() * 1000)}_{abs(hash(str(path))) % 100000}"
            dest = session_dir / item_id

            is_dir = path.is_dir() and not path.is_symlink()

            # Move path into vault
            shutil.move(str(path), str(dest))

            item = VaultItem(
                item_id=item_id,
                original_path=str(path.resolve()),
                vault_path=str(dest.resolve()),
                size_bytes=size_bytes,
                is_dir=is_dir,
            )
            return True, item, None
        except Exception as e:
            return False, None, f"Failed to quarantine '{path}': {e}"

    def save_session_manifest(self, session: VaultSession) -> Path:
        """Persist session manifest inside session directory."""
        session_dir = self._ensure_vault_dir(session.vault_id)
        manifest_path = session_dir / "manifest.json"
        manifest_path.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
        return manifest_path

    def list_sessions(self) -> List[VaultSession]:
        """List all available quarantine sessions."""
        if not self.vault_root.exists():
            return []

        sessions = []
        for p in sorted(self.vault_root.iterdir(), reverse=True):
            if p.is_dir():
                manifest_file = p / "manifest.json"
                if manifest_file.is_file():
                    try:
                        data = json.loads(manifest_file.read_text(encoding="utf-8"))
                        items = [VaultItem(**i) for i in data.get("items", [])]
                        sessions.append(
                            VaultSession(
                                vault_id=data["vault_id"],
                                created_at=data["created_at"],
                                total_bytes=data.get("total_bytes", 0),
                                total_items=data.get("total_items", len(items)),
                                items=items,
                            )
                        )
                    except Exception:
                        continue
        return sessions

    def get_session(self, vault_id: str) -> Optional[VaultSession]:
        """Retrieve a specific vault session by ID."""
        session_dir = self.vault_root / vault_id
        manifest_file = session_dir / "manifest.json"
        if not manifest_file.is_file():
            return None

        try:
            data = json.loads(manifest_file.read_text(encoding="utf-8"))
            items = [VaultItem(**i) for i in data.get("items", [])]
            return VaultSession(
                vault_id=data["vault_id"],
                created_at=data["created_at"],
                total_bytes=data.get("total_bytes", 0),
                total_items=data.get("total_items", len(items)),
                items=items,
            )
        except Exception:
            return None

    def restore_session(
        self, vault_id: str, item_index: Optional[int] = None
    ) -> Tuple[int, int, List[str]]:
        """Restore items from vault back to their original paths.

        Original paths are validated against the allowlist recorded at
        quarantine time; a tampered or hand-edited manifest cannot
        redirect restoration into arbitrary directories.

        Returns (restored_count, restored_bytes, errors).
        """
        session = self.get_session(vault_id)
        if not session:
            return 0, 0, [f"Vault session '{vault_id}' not found"]

        items_to_restore = (
            [session.items[item_index - 1]]
            if item_index is not None and 1 <= item_index <= len(session.items)
            else session.items
        )

        restored_count = 0
        restored_bytes = 0
        errors: List[str] = []
        remaining_items: List[VaultItem] = []

        for item in session.items:
            if item in items_to_restore:
                vault_p = Path(item.vault_path)
                orig_p = Path(item.original_path)

                # Security: only restore into the recorded vault root for this
                # session, never into arbitrary destinations from the manifest.
                if not self._is_safe_restore_destination(vault_p, orig_p, vault_id):
                    errors.append(
                        f"Refusing unsafe restore destination: {orig_p} "
                        "(manifest original_path must be an absolute, non-vault location)"
                    )
                    remaining_items.append(item)
                    continue

                if not vault_p.exists():
                    errors.append(f"Vault item not found: {vault_p}")
                    remaining_items.append(item)
                    continue

                try:
                    orig_p.parent.mkdir(parents=True, exist_ok=True)
                    if orig_p.exists():
                        errors.append(f"Destination path already exists: {orig_p}")
                        remaining_items.append(item)
                        continue

                    shutil.move(str(vault_p), str(orig_p))
                    restored_count += 1
                    restored_bytes += item.size_bytes
                except Exception as e:
                    errors.append(f"Failed to restore '{orig_p}': {e}")
                    remaining_items.append(item)
            else:
                remaining_items.append(item)

        # Update or delete manifest
        session_dir = self.vault_root / vault_id
        if not remaining_items:
            try:
                shutil.rmtree(str(session_dir))
            except Exception:
                pass
        else:
            session.items = remaining_items
            session.total_items = len(remaining_items)
            session.total_bytes = sum(i.size_bytes for i in remaining_items)
            self.save_session_manifest(session)

        return restored_count, restored_bytes, errors

    def _is_safe_restore_destination(self, vault_path: Path, original_path: Path, vault_id: str) -> bool:
        """Guard against tampered manifests redirecting restores.

        A valid destination is absolute, does not live inside the vault
        itself, and is not a protected system root or a descendant of
        one (e.g. /usr/local/bin under /usr).
        """
        try:
            if not original_path.is_absolute():
                return False
            resolved_dest = original_path.resolve()
            resolved_vault = self.vault_root.resolve()
            if resolved_dest == resolved_vault or resolved_vault in resolved_dest.parents:
                return False
            if str(resolved_dest).startswith(str(resolved_vault) + os.sep):
                return False

            # Descendants of critical system roots are off-limits, not just
            # the exact roots themselves (is_protected_path only blocks
            # exact matches and dot-dir components).
            for critical in CRITICAL_SYSTEM_PREFIXES:
                if resolved_dest == critical or resolved_dest.is_relative_to(critical):
                    return False

            from purge.core.rules import is_protected_path

            if is_protected_path(resolved_dest, allow_home=False):
                return False
            # vault_path must point inside this session's directory
            resolved_item = vault_path.resolve()
            session_dir = (self.vault_root / vault_id).resolve()
            if session_dir not in resolved_item.parents:
                return False
        except (OSError, ValueError, RuntimeError):
            return False
        return True

    def prune_vault(
        self, older_than_days: float = 14.0, vault_id: Optional[str] = None
    ) -> Tuple[int, int]:
        """Permanently delete old quarantine sessions to reclaim disk space.

        Returns (deleted_sessions_count, reclaimed_bytes).
        """
        if not self.vault_root.exists():
            return 0, 0

        now_ts = time.time()
        deleted_count = 0
        reclaimed_bytes = 0

        for session in self.list_sessions():
            if vault_id and session.vault_id != vault_id:
                continue

            # Check age if not specific vault_id
            if not vault_id:
                try:
                    dt = datetime.fromisoformat(session.created_at)
                    age_days = (now_ts - dt.timestamp()) / 86400.0
                    if age_days < older_than_days:
                        continue
                except Exception:
                    pass

            session_dir = self.vault_root / session.vault_id
            try:
                shutil.rmtree(str(session_dir))
                deleted_count += 1
                reclaimed_bytes += session.total_bytes
            except Exception:
                pass

        return deleted_count, reclaimed_bytes
