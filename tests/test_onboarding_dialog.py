"""Tests for the first-run onboarding dialog."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QDialog

from filepilot.ui.onboarding_dialog import OnboardingDialog


def test_skip_completes_onboarding(qtbot):
    dialog = OnboardingDialog()
    qtbot.addWidget(dialog)

    completed = []
    dialog.completed.connect(lambda: completed.append(True))

    dialog.skip_button.click()

    assert completed == [True]
    assert dialog.result() == QDialog.Accepted


def test_open_folder_button_emits_request(qtbot):
    dialog = OnboardingDialog()
    qtbot.addWidget(dialog)

    completed = []
    requests = []
    dialog.completed.connect(lambda: completed.append(True))
    dialog.open_folder_requested.connect(lambda: requests.append(True))

    dialog.open_folder_button.click()
    qtbot.waitUntil(lambda: requests == [True], timeout=1000)

    assert completed == [True]
    assert requests == [True]


def test_open_settings_button_emits_request(qtbot):
    dialog = OnboardingDialog()
    qtbot.addWidget(dialog)

    completed = []
    requests = []
    dialog.completed.connect(lambda: completed.append(True))
    dialog.open_settings_requested.connect(lambda: requests.append(True))

    dialog.settings_button.click()
    qtbot.waitUntil(lambda: requests == [True], timeout=1000)

    assert completed == [True]
    assert requests == [True]
