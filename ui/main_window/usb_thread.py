#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USB制作线程 - 使用统一WIM管理器
"""

from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal

from utils.logger import log_error


class USBBootableThread(QThread):
    """USB启动盘制作线程"""

    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)
    error_signal = pyqtSignal(str)

    def __init__(self, build_dir: Path, usb_path: Path, main_window, config_manager, adk_manager):
        super().__init__()
        self.build_dir = build_dir
        self.usb_path = usb_path
        self.main_window = main_window
        self.config_manager = config_manager
        self.adk_manager = adk_manager
        self._is_running = True

    def run(self):
        """执行USB启动盘制作"""
        try:
            from core.unified_manager import UnifiedWIMManager

            # 创建统一WIM管理器
            self.progress_signal.emit(10)
            if not self._is_running:
                return

            wim_manager = UnifiedWIMManager(
                self.config_manager,
                self.adk_manager,
                self.main_window
            )

            self.progress_signal.emit(20)
            if not self._is_running:
                return

            # 使用统一管理器制作USB
            success, message = wim_manager.create_usb(self.build_dir, self.usb_path)

            if self._is_running:
                self.progress_signal.emit(100)
                self.finished_signal.emit(success, message)

        except Exception as e:
            if self._is_running:
                log_error(e, "USB制作线程")
                self.error_signal.emit(f"USB制作过程中发生错误: {str(e)}")

    def stop(self):
        """停止操作"""
        self._is_running = False