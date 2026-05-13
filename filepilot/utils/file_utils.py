"""文件操作工具函数"""

import hashlib
import os
import re
from datetime import datetime
from enum import Enum
from pathlib import Path


class FileCategory(Enum):
    """文件分类"""
    DOCUMENT = ("文档", ".txt,.doc,.docx,.rtf,.odt", "📄")
    IMAGE = ("图片", ".jpg,.jpeg,.png,.gif,.bmp,.svg,.webp,.ico", "🖼️")
    VIDEO = ("视频", ".mp4,.avi,.mkv,.mov,.wmv,.flv,.webm", "🎬")
    AUDIO = ("音频", ".mp3,.wav,.flac,.aac,.ogg,.wma,.m4a", "🎵")
    CODE = ("代码", ".py,.js,.ts,.java,.cpp,.c,.h,.hpp,.cs,.go,.rs,.rb,.php,.swift,.kt,.scala,.sql,.sh,.bash,.ps1,.bat,.pl,.lua,.r,.m,.dart", "💻")
    ARCHIVE = ("压缩包", ".zip,.rar,.7z,.tar,.gz,.bz2,.xz,.zst,.iso", "🗜️")
    PDF = ("PDF", ".pdf", "📕")
    MARKDOWN = ("Markdown", ".md,.markdown,.rst", "📝")
    SPREADSHEET = ("表格", ".xls,.xlsx,.csv,.ods", "📊")
    PRESENTATION = ("演示", ".ppt,.pptx,.odp,.key", "📽️")
    DATA = ("数据", ".json,.xml,.yaml,.yml,.toml,.ini,.cfg,.conf", "🗃️")
    EXECUTABLE = ("可执行文件", ".exe,.msi,.app,.dmg,.deb,.rpm,.sh,.bat", "⚙️")
    FONT = ("字体", ".ttf,.otf,.woff,.woff2,.eot", "🔤")
    UNKNOWN = ("其他", "", "❓")

    def __init__(self, label: str, extensions: str, icon: str):
        self.label = label
        self.extensions = set(extensions.split(",")) if extensions else set()
        self.icon = icon


# 扩展名到分类的映射
_EXTENSION_MAP: dict[str, FileCategory] = {}
for cat in FileCategory:
    for ext in cat.extensions:
        _EXTENSION_MAP[ext.strip().lower()] = cat


def get_file_category(file_path: str | Path) -> FileCategory:
    """根据文件扩展名获取分类"""
    ext = Path(file_path).suffix.lower()
    # PDF 优先匹配
    if ext == ".pdf":
        return FileCategory.PDF
    if ext == ".md" or ext == ".markdown":
        return FileCategory.MARKDOWN
    return _EXTENSION_MAP.get(ext, FileCategory.UNKNOWN)


def get_file_size_str(size_bytes: int) -> str:
    """将字节数转为人类可读的字符串"""
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
    """将字符串转为安全的文件名"""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r'\s+', " ", name).strip()
    name = re.sub(r'[\.]+$', "", name)
    return name or "untitled"


def get_file_extension(file_path: str | Path) -> str:
    """获取文件扩展名（小写，带点）"""
    return Path(file_path).suffix.lower()


def normalize_path(path: str | Path) -> Path:
    """规范化路径"""
    return Path(path).resolve()


def compute_file_hash(file_path: str | Path, algorithm: str = "sha256") -> str:
    """计算文件哈希值"""
    hasher = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_file_modified_time(file_path: str | Path) -> datetime:
    """获取文件修改时间"""
    timestamp = os.path.getmtime(file_path)
    return datetime.fromtimestamp(timestamp)


def get_file_created_time(file_path: str | Path) -> datetime:
    """获取文件创建时间"""
    timestamp = os.path.getctime(file_path)
    return datetime.fromtimestamp(timestamp)
