from pathlib import Path

from purge.core.config import PurgeConfig, _simple_toml_fallback, load_config


def test_purge_config_defaults():
    cfg = PurgeConfig()
    assert cfg.max_depth == 10
    assert cfg.min_stale_days == 0.0
    assert cfg.min_size_bytes == 0
    assert cfg.git_aware is True
    assert cfg.default_trash is False
    assert cfg.default_format == "terminal"


def test_purge_config_from_dict():
    data = {
        "max_depth": 5,
        "min_stale_days": 14.5,
        "min_size_bytes": 1048576,
        "categories": ["Node.js & Web", "Python"],
        "custom_rules": {"MyCache": ["cache_dir"]},
        "ignore_paths": ["vendor/*"],
        "default_trash": True,
        "git_aware": False,
        "default_format": "json",
    }
    cfg = PurgeConfig.from_dict(data)
    assert cfg.max_depth == 5
    assert cfg.min_stale_days == 14.5
    assert cfg.min_size_bytes == 1048576
    assert cfg.categories == ["Node.js & Web", "Python"]
    assert cfg.custom_rules == {"MyCache": ["cache_dir"]}
    assert cfg.ignore_paths == ["vendor/*"]
    assert cfg.default_trash is True
    assert cfg.git_aware is False
    assert cfg.default_format == "json"


def test_load_config_from_purge_toml(tmp_path: Path):
    toml_file = tmp_path / "purge.toml"
    toml_file.write_text(
        """[purge]
max_depth = 8
min_stale_days = 30
git_aware = false
""",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.max_depth == 8
    assert cfg.min_stale_days == 30.0
    assert cfg.git_aware is False


def test_load_config_from_pyproject_toml(tmp_path: Path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[tool.purge]
max_depth = 4
default_trash = true
""",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.max_depth == 4
    assert cfg.default_trash is True


def test_simple_toml_fallback_parser():
    content = """
    # Comment
    [purge]
    max_depth = 12
    git_aware = true
    default_format = "json"
    categories = ["Node.js & Web", "Rust / Cargo"]
    """
    res = _simple_toml_fallback(content)
    assert res.get("max_depth") == 12
    assert res.get("git_aware") is True
    assert res.get("default_format") == "json"
    assert res.get("categories") == ["Node.js & Web", "Rust / Cargo"]
