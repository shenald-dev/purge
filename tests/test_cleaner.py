from purge.core.cleaner import PurgeCleaner
from purge.core.models import Artifact


def test_cleaner_dry_run(tmp_path):
    f = tmp_path / "node_modules"
    f.mkdir()
    (f / "lib.js").write_text("code")

    art = Artifact(path=f, category="Node.js & Web", size_bytes=100)
    cleaner = PurgeCleaner(dry_run=True)
    res = cleaner.purge([art])

    assert res.reclaimed_bytes == 100
    assert res.deleted_artifacts_count == 1
    # File must still exist in dry-run
    assert f.exists()


def test_cleaner_actual_deletion(tmp_path):
    f = tmp_path / ".venv"
    f.mkdir()
    (f / "pyvenv.cfg").write_text("home = ...")

    art = Artifact(path=f, category="Python", size_bytes=50)
    cleaner = PurgeCleaner(dry_run=False)
    res = cleaner.purge([art])

    assert res.reclaimed_bytes == 50
    assert res.deleted_artifacts_count == 1
    # File must be permanently deleted
    assert not f.exists()


def test_cleaner_protects_git_and_system(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main")

    art = Artifact(path=git_dir, category="Git", size_bytes=1000)
    cleaner = PurgeCleaner(dry_run=False)
    res = cleaner.purge([art])

    # Should not delete protected path
    assert res.deleted_artifacts_count == 0
    assert git_dir.exists()
    assert len(res.errors) == 1
    assert "Protected path" in res.errors[0]


def test_cleaner_nonexistent_path(tmp_path):
    missing_path = tmp_path / "does_not_exist"
    art = Artifact(path=missing_path, category="Unknown", size_bytes=500)

    cleaner = PurgeCleaner(dry_run=False)
    res = cleaner.purge([art])

    assert res.deleted_artifacts_count == 0
    assert res.reclaimed_bytes == 0
    assert len(res.errors) == 1
    assert "no longer exists" in res.errors[0]
