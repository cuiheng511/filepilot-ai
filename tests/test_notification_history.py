"""Tests for notification history widget."""

from filepilot.ui.notification_history import NotificationHistory


def test_records_and_clears_notifications(qtbot):
    widget = NotificationHistory()
    qtbot.addWidget(widget)

    assert widget.accessibleName() == "Notifications"
    widget.record("Saved settings", "success")
    widget.record("Network failed", "error")

    assert widget.entry_count() == 2
    assert widget.list_widget.count() == 2
    assert widget.count_label.text() == "2"

    widget.clear()

    assert widget.entry_count() == 0
    assert widget.list_widget.count() == 0
    assert widget.count_label.text() == "0"


def test_notification_history_trims_old_entries(qtbot):
    widget = NotificationHistory()
    qtbot.addWidget(widget)
    widget.MAX_ENTRIES = 2

    widget.record("one")
    widget.record("two")
    widget.record("three")

    assert widget.entry_count() == 2
    assert widget.entries[0]["text"] == "two"
    assert widget.entries[1]["text"] == "three"
