"""Adversarial edge-case tests: boundary conditions, failure injection, fuzzed inputs."""

from pathlib import Path

import pytest

from purge.core.api import PurgeEngine
from purge.core.models import parse_size_to_bytes
from purge.core.scanner import DiskScanner


class TestParseSizeFuzz:
    @pytest.mark.parametrize("raw,expected", [
        ("50MB", 50 * 1024**2),
        ("1.5GB", int(1.5 * 1024**3)),
        ("500KB", 500 * 1024),
        ("2TB", 2 * 1024**4),
        ("1024B", 1024),
        ("1073741824", 1073741824),
        ("  10 mb  ", 10 * 1024**2),   # case/space tolerant
        ("10Mb", 10 * 1024**2),
        ("0KB", 0),
        ("", 0),
        ("garbage", 0),
        ("999999999999999PB", 999999999999999 * 1024**5),
    ])
    def test_parse_size_boundaries(self, raw, expected):
        assert parse_size_to_bytes(raw) == expected

    def test_negative_protection(self):
        # negative or invalid sizes must never yield negative byte counts
        for bad in ("-5MB", "MB", "1.2.3GB", "∞GB"):
            result = parse_size_to_bytes(bad)
            assert result >= 0

class TestScanEdgeCases:
    def test_scan_empty_directory(self, tmp_path):
        report = DiskScanner(git_aware=False).scan(tmp_path)
        assert report.artifacts == []
        assert report.total_bytes == 0

    def test_scan_max_depth_zero(self, tmp_path):
        nested = tmp_path / "a" / "b" / "node_modules"
        nested.mkdir(parents=True)
        (nested / "f.txt").write_text("x", encoding="utf-8")
        report = DiskScanner(git_aware=False).scan(tmp_path, max_depth=0)
        # depth 0 only scans the root dir itself; nested artifacts unreachable
        assert report.artifacts == []

    def test_scan_symlink_loops_terminate(self, tmp_path):
        link = tmp_path / "loop"
        link.symlink_to(tmp_path, target_is_directory=True)
        report = DiskScanner(git_aware=False).scan(tmp_path, max_depth=5)
        assert report.duration_seconds < 10.0  # terminates, no hang

    def test_scan_deeply_nested(self, tmp_path):
        deep = tmp_path
        for i in range(25):
            deep = deep / f"d{i}"
        deep.mkdir(parents=True)
        (deep / "package.json").write_text("{}", encoding="utf-8")
        nm = deep / "node_modules"
        nm.mkdir()
        (nm / "x").write_text("y", encoding="utf-8")
        report = DiskScanner(git_aware=False).scan(tmp_path, max_depth=30)
        assert any(a.path.name == "node_modules" for a in report.artifacts)

    def test_scan_permission_error_resilience(self, tmp_path, monkeypatch):
        # Inject stat failures mid-traversal: scanner must skip and continue
        import purge.core.scanner as scanner_mod

        original_scandir = scanner_mod.os.scandir

        def flaky_scandir(path):
            if str(path).endswith("poisoned"):
                raise PermissionError("injected")
            return original_scandir(path)

        monkeypatch.setattr(scanner_mod.os, "scandir", flaky_scandir)
        (tmp_path / "poisoned").mkdir()
        (tmp_path / "poisoned" / "x").write_text("x", encoding="utf-8")
        report = DiskScanner(git_aware=False).scan(tmp_path)
        assert report is not None

    def test_scan_unicode_paths(self, tmp_path):
        proj = tmp_path / "projéct-ünïcode"
        proj.mkdir()
        (proj / "package.json").write_text("{}", encoding="utf-8")
        nm = proj / "node_modules"
        nm.mkdir()
        (nm / "数据.bin").write_bytes(b"z" * 100)
        report = DiskScanner(git_aware=False).scan(tmp_path)
        assert any("projéct-ünïcode" in str(a.path) for a in report.artifacts)
        assert any(a.file_count == 1 and a.size_bytes == 100 for a in report.artifacts)


class TestCleanerFailureInjection:
    def test_delete_missing_path_reports_error(self, tmp_path):
        from purge.core.cleaner import PurgeCleaner
        from purge.core.models import Artifact

        ghost = Artifact(path=tmp_path / "ghost_dir", category="X", size_bytes=1)
        cleaner = PurgeCleaner(record_history=False)
        ok, err, _ = cleaner.delete_artifact(ghost)
        assert ok is False
        assert "no longer exists" in err

    def test_purge_with_raising_delete_continues(self, tmp_path, monkeypatch):
        from purge.core.cleaner import PurgeCleaner
        from purge.core.models import Artifact

        a1 = Artifact(path=tmp_path / "one", category="X", size_bytes=10)
        a2 = Artifact(path=tmp_path / "two", category="X", size_bytes=10)
        (tmp_path / "one").mkdir()
        (tmp_path / "two").mkdir()

        calls = {"n": 0}

        def flaky_delete(self, artifact, vault_session_id=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return False, f"Injected failure for {artifact.path}", None
            return True, None, None

        monkeypatch.setattr(PurgeCleaner, "delete_artifact", flaky_delete)
        cleaner = PurgeCleaner(workers=1, record_history=False)
        result = cleaner.purge([a1, a2])
        assert len(result.errors) == 1
        assert result.deleted_artifacts_count == 1
        assert (tmp_path / "two").exists()  # dry_run didn't delete; flaky returned True but monkeypatched


class TestProtectedPathMatrix:
    @pytest.mark.parametrize("candidate,protected", [
        ("/", True),
        ("/usr", True),
        ("/etc", True),
        ("/home/someuser", False),  # inside home but not home root: scannable
        ("/tmp/ok", False),
    ])
    def test_protection_matrix(self, candidate, protected):
        from purge.core.rules import is_protected_path

        assert is_protected_path(Path(candidate), allow_home=False) is protected

    def test_home_root_itself_is_protected(self):
        from pathlib import Path as P

        from purge.core.rules import is_protected_path

        assert is_protected_path(P.home(), allow_home=False) is True
        assert is_protected_path(P.home(), allow_home=True) is False


class TestEngineFuzz:
    def test_scan_random_garbage_options_do_not_crash(self, tmp_path):
        engine = PurgeEngine(root_path=tmp_path)
        for weird in (None, [], "", -1, 999999, 0.0001, "Ω"):
            try:
                engine.scan(path=tmp_path, min_score=weird, min_stale_days=weird)
            except (TypeError, ValueError):
                pass  # graceful rejection is acceptable; a crash is not
