"""Security tests for vault manifest hardening and cleanup fixes."""

import json
from pathlib import Path

import pytest

from purge.core.vault import QuarantineVault, VaultItem, VaultSession


@pytest.fixture()
def vault(tmp_path: Path) -> QuarantineVault:
    return QuarantineVault(vault_root=tmp_path / "vault")


def _make_session(vault_root: Path, vault_id: str, items) -> Path:
    session_dir = vault_root / vault_id
    session_dir.mkdir(parents=True, exist_ok=True)
    for item in items:
        item_dir = session_dir / item.item_id
        item_dir.mkdir(exist_ok=True)
        (item_dir / "payload.txt").write_text("data", encoding="utf-8")
    manifest = VaultSession(
        vault_id=vault_id,
        created_at="2026-11-17T00:00:00Z",
        total_bytes=sum(i.size_bytes for i in items),
        total_items=len(items),
        items=list(items),
    )
    (session_dir / "manifest.json").write_text(json.dumps(manifest.to_dict()), encoding="utf-8")
    return session_dir


class TestVaultPathTraversalHardening:
    def test_restore_refuses_relative_destination(self, vault, tmp_path):
        items = [VaultItem(
            item_id="item_1", original_path="relative/escape/target",
            vault_path=str(vault.vault_root / "s1" / "item_1"),
            size_bytes=10, is_dir=True,
        )]
        _make_session(vault.vault_root, "s1", items)
        count, byte_count, errors = vault.restore_session("s1")
        assert count == 0
        assert any("unsafe" in e.lower() for e in errors)

    def test_restore_refuses_destination_inside_vault(self, vault):
        items = [VaultItem(
            item_id="item_1",
            original_path=str(vault.vault_root / "s1" / "injected_target"),
            vault_path=str(vault.vault_root / "s1" / "item_1"),
            size_bytes=10, is_dir=True,
        )]
        _make_session(vault.vault_root, "s1", items)
        count, _, errors = vault.restore_session("s1")
        assert count == 0
        assert any("unsafe" in e.lower() for e in errors)

    def test_restore_refuses_protected_system_destination(self, vault):
        items = [VaultItem(
            item_id="item_1",
            original_path="/usr/local/bin",
            vault_path=str(vault.vault_root / "s1" / "item_1"),
            size_bytes=10, is_dir=True,
        )]
        _make_session(vault.vault_root, "s1", items)
        count, _, errors = vault.restore_session("s1")
        assert count == 0
        assert any("unsafe" in e.lower() for e in errors)

    def test_restore_allows_legitimate_destination(self, vault, tmp_path):
        legit_target = tmp_path / "projects" / "web" / "node_modules"
        items = [VaultItem(
            item_id="item_1",
            original_path=str(legit_target),
            vault_path=str(vault.vault_root / "s1" / "item_1"),
            size_bytes=10, is_dir=True,
        )]
        _make_session(vault.vault_root, "s1", items)
        count, _, errors = vault.restore_session("s1")
        assert count == 1
        assert errors == []
        assert legit_target.exists()
        assert (legit_target / "payload.txt").read_text() == "data"

    def test_restore_refuses_vault_path_outside_session(self, vault, tmp_path):
        # manifest claims an item stored in a DIFFERENT session's directory
        other_dir = vault.vault_root / "other_session" / "item_9"
        other_dir.mkdir(parents=True, exist_ok=True)
        (other_dir / "payload.txt").write_text("evil", encoding="utf-8")
        items = [VaultItem(
            item_id="item_9",
            original_path=str(tmp_path / "stolen_destination"),
            vault_path=str(other_dir),
            size_bytes=10, is_dir=True,
        )]
        _make_session(vault.vault_root, "s1", items)
        count, _, errors = vault.restore_session("s1")
        assert count == 0
        assert any("unsafe" in e.lower() for e in errors)
        # the attacker-controlled payload was NOT moved out of the vault
        assert (other_dir / "payload.txt").exists()


class TestTrashErrorClassification:
    def test_missing_send2trash_reports_install_hint(self, tmp_path, monkeypatch):
        from purge.core.cleaner import PurgeCleaner
        from purge.core.models import Artifact

        f = tmp_path / "artifact_dir"
        f.mkdir()
        (f / "x.txt").write_text("x", encoding="utf-8")
        art = Artifact(path=f, category="Temp", size_bytes=10)

        import builtins
        real_import = builtins.__import__

        def blocked_import(name, *args, **kwargs):
            if name == "send2trash":
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", blocked_import)
        cleaner = PurgeCleaner(to_trash=True, record_history=False)
        ok, err, _ = cleaner.delete_artifact(art)
        assert ok is False
        assert "purge-reaper[trash]" in err or "send2trash" in err

    def test_runtime_trash_failure_reports_real_cause(self, tmp_path, monkeypatch):
        from purge.core.cleaner import PurgeCleaner
        from purge.core.models import Artifact

        f = tmp_path / "artifact_dir"
        f.mkdir()
        (f / "x.txt").write_text("x", encoding="utf-8")
        art = Artifact(path=f, category="Temp", size_bytes=10)

        import send2trash
        monkeypatch.setattr(
            send2trash, "send2trash",
            lambda p: (_ for _ in ()).throw(RuntimeError("trash daemon unavailable")),
        )
        cleaner = PurgeCleaner(to_trash=True, record_history=False)
        ok, err, _ = cleaner.delete_artifact(art)
        assert ok is False
        assert "Failed to move" in err
        assert "trash daemon unavailable" in err
