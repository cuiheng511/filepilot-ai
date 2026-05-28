"""Tests for shared file operation service."""

from filepilot.core.file_operations import FileOperationService


def test_copy_renames_conflicting_destination(tmp_path):
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    src.mkdir()
    dest.mkdir()
    source_file = src / "report.txt"
    source_file.write_text("new", encoding="utf-8")
    (dest / "report.txt").write_text("existing", encoding="utf-8")

    result = FileOperationService().copy([source_file], dest)

    assert result.success_count == 1
    assert result.renamed_count == 1
    assert (dest / "report.txt").read_text(encoding="utf-8") == "existing"
    assert (dest / "report_1.txt").read_text(encoding="utf-8") == "new"


def test_move_records_successful_destination_for_undo(tmp_path):
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    src.mkdir()
    dest.mkdir()
    source_file = src / "report.txt"
    source_file.write_text("new", encoding="utf-8")

    result = FileOperationService().move([source_file], dest)

    assert result.success_count == 1
    assert result.successful_operations[0].source == source_file
    assert result.successful_operations[0].destination == dest / "report.txt"
    assert not source_file.exists()
    assert (dest / "report.txt").exists()


def test_batch_plan_reserves_future_destinations(tmp_path):
    src_a = tmp_path / "a" / "same.txt"
    src_b = tmp_path / "b" / "same.txt"
    dest = tmp_path / "dest"
    src_a.parent.mkdir()
    src_b.parent.mkdir()
    dest.mkdir()
    src_a.write_text("a", encoding="utf-8")
    src_b.write_text("b", encoding="utf-8")

    result = FileOperationService().copy([src_a, src_b], dest)

    assert result.success_count == 2
    assert (dest / "same.txt").read_text(encoding="utf-8") == "a"
    assert (dest / "same_1.txt").read_text(encoding="utf-8") == "b"


def test_copy_directory(tmp_path):
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    folder = src / "folder"
    folder.mkdir(parents=True)
    dest.mkdir()
    (folder / "note.txt").write_text("hello", encoding="utf-8")

    result = FileOperationService().copy([folder], dest)

    assert result.success_count == 1
    assert (dest / "folder" / "note.txt").read_text(encoding="utf-8") == "hello"
