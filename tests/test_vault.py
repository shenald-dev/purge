"""Tests for quarantine vault and undo restoration engine."""

from purge.core.vault import QuarantineVault, VaultSession


def test_quarantine_and_restore(tmp_path):
    """Test full cycle: quarantine a folder and restore it back."""
    vault_root = tmp_path / "vault"
    vault = QuarantineVault(vault_root=vault_root)

    # Create dummy project directory
    project = tmp_path / "my_project"
    project.mkdir()
    node_modules = project / "node_modules"
    node_modules.mkdir()
    (node_modules / "dummy.txt").write_text("dummy package content")

    session_id = vault.create_session()
    ok, item, err = vault.quarantine(node_modules, session_id, size_bytes=500)

    assert ok is True
    assert err is None
    assert item is not None
    assert not node_modules.exists()

    # Save session manifest
    session = VaultSession(
        vault_id=session_id,
        created_at="2026-11-03T12:00:00Z",
        total_bytes=500,
        total_items=1,
        items=[item],
    )
    vault.save_session_manifest(session)

    # Verify listing
    sessions = vault.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].vault_id == session_id

    # Restore session
    restored_count, restored_bytes, errors = vault.restore_session(session_id)
    assert restored_count == 1
    assert restored_bytes == 500
    assert not errors
    assert node_modules.exists()
    assert (node_modules / "dummy.txt").read_text() == "dummy package content"


def test_quarantine_single_file(tmp_path):
    """Test quarantining a single file."""
    vault_root = tmp_path / "vault"
    vault = QuarantineVault(vault_root=vault_root)

    f = tmp_path / "temp_cache.bin"
    f.write_text("cache")

    session_id = vault.create_session()
    ok, item, err = vault.quarantine(f, session_id, size_bytes=5)
    assert ok is True
    assert not f.exists()
    assert item.is_dir is False


def test_vault_prune(tmp_path):
    """Test pruning quarantine sessions."""
    vault_root = tmp_path / "vault"
    vault = QuarantineVault(vault_root=vault_root)

    session_dir = vault_root / "vault_old"
    session_dir.mkdir(parents=True)
    manifest = session_dir / "manifest.json"
    manifest.write_text(
        '{"vault_id": "vault_old", "created_at": "2020-01-01T00:00:00Z", "total_bytes": 1000, "total_items": 1, "items": []}'
    )

    deleted, freed = vault.prune_vault(older_than_days=1.0)
    assert deleted == 1
    assert freed == 1000
    assert not session_dir.exists()
