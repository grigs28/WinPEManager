#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按钮立体效果样式器
为程序中的所有按钮添加立体3D效果
"""

from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QLinearGradient, QPalette, QColor, QFont


def apply_3d_button_style(button):
    """为按钮应用立体3D样式"""
    
    # 设置按钮大小和文字样式
    button.setMinimumHeight(22)
    button.setMinimumWidth(85)

    # 设置字体
    font = QFont("Microsoft YaHei", 9, QFont.Bold)
    button.setFont(font)

    # 设置柔和的立体3D样式表
    style = """
        QPushButton {
            min-height: 22px;
            min-width: 85px;
            border: 1px solid #C0C0C0;
            border-radius: 6px;
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #F5F5F5, stop: 0.5 #E8E8E8, stop: 1 #DCDCDC);
            color: #333333;
            font-weight: 500;
            font-size: 9pt;
            font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
            text-align: center;
            padding: 4px 10px;
        }

        QPushButton:hover {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #E8E8E8, stop: 0.5 #D8D8D8, stop: 1 #C8C8C8);
            border: 1px solid #B8B8B8;
        }

        QPushButton:pressed {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #C8C8C8, stop: 0.5 #B8B8B8, stop: 1 #A8A8A8);
            border: 1px solid #A8A8A8;
            padding: 5px 9px 3px 11px;
        }

        QPushButton:disabled {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #F0F0F0, stop: 1 #E0E0E0);
            color: #999999;
            border: 1px solid #D0D0D0;
            font-weight: normal;
        }
    """

    button.setStyleSheet(style)
    return style


def apply_3d_button_style_alternate(button):
    """为按钮应用交替立体3D样式（绿色系）"""
    
    # 设置按钮大小和文字样式
    button.setMinimumHeight(22)
    button.setMinimumWidth(85)

    # 设置字体
    font = QFont("Microsoft YaHei", 9, QFont.Bold)
    button.setFont(font)

    # 设置柔和的绿色立体3D样式表
    style = """
        QPushButton {
            min-height: 22px;
            min-width: 85px;
            border: 1px solid #C0C0C0;
            border-radius: 6px;
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #F5F5F5, stop: 0.5 #E8E8E8, stop: 1 #DCDCDC);
            color: #333333;
            font-weight: 500;
            font-size: 9pt;
            font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
            text-align: center;
            padding: 4px 10px;
        }

        QPushButton:hover {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #E8E8E8, stop: 0.5 #D8D8D8, stop: 1 #C8C8C8);
            border: 1px solid #B8B8B8;
        }

        QPushButton:pressed {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #C8C8C8, stop: 0.5 #B8B8B8, stop: 1 #A8A8A8);
            border: 1px solid #A8A8A8;
            padding: 5px 9px 3px 11px;
        }

        QPushButton:disabled {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #F0F0F0, stop: 1 #E0E0E0);
            color: #999999;
            border: 1px solid #D0D0D0;
            font-weight: normal;
        }
    """

    button.setStyleSheet(style)
    return style


def apply_flat_modern_style(button):
    """为按钮应用扁平现代样式"""

    button.setMinimumHeight(22)
    button.setMinimumWidth(85)

    font = QFont("Segoe UI", 9)
    button.setFont(font)

    style = """
        QPushButton {
            min-height: 22px;
            min-width: 85px;
            border: 1px solid #C0C0C0;
            border-radius: 6px;
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #F5F5F5, stop: 0.5 #E8E8E8, stop: 1 #DCDCDC);
            color: #333333;
            font-weight: 500;
            font-size: 9px;
            text-align: center;
            padding: 4px 10px;
        }

        QPushButton:hover {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #E8E8E8, stop: 0.5 #D8D8D8, stop: 1 #C8C8C8);
            border: 1px solid #B8B8B8;
        }

        QPushButton:pressed {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #C8C8C8, stop: 0.5 #B8B8B8, stop: 1 #A8A8A8);
            border: 1px solid #A8A8A8;
            padding: 5px 9px 3px 11px;
        }

        QPushButton:disabled {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #F0F0F0, stop: 1 #E0E0E0);
            color: #999999;
            border: 1px solid #D0D0D0;
            font-weight: normal;
        }
    """

    button.setStyleSheet(style)
    return style


def apply_3d_button_style_red(button):
    """为按钮应用红色立体3D样式（用于危险操作）"""
    
    # 设置按钮大小和文字样式
    button.setMinimumHeight(22)
    button.setMinimumWidth(85)

    # 设置字体
    font = QFont("Microsoft YaHei", 9, QFont.Bold)
    button.setFont(font)

    # 设置柔和的红色立体3D样式表
    style = """
        QPushButton {
            min-height: 22px;
            min-width: 85px;
            border: 1px solid #C0C0C0;
            border-radius: 6px;
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #F5F5F5, stop: 0.5 #E8E8E8, stop: 1 #DCDCDC);
            color: #333333;
            font-weight: 500;
            font-size: 9pt;
            font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
            text-align: center;
            padding: 4px 10px;
        }

        QPushButton:hover {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #E8E8E8, stop: 0.5 #D8D8D8, stop: 1 #C8C8C8);
            border: 1px solid #B8B8B8;
        }

        QPushButton:pressed {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #C8C8C8, stop: 0.5 #B8B8B8, stop: 1 #A8A8A8);
            border: 1px solid #A8A8A8;
            padding: 5px 9px 3px 11px;
        }

        QPushButton:disabled {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #F0F0F0, stop: 1 #E0E0E0);
            color: #999999;
            border: 1px solid #D0D0D0;
            font-weight: normal;
        }
    """

    button.setStyleSheet(style)
    return style


def apply_styled_button(button, style_type="3d_blue"):
    """根据类型应用不同样式"""

    style_functions = {
        "3d_blue": apply_3d_button_style,
        "3d_green": apply_3d_button_style_alternate,
        "3d_red": apply_3d_button_style_red,
        "flat_modern": apply_flat_modern_style,
        "default": lambda btn: None  # 默认样式
    }

    if style_type in style_functions:
        return style_functions[style_type](button)
    else:
        return apply_3d_button_style(button)  # 默认使用蓝色立体样式