"""Code Content Extractor"""

import re
from pathlib import Path


class CodeExtractor:
    """Extract text and metadata from source code files."""

    SUPPORTED_EXTENSIONS = {
        ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".hpp",
        ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
        ".sql", ".sh", ".bash", ".ps1", ".bat", ".pl", ".lua", ".r",
        ".m", ".dart", ".tsx", ".jsx", ".vue", ".svelte",
    }

    COMMENT_PATTERNS: dict[str, list[str]] = {
        "python": [r'#.*$', r'""".*?"""', r"'''.*?'''"],
        "javascript": [r'//.*$', r'/\*.*?\*/'],
        "typescript": [r'//.*$', r'/\*.*?\*/'],
        "java": [r'//.*$', r'/\*.*?\*/'],
        "default": [r'//.*$', r'/\*.*?\*/', r'#.*$'],
    }

    def extract_text(self, file_path: str | Path) -> str:
        """Read the full text content of a source code file."""
        try:
            return Path(file_path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    def extract_metadata(self, file_path: str | Path) -> dict:
        """Extract metadata from source code including language, definitions, and imports."""
        content = self.extract_text(file_path)
        if not content:
            return {}
        lines = content.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]
        ext = Path(file_path).suffix.lower()
        language = self._detect_language(ext)
        definitions = self._extract_definitions(content, language)
        imports = self._extract_imports(content, language)
        comments = self._extract_comments(content, language)
        return {
            "language": language,
            "lines": len(lines),
            "code_lines": len(non_empty_lines),
            "blank_lines": len(lines) - len(non_empty_lines),
            "definitions": definitions,
            "imports": imports[:50],  # Limit number of imports
            "comment_lines": len(comments),
            "char_count": len(content),
        }

    def _detect_language(self, extension: str) -> str:
        """Detect the programming language from file extension."""
        lang_map = {
            ".py": "python",
            ".js": "javascript", ".jsx": "javascript",
            ".ts": "typescript", ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp", ".c": "c", ".h": "c", ".hpp": "cpp",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".sql": "sql",
            ".sh": "bash", ".bash": "bash",
            ".ps1": "powershell",
            ".vue": "vue",
        }
        return lang_map.get(extension, "unknown")

    def _extract_definitions(self, content: str, language: str) -> list[dict]:
        """Extract function/class definitions from source code."""
        definitions: list[dict] = []
        if language == "python":
            for m in re.finditer(r'^(?:async\s+)?def\s+(\w+)\s*\(', content, re.MULTILINE):
                definitions.append({"type": "function", "name": m.group(1)})
            for m in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
                definitions.append({"type": "class", "name": m.group(1)})
        elif language in ("javascript", "typescript"):
            for m in re.finditer(r'(?:export\s+)?(?:function|class|const|let|var)\s+(\w+)', content, re.MULTILINE):
                definitions.append({"type": "declaration", "name": m.group(1)})
            for m in re.finditer(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', content, re.MULTILINE):
                definitions.append({"type": "function", "name": m.group(1)})
        elif language == "java":
            for m in re.finditer(r'(?:public|private|protected)?\s*(?:static\s+)?(?:class|interface|enum)\s+(\w+)', content):
                definitions.append({"type": "class", "name": m.group(1)})
            for m in re.finditer(r'(?:public|private|protected)?\s*\w+\s+(\w+)\s*\(', content):
                definitions.append({"type": "method", "name": m.group(1)})
        return definitions

    def _extract_imports(self, content: str, language: str) -> list[str]:
        """Extract import statements from source code."""
        imports: list[str] = []
        if language == "python":
            for m in re.finditer(r'^(?:from\s+\S+\s+)?import\s+\S+', content, re.MULTILINE):
                imports.append(m.group(0).strip())
        elif language in ("javascript", "typescript"):
            for m in re.finditer(r'^(?:import\s+.*?|const\s+\w+\s*=\s*require\(.*?\))', content, re.MULTILINE):
                imports.append(m.group(0).strip())
        elif language == "java":
            for m in re.finditer(r'^import\s+[\w.*]+;', content, re.MULTILINE):
                imports.append(m.group(0).strip())
        elif language == "go":
            for m in re.finditer(r'^import\s+["\w./]+', content, re.MULTILINE):
                imports.append(m.group(0).strip())
        return imports

    def _extract_comments(self, content: str, language: str) -> list[str]:
        """Extract comments from source code."""
        comments: list[str] = []
        patterns = self.COMMENT_PATTERNS.get(language, self.COMMENT_PATTERNS["default"])
        for pattern in patterns:
            for m in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                comment = m.group(0).strip()
                if comment and len(comment) > 3:  # Filter empty comments
                    comments.append(comment)
        return comments
