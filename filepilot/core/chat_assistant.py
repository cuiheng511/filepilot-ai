"""Local file-assistant query handling used by the chat UI."""

from __future__ import annotations

from typing import Protocol


class FileQueryIndexer(Protocol):
    """Indexer methods needed by the chat assistant."""

    def get_stats(self) -> dict: ...

    def search_by_category(self, category: str, limit: int = 20) -> list[dict]: ...

    def search_metadata(self, **kwargs) -> list[dict]: ...

    def search_by_extension(self, ext: str, limit: int = 20) -> list[dict]: ...

    def search(self, query: str, limit: int = 10) -> list[dict]: ...


class ChatAIProvider(Protocol):
    """AI provider methods needed by the chat assistant."""

    @property
    def is_available(self) -> bool: ...

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        on_token=None,
    ) -> str: ...


def process_file_query(
    query: str,
    indexer: FileQueryIndexer | None,
    ai_provider: ChatAIProvider | None = None,
) -> str:
    """Answer a file-management query using local parsing first, then AI."""
    query_lower = query.lower()
    local_result = try_local_query(query_lower, indexer)
    if local_result:
        return local_result

    if ai_provider and ai_provider.is_available:
        return ai_query(query, indexer, ai_provider)

    return local_query_fallback(query_lower, query, indexer)


def try_local_query(query_lower: str, indexer: FileQueryIndexer | None) -> str | None:
    """Parse simple queries without AI."""
    if not indexer:
        return "No indexer available. Please build the index first."

    stats = indexer.get_stats()

    if "how many" in query_lower or "count" in query_lower:
        if "file" in query_lower:
            return (
                f"You have {stats['indexed_files']:,} indexed files "
                f"({stats.get('total_size_str', '?')})."
            )
        for cat in ["pdf", "code", "image", "markdown", "video", "audio", "office"]:
            if cat in query_lower:
                results = indexer.search_by_category(cat.capitalize(), limit=10000)
                return f"You have {len(results)} {cat.capitalize()} files."

    if any(kw in query_lower for kw in ["find", "show", "search", "list"]):
        if "large" in query_lower or "big" in query_lower:
            results = indexer.search_metadata(size_min=100 * 1024 * 1024, limit=10)
            if results:
                lines = [f"Found {len(results)} large files (>100MB):"]
                for r in results[:10]:
                    lines.append(f"  {r['filename']} ({r['size_str']})")
                return "\n".join(lines)
            return "No files larger than 100MB found in the index."

        if "small" in query_lower:
            results = indexer.search_metadata(size_max=1024, limit=10)
            if results:
                lines = [f"Found {len(results)} small files (<1KB):"]
                for r in results[:10]:
                    lines.append(f"  {r['filename']} ({r['size_str']})")
                return "\n".join(lines)
            return "No very small files found."

        for cat in ["pdf", "code", "image", "markdown", "video", "audio", "document"]:
            if cat in query_lower:
                results = indexer.search_by_category(cat.capitalize(), limit=20)
                if results:
                    lines = [f"Found {len(results)} {cat} files:"]
                    for r in results[:10]:
                        lines.append(f"  {r['filename']} - {r.get('modified', '')}")
                    if len(results) > 10:
                        lines.append(f"  ... and {len(results) - 10} more")
                    return "\n".join(lines)
                return f"No {cat} files found in the index."

        for ext in [".py", ".js", ".ts", ".pdf", ".md", ".docx", ".xlsx"]:
            if ext.lstrip(".") in query_lower:
                results = indexer.search_by_extension(ext, limit=20)
                if results:
                    lines = [f"Found {len(results)} {ext} files:"]
                    for r in results[:10]:
                        lines.append(f"  {r['filename']}")
                    return "\n".join(lines)

        search_terms = (
            query_lower.replace("find", "")
            .replace("show", "")
            .replace("search", "")
            .replace("list", "")
            .strip()
        )
        if search_terms and len(search_terms) > 2:
            results = indexer.search(search_terms, limit=10)
            if results:
                lines = [f"Found {len(results)} results for '{search_terms}':"]
                for r in results[:10]:
                    lines.append(f"  {r['filename']} (match: {r['score']:.0%})")
                return "\n".join(lines)

    return None


def local_query_fallback(
    query_lower: str,
    query: str,
    indexer: FileQueryIndexer | None,
) -> str:
    """Fallback when no AI is available."""
    if not indexer:
        return (
            "I can help you find files! But first, please:\n"
            "1. Open a folder\n"
            "2. Build the index (Index panel)\n\n"
            "Then ask me things like:\n"
            '- "How many PDF files do I have?"\n'
            '- "Find large files"\n'
            '- "Show Python files"'
        )

    results = indexer.search(query, limit=5)
    if results:
        lines = [f"I found {len(results)} files matching your query:"]
        for r in results:
            lines.append(f"  {r['filename']} ({r['size_str']}) - {r.get('modified', '')}")
        lines.append("\nTip: Configure an AI provider in Settings for smarter responses.")
        return "\n".join(lines)

    return (
        "I couldn't find files matching that query.\n\n"
        "Try:\n"
        '- "Find PDF files"\n'
        '- "Show large files"\n'
        '- "How many code files?"\n\n'
        "Tip: Configure an AI provider in Settings for natural language understanding."
    )


def ai_query(
    query: str,
    indexer: FileQueryIndexer | None,
    ai_provider: ChatAIProvider,
) -> str:
    """Use AI provider to understand and respond to the query."""
    stats = indexer.get_stats() if indexer else {}
    context = (
        f"You are a file management assistant. The user has {stats.get('indexed_files', 0)} "
        f"indexed files totaling {stats.get('total_size_str', 'unknown')}. "
        f"Help them find and manage their files. Be concise."
    )

    try:
        response = ai_provider.generate(
            prompt=query,
            system_prompt=context,
            temperature=0.3,
            max_tokens=500,
        )
        return response or "I couldn't generate a response. Please try again."
    except Exception as e:
        return f"AI error: {e}\n\nFalling back to local search..."
