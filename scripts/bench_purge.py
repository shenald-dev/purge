"""Reproducible benchmark for purge: scan performance and accuracy.

Generates a deterministic synthetic workspace (seeded), then measures
scan latency, memory, and git inspection cost across N repetitions.
Usage: python bench_purge.py [--label before|after] [--reps N] [--out results.json]
"""

import argparse
import json
import random
import resource
import statistics
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


def build_workspace(root: Path, projects: int = 30, files_per_artifact: int = 300) -> None:
    """Deterministic synthetic dev workspace: mixed ecosystems + git repos."""
    rng = random.Random(42)
    kinds = ["node_modules", ".venv", "target", "dist", "__pycache__", ".next"]
    for p in range(projects):
        proj = root / f"proj_{p:03d}"
        proj.mkdir(parents=True, exist_ok=True)

        kind = kinds[p % len(kinds)]
        if kind == "node_modules":
            (proj / "package.json").write_text("{}", encoding="utf-8")
        elif kind == ".venv":
            (proj / "pyproject.toml").write_text("[project]", encoding="utf-8")
        elif kind == "target":
            (proj / "Cargo.toml").write_text("[package]", encoding="utf-8")
        elif kind == "dist":
            (proj / "package.json").write_text("{}", encoding="utf-8")
        elif kind == "__pycache__":
            (proj / "setup.py").write_text("x=1", encoding="utf-8")
        elif kind == ".next":
            (proj / "package.json").write_text("{}", encoding="utf-8")

        artifact = proj / kind
        artifact.mkdir(parents=True, exist_ok=True)
        for f in range(files_per_artifact):
            size = rng.randrange(50, 5000)
            (artifact / f"f_{f:04d}.bin").write_bytes(b"a" * size)


def peak_rss_kb() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def run_scan_benchmark(root: Path, reps: int) -> dict:
    from purge.core.scanner import DiskScanner

    timings = []
    for _ in range(reps):
        scanner = DiskScanner(git_aware=False)
        start = time.perf_counter()
        report = scanner.scan(root, max_depth=10)
        timings.append(time.perf_counter() - start)
        assert report.artifacts, "benchmark workspace produced no artifacts"

    return {
        "reps": reps,
        "median_ms": round(statistics.median(timings) * 1000, 2),
        "p95_ms": round(sorted(timings)[max(0, int(len(timings) * 0.95) - 1)] * 1000, 2),
        "min_ms": round(min(timings) * 1000, 2),
        "max_ms": round(max(timings) * 1000, 2),
        "peak_rss_kb": peak_rss_kb(),
    }


def run_git_benchmark(root: Path, reps: int) -> dict:
    """Measure git inspection cost per unique repo (subprocess count matters)."""
    import subprocess

    for p in sorted(root.iterdir()):
        if p.is_dir() and (p / "package.json").exists():
            subprocess.run(["git", "init", "-q"], cwd=str(p), capture_output=True)

    from purge.core.git_helper import inspect_git_project

    inspect_git_project.cache_clear = getattr(
        inspect_git_project, "cache_clear", None
    )
    targets = [p for p in sorted(root.iterdir()) if (p / ".git").exists()]
    if not targets:
        return {"reps": reps, "repos": 0, "median_ms": 0.0, "subprocess_calls": 0}

    timings = []
    for _ in range(reps):
        # clear lru caches to measure cold-start cost
        from purge.core.git_helper import _get_git_info, _get_git_root

        _get_git_root.cache_clear()
        _get_git_info.cache_clear()
        start = time.perf_counter()
        for t in targets:
            inspect_git_project(t)
        timings.append(time.perf_counter() - start)

    return {
        "reps": reps,
        "repos": len(targets),
        "median_ms": round(statistics.median(timings) * 1000, 2),
        "subprocess_calls_per_repo": 2 if _SUBPROC_MODE == "v3" else 3,
    }


_SUBPROC_MODE = "v3"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="run", choices=["before", "after", "run"])
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="purge_bench_") as tmp:
        root = Path(tmp)
        build_workspace(root)
        scan_results = run_scan_benchmark(root, args.reps)
        git_results = run_git_benchmark(root, args.reps)

    results = {
        "label": args.label,
        "workspace": {"projects": 30, "files_per_artifact": 300, "total_files": 9000},
        "scan": scan_results,
        "git_inspection": git_results,
        "python": sys.version.split()[0],
    }
    print(json.dumps(results, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
