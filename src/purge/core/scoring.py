"""Purge Priority & Safety Scoring Engine.

Calculates intelligent 0-100 reclamation priority scores based on size,
staleness, ecosystem rebuild cost, and Git repository state.
"""

from dataclasses import dataclass
from enum import Enum


class SafetyLevel(str, Enum):
    """Safety classification for artifact removal."""

    SAFE = "SAFE"
    MODERATE = "MODERATE"
    CAUTION = "CAUTION"
    PROTECTED = "PROTECTED"


@dataclass
class ScoreBreakdown:
    """Detailed components contributing to an artifact's purge score."""

    size_score: float
    stale_score: float
    ephemeral_score: float
    git_score: float
    penalty: float
    total_score: float
    safety_level: SafetyLevel
    recommendation: str


# Highly ephemeral build caches that are trivially re-generated
TRIVIALLY_REGENERATED = {
    "node_modules",
    ".next",
    ".turbo",
    ".nuxt",
    ".parcel-cache",
    ".svelte-kit",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    ".hypothesis",
    "target",
    ".gradle",
    "dist",
    "build",
    "out",
    "coverage",
    ".nyc_output",
    ".DS_Store",
    "Thumbs.db",
    "DerivedData",
    ".dart_tool",
    ".nx",
}


def calculate_purge_score(
    size_bytes: int,
    days_stale: float,
    category: str,
    artifact_name: str,
    is_git_repo: bool = False,
    has_uncommitted: bool = False,
    days_since_commit: float = 0.0,
    is_global_cache: bool = False,
) -> ScoreBreakdown:
    """Calculate the 0-100 Purge Priority Score for an artifact."""
    # 1. Size Component (Max 35 points)
    mb = size_bytes / (1024.0 * 1024.0)
    if mb >= 2048:  # >= 2GB
        size_score = 35.0
    elif mb >= 500:  # 500MB - 2GB
        size_score = 28.0
    elif mb >= 100:  # 100MB - 500MB
        size_score = 20.0
    elif mb >= 10:  # 10MB - 100MB
        size_score = 12.0
    elif mb > 0:
        size_score = 5.0
    else:
        size_score = 0.0

    # 2. Staleness Component (Max 30 points)
    if days_stale >= 90:
        stale_score = 30.0
    elif days_stale >= 30:
        stale_score = 25.0
    elif days_stale >= 7:
        stale_score = 18.0
    elif days_stale >= 1:
        stale_score = 8.0
    else:
        stale_score = 2.0

    # 3. Ephemerality & Ecosystem Component (Max 20 points)
    name_lower = artifact_name.lower()
    if is_global_cache:
        ephemeral_score = 16.0
    elif any(t in name_lower for t in TRIVIALLY_REGENERATED):
        ephemeral_score = 20.0
    elif any(v in name_lower for v in [".venv", "venv", "env"]):
        ephemeral_score = 12.0  # Requires reinstalling dependencies
    else:
        ephemeral_score = 10.0

    # 4. Git Repository Intelligence Component (Max 15 points)
    git_score = 0.0
    penalty = 0.0

    if is_git_repo:
        if has_uncommitted:
            # Active work-in-progress: apply strong penalty
            penalty += 35.0
            git_score = 0.0
        else:
            if days_since_commit >= 60:
                git_score = 15.0
            elif days_since_commit >= 14:
                git_score = 10.0
            else:
                git_score = 5.0
    elif is_global_cache:
        git_score = 10.0
    else:
        git_score = 5.0

    # Compute total score clamped to [0, 100]
    raw_score = size_score + stale_score + ephemeral_score + git_score - penalty
    total_score = max(0.0, min(100.0, round(raw_score, 1)))

    # Determine safety level
    if has_uncommitted:
        safety = SafetyLevel.CAUTION
        rec = "Review uncommitted git work before purging"
    elif total_score >= 65.0:
        safety = SafetyLevel.SAFE
        rec = "High-priority reclamation target; safe to purge"
    elif total_score >= 35.0:
        safety = SafetyLevel.MODERATE
        rec = "Moderate priority; safe to prune if not in active use"
    else:
        safety = SafetyLevel.CAUTION
        rec = "Recently active or low reclamation yield; purge selectively"

    return ScoreBreakdown(
        size_score=size_score,
        stale_score=stale_score,
        ephemeral_score=ephemeral_score,
        git_score=git_score,
        penalty=penalty,
        total_score=total_score,
        safety_level=safety,
        recommendation=rec,
    )
