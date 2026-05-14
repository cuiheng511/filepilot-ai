"""Tests for CodeExtractor"""

from pathlib import Path

from filepilot.extractors.code_extractor import CodeExtractor


class TestCodeExtractor:
    def setup_method(self):
        self.extractor = CodeExtractor()

    def test_supported_extensions(self):
        assert ".py" in CodeExtractor.SUPPORTED_EXTENSIONS
        assert ".js" in CodeExtractor.SUPPORTED_EXTENSIONS
        assert ".ts" in CodeExtractor.SUPPORTED_EXTENSIONS
        assert ".java" in CodeExtractor.SUPPORTED_EXTENSIONS

    def test_extract_text(self, tmp_path):
        test_file = tmp_path / "hello.py"
        code = "def hello():\n    print('Hello, World!')\n"
        test_file.write_text(code, encoding="utf-8")

        result = self.extractor.extract_text(test_file)
        assert result == code

    def test_extract_text_nonexistent_file(self):
        result = self.extractor.extract_text("/nonexistent/file.py")
        assert result == ""

    def test_extract_metadata_python(self, tmp_path):
        test_file = tmp_path / "script.py"
        test_file.write_text(
            '"""Module docstring"""\n'
            "import os\n"
            "from pathlib import Path\n"
            "\n"
            "def hello(name):\n"
            '    """Greet"""\n'
            "    return f'Hello {name}'\n"
            "\n"
            "class Calculator:\n"
            "    def add(self, a, b):\n"
            "        return a + b\n",
            encoding="utf-8",
        )

        meta = self.extractor.extract_metadata(test_file)
        assert meta["language"] == "python"
        assert meta["lines"] == 12
        assert meta["code_lines"] == 9
        assert meta["blank_lines"] == 3

        definitions = meta["definitions"]
        def_names = [d["name"] for d in definitions]
        assert "hello" in def_names
        assert "Calculator" in def_names

        imports = meta["imports"]
        assert any("import os" in i for i in imports)
        assert any("from pathlib import Path" in i for i in imports)

        assert meta["comment_lines"] >= 1  # docstrings

    def test_extract_metadata_empty_file(self, tmp_path):
        test_file = tmp_path / "empty.py"
        test_file.write_text("", encoding="utf-8")

        meta = self.extractor.extract_metadata(test_file)
        # Empty file returns empty metadata (no content to parse)
        assert meta == {}

    def test_detect_language(self):
        assert self.extractor._detect_language(".py") == "python"
        assert self.extractor._detect_language(".js") == "javascript"
        assert self.extractor._detect_language(".ts") == "typescript"
        assert self.extractor._detect_language(".java") == "java"
        assert self.extractor._detect_language(".cpp") == "cpp"
        assert self.extractor._detect_language(".rs") == "rust"
        assert self.extractor._detect_language(".go") == "go"
        assert self.extractor._detect_language(".xyz") == "unknown"

    def test_extract_definitions_python(self, tmp_path):
        test_file = tmp_path / "defs.py"
        test_file.write_text(
            "async def fetch_data():\n"
            "    pass\n"
            "class MyClass:\n"
            "    def method(self):\n"
            "        pass\n",
            encoding="utf-8",
        )

        meta = self.extractor.extract_metadata(test_file)
        defs = meta["definitions"]
        assert any(d["name"] == "fetch_data" for d in defs)
        assert any(d["name"] == "MyClass" for d in defs)

    def test_extract_imports_java(self, tmp_path):
        test_file = tmp_path / "Main.java"
        test_file.write_text(
            "package com.example;\n"
            "import java.util.List;\n"
            "import java.io.File;\n"
            "public class Main {}\n",
            encoding="utf-8",
        )

        meta = self.extractor.extract_metadata(test_file)
        assert meta["language"] == "java"
        imports = meta["imports"]
        assert any("import java.util.List" in i for i in imports)
        assert any("import java.io.File" in i for i in imports)

    def test_extract_comments(self, tmp_path):
        test_file = tmp_path / "commented.py"
        test_file.write_text(
            "# This is a comment\n"
            '"""Module docstring"""\n'
            "x = 1  # inline comment\n",
            encoding="utf-8",
        )

        meta = self.extractor.extract_metadata(test_file)
        assert meta["comment_lines"] >= 2
