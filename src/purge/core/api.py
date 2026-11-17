"""Headless reclamation engine for purge.

PurgeEngine is the single programmatic facade over scan, inspection,
cleaning, quarantine, zombie hunting, and telemetry. It powers both the
CLI and the MCP server, keeping all product intelligence callable from
Python without a terminal attached.
"""

from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union

from purge.core.config import PurgeConfig, load_config
from purge.core.models import Artifact, CleanResult, PurgeReport, parse_size_to_bytes
from purge.core.zombies import find_zombies, get_process_on_port

CategorySpec = Optional[Union[str, List[str]]]


def _resolve_categories(spec: CategorySpec, config: PurgeConfig) -> Optional[List[str]]:
    """Merge CLI-style category flags with configured categories."""
    if spec is None:
        return config.categories
    if isinstance(spec, str):
        spec = [spec]
    return list(dict.fromkeys(spec))


def _as_positive(value: float, fallback: float) -> float:
    """Pick an explicitly provided positive option over the configured fallback."""
    return value if value and value > 0 else fallback


class PurgeEngine:
    """Programmatic access to every purge capability without the CLI.

    The engine intentionally mirrors CLI semantics (defaults, filters,
    safety rules) so that scripts, CI pipelines, and MCP hosts observe
    exactly the same behavior as interactive users.
    """

    def __init__(
        self,
        root_path: Optional[Union[str, Path]] = None,
        config: Optional[PurgeConfig] = None,
        config_path: Optional[Path] = None,
        vault_root: Optional[Path] = None,
    ):
        self.root_path = Path(root_path) if root_path is not None else Path.cwd()
        self.config = config if config is not None else load_config(config_path or self.root_path)
        self._vault_root = vault_root

    # ------------------------------------------------------------------
    # Scanning & inspection
    # ------------------------------------------------------------------

    def scan(
        self,
        path: Optional[Union[str, Path]] = None,
        categories: CategorySpec = None,
        min_stale_days: Optional[float] = None,
        min_size: Optional[Union[str, int]] = None,
        min_score: Optional[float] = None,
        sort_by: Optional[str] = None,
        top: Optional[int] = None,
        git_aware: Optional[bool] = None,
        max_depth: Optional[int] = None,
        include_global_caches: bool = False,
        ignore_paths: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> PurgeReport:
        """Scan a directory tree and return a structured PurgeReport.

        Size filters accept either raw byte counts or human strings like
        '50MB' / '1.5GB', matching the CLI --min-size grammar.
        """
        from purge.core.scanner import DiskScanner

        target = Path(path) if path is not None else self.root_path

        if isinstance(min_size, str):
            min_size_bytes = parse_size_to_bytes(min_size)
        else:
            min_size_bytes = min_size if min_size is not None else self.config.min_size_bytes

        effective_categories = _resolve_categories(categories, self.config)
        effective_stale = (
            min_stale_days if min_stale_days is not None and min_stale_days > 0
            else self.config.min_stale_days
        )
        effective_score = min_score if min_score is not None else self.config.min_score
        effective_git = git_aware if git_aware is not None else self.config.git_aware
        effective_sort = sort_by if sort_by is not None else self.config.sort_by
        effective_depth = max_depth if max_depth is not None else self.config.max_depth

        ignores = list(self.config.ignore_paths)
        if ignore_paths:
            ignores.extend(ignore_paths)

        scanner = DiskScanner(
            categories=effective_categories,
            min_stale_days=effective_stale,
            min_size_bytes=min_size_bytes,
            min_score=effective_score,
            sort_by=effective_sort,
            top=top,
            git_aware=effective_git,
            custom_rules=self.config.custom_rules,
            ignore_paths=ignores,
            progress_callback=progress_callback,
        )
        return scanner.scan(
            target,
            max_depth=effective_depth,
            include_global_caches=include_global_caches,
        )

    def inspect(self, path: Union[str, Path]) -> dict:
        """Inspect a single artifact candidate without a full scan.

        Returns the artifact's size, staleness, category, and purge score
        as a plain dictionary. Never deletes anything.
        """
        from purge.core.rules import identify_artifact_category
        from purge.core.scanner import get_path_stats
        from purge.core.scoring import calculate_purge_score

        target = Path(path)
        stats = get_path_stats(target)
        bytes_size, file_count, last_mod, days_stale = stats

        parent = target.parent if target.is_dir() else target.parent
        category = identify_artifact_category(
            target.name, parent, custom_rules=self.config.custom_rules
        )

        git_aware = self.config.git_aware
        is_git = False
        has_uncommitted = False
        days_since_commit = 0.0
        if git_aware:
            from purge.core.git_helper import inspect_git_project

            git_info = inspect_git_project(target.parent)
            is_git = git_info.is_git
            has_uncommitted = git_info.has_uncommitted
            days_since_commit = git_info.days_since_last_commit

        score_info = calculate_purge_score(
            size_bytes=bytes_size,
            days_stale=days_stale,
            category=category or "Unknown",
            artifact_name=target.name,
            is_git_repo=is_git,
            has_uncommitted=has_uncommitted,
            days_since_commit=days_since_commit,
        )

        return {
            "path": str(target),
            "category": category,
            "size_bytes": bytes_size,
            "human_size": _human_size(bytes_size),
            "file_count": file_count,
            "days_stale": round(days_stale, 1),
            "last_modified": last_mod.isoformat() if last_mod else None,
            "is_git_repo": is_git,
            "has_uncommitted": has_uncommitted,
            "days_since_commit": round(days_since_commit, 1) if is_git else None,
            "purge_score": score_info.total_score,
            "safety_level": score_info.safety_level.value,
            "score_recommendation": score_info.recommendation,
        }

    # ------------------------------------------------------------------
    # Cleaning
    # ------------------------------------------------------------------

    def clean(
        self,
        artifacts: Optional[List[Artifact]] = None,
        path: Optional[Union[str, Path]] = None,
        scan_kwargs: Optional[dict] = None,
        dry_run: bool = False,
        to_trash: bool = False,
        to_vault: bool = False,
        vault_root: Optional[Path] = None,
        workers: Optional[int] = None,
        record_history: bool = True,
        skip_uncommitted: bool = False,
        auto_min_score: Optional[float] = None,
        zombies: Optional[List] = None,
        kill_zombies: bool = False,
    ) -> CleanResult:
        """Clean discovered artifacts, quarantining or deleting them.

        Pass an explicit ``artifacts`` list (from scan()) for precise
        control, or let the engine scan ``path`` itself using
        ``scan_kwargs`` (same grammar as engine.scan).
        """
        from purge.core.cleaner import PurgeCleaner

        if artifacts is None:
            report = self.scan(path=path, **(scan_kwargs or {}))
            artifacts = report.artifacts

        if skip_uncommitted:
            artifacts = [a for a in artifacts if not a.has_uncommitted]

        if auto_min_score is not None:
            artifacts = [
                a for a in artifacts
                if getattr(a, "purge_score", 0.0) >= auto_min_score and not a.has_uncommitted
            ]

        if kill_zombies:
            zombies = find_zombies() if zombies is None else zombies
        else:
            zombies = []

        effective_vault_root = vault_root if vault_root is not None else self._vault_root
        cleaner = PurgeCleaner(
            dry_run=dry_run,
            to_trash=to_trash or self.config.default_trash,
            to_vault=to_vault or self.config.default_vault,
            vault_root=effective_vault_root,
            record_history=record_history,
            workers=workers if workers is not None else self.config.workers,
        )
        result = cleaner.purge(artifacts, zombies=zombies)

        # Remember the vault root used so subsequent vault_* calls on this
        # engine address the same vault (quarantine then restore round-trip).
        if to_vault and effective_vault_root is not None:
            self._vault_root = effective_vault_root

        return result

    # ------------------------------------------------------------------
    # Global caches, zombies, ports, telemetry
    # ------------------------------------------------------------------

    def scan_global_caches(self) -> List[Artifact]:
        """List global package-manager caches with sizes and scores."""
        from purge.core.scanner import DiskScanner

        return DiskScanner(
            custom_rules=self.config.custom_rules,
            ignore_paths=self.config.ignore_paths,
            max_workers=self.config.workers if self.config.workers else 8,
        ).scan_global_caches()

    def find_zombies(self, target_port: Optional[int] = None) -> List:
        """Detect zombie dev servers and port hogs."""
        return find_zombies(target_port=target_port)

    def get_process_on_port(self, port: int):
        """Return the process occupying a port, if any."""
        return get_process_on_port(port)

    def kill_zombie_tree(self, pid: int) -> int:
        """Terminate a process and all children. Returns processes slain."""
        from purge.core.zombies import kill_zombie_tree

        return kill_zombie_tree(pid)

    def stats(self) -> dict:
        """Lifetime reclamation telemetry."""
        from purge.core.history import get_lifetime_stats

        return get_lifetime_stats()

    # ------------------------------------------------------------------
    # Quarantine vault
    # ------------------------------------------------------------------

    def vault_list_sessions(self) -> List:
        """List quarantine vault sessions."""
        from purge.core.vault import QuarantineVault

        return QuarantineVault(vault_root=self._vault_root).list_sessions()

    def vault_get_session(self, vault_id: str):
        """Fetch a vault session by ID."""
        from purge.core.vault import QuarantineVault

        return QuarantineVault(vault_root=self._vault_root).get_session(vault_id)

    def vault_restore(self, vault_id: str, item_index: Optional[int] = None) -> Tuple[int, int, List[str]]:
        """Restore quarantined items. Returns (count, bytes, errors)."""
        from purge.core.vault import QuarantineVault

        return QuarantineVault(vault_root=self._vault_root).restore_session(vault_id, item_index=item_index)

    def vault_prune(self, older_than_days: float = 14.0, vault_id: Optional[str] = None) -> Tuple[int, int]:
        """Delete old vault sessions. Returns (sessions, bytes)."""
        from purge.core.vault import QuarantineVault

        return QuarantineVault(vault_root=self._vault_root).prune_vault(older_than_days=older_than_days, vault_id=vault_id)


def _human_size(num_bytes: float) -> str:
    from purge.core.models import format_bytes

    return format_bytes(num_bytes)
