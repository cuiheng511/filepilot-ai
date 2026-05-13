"""FilePilot AI 应用配置"""

import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from filepilot.ai.cloud_ai import CloudAI
from filepilot.ai.local_ai import LocalAI
from filepilot.ai.summarizer import Summarizer
from filepilot.core.duplicate_finder import DuplicateFinder
from filepilot.core.file_organizer import FileOrganizer
from filepilot.core.file_scanner import FileScanner
from filepilot.core.indexer import FileIndexer
from filepilot.ui.main_window import MainWindow


def create_app() -> QApplication:
    """创建 QApplication 实例"""
    app = QApplication(sys.argv)
    app.setApplicationName("FilePilot AI")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("FilePilot")

    # 设置全局字体
    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)

    # 全局样式
    app.setStyle("Fusion")

    return app


def load_settings() -> dict:
    """加载用户设置"""
    settings_path = Path.home() / ".filepilot" / "settings.json"
    if settings_path.exists():
        try:
            return json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def create_services(settings: dict) -> dict:
    """创建各服务模块实例"""
    ai_mode = settings.get("ai_mode", "local")

    # AI 引擎
    local_ai = LocalAI(model=settings.get("ollama_model", "qwen2.5:7b"))
    cloud_ai = CloudAI(
        api_key=settings.get("openai_key", ""),
        model=settings.get("openai_model", "gpt-4o-mini"),
    )

    # 摘要器
    summarizer = Summarizer(
        local_ai=local_ai,
        cloud_ai=cloud_ai,
        prefer_local=(ai_mode in ("local", "hybrid")),
    )

    return {
        "scanner": FileScanner(),
        "organizer": FileOrganizer(),
        "duplicate_finder": DuplicateFinder(),
        "indexer": FileIndexer(
            index_dir=settings.get("index_dir", "~/.filepilot/index")
        ),
        "local_ai": local_ai,
        "cloud_ai": cloud_ai,
        "summarizer": summarizer,
    }
