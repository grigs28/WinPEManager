#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinPE制作管理程序主入口
用于创建和管理自定义Windows PE环境
"""

import sys
import os
import logging
import importlib.util
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTranslator, QLocale
from PyQt5.QtGui import QIcon

# 使用importlib直接导入main_window.py模块文件
main_window_spec = importlib.util.spec_from_file_location(
    "main_window_module", 
    project_root / "ui" / "main_window.py"
)
main_window_module = importlib.util.module_from_spec(main_window_spec)
main_window_spec.loader.exec_module(main_window_module)
MainWindow = main_window_module.MainWindow

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
        build_log_path = project_root / "logs" / "build_logs"
        
        # 使用增强的日志系统
        setup_logger(
            log_file_path=log_file,
            enable_system_log=True,
            enable_build_log=True,
            build_log_path=build_log_path,
            app_name="WinPEManager",
            context={"app_version": "1.0.0", "startup_time": "now"}
        )

        # 确保必要的目录存在
        for dir_name in ["logs", "output", "config", "drivers", "scripts", "templates"]:
            (project_root / dir_name).mkdir(exist_ok=True)

        # 记录应用程序启动
        from utils.logger import log_system_event
        log_system_event("应用程序启动", "WinPE管理器应用程序已启动", "info")

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
        
        # 尝试记录启动错误到系统日志
        try:
            from utils.logger import log_system_event
            log_system_event("应用程序启动失败", f"程序启动失败: {str(e)}", "error")
        except:
            pass  # 如果日志系统也无法工作，则忽略
            
        return 1


if __name__ == "__main__":
    main()