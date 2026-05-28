"""Tests for file operation history snapshots."""

from filepilot.core.file_snapshot import FileSnapshot


def test_records_move_and_finds_previous_location(tmp_path):
    db_path = tmp_path / "history.db"
    destination = tmp_path / "dest.txt"
    destination.write_text("hello", encoding="utf-8")
    snapshot = FileSnapshot(db_path)

    snapshot.record_move(tmp_path / "src.txt", destination)
    rows = snapshot.find_previous_location("src.txt")

    assert snapshot.count() == 1
    assert rows[0]["operation"] == "move"
    assert rows[0]["dest_path"] == str(destination)
    assert rows[0]["file_size"] == 5


def test_records_delete_and_clear(tmp_path):
    snapshot = FileSnapshot(tmp_path / "history.db")

    snapshot.record_delete(tmp_path / "gone.txt", file_size=123)

    deletions = snapshot.get_deletions()
    assert deletions[0]["operation"] == "delete"
    assert deletions[0]["file_size"] == 123

    snapshot.clear()
    assert snapshot.count() == 0


def test_prunes_old_entries(tmp_path):
    snapshot = FileSnapshot(tmp_path / "history.db")
    snapshot.MAX_ENTRIES = 3

    for i in range(5):
        snapshot.record_delete(tmp_path / f"{i}.txt", file_size=i)

    assert snapshot.count() == 3
    recent_names = {row["file_name"] for row in snapshot.get_recent(limit=10)}
    assert recent_names == {"2.txt", "3.txt", "4.txt"}
