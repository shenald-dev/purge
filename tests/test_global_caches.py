from pathlib import Path

from purge.core import rules
from purge.core.scanner import DiskScanner


def test_get_global_cache_targets_mock(tmp_path: Path, monkeypatch):
    mock_home = tmp_path / "home"
    mock_npm = mock_home / ".npm" / "_cacache"
    mock_npm.mkdir(parents=True)
    (mock_npm / "dummy.cache").write_text("cache data")

    monkeypatch.setattr(Path, "home", lambda: mock_home)
    monkeypatch.setenv("LOCALAPPDATA", str(mock_home / "AppData" / "Local"))

    targets = rules.get_global_cache_targets()
    target_paths = [str(p) for p, _, _ in targets]
    assert str(mock_npm.resolve()) in target_paths


def test_scan_global_caches_in_scanner(tmp_path: Path, monkeypatch):
    mock_home = tmp_path / "user"
    mock_pip = mock_home / ".cache" / "pip"
    mock_pip.mkdir(parents=True)
    (mock_pip / "wheel.whl").write_bytes(b"x" * 2048)

    monkeypatch.setattr(Path, "home", lambda: mock_home)
    monkeypatch.setenv("LOCALAPPDATA", str(mock_home / "AppData" / "Local"))

    scanner = DiskScanner()
    caches = scanner.scan_global_caches()
    assert len(caches) >= 1
    pip_cache = next(c for c in caches if "pip" in c.category.lower())
    assert pip_cache.size_bytes == 2048
    assert pip_cache.is_global_cache is True
