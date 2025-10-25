#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单图标选择模块
从ico目录中随机选择PNG文件作为程序图标
"""

import os
import random
from pathlib import Path
from typing import Optional, List
import logging

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSize

logger = logging.getLogger("WinPEManager")


class SimpleIconManager:
    """简单的图标管理器，从ico目录选择PNG文件"""

    def __init__(self, ico_dir: Optional[Path] = None):
        """
        初始化图标管理器

        Args:
            ico_dir: 图标目录路径，如果为None则使用默认路径
        """
        if ico_dir is None:
            ico_dir = Path(__file__).parent.parent / "ico"

        self.ico_dir = Path(ico_dir)
        self.png_files: List[Path] = []
        self.current_icon: Optional[Path] = None

        # 扫描PNG文件
        self.scan_png_files()

    def scan_png_files(self) -> None:
        """扫描ico目录中的PNG文件"""
        self.png_files.clear()

        if not self.ico_dir.exists():
            logger.warning(f"图标目录不存在: {self.ico_dir}")
            return

        # 查找所有.png文件
        for png_file in self.ico_dir.glob("*.png"):
            if png_file.is_file():
                self.png_files.append(png_file)

        logger.info(f"找到 {len(self.png_files)} 个PNG文件: {[f.name for f in self.png_files]}")

    def get_random_icon(self) -> Optional[QIcon]:
        """
        随机获取一个图标

        Returns:
            QIcon: 随机选择的图标，如果没有图标则返回None
        """
        if not self.png_files:
            logger.warning("没有找到可用的PNG文件")
            return None

        # 随机选择一个PNG文件
        selected_png = random.choice(self.png_files)
        self.current_icon = selected_png

        logger.info(f"随机选择图标: {selected_png.name}")

        try:
            # 创建QIcon，从PNG文件创建
            pixmap = QPixmap(str(selected_png))
            if not pixmap.isNull():
                # 调整图标大小到合适尺寸
                scaled_pixmap = pixmap.scaled(32, 32, aspectRatioMode=1, transformMode=1)
                return QIcon(scaled_pixmap)
            else:
                logger.error(f"无法加载PNG文件: {selected_png}")
                return None
        except Exception as e:
            logger.error(f"加载图标失败 {selected_png}: {str(e)}")
            return None

    def get_random_icon_for_window(self) -> Optional[QIcon]:
        """
        为窗口获取随机图标（可能使用不同尺寸）

        Returns:
            QIcon: 适合窗口的图标
        """
        if not self.png_files:
            return None

        selected_png = random.choice(self.png_files)

        try:
            # 为窗口创建稍大的图标
            pixmap = QPixmap(str(selected_png))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(64, 64, aspectRatioMode=1, transformMode=1)
                return QIcon(scaled_pixmap)
        except Exception as e:
            logger.error(f"创建窗口图标失败 {selected_png}: {str(e)}")

        return None

    def get_current_icon_info(self) -> dict:
        """
        获取当前图标信息

        Returns:
            dict: 包含当前图标信息的字典
        """
        return {
            "current_icon": str(self.current_icon) if self.current_icon else None,
            "available_icons": [str(f) for f in self.png_files],
            "total_icons": len(self.png_files),
            "ico_dir": str(self.ico_dir)
        }

    def refresh_icon_list(self) -> None:
        """重新扫描PNG文件列表"""
        logger.info("重新扫描PNG文件...")
        self.scan_png_files()

    def has_icons(self) -> bool:
        """
        检查是否有可用的图标文件

        Returns:
            bool: 是否有可用的图标文件
        """
        return len(self.png_files) > 0


# 全局图标管理器实例
_icon_manager: Optional[SimpleIconManager] = None


def get_icon_manager(ico_dir: Optional[Path] = None) -> SimpleIconManager:
    """
    获取全局图标管理器实例

    Args:
        ico_dir: 图标目录路径

    Returns:
        SimpleIconManager: 图标管理器实例
    """
    global _icon_manager
    if _icon_manager is None:
        _icon_manager = SimpleIconManager(ico_dir)
    return _icon_manager


def set_random_icon(app_or_window) -> bool:
    """
    为应用程序或窗口设置随机图标

    Args:
        app_or_window: QApplication或QWindow实例

    Returns:
        bool: 是否成功设置图标
    """
    icon_manager = get_icon_manager()
    icon = icon_manager.get_random_icon()

    if icon:
        try:
            app_or_window.setWindowIcon(icon)
            logger.info("成功设置随机图标")
            return True
        except Exception as e:
            logger.error(f"设置图标失败: {str(e)}")

    return False


def set_random_window_icon(window) -> bool:
    """
    为窗口设置随机图标

    Args:
        window: QWindow实例

    Returns:
        bool: 是否成功设置图标
    """
    icon_manager = get_icon_manager()
    icon = icon_manager.get_random_icon_for_window()

    if icon:
        try:
            window.setWindowIcon(icon)
            logger.info("成功设置窗口随机图标")
            return True
        except Exception as e:
            logger.error(f"设置窗口图标失败: {str(e)}")

    return False