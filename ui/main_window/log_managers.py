#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口日志管理模块
提供日志显示和管理相关的方法
"""

import datetime
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from PyQt5.QtGui import QColor
from utils.logger import log_error


class LogManagers:
    """日志管理器类，包含所有日志相关的方法"""
    
    def __init__(self, main_window):
        self.main_window = main_window
    
    def log_message(self, message: str):
        """添加日志消息"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"

        # 简单的文本格式（不使用HTML，保持兼容性）
        self.main_window.log_text.append(formatted_message)
        # 确保总是显示最后一行
        self.main_window.log_text.moveCursor(self.main_window.log_text.textCursor().End)
        self.main_window.log_text.ensureCursorVisible()
        # 强制滚动到底部
        scrollbar = self.main_window.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # 可选：如果需要颜色，可以设置文本格式
        cursor = self.main_window.log_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.select(cursor.BlockUnderCursor)

        # 根据消息内容设置文本颜色
        if message.startswith("==="):
            # 分隔线，使用蓝色
            self.main_window.log_text.setTextColor(QColor("#0066CC"))
        elif message.startswith("✅"):
            # 成功消息，绿色
            self.main_window.log_text.setTextColor(QColor("green"))
        elif message.startswith("❌"):
            # 错误消息，红色
            self.main_window.log_text.setTextColor(QColor("red"))
        elif message.startswith("⚠️"):
            # 警告消息，橙色
            self.main_window.log_text.setTextColor(QColor("orange"))
        elif message.startswith("ℹ️"):
            # 信息消息，蓝色
            self.main_window.log_text.setTextColor(QColor("#0066CC"))
        elif message.startswith("步骤"):
            # 步骤消息，紫色
            self.main_window.log_text.setTextColor(QColor("#800080"))
        elif message.startswith("🎉"):
            # 完成消息，特殊颜色
            self.main_window.log_text.setTextColor(QColor("#FF1493"))
        else:
            # 普通消息，黑色
            self.main_window.log_text.setTextColor(QColor("black"))

        self.main_window.log_text.setTextCursor(cursor)

    def clear_log(self):
        """清空日志"""
        self.main_window.log_text.clear()
        self.log_message("=== 日志已清空 ===")

    def save_log(self):
        """保存日志"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"winpe_build_log_{timestamp}.txt"
            file_path, _ = QFileDialog.getSaveFileName(
                self.main_window, "保存日志", default_name, "文本文件 (*.txt);;所有文件 (*)"
            )
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # 保存纯文本格式的日志
                    plain_text = self.main_window.log_text.toPlainText()
                    f.write(plain_text)
                    # 添加额外的信息
                    f.write(f"\n\n=== 日志保存信息 ===\n")
                    f.write(f"保存时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"程序版本: WinPE制作管理器\n")
                self.log_message(f"✅ 日志已保存到: {file_path}")
                QMessageBox.information(self.main_window, "保存成功", f"日志已保存到: {file_path}")
        except Exception as e:
            self.log_message(f"❌ 保存日志失败: {str(e)}")
            log_error(e, "保存日志")