"""Tests for the v3.0 PurgeEngine programmatic API."""

from pathlib import Path

import pytest

from purge.core.api import PurgeEngine


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Build a mini dev workspace with one Node and one Python artifact."""
    node_root = tmp_path / "web"
    node_root.mkdir()
    (node_root / "package.json").write_text("{}", encoding="utf-8")
    nm = node_root / "node_modules"
    nm.mkdir()
    for i in range(5):
        (nm / f"pkg_{i}").write_text("x" * 100, encoding="utf-8")

    py_root = tmp_path / "service"
    py_root.mkdir()
    (py_root / "pyproject.toml").write_text("[project]", encoding="utf-8")
    venv = py_root / ".venv"
    venv.mkdir()
    (venv / "pyvenv.cfg").write_text("cfg", encoding="utf-8")
    return tmp_path


class TestPurgeEngineScan:
    def test_scan_returns_report_with_artifacts(self, workspace: Path):
        engine = PurgeEngine(root_path=workspace)
        report = engine.scan(path=workspace)

        names = [a.path.name for a in report.artifacts]
        assert "node_modules" in names
        assert ".venv" in names
        assert report.total_bytes > 0
        assert report.duration_seconds >= 0.0

    def test_scan_filters_by_min_size_bytes(self, workspace: Path):
        engine = PurgeEngine(root_path=workspace)
        report = engine.scan(path=workspace, min_size=10_000_000)
        assert report.artifacts == []

    def test_scan_filters_by_category(self, workspace: Path):
        engine = PurgeEngine(root_path=workspace)
        report = engine.scan(path=workspace, categories=["Python"])
        assert all(a.category == "Python" for a in report.artifacts)
        assert any(a.path.name == ".venv" for a in report.artifacts)

    def test_scan_accepts_human_size_string(self, workspace: Path):
        engine = PurgeEngine(root_path=workspace)
        report = engine.scan(path=workspace, min_size="1KB")
        # artifacts are ~500+ bytes; 1KB filter keeps those >= 1024 bytes
        assert all(a.size_bytes >= 1024 for a in report.artifacts)

    def test_scan_top_limit(self, workspace: Path):
        engine = PurgeEngine(root_path=workspace)
        report = engine.scan(path=workspace, top=1)
        assert len(report.artifacts) <= 1

    def test_scan_rejects_protected_root(self):
        engine = PurgeEngine()
        with pytest.raises(ValueError):
            engine.scan(path=Path("/usr"))


class TestPurgeEngineInspect:
    def test_inspect_node_modules(self, workspace: Path):
        engine = PurgeEngine(root_path=workspace)
        target = workspace / "web" / "node_modules"
        info = engine.inspect(target)

        assert info["path"] == str(target)
        assert info["category"] == "Node.js & Web"
        assert info["file_count"] == 5
        assert info["size_bytes"] >= 500
        assert 0.0 <= info["purge_score"] <= 100.0
        assert info["safety_level"] in ("SAFE", "MODERATE", "CAUTION")

    def test_inspect_unknown_path_has_no_category(self, workspace: Path):
        engine = PurgeEngine(root_path=workspace)
        plain = workspace / "web"
        info = engine.inspect(plain)
        assert info["category"] is None


class TestPurgeEngineClean:
    def test_clean_dry_run_deletes_nothing(self, workspace: Path):
        engine = PurgeEngine(root_path=workspace)
        report = engine.scan(path=workspace)
        result = engine.clean(artifacts=report.artifacts, dry_run=True)

        assert result.deleted_artifacts_count == len(report.artifacts)
        assert (workspace / "web" / "node_modules").exists()
        assert (workspace / "service" / ".venv").exists()

    def test_clean_deletes_for_real(self, workspace: Path):
        engine = PurgeEngine(root_path=workspace)
        report = engine.scan(path=workspace)
        result = engine.clean(artifacts=report.artifacts, record_history=False)

        assert result.deleted_artifacts_count >= 1
        assert not (workspace / "web" / "node_modules").exists()
        assert result.reclaimed_bytes > 0
        assert result.errors == []

    def test_clean_auto_mode_only_high_scores(self, workspace: Path):
        engine = PurgeEngine(root_path=workspace)
        report = engine.scan(path=workspace)
        result = engine.clean(artifacts=report.artifacts, auto_min_score=101.0, record_history=False)
        # impossible threshold => nothing selected, nothing deleted
        assert result.deleted_artifacts_count == 0

    def test_clean_quarantines_to_vault(self, workspace: Path):
        engine = PurgeEngine(root_path=workspace)
        vault_root = tmp_unique_dir()
        report = engine.scan(path=workspace)
        result = engine.clean(
            artifacts=report.artifacts,
            to_vault=True,
            vault_root=vault_root,
            record_history=False,
        )

        assert result.quarantined_count == len(report.artifacts)
        assert result.vault_session_id is not None
        assert not (workspace / "web" / "node_modules").exists()

        # restore round-trip
        count, restored_bytes, errors = engine.vault_restore(result.vault_session_id)
        assert count == len(report.artifacts)
        assert errors == []
        assert (workspace / "web" / "node_modules").exists()


def tmp_unique_dir() -> Path:
    import tempfile

    d = Path(tempfile.mkdtemp(prefix="purge_vault_test_"))
    return d


class TestPurgeEngineMisc:
    def test_stats_shape(self):
        engine = PurgeEngine()
        stats = engine.stats()
        assert "total_reclaimed_bytes" in stats
        assert "total_purges_run" in stats

    def test_find_zombies_returns_list(self):
        engine = PurgeEngine()
        assert isinstance(engine.find_zombies(), list)

    def test_engine_defaults_match_config(self, workspace: Path):
        engine = PurgeEngine(root_path=workspace)
        assert engine.root_path == workspace
        assert engine.config.git_aware is True
