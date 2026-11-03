"""Tests for purge scoring and safety priority engine."""

from purge.core.scoring import SafetyLevel, calculate_purge_score


def test_scoring_high_priority_target():
    """Large, stale, re-generable artifact in clean git repo gets high purge score."""
    res = calculate_purge_score(
        size_bytes=1024 * 1024 * 1024,  # 1 GB
        days_stale=45.0,
        category="Node.js & Web",
        artifact_name="node_modules",
        is_git_repo=True,
        has_uncommitted=False,
        days_since_commit=65.0,
    )
    assert res.total_score >= 80.0
    assert res.safety_level == SafetyLevel.SAFE
    assert "High-priority" in res.recommendation


def test_scoring_uncommitted_changes_penalty():
    """Artifact in repo with uncommitted work receives penalty and CAUTION safety level."""
    res = calculate_purge_score(
        size_bytes=200 * 1024 * 1024,  # 200 MB
        days_stale=10.0,
        category="Python",
        artifact_name=".venv",
        is_git_repo=True,
        has_uncommitted=True,
    )
    assert res.penalty >= 30.0
    assert res.safety_level == SafetyLevel.CAUTION
    assert "Review uncommitted git work" in res.recommendation


def test_scoring_global_cache():
    """Global package manager cache scoring."""
    res = calculate_purge_score(
        size_bytes=3 * 1024 * 1024 * 1024,  # 3 GB
        days_stale=100.0,
        category="Global Cache: npm",
        artifact_name="_cacache",
        is_global_cache=True,
    )
    assert res.total_score >= 85.0
    assert res.safety_level == SafetyLevel.SAFE


def test_scoring_small_recent_target():
    """Small recent artifact gets low priority."""
    res = calculate_purge_score(
        size_bytes=1024 * 50,  # 50 KB
        days_stale=0.2,
        category="Python",
        artifact_name="__pycache__",
        is_git_repo=False,
    )
    assert res.total_score < 40.0
    assert res.safety_level == SafetyLevel.MODERATE or res.safety_level == SafetyLevel.CAUTION
