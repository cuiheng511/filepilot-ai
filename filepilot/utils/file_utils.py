"""File operation utility functions"""

import hashlib
import os
import re
from datetime import datetime
from enum import Enum
from pathlib import Path


class FileCategory(Enum):
    """File classification"""
    DOCUMENT = ("Document", ".txt,.doc,.docx,.rtf,.odt", "📄")
    IMAGE = ("Image", ".jpg,.jpeg,.png,.gif,.bmp,.svg,.webp,.ico", "🖼️")
    VIDEO = ("Video", ".mp4,.avi,.mkv,.mov,.wmv,.flv,.webm", "🎬")
    AUDIO = ("Audio", ".mp3,.wav,.flac,.aac,.ogg,.wma,.m4a", "🎵")
    CODE = ("Code", ".py,.js,.ts,.java,.cpp,.c,.h,.hpp,.cs,.go,.rs,.rb,.php,.swift,.kt,.scala,.sql,.sh,.bash,.ps1,.bat,.pl,.lua,.r,.m,.dart", "💻")
    ARCHIVE = ("Archive", ".zip,.rar,.7z,.tar,.gz,.bz2,.xz,.zst,.iso", "🗜️")
    PDF = ("PDF", ".pdf", "📕")
    MARKDOWN = ("Markdown", ".md,.markdown,.rst", "📝")
    SPREADSHEET = ("Spreadsheet", ".xls,.xlsx,.csv,.ods", "📊")
    PRESENTATION = ("Presentation", ".ppt,.pptx,.odp,.key", "📽️")
    DATA = ("Data", ".json,.xml,.yaml,.yml,.toml,.ini,.cfg,.conf", "🗃️")
    EXECUTABLE = ("Executable", ".exe,.msi,.app,.dmg,.deb,.rpm,.sh,.bat", "⚙️")
    FONT = ("Font", ".ttf,.otf,.woff,.woff2,.eot", "🔤")
    UNKNOWN = ("Other", "", "❓")

    def __init__(self, label: str, extensions: str, icon: str):
        self.label = label
        self.extensions = set(extensions.split(",")) if extensions else set()
        self.icon = icon


# Extension-to-category mapping
_EXTENSION_MAP: dict[str, FileCategory] = {}
for cat in FileCategory:
    for ext in cat.extensions:
        _EXTENSION_MAP[ext.strip().lower()] = cat


# ── UI-focused category sets (simplified groups for file_browser) ──
CAT_PDF      = {".pdf"}
CAT_MARKDOWN = {".md", ".markdown", ".mdx", ".rst"}
CAT_CODE     = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cpp", ".c",
               ".h", ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".swift",
               ".kt", ".scala", ".sql", ".sh", ".bash", ".ps1", ".lua"}
CAT_IMAGE    = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"}
CAT_VIDEO    = {".mp4", ".avi", ".mov", ".mkv"}
CAT_AUDIO    = {".mp3", ".wav", ".flac"}
CAT_OFFICE   = {".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt"}
CAT_TEXT     = {".txt", ".log", ".cfg", ".ini", ".conf", ".yaml", ".yml",
               ".toml", ".json", ".xml"}


# ── Icon lookup for UI panels (category_name → emoji) ──
CATEGORY_ICONS: dict[str, str] = {
    "PDF": "📕", "Markdown": "📝", "Code": "💻",
    "Image": "🖼️", "Video": "🎬", "Audio": "🎵",
    "Office": "📊", "Text": "📄", "Other": "📁",
}


def get_category_name(ext: str) -> str:
    """Map a file extension to a category name (case-insensitive)

    Returns one of: PDF, Markdown, Code, Image, Video, Audio, Office, Text, Other
    """
    ext = ext.lower()
    if ext in CAT_PDF:
        return "PDF"
    if ext in CAT_MARKDOWN:
        return "Markdown"
    if ext in CAT_CODE:
        return "Code"
    if ext in CAT_IMAGE:
        return "Image"
    if ext in CAT_VIDEO:
        return "Video"
    if ext in CAT_AUDIO:
        return "Audio"
    if ext in CAT_OFFICE:
        return "Office"
    if ext in CAT_TEXT:
        return "Text"
    return "Other"


def get_file_category(file_path: str | Path) -> FileCategory:
    """Get the file category based on its extension"""
    ext = Path(file_path).suffix.lower()
    # PDF priority match
    if ext == ".pdf":
        return FileCategory.PDF
    if ext == ".md" or ext == ".markdown":
        return FileCategory.MARKDOWN
    return _EXTENSION_MAP.get(ext, FileCategory.UNKNOWN)


def get_file_size_str(size_bytes: int) -> str:
    """Convert byte count to a human-readable string"""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.1f} {units[i]}"


def safe_filename(name: str) -> str:
    """Convert a string to a safe filename"""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r'\s+', " ", name).strip()
    name = re.sub(r'[\.]+$', "", name)
    return name or "untitled"


def get_file_extension(file_path: str | Path) -> str:
    """Get the file extension (lowercase, with dot)"""
    return Path(file_path).suffix.lower()


def normalize_path(path: str | Path) -> Path:
    """Normalize a file path"""
    return Path(path).resolve()


def compute_file_hash(file_path: str | Path, algorithm: str = "sha256") -> str:
    """Compute the file hash value"""
    hasher = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_file_modified_time(file_path: str | Path) -> datetime:
    """Get the file modification time"""
    timestamp = os.path.getmtime(file_path)
    return datetime.fromtimestamp(timestamp)


def get_file_created_time(file_path: str | Path) -> datetime:
    """Get the file creation time"""
    timestamp = os.path.getctime(file_path)
    return datetime.fromtimestamp(timestamp)
