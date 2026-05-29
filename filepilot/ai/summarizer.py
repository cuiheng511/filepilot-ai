"""Content Summarizer — Supports local and cloud AI"""

from collections.abc import Callable
from pathlib import Path

from filepilot.ai.cloud_ai import CloudAI
from filepilot.ai.local_ai import LocalAI


class Summarizer:
    """Intelligent summary generator

    Automatically detects file type, extracts content, and generates
    summary using AI. Prefers local models with cloud fallback.
    """

    def __init__(
        self,
        local_ai: LocalAI | None = None,
        cloud_ai: CloudAI | None = None,
        prefer_local: bool = True,
    ):
        self.local_ai = local_ai or LocalAI()
        self.cloud_ai = cloud_ai or CloudAI()
        self.prefer_local = prefer_local

    def summarize(
        self,
        file_path: str | Path,
        max_length: int = 200,
        on_progress: Callable[[str], None] | None = None,
    ) -> dict:
        """Generate file summary

        Args:
            file_path: Path to the file
            max_length: Maximum summary length in characters
            on_progress: Progress callback

        Returns:
            Summary result dictionary

        """
        path = Path(file_path)
        result = {
            "path": str(path),
            "filename": path.name,
            "success": False,
            "summary": "",
            "keywords": [],
            "error": "",
        }

        # 1. Extract text content
        if on_progress:
            on_progress("Extracting file content...")

        content = self._extract_content(path)
        if not content.strip():
            result["error"] = "Unable to extract file content"
            return result

        # 2. Crop content length
        content = content[:8000]  # Limit input length

        # 3. Generate summary
        if on_progress:
            on_progress("AI is generating summary...")

        summary = self._generate_summary(content, max_length)
        if not summary:
            result["error"] = "AI summary generation failed, please check AI configuration"
            return result

        # 4. Extract keywords
        if on_progress:
            on_progress("Extracting keywords...")

        keywords = self._extract_keywords(content)

        result["success"] = True
        result["summary"] = summary
        result["keywords"] = keywords
        return result

    def summarize_text(self, text: str, max_length: int = 200) -> str:
        """Generate summary from plain text content directly

        Unlike `summarize()` which takes a file path and extracts content,
        this method accepts pre-extracted text. Useful when you already
        have the file content in memory.

        Args:
            text: Pre-extracted text content to summarize
            max_length: Maximum summary length in characters

        Returns:
            Generated summary string, or empty string on failure

        """
        return self._generate_summary(text, max_length)

    def extract_keywords(self, content: str, top_n: int = 10) -> list[str]:
        """Extract keywords from text content (public method)

        Args:
            content: Text content to extract keywords from
            top_n: Number of top keywords to return

        Returns:
            List of keyword strings

        """
        return self._extract_keywords(content, top_n)

    def batch_summarize(
        self,
        files: list[Path],
        max_length: int = 200,
        on_progress: Callable[[int, str], None] | None = None,
    ) -> list[dict]:
        """Batch generate file summaries"""
        results = []
        for i, file_path in enumerate(files):
            if on_progress:
                on_progress(i + 1, f"Processing ({i + 1}/{len(files)}): {file_path.name}")

            result = self.summarize(file_path, max_length)
            results.append(result)

        return results

    def _extract_content(self, file_path: Path) -> str:
        """Extract text content based on file type."""
        from filepilot.extractors.text_extraction import (
            CODE_EXTS,
            extract_code_with_context,
            extract_text,
        )

        ext = file_path.suffix.lower()
        # Code files get a metadata header (language + definitions) for richer summaries
        if ext in CODE_EXTS or ext in (".scala", ".rb", ".php", ".swift", ".kt"):
            return extract_code_with_context(file_path)
        return extract_text(file_path)

    def _generate_summary(self, content: str, max_length: int) -> str:
        """Generate content summary using AI"""
        system_prompt = (
            "You are a file summary assistant. Please summarize the key points of "
            "the following file content concisely. "
            f"Keep it within {max_length} characters."
        )

        user_prompt = f"Please summarize the following content:\n\n{content}"

        # Prefer local AI
        if self.prefer_local and self.local_ai.is_available:
            return self.local_ai.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=max_length * 2,
            )

        # Fall back to cloud AI
        if self.cloud_ai.is_available:
            return self.cloud_ai.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=max_length * 2,
            )

        return ""

    def _extract_keywords(self, content: str, top_n: int = 10) -> list[str]:
        """Extract keywords (simple TF statistics)"""
        import re
        from collections import Counter

        # Tokenize content
        words = re.findall(r"[\u4e00-\u9fff\w]+", content.lower())
        # Filter common stop words
        stop_words = {
            "的",
            "了",
            "在",
            "是",
            "我",
            "有",
            "和",
            "就",
            "不",
            "人",
            "都",
            "一",
            "一个",
            "上",
            "也",
            "很",
            "到",
            "说",
            "要",
            "去",
            "你",
            "会",
            "着",
            "没有",
            "看",
            "好",
            "自己",
            "这",
            "他",
            "她",
            "它",
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "shall",
            "can",
        }

        word_counts = Counter(word for word in words if word not in stop_words and len(word) > 1)

        return [word for word, _ in word_counts.most_common(top_n)]
