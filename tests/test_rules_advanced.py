from pathlib import Path

from purge.core.rules import identify_artifact_category, is_protected_path


def test_custom_rules_override(tmp_path: Path):
    custom = {"TeamCache": ["team_temp", "local_dump"]}
    cat = identify_artifact_category("team_temp", tmp_path, custom_rules=custom)
    assert cat == "TeamCache"


def test_maven_pom_identification(tmp_path: Path):
    (tmp_path / "pom.xml").write_text("<project></project>")
    cat = identify_artifact_category("target", tmp_path)
    assert cat == "Java / Maven"


def test_manifest_verification_for_build_and_dist(tmp_path: Path):
    # Without manifest, 'build' should NOT be flagged (protects arbitrary folders)
    assert identify_artifact_category("build", tmp_path) is None
    assert identify_artifact_category("dist", tmp_path) is None

    # With package.json, it should be recognized
    (tmp_path / "package.json").write_text("{}")
    assert identify_artifact_category("build", tmp_path) == "Build Artifacts"
    assert identify_artifact_category("dist", tmp_path) == "Build Artifacts"


def test_modern_framework_categories(tmp_path: Path):
    assert identify_artifact_category(".astro", tmp_path) == "Node.js & Web"
    assert identify_artifact_category(".expo", tmp_path) == "Mobile / Cross-Platform"
    assert identify_artifact_category("Pods", tmp_path) == "Mobile / Cross-Platform"
    assert identify_artifact_category(".pytest_cache", tmp_path) == "Python"


def test_protected_roots():
    assert is_protected_path(Path("C:\\")) is True
    assert is_protected_path(Path("/")) is True
    # Git directory should be protected
    assert is_protected_path(Path("/Users/test/project/.git")) is True
