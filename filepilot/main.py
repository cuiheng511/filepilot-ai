#!/usr/bin/env python3
"""FilePilot AI — 智能文件管家 启动入口"""

import sys

from filepilot.app import create_app, create_services, load_settings
from filepilot.ui.main_window import MainWindow


def main():
    """主函数"""
    app = create_app()

    # 加载设置
    settings = load_settings()

    # 创建服务
    services = create_services(settings)

    # 创建主窗口（注入服务实例）
    window = MainWindow(services=services)
    window.show()

    # 运行事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
