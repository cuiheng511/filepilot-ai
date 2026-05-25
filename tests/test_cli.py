"""Tests for filepilot.cli — CLI subcommands"""

import json
import sys

import pytest

from filepilot.cli import _fmt, cmd_disk_usage, main


def test_fmt():
    assert _fmt(0) == "0.0 B"
    assert _fmt(500) == "500.0 B"
    assert _fmt(1024) == "1.0 KB"
    assert _fmt(1048576) == "1.0 MB"
    assert _fmt(1073741824) == "1.0 GB"
    assert _fmt(1099511627776) == "1.0 TB"


def test_disk_usage_nonexistent_path(capsys):
    cmd_disk_usage(_Args(path="/nonexistent_path_xyz"))
    captured = capsys.readouterr()
    assert "Path does not exist" in captured.err


def test_disk_usage_empty_dir(tmp_path, capsys):
    cmd_disk_usage(_Args(path=str(tmp_path)))
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_size"] == 0
    assert data["total_dirs"] == 0


def test_disk_usage_with_files(tmp_path, capsys):
    (tmp_path / "a.txt").write_text("hello")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("world")
    cmd_disk_usage(_Args(path=str(tmp_path)))
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_size"] > 0
    assert data["total_dirs"] >= 1


def test_main_scan_help(capsys):
    with pytest.raises(SystemExit):
        main()


def test_main_unknown_command(capsys):
    with pytest.raises(SystemExit):
        main_args(["unknown_cmd"])


def test_scan_no_recursive(tmp_path, capsys):
    (tmp_path / "a.txt").write_text("hello")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("world")
    from filepilot.cli import cmd_scan
    cmd_scan(_Args(path=str(tmp_path), no_recursive=True))
    captured = capsys.readouterr()
    assert "Scan complete" in captured.err


class _Args:
    """Fake argparse namespace for testing CLI commands."""
    def __init__(self, **kwargs):
        self.path = ""
        self.query = ""
        self.limit = 50
        self.no_recursive = False
        self.rules = ["category"]
        self.target = ""
        self.dry_run = True
        self.rename = ""
        self.format = "json"
        self.output = None
        self.__dict__.update(kwargs)


def main_args(argv):
    """Run main() with custom argv"""
    old_argv = sys.argv
    try:
        sys.argv = ["filepilot.cli"] + argv
        main()
    except SystemExit:
        raise
    finally:
        sys.argv = old_argv
