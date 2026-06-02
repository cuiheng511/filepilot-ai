import runpy
import sys
import types
from pathlib import Path

import pytest

import filepilot.main as main_module


class FakeApp:
    def __init__(self, exit_code: int = 0):
        self.exit_code = exit_code
        self.exec_called = False

    def exec(self) -> int:
        self.exec_called = True
        return self.exit_code


class FakeGeometry:
    def __init__(self):
        self._x = 10
        self._y = 20
        self._width = 1200
        self._height = 800

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height


class FakeScreen:
    def availableGeometry(self) -> FakeGeometry:
        return FakeGeometry()


class FakeQApplication:
    screen = FakeScreen()

    @classmethod
    def primaryScreen(cls):
        return cls.screen


class FakeTray:
    def __init__(self):
        self.shown = False

    def show(self) -> None:
        self.shown = True


class FakeWindow:
    instances: list["FakeWindow"] = []

    def __init__(self, services):
        self.services = services
        self.tray_manager = None
        self.shown = False
        self.hidden = False
        self.moves: list[tuple[int, int]] = []
        self._notify = object()
        FakeWindow.instances.append(self)

    def show(self) -> None:
        self.shown = True

    def hide(self) -> None:
        self.hidden = True

    def width(self) -> int:
        return 400

    def height(self) -> int:
        return 300

    def move(self, x: int, y: int) -> None:
        self.moves.append((x, y))


def install_main_fakes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    settings: dict,
    exit_code: int = 0,
    screen: FakeScreen | None = None,
    screen_available: bool = True,
) -> dict:
    calls: dict = {}
    fake_app = FakeApp(exit_code)
    fake_tray = FakeTray()
    fake_services = object()
    FakeWindow.instances.clear()

    monkeypatch.setattr(main_module.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(
        main_module,
        "setup_logging",
        lambda log_file: calls.setdefault("log_file", log_file),
    )
    FakeQApplication.screen = (
        (FakeScreen() if screen is None else screen) if screen_available else None
    )
    monkeypatch.setattr(main_module, "QApplication", FakeQApplication)

    fake_i18n = types.ModuleType("filepilot.i18n")
    fake_i18n.load_language_from_settings = lambda: calls.setdefault("language_loaded", True)
    monkeypatch.setitem(sys.modules, "filepilot.i18n", fake_i18n)

    fake_filepilot_app = types.ModuleType("filepilot.app")
    fake_filepilot_app.create_app = lambda: fake_app
    fake_filepilot_app.load_settings = lambda: settings
    fake_filepilot_app.create_service_container = lambda loaded_settings: (
        calls.setdefault("settings", loaded_settings),
        fake_services,
    )[1]
    fake_filepilot_app.create_tray_from_container = lambda window, services, notify: (
        calls.setdefault("tray_args", (window, services, notify)),
        fake_tray,
    )[1]
    monkeypatch.setitem(sys.modules, "filepilot.app", fake_filepilot_app)

    fake_main_window = types.ModuleType("filepilot.ui.main_window")
    fake_main_window.MainWindow = FakeWindow
    monkeypatch.setitem(sys.modules, "filepilot.ui.main_window", fake_main_window)

    return {"calls": calls, "app": fake_app, "tray": fake_tray, "services": fake_services}


def test_main_shows_and_centers_window_when_not_start_minimized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    state = install_main_fakes(
        monkeypatch,
        tmp_path,
        settings={"start_minimized": False},
        exit_code=7,
    )

    with pytest.raises(SystemExit) as exc_info:
        main_module.main()

    window = FakeWindow.instances[-1]
    assert exc_info.value.code == 7
    assert state["calls"]["log_file"] == str(tmp_path / ".filepilot" / "logs" / "filepilot.log")
    assert state["calls"]["language_loaded"] is True
    assert state["calls"]["settings"] == {"start_minimized": False}
    assert state["tray"].shown is True
    assert window.tray_manager is state["tray"]
    assert window.shown is True
    assert window.hidden is False
    assert window.moves == [(410, 270)]
    assert state["app"].exec_called is True


def test_main_hides_window_when_start_minimized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    state = install_main_fakes(
        monkeypatch,
        tmp_path,
        settings={"start_minimized": True},
    )

    with pytest.raises(SystemExit) as exc_info:
        main_module.main()

    window = FakeWindow.instances[-1]
    assert exc_info.value.code == 0
    assert state["tray"].shown is True
    assert window.shown is False
    assert window.hidden is True
    assert window.moves == []


def test_main_skips_centering_when_primary_screen_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    install_main_fakes(
        monkeypatch,
        tmp_path,
        settings={"start_minimized": False},
        screen_available=False,
    )

    with pytest.raises(SystemExit):
        main_module.main()

    window = FakeWindow.instances[-1]
    assert window.shown is True
    assert window.moves == []


def test_python_m_filepilot_delegates_to_cli_main(monkeypatch: pytest.MonkeyPatch):
    calls = []

    import filepilot.cli

    monkeypatch.setattr(filepilot.cli, "main", lambda: calls.append("called"))

    runpy.run_module("filepilot.__main__", run_name="__main__")

    assert calls == ["called"]
