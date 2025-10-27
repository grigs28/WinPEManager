#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WIM映像管理模块 - 主入口
基于UnifiedWIMManager重建的WIM管理功能

此文件作为WIM管理模块的主入口点，导入并整合所有拆分后的子模块。
"""

# 导入所有拆分后的模块
from .wim_thread import WIMOperationThread
from .wim_manager_ui import WIMManager, WIMManagerDialogUI
from .wim_operations import WIMOperations
from .wim_dialog_utils import create_wim_manager_dialog

# 导出主要类和函数，保持向后兼容性
__all__ = [
    'WIMManager',
    'WIMManagerDialog',
    'WIMOperationThread',
    'WIMManagerDialogUI',
    'WIMOperations',
    'create_wim_manager_dialog'
]

# 为了保持向后兼容性，创建一个完整的对话框类
class WIMManagerDialog:
    """
    WIM映像管理对话框 - 完整实现
    这个类保持了原有的接口，确保现有代码不会破坏
    """

    def __init__(self, parent, config_manager, adk_manager):
        # 使用工厂函数创建对话框实例
        self._dialog = create_wim_manager_dialog(parent, config_manager, adk_manager)

    def __getattr__(self, name):
        """代理所有未定义的属性到内部对话框实例"""
        return getattr(self._dialog, name)

    def exec_(self):
        """代理exec_方法"""
        return self._dialog.exec_()

    def show(self):
        """代理show方法"""
        return self._dialog.show()

    def close(self):
        """代理close方法"""
        return self._dialog.close()