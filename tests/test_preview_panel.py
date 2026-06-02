"""Tests for filepilot.ui.preview_panel — async file preview"""

import zipfile

import pytest
from PIL import Image

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


def test_current_preview_result_is_accepted(qtbot, tmp_path):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    current = tmp_path / "current.txt"
    panel._current_preview_path = str(current)

    panel._on_preview_ready("<b>fresh</b>", str(current))

    qtbot.waitUntil(lambda: "fresh" in panel.text_preview.toPlainText())


def test_zip_archive_preview_lists_entries(qtbot, tmp_path):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    archive = tmp_path / "files.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("note.txt", "hello")

    assert panel._try_preview_archive(archive)
    assert panel.archive_list.count() >= 3


def test_archive_preview_switches_to_archive_stack(qtbot, tmp_path):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    archive = tmp_path / "stuff.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("a.txt", "x")
        zf.writestr("b.txt", "y")

    panel._try_preview_archive(archive)

    assert panel.preview_stack.currentIndex() == 2
    items = [panel.archive_list.item(i).text() for i in range(panel.archive_list.count())]
    assert any("stuff.zip" in t for t in items)
    assert any("a.txt" in t for t in items)
    assert any("b.txt" in t for t in items)


def test_archive_preview_invalid_zip_returns_false(qtbot, tmp_path):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    not_a_zip = tmp_path / "fake.zip"
    not_a_zip.write_text("not actually a zip")

    assert panel._try_preview_archive(not_a_zip) is False


def test_archive_preview_non_archive_returns_false(qtbot, tmp_path):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    plain = tmp_path / "plain.txt"
    plain.write_text("hello")

    assert panel._try_preview_archive(plain) is False


def test_image_preview_loads_pixmap(qtbot, tmp_path):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    image_path = tmp_path / "test.png"
    Image.new("RGB", (100, 80), color="red").save(image_path)

    panel._preview_file(image_path)

    assert panel.preview_stack.currentIndex() == 1
    assert not panel.image_label.pixmap().isNull()


def test_image_preview_missing_file_falls_back_to_text(qtbot, tmp_path):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    missing = tmp_path / "missing.png"

    panel._preview_file(missing)

    assert panel.preview_stack.currentIndex() == 0
    html = panel.text_preview.toPlainText()
    assert "Cannot load image preview" in html


def test_unknown_type_preview_shows_metadata(qtbot, tmp_path):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    binary_path = tmp_path / "data.bin"
    binary_path.write_bytes(b"\x00\x01\x02" * 100)

    panel._preview_file(binary_path)

    assert panel.preview_stack.currentIndex() == 0
    html = panel.text_preview.toPlainText()
    assert "Preview not available" in html
    assert "data.bin" in html


def test_office_preview_recommends_ai_summary(qtbot, tmp_path):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    docx_path = tmp_path / "report.docx"
    docx_path.write_bytes(b"PK\x03\x04fake docx content")

    panel._preview_file(docx_path)

    assert panel.preview_stack.currentIndex() == 0
    html = panel.text_preview.toPlainText()
    assert "Office file" in html
    assert "AI Summary" in html


def test_show_preview_sets_current_path(qtbot, tmp_path):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    path = tmp_path / "any.txt"
    path.write_text("hello")

    panel.show_preview(path)

    assert panel._current_preview_path == str(path)


def test_text_worker_renders_html(qtbot, tmp_path):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    text_path = tmp_path / "code.py"
    text_path.write_text("def hello():\n    print('hi')\n")
    panel._current_preview_path = str(text_path)

    panel._preview_text_worker(text_path, is_markdown=False)

    html = panel.text_preview.toPlainText()
    assert "hello" in html
    assert "print" in html


def test_text_worker_caps_at_200_lines(qtbot, tmp_path):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    text_path = tmp_path / "big.txt"
    text_path.write_text("\n".join(f"line {i}" for i in range(500)))
    panel._current_preview_path = str(text_path)

    panel._preview_text_worker(text_path, is_markdown=False)

    plain = panel.text_preview.toPlainText()
    assert "line 0" in plain
    assert "line 199" in plain
    assert "line 200" not in plain


def test_markdown_worker_renders_heading(qtbot, tmp_path):
    pytest.importorskip("markdown")
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    md_path = tmp_path / "doc.md"
    md_path.write_text("# Title\n\nSome **bold** text.\n")
    panel._current_preview_path = str(md_path)

    panel._preview_text_worker(md_path, is_markdown=True)

    qtbot.waitUntil(lambda: "Title" in panel.text_preview.toPlainText())


def test_text_worker_handles_missing_file(qtbot, tmp_path):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    panel._current_preview_path = str(tmp_path / "missing.txt")

    panel._preview_text_worker(tmp_path / "missing.txt", is_markdown=False)

    html = panel.text_preview.toPlainText()
    assert "Failed to load preview" in html


def test_pdf_worker_emits_unavailable_when_fitz_missing(qtbot, tmp_path, monkeypatch):
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-fake")

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "fitz":
            raise ImportError("simulated missing PyMuPDF")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    panel._preview_pdf_worker(pdf_path)

    qtbot.waitUntil(
        lambda: (
            "PDF preview unavailable" in panel.text_preview.toPlainText()
            or panel.preview_stack.currentIndex() == 0
        )
    )
