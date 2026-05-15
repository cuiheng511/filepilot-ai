"""Tests for batch regex rename functionality."""

import re
import tempfile
from unittest import TestCase

import pytest

from filepilot.core.file_scanner import FileScanner


class TestRegexRename(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.scanner = FileScanner()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_regex_pattern_valid(self):
        pattern = r"^(\d{4})-(\d{2})-(\d{2})_"
        compiled = re.compile(pattern)
        self.assertTrue(compiled.match("2024-01-15_report.pdf"))

    def test_regex_replacement(self):
        pattern = r"^(\d{4})-(\d{2})-(\d{2})_"
        replacement = r"\2/\3/\1_"
        compiled = re.compile(pattern)
        result = compiled.sub(replacement, "2024-01-15_report.pdf")
        self.assertEqual("01/15/2024_report.pdf", result)

    def test_regex_case_insensitive(self):
        pattern = r"^test"
        compiled = re.compile(pattern, re.IGNORECASE)
        self.assertTrue(compiled.match("TEST_file.txt"))

    def test_regex_no_match(self):
        pattern = r"^(\d{4})-(\d{2})-(\d{2})_"
        compiled = re.compile(pattern)
        result = compiled.sub(r"\2/\3/\1_", "report.pdf")
        self.assertEqual("report.pdf", result)

    def test_regex_invalid_pattern(self):
        with pytest.raises(re.error):
            re.compile(r"[invalid")

    def test_regex_multiple_matches(self):
        pattern = r"\s+"
        compiled = re.compile(pattern)
        result = compiled.sub("_", "my  file   name.txt")
        self.assertEqual("my_file_name.txt", result)

    def test_regex_special_characters(self):
        pattern = r"[^\w\s.]"
        compiled = re.compile(pattern)
        result = compiled.sub("", "file@#name!.txt")
        self.assertEqual("filename.txt", result)
