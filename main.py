#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinPE制作管理程序主入口
用于创建和管理自定义Windows PE环境
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTranslator, QLocale
from PyQt5.QtGui import QIcon

from ui.main_window import MainWindow
from utils.logger import setup_logger
from core.config_manager import ConfigManager
from core.simple_icon import get_icon_manager, set_random_icon
from core.version_manager import get_version_manager


def setup_application():
    """设置应用程序基本配置"""
    # 设置控制台编码
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    
    app = QApplication(sys.argv)

    # 设置应用程序信息
    app.setApplicationName("WinPE制作管理器")

    # 从版本管理器获取版本信息
    version_manager = get_version_manager(project_root)
    current_version = version_manager.get_version_string()
    app.setApplicationVersion(current_version)

    app.setOrganizationName("WinPE管理工具")

    # 设置随机应用程序图标
    # 从ico目录随机选择PNG图标
    icon_manager = get_icon_manager(project_root / "ico")
    if icon_manager.has_icons():
        set_random_icon(app)
    else:
        logger.warning("ico目录中没有找到PNG图标文件")

    # 设置中文本地化
    translator = QTranslator()
    if translator.load("zh_CN", ":/translations"):
        app.installTranslator(translator)

    return app


def main():
    """主函数"""
    try:
        # 设置日志
        log_file = project_root / "logs" / "winpe_manager.log"
        setup_logger(log_file)

        # 确保必要的目录存在
        for dir_name in ["logs", "output", "config", "drivers", "scripts", "templates"]:
            (project_root / dir_name).mkdir(exist_ok=True)

        # 初始化配置管理器
        config_manager = ConfigManager()

        # 创建应用程序
        app = setup_application()

        # 创建主窗口
        main_window = MainWindow(config_manager)
        main_window.show()

        # 运行应用程序
        sys.exit(app.exec_())

    except Exception as e:
        logging.error(f"程序启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    main()