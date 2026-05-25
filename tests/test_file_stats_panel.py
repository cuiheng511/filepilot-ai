"""Tests for filepilot.ui.file_stats_panel — distribution analysis & treemap"""

from filepilot.ui.file_stats_panel import FileStatsPanel, TreemapWidget


def test_file_stats_panel_init(qtbot):
    panel = FileStatsPanel()
    qtbot.addWidget(panel)
    assert panel is not None


def test_set_current_dir(qtbot):
    panel = FileStatsPanel()
    qtbot.addWidget(panel)
    panel.set_current_dir("C:\\test")
    assert panel.current_dir == "C:\\test"


def test_set_current_dir_none(qtbot):
    panel = FileStatsPanel()
    qtbot.addWidget(panel)
    panel.set_current_dir(None)
    assert panel.current_dir is None


def test_treemap_widget_init(qtbot):
    widget = TreemapWidget()
    qtbot.addWidget(widget)
    assert widget is not None


def test_treemap_set_data(qtbot):
    widget = TreemapWidget()
    qtbot.addWidget(widget)
    data = [("Documents", 100, "#4a9eff"), ("Images", 200, "#f5a623"), ("Code", 50, "#2ecc71")]
    widget.set_data(data)
    assert len(widget.data) == 3


def test_treemap_set_empty_data(qtbot):
    widget = TreemapWidget()
    qtbot.addWidget(widget)
    widget.set_data([])
    assert widget.data == []


def test_treemap_update(qtbot):
    widget = TreemapWidget()
    qtbot.addWidget(widget)
    widget.set_data([("A", 100, "#ff0000")])
    widget.set_data([("B", 200, "#00ff00")])
    assert len(widget.data) == 1
    assert widget.data[0][0] == "B"
