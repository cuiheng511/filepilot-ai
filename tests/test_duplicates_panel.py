from datetime import datetime

from PySide6.QtCore import Qt

from filepilot.core.file_scanner import FileInfo
from filepilot.ui.duplicates_panel import DuplicatesPanel
from filepilot.utils.file_utils import FileCategory


def _file_info(path, size=10):
    return FileInfo(
        path=path,
        name=path.name,
        extension=path.suffix,
        size_bytes=size,
        size_str=f"{size} B",
        category=FileCategory.DOCUMENT,
        mime_type="text/plain",
        modified_time=datetime(2026, 1, 1, 12, 0),
        created_time=datetime(2026, 1, 1, 12, 0),
    )


def test_duplicate_group_kept_file_is_not_preselected_for_deletion(qtbot, tmp_path):
    panel = DuplicatesPanel()
    qtbot.addWidget(panel)

    kept = _file_info(tmp_path / "kept.txt")
    duplicate = _file_info(tmp_path / "duplicate.txt")

    panel._display_results([[kept, duplicate]], [], [kept, duplicate])

    group = panel.result_tree.topLevelItem(0)
    kept_item = group.child(0)
    duplicate_item = group.child(1)

    assert kept_item.checkState(0) == Qt.Unchecked
    assert not kept_item.flags() & Qt.ItemIsUserCheckable
    assert duplicate_item.checkState(0) == Qt.Unchecked
    assert duplicate_item.flags() & Qt.ItemIsUserCheckable
    assert panel._get_checked_paths() == []
