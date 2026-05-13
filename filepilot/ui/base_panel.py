"""BasePanel — 所有功能面板的基类

提供共享信号、取消操作支持和统计卡片方法。
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class BasePanel(QWidget):
    """所有功能面板的基类，提供共享信号和通用方法。"""

    # === 共享信号 ===
    status_message = Signal(str)
    progress_updated = Signal(int)
    progress_text = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # 取消操作支持
        self._cancelled: bool = False

        # 取消按钮（由子类添加到各自布局中）
        self.btn_cancel = QPushButton("✕ 取消")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._on_cancel)

        # 统计卡片字典（仅使用 _make_stat_card 的面板需要初始化）
        self.stat_cards: dict[str, QLabel] = {}

    # ── 取消操作 ──────────────────────────────────────────────

    def reset_cancel(self) -> None:
        """启动新操作前调用，清空取消标志。"""
        self._cancelled = False

    @Slot()
    def _on_cancel(self) -> None:
        """取消当前操作（设置标志，由子类增强）。"""
        self._cancelled = True
        self.status_message.emit("⏹️ 正在取消...")

    @Slot()
    def _on_cancel_done(self) -> None:
        """取消完成后恢复 UI（由子类覆写以处理各自的控件）。"""
        self.btn_cancel.setVisible(False)
        # 安全地隐藏进度条（如果有）
        progress_bar = getattr(self, "progress_bar", None)
        if progress_bar is not None:
            progress_bar.setVisible(False)
        progress_label = getattr(self, "progress_label", None)
        if progress_label is not None:
            progress_label.setVisible(False)

    # ── 统计卡片 ──────────────────────────────────────────────

    def _make_stat_card(self, title: str, value: str) -> QFrame:
        """创建统一样式的统计卡片。"""
        card = QFrame()
        card.setObjectName("statCard")
        card.setStyleSheet("""
            QFrame#statCard {
                background: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 11px; color: #6c7086;")
        title_label.setAlignment(Qt.AlignCenter)

        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        value_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #cdd6f4;"
        )
        value_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        self.stat_cards[title] = value_label
        return card

    def _update_stat(self, title: str, value: str) -> None:
        """更新统计卡片的值。"""
        if title in self.stat_cards:
            self.stat_cards[title].setText(str(value))
