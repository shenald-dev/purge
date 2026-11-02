from purge.core import history
from purge.core.models import CleanResult


def test_record_clean_event(tmp_path, monkeypatch):
    test_hist_file = tmp_path / "history.json"
    monkeypatch.setattr(history, "HISTORY_DIR", tmp_path)
    monkeypatch.setattr(history, "HISTORY_FILE", test_hist_file)

    # Initial stats should be empty
    stats = history.get_lifetime_stats()
    assert stats["total_reclaimed_bytes"] == 0
    assert stats["total_purges_run"] == 0

    # Record first clean event
    r1 = CleanResult(
        reclaimed_bytes=1048576 * 50,  # 50 MB
        deleted_artifacts_count=5,
        slain_zombies_count=2,
        duration_seconds=1.2,
    )
    res1 = history.record_clean_event(r1)
    assert res1["total_reclaimed_bytes"] == 1048576 * 50
    assert res1["total_purges_run"] == 1
    assert res1["total_artifacts_deleted"] == 5
    assert res1["total_zombies_slayed"] == 2
    assert len(res1["recent_events"]) == 1

    # Record second clean event
    r2 = CleanResult(
        reclaimed_bytes=1048576 * 25,  # 25 MB
        deleted_artifacts_count=3,
        slain_zombies_count=0,
        duration_seconds=0.8,
    )
    res2 = history.record_clean_event(r2)
    assert res2["total_reclaimed_bytes"] == 1048576 * 75
    assert res2["total_purges_run"] == 2
    assert res2["total_artifacts_deleted"] == 8
    assert res2["total_zombies_slayed"] == 2
    assert len(res2["recent_events"]) == 2


def test_record_empty_event_does_nothing(tmp_path, monkeypatch):
    test_hist_file = tmp_path / "history.json"
    monkeypatch.setattr(history, "HISTORY_DIR", tmp_path)
    monkeypatch.setattr(history, "HISTORY_FILE", test_hist_file)

    empty_res = CleanResult(reclaimed_bytes=0, slain_zombies_count=0)
    res = history.record_clean_event(empty_res)
    assert res["total_purges_run"] == 0
    assert not test_hist_file.exists()
