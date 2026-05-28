"""Tests for filepilot.ui.preview_panel — async file preview"""

from filepilot.ui.preview_panel import PreviewPanel


def test_preview_panel_init(qtbot):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    assert panel is not None


def test_preview_starts_empty(qtbot):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    assert panel._current_preview_path is None


def test_clear_preview(qtbot):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    panel.clear()
    assert panel._current_preview_path is None


def test_stale_preview_result_is_ignored(qtbot, tmp_path):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    current = tmp_path / "current.txt"
    stale = tmp_path / "stale.txt"
    panel._current_preview_path = str(current)

    panel._on_preview_ready("<b>stale</b>", str(stale))

    assert "stale" not in panel.text_preview.toPlainText()


def test_zip_archive_preview_lists_entries(qtbot, tmp_path):
    import zipfile

    panel = PreviewPanel()
    qtbot.addWidget(panel)
    archive = tmp_path / "files.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("note.txt", "hello")

    assert panel._try_preview_archive(archive)
    assert panel.archive_list.count() >= 3
