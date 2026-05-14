"""Markdown Content Extractor"""

import re
from pathlib import Path


class MarkdownExtractor:
    """Markdown file content extraction"""

    SUPPORTED_EXTENSIONS = {".md", ".markdown", ".mdx"}

    def extract_text(self, file_path: str | Path) -> str:
        """Extract plain text content from Markdown (strip markup syntax)"""
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""
        content = re.sub(r"```[\s\S]*?```", "", content)
        content = re.sub(r"`[^`]+`", "", content)
        content = re.sub(r"!\[.*?\]\(.*?\)", "", content)
        content = re.sub(r"\[([^\]]+)\]\(.*?\)", r"\1", content)
        content = re.sub(r"[#*_~>|`\-]", "", content)
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content.strip()

    def extract_metadata(self, file_path: str | Path) -> dict:
        """Extract Markdown metadata (Front Matter)"""
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            return {}
        metadata: dict = {}
        # Parse YAML Front Matter
        front_matter_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if front_matter_match:
            yaml_str = front_matter_match.group(1)
            try:
                import yaml

                metadata = yaml.safe_load(yaml_str) or {}
            except Exception:
                for line in yaml_str.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip().strip('"').strip("'")
        title_match = re.search(r"^#\s+(.+)", content, re.MULTILINE)
        if title_match and "title" not in metadata:
            metadata["title"] = title_match.group(1).strip()
        metadata["_word_count"] = len(self.extract_text(file_path).split())
        metadata["_char_count"] = len(content)
        return metadata

    def extract_headings(self, file_path: str | Path) -> list[dict]:
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            return []
        headings: list[dict] = []
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
        for match in heading_pattern.finditer(content):
            level = len(match.group(1))
            title = match.group(2).strip()
            headings.append(
                {
                    "level": level,
                    "title": title,
                }
            )
        return headings

    def extract_code_blocks(self, file_path: str | Path) -> list[dict]:
        """Extract code blocks from Markdown"""
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            return []
        blocks: list[dict] = []
        code_pattern = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
        for match in code_pattern.finditer(content):
            language = match.group(1) or "text"
            code = match.group(2).strip()
            blocks.append({"language": language, "code": code})
        return blocks
