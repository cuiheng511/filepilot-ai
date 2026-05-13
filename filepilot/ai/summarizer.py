"""内容摘要生成器 — 支持本地和云端 AI"""

from pathlib import Path
from typing import Callable

from filepilot.ai.local_ai import LocalAI
from filepilot.ai.cloud_ai import CloudAI
from filepilot.extractors.pdf_extractor import PDFExtractor
from filepilot.extractors.markdown_extractor import MarkdownExtractor
from filepilot.utils.file_utils import get_file_category


class Summarizer:
    """智能摘要生成器

    自动检测文件类型，提取内容，并用 AI 生成摘要。
    优先使用本地模型，可选云端模型。
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
        """生成文件摘要

        Args:
            file_path: 文件路径
            max_length: 摘要最大字数
            on_progress: 进度回调

        Returns:
            摘要结果字典
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        result = {
            "path": str(path),
            "filename": path.name,
            "success": False,
            "summary": "",
            "keywords": [],
            "error": "",
        }

        # 1. 提取文本内容
        if on_progress:
            on_progress("正在提取文件内容...")

        content = self._extract_content(path)
        if not content.strip():
            result["error"] = "无法提取文件内容"
            return result

        # 2. 内容裁剪
        content = content[:8000]  # 限制输入长度

        # 3. 生成摘要
        if on_progress:
            on_progress("AI 正在生成摘要...")

        summary = self._generate_summary(content, max_length)
        if not summary:
            result["error"] = "AI 生成摘要失败，请检查 AI 配置"
            return result

        # 4. 提取关键词
        if on_progress:
            on_progress("正在提取关键词...")

        keywords = self._extract_keywords(content)

        result["success"] = True
        result["summary"] = summary
        result["keywords"] = keywords
        return result

    def batch_summarize(
        self,
        files: list[Path],
        max_length: int = 200,
        on_progress: Callable[[int, str], None] | None = None,
    ) -> list[dict]:
        """批量生成文件摘要"""
        results = []
        for i, file_path in enumerate(files):
            if on_progress:
                on_progress(i + 1, f"正在处理 ({i + 1}/{len(files)}): {file_path.name}")

            result = self.summarize(file_path, max_length)
            results.append(result)

        return results

    def _extract_content(self, file_path: Path) -> str:
        """根据文件类型提取文本内容"""
        ext = file_path.suffix.lower()

        if ext == ".pdf":
            from filepilot.extractors.pdf_extractor import PDFExtractor
            return PDFExtractor().extract_text(file_path)

        elif ext in (".md", ".markdown", ".mdx"):
            from filepilot.extractors.markdown_extractor import MarkdownExtractor
            return MarkdownExtractor().extract_text(file_path)

        elif ext == ".docx":
            from filepilot.extractors.docx_extractor import DocxExtractor
            return DocxExtractor().extract_text(file_path)

        elif ext in (".xlsx", ".xls"):
            from filepilot.extractors.xlsx_extractor import XlsxExtractor
            return XlsxExtractor().extract_text(file_path)

        elif ext in (".pptx", ".ppt"):
            from filepilot.extractors.pptx_extractor import PptxExtractor
            return PptxExtractor().extract_text(file_path)

        elif ext in (".py", ".js", ".ts", ".java", ".cpp", ".c", ".rs", ".go"):
            from filepilot.extractors.code_extractor import CodeExtractor
            extractor = CodeExtractor()
            meta = extractor.extract_metadata(file_path)
            code = extractor.extract_text(file_path)
            context_parts = [f"语言: {meta.get('language', '未知')}"]
            defs = meta.get("definitions", [])
            if defs:
                def_names = [d["name"] for d in defs[:20]]
                context_parts.append(f"函数/类: {', '.join(def_names)}")
            return f"{' | '.join(context_parts)}\n\n{code[:6000]}"

        else:
            try:
                return file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                return ""

    def _generate_summary(self, content: str, max_length: int) -> str:
        """用 AI 生成内容摘要"""
        system_prompt = (
            "你是一个文件摘要助手。请用简洁的语言总结以下文件内容的核心要点。"
            f"控制在 {max_length} 字以内。"
        )

        user_prompt = f"请总结以下内容：\n\n{content}"

        # 优先使用本地 AI
        if self.prefer_local and self.local_ai.is_available:
            return self.local_ai.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=max_length * 2,
            )

        # 回退到云端 AI
        if self.cloud_ai.is_available:
            return self.cloud_ai.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=max_length * 2,
            )

        return ""

    def _extract_keywords(self, content: str, top_n: int = 10) -> list[str]:
        """提取关键词（简单 TF 统计）"""
        import re
        from collections import Counter

        # 中文分词
        words = re.findall(r'[\u4e00-\u9fff\w]+', content.lower())
        # 过滤常见停用词
        stop_words = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
            "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
            "会", "着", "没有", "看", "好", "自己", "这", "他", "她", "它",
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
        }

        word_counts = Counter(
            word for word in words
            if word not in stop_words and len(word) > 1
        )

        return [word for word, _ in word_counts.most_common(top_n)]
