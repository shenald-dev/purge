"""Configuration engine for purge.

Loads project and user settings from purge.toml or pyproject.toml.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


@dataclass
class PurgeConfig:
    max_depth: int = 10
    min_stale_days: float = 0.0
    min_size_bytes: int = 0
    categories: Optional[List[str]] = None
    custom_rules: Dict[str, List[str]] = field(default_factory=dict)
    ignore_paths: List[str] = field(default_factory=list)
    default_trash: bool = False
    git_aware: bool = True
    default_format: str = "terminal"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PurgeConfig":
        cfg = cls()
        if "max_depth" in data:
            cfg.max_depth = int(data["max_depth"])
        if "min_stale_days" in data:
            cfg.min_stale_days = float(data["min_stale_days"])
        if "min_size_bytes" in data:
            cfg.min_size_bytes = int(data["min_size_bytes"])
        if "categories" in data and isinstance(data["categories"], list):
            cfg.categories = [str(c) for c in data["categories"]]
        if "custom_rules" in data and isinstance(data["custom_rules"], dict):
            cfg.custom_rules = {str(k): list(v) for k, v in data["custom_rules"].items()}
        if "ignore_paths" in data and isinstance(data["ignore_paths"], list):
            cfg.ignore_paths = [str(p) for p in data["ignore_paths"]]
        if "default_trash" in data:
            cfg.default_trash = bool(data["default_trash"])
        if "git_aware" in data:
            cfg.git_aware = bool(data["git_aware"])
        if "default_format" in data:
            cfg.default_format = str(data["default_format"]).lower()
        return cfg


def _simple_toml_fallback(content: str) -> Dict[str, Any]:
    """Lightweight fallback parser for basic key-value toml if tomllib is unavailable."""
    result: Dict[str, Any] = {}
    in_section = False
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            in_section = section in ("purge", "tool.purge")
            continue
        if in_section and "=" in line:
            key, val = [p.strip() for p in line.split("=", 1)]
            if val.lower() == "true":
                result[key] = True
            elif val.lower() == "false":
                result[key] = False
            elif val.isdigit():
                result[key] = int(val)
            elif val.startswith('"') and val.endswith('"'):
                result[key] = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                result[key] = val[1:-1]
            elif val.startswith("[") and val.endswith("]"):
                items = [i.strip().strip("'\"") for i in val[1:-1].split(",") if i.strip()]
                result[key] = items
    return result


def load_config(root_path: Optional[Path] = None) -> PurgeConfig:
    """Load configuration from purge.toml, pyproject.toml, or defaults."""
    root = root_path or Path.cwd()

    # 1. Check purge.toml in target or home
    candidate_files = [
        root / "purge.toml",
        Path.home() / ".config" / "purge" / "purge.toml",
        Path.home() / ".purgerc",
    ]

    for p_file in candidate_files:
        if p_file.is_file():
            try:
                content = p_file.read_text(encoding="utf-8")
                if tomllib is not None:
                    parsed = tomllib.loads(content)
                    section = parsed.get("purge", parsed)
                    return PurgeConfig.from_dict(section)
                else:
                    return PurgeConfig.from_dict(_simple_toml_fallback(content))
            except Exception:
                pass

    # 2. Check pyproject.toml [tool.purge]
    pyproject_file = root / "pyproject.toml"
    if pyproject_file.is_file():
        try:
            content = pyproject_file.read_text(encoding="utf-8")
            if tomllib is not None:
                parsed = tomllib.loads(content)
                tool_section = parsed.get("tool", {}).get("purge", {})
                if tool_section:
                    return PurgeConfig.from_dict(tool_section)
            else:
                fallback = _simple_toml_fallback(content)
                if fallback:
                    return PurgeConfig.from_dict(fallback)
        except Exception:
            pass

    return PurgeConfig()
