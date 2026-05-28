"""Tests for tag cloud widget and flow layout."""

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QLabel, QWidget

from filepilot.ui.tag_cloud import FlowLayout, TagCloudWidget


class FakeTagManager:
    def __init__(self, data):
        self._data = data

    def get_tagged_files(self):
        return self._data


def test_tag_cloud_refresh_builds_clickable_labels(qtbot):
    manager = FakeTagManager(
        {
            "a.txt": {"tags": ["work", "urgent"]},
            "b.txt": {"tags": ["work"]},
        }
    )
    widget = TagCloudWidget(tag_manager=manager)
    qtbot.addWidget(widget)

    widget.refresh()

    assert len(widget._tag_labels) == 2
    assert any("work (2)" in label.text() for label in widget._tag_labels)
    assert any(label.accessibleName() == "work, 2 files" for label in widget._tag_labels)


def test_tag_cloud_refresh_clears_old_layout_items(qtbot):
    manager = FakeTagManager({"a.txt": {"tags": ["old"]}})
    widget = TagCloudWidget(tag_manager=manager)
    qtbot.addWidget(widget)

    widget.refresh()
    manager._data = {"b.txt": {"tags": ["new"]}}
    widget.refresh()

    assert len(widget._tag_labels) == 1
    assert "new (1)" in widget._tag_labels[0].text()


def test_flow_layout_wraps_without_manual_container(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    layout = FlowLayout(parent)
    parent.setLayout(layout)
    for i in range(5):
        layout.addWidget(QLabel(f"tag-{i}"))

    layout.setGeometry(QRect(0, 0, 80, 200))

    assert layout.count() == 5
    assert layout.heightForWidth(80) > 0
