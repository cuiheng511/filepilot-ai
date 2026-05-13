"""FilePilot AI — Internationalization (i18n) Support

Simple string translation framework. Supports Chinese/English switching.
"""

import json
from pathlib import Path

# Current language
_current_lang = "en"

# Translation dictionary
_translations: dict[str, dict[str, str]] = {
    "zh": {
        # General
        "app_name": "FilePilot AI",
        "app_subtitle": "智能文件管家",
        "ok": "确定",
        "cancel": "取消",
        "save": "保存",
        "close": "关闭",
        "yes": "是",
        "no": "否",
        "loading": "加载中...",
        "ready": "就绪",
        "error": "错误",
        "success": "成功",
        "warning": "警告",
        # Navigation
        "nav_browse": "📂  文件浏览",
        "nav_search": "🔍  文件搜索",
        "nav_organize": "📋  文件整理",
        "nav_duplicates": "🔗  查重工具",
        "nav_summary": "📝  摘要生成",
        "nav_index": "🗂️  文件索引",
        # File Browser
        "browse_title": "文件浏览",
        "browse_desc": "浏览和管理本地文件",
        "browse_no_folder": "未选择文件夹",
        "browse_scan": "🔄 扫描",
        "browse_export": "📥 导出",
        "browse_stats": "就绪 - 选择文件夹开始浏览",
        # Search
        "search_title": "🔍 文件搜索",
        "search_desc": "自然语言搜索本地文件。支持按文件名、内容、类型、日期搜索。",
        "search_placeholder": "输入搜索关键词...",
        "search_btn": "🔍 搜索",
        "search_index_btn": "🗂️ 建立索引",
        "search_no_results": "没有找到相关结果",
        # Organize
        "organize_title": "📋 文件整理",
        "organize_desc": "选择源文件夹和目标文件夹，配置规则后一键整理文件。",
        "organize_src": "📂 源文件夹:",
        "organize_dst": "🎯 目标文件夹:",
        "organize_preview": "👁️ 预览整理",
        "organize_execute": "🚀 执行整理",
        "organize_undo": "↩️ 撤销整理",
        "organize_confirm": "确认整理",
        "organize_done": "整理完成",
        # Duplicates
        "duplicates_title": "🔗 重复文件查找",
        "duplicates_desc": "基于内容哈希精准查找重复文件，释放磁盘空间。",
        "duplicates_scan": "🔍 开始扫描",
        "duplicates_groups": "📦 重复组",
        "duplicates_files": "📄 重复文件",
        "duplicates_wasted": "💾 浪费空间",
        # Summary
        "summary_title": "📝 AI 摘要生成",
        "summary_desc": "使用 AI 自动提取 PDF、Markdown、代码文件的摘要和关键词。",
        "summary_select_file": "选择文件...",
        "summary_select_folder": "选择文件夹（批量）...",
        "summary_generate": "🤖 生成摘要",
        "summary_batch": "📦 批量处理",
        "summary_copy": "📋 复制摘要",
        "summary_no_ai": "无可用的 AI 引擎，请在设置中配置",
        # Index
        "index_title": "🗂️ 文件索引管理",
        "index_desc": "管理 Whoosh 全文搜索索引。建立索引后可实现快速全文搜索。",
        "index_build": "🔨 建立索引",
        "index_clear": "🗑️ 清空索引",
        # Settings
        "settings_title": "⚙️ 设置",
        "settings_ai": "🤖 AI 引擎",
        "settings_general": "⚙️ 通用",
        "settings_provider": "AI Provider",
        "settings_model": "模型设置",
        "settings_model_label": "模型:",
        "settings_api_base": "API 地址:",
        "settings_api_key": "API Key:",
        # Disk Analysis
        "disk_title": "📊 磁盘占用分析",
        "disk_total": "总大小",
        "disk_dirs": "目录数",
    },
    "en": {
        "app_name": "FilePilot AI",
        "app_subtitle": "Smart File Manager",
        "ok": "OK",
        "cancel": "Cancel",
        "save": "Save",
        "close": "Close",
        "yes": "Yes",
        "no": "No",
        "loading": "Loading...",
        "ready": "Ready",
        "error": "Error",
        "success": "Success",
        "warning": "Warning",
        "nav_browse": "📂  File Browser",
        "nav_search": "🔍  Search",
        "nav_organize": "📋  Organize",
        "nav_duplicates": "🔗  Duplicates",
        "nav_summary": "📝  AI Summary",
        "nav_index": "🗂️  Index",
        "browse_title": "File Browser",
        "browse_desc": "Browse and manage local files",
        "browse_no_folder": "No folder selected",
        "browse_scan": "🔄 Scan",
        "browse_export": "📥 Export",
        "browse_stats": "Ready - Select a folder to start",
        "search_title": "🔍 File Search",
        "search_desc": "Natural language search for local files.",
        "search_placeholder": "Search keywords...",
        "search_btn": "🔍 Search",
        "search_index_btn": "🗂️ Build Index",
        "search_no_results": "No results found",
        "organize_title": "📋 File Organizer",
        "organize_desc": "Select source and target folders, configure rules, and organize files.",
        "organize_src": "📂 Source:",
        "organize_dst": "🎯 Target:",
        "organize_preview": "👁️ Preview",
        "organize_execute": "🚀 Execute",
        "organize_undo": "↩️ Undo",
        "organize_confirm": "Confirm",
        "organize_done": "Done",
        "duplicates_title": "🔗 Duplicate Finder",
        "duplicates_desc": "Find duplicate files using content hashing.",
        "duplicates_scan": "🔍 Scan",
        "duplicates_groups": "📦 Groups",
        "duplicates_files": "📄 Duplicates",
        "duplicates_wasted": "💾 Wasted",
        "summary_title": "📝 AI Summary",
        "summary_desc": "Generate AI summaries for PDF, Markdown, and code files.",
        "summary_select_file": "Select file...",
        "summary_select_folder": "Select folder (batch)...",
        "summary_generate": "🤖 Generate",
        "summary_batch": "📦 Batch",
        "summary_copy": "📋 Copy",
        "summary_no_ai": "No AI engine available. Configure in Settings.",
        "index_title": "🗂️ Index Manager",
        "index_desc": "Manage Whoosh full-text search index.",
        "index_build": "🔨 Build Index",
        "index_clear": "🗑️ Clear Index",
        "settings_title": "⚙️ Settings",
        "settings_ai": "🤖 AI Engine",
        "settings_general": "⚙️ General",
        "settings_provider": "AI Provider",
        "settings_model": "Model Settings",
        "settings_model_label": "Model:",
        "settings_api_base": "API Base:",
        "settings_api_key": "API Key:",
        "disk_title": "📊 Disk Usage",
        "disk_total": "Total Size",
        "disk_dirs": "Directories",
    },
}


def set_language(lang: str) -> None:
    """Set the current language"""
    global _current_lang
    if lang in _translations:
        _current_lang = lang


def get_language() -> str:
    """Get the current language"""
    return _current_lang


def t(key: str, **kwargs) -> str:
    """Translate a string

    Args:
        key: Translation key
        **kwargs: Format arguments

    Returns:
        Translated string, returns key itself if not found
    """
    text = _translations.get(_current_lang, {}).get(key)
    if text is None:
        text = _translations.get("en", {}).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def load_language_from_settings() -> None:
    """Load language from user settings"""
    settings_path = Path.home() / ".filepilot" / "settings.json"
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            lang = settings.get("language", "en")
            set_language(lang)
        except Exception:
            pass
