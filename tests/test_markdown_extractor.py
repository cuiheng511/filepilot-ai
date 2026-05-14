"""Tests for MarkdownExtractor"""

from pathlib import Path

from filepilot.extractors.markdown_extractor import MarkdownExtractor


class TestMarkdownExtractor:
    def setup_method(self):
        self.extractor = MarkdownExtractor()

    def test_supported_extensions(self):
        assert ".md" in MarkdownExtractor.SUPPORTED_EXTENSIONS
        assert ".markdown" in MarkdownExtractor.SUPPORTED_EXTENSIONS
        assert ".mdx" in MarkdownExtractor.SUPPORTED_EXTENSIONS

    def test_extract_text_strips_markup(self, tmp_path):
        md_content = (
            "# Title\n\n"
            "This is **bold** and *italic* text.\n\n"
            "- List item 1\n"
            "- List item 2\n\n"
            "> A blockquote\n\n"
            "`inline code` and a [link](https://example.com)\n"
        )
        test_file = tmp_path / "test.md"
        test_file.write_text(md_content, encoding="utf-8")

        text = self.extractor.extract_text(test_file)
        assert "Title" in text
        assert "bold" in text
        assert "italic" in text
        assert "List item 1" in text
        assert "List item 2" in text
        assert "inline code" not in text  # backticks stripped
        assert "**" not in text  # bold markers stripped
        assert "link" in text  # link text preserved
        assert "https://" not in text  # URL stripped

    def test_extract_text_removes_code_blocks(self, tmp_path):
        md_content = (
            "# Code Demo\n\n"
            "Some text.\n\n"
            "```python\n"
            "def hello():\n"
            "    print('hi')\n"
            "```\n\n"
            "More text.\n"
        )
        test_file = tmp_path / "code.md"
        test_file.write_text(md_content, encoding="utf-8")

        text = self.extractor.extract_text(test_file)
        assert "Code Demo" in text
        assert "def hello()" not in text  # code block removed
        assert "hi" not in text

    def test_extract_text_nonexistent_file(self):
        text = self.extractor.extract_text("/nonexistent/file.md")
        assert text == ""

    def test_extract_metadata_yaml_front_matter(self, tmp_path):
        md_content = (
            "---\n"
            "title: My Document\n"
            "author: Test User\n"
            "tags: [python, testing]\n"
            "---\n"
            "\n"
            "# Content\n\n"
            "Body text here.\n"
        )
        test_file = tmp_path / "frontmatter.md"
        test_file.write_text(md_content, encoding="utf-8")

        meta = self.extractor.extract_metadata(test_file)
        assert meta["title"] == "My Document"
        assert meta["author"] == "Test User"
        assert "_word_count" in meta
        assert "_char_count" in meta

    def test_extract_metadata_title_from_h1(self, tmp_path):
        md_content = "# Just a Title\n\nSome content here.\n"
        test_file = tmp_path / "notitle.md"
        test_file.write_text(md_content, encoding="utf-8")

        meta = self.extractor.extract_metadata(test_file)
        assert meta["title"] == "Just a Title"

    def test_extract_metadata_empty_file(self, tmp_path):
        test_file = tmp_path / "empty.md"
        test_file.write_text("", encoding="utf-8")

        meta = self.extractor.extract_metadata(test_file)
        assert "_word_count" in meta
        assert meta["_word_count"] == 0

    def test_extract_headings(self, tmp_path):
        md_content = (
            "# Title\n\n"
            "## Section 1\n\n"
            "Text.\n\n"
            "### Subsection\n\n"
            "More text.\n\n"
            "## Section 2\n\n"
            "End.\n"
        )
        test_file = tmp_path / "headings.md"
        test_file.write_text(md_content, encoding="utf-8")

        headings = self.extractor.extract_headings(test_file)
        assert len(headings) == 4
        assert headings[0] == {"level": 1, "title": "Title"}
        assert headings[1] == {"level": 2, "title": "Section 1"}
        assert headings[2] == {"level": 3, "title": "Subsection"}
        assert headings[3] == {"level": 2, "title": "Section 2"}

    def test_extract_code_blocks(self, tmp_path):
        md_content = (
            "Some text.\n\n"
            "```python\n"
            "def hello():\n"
            "    print('hi')\n"
            "```\n\n"
            "More text.\n\n"
            "```javascript\n"
            "console.log('hello');\n"
            "```\n"
        )
        test_file = tmp_path / "codeblocks.md"
        test_file.write_text(md_content, encoding="utf-8")

        blocks = self.extractor.extract_code_blocks(test_file)
        assert len(blocks) == 2
        assert blocks[0]["language"] == "python"
        assert "def hello()" in blocks[0]["code"]
        assert blocks[1]["language"] == "javascript"
        assert "console.log('hello')" in blocks[1]["code"]

    def test_extract_code_blocks_no_code(self, tmp_path):
        test_file = tmp_path / "nocode.md"
        test_file.write_text("Just plain text.", encoding="utf-8")

        blocks = self.extractor.extract_code_blocks(test_file)
        assert blocks == []
