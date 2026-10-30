import os

from purge.core.cleaner import PurgeCleaner
from purge.core.models import Artifact


def test_cleaner_symlink_preserves_target(tmp_path):
    target = tmp_path / "target_dir"
    target.mkdir()
    (target / "file.txt").write_text("hello")

    link = tmp_path / "node_modules"
    os.symlink(target, link)

    art = Artifact(path=link, category="Node.js & Web", size_bytes=100)
    cleaner = PurgeCleaner(dry_run=False)
    res = cleaner.purge([art])

    assert res.deleted_artifacts_count == 1

    # The symlink should be deleted
    assert not link.exists()
    assert not link.is_symlink()

    # The target directory should STILL exist and be untouched!
    assert target.exists()
    assert (target / "file.txt").exists()
