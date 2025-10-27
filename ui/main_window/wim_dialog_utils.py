#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WIM对话框工具函数模块
包含WIM管理器的辅助工具函数
"""

import ctypes
import sys
import subprocess
import platform
from pathlib import Path
from typing import Dict, List

from PyQt5.QtWidgets import QMessageBox, QDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from utils.logger import log_error


class WIMDialogUtils:
    """WIM对话框工具类"""

    def __init__(self, dialog):
        self.dialog = dialog
        self.parent = dialog.parent
        self.config_manager = dialog.config_manager
        self.wim_manager = dialog.wim_manager

    def refresh_wim_list(self):
        """刷新WIM文件列表 - 使用UnifiedWIMManager"""
        try:
            self.dialog.wim_list.clear()

            # 获取工作空间路径
            configured_workspace = self.config_manager.get("output.workspace", "").strip()
            if configured_workspace:
                workspace = Path(configured_workspace)
            else:
                # 使用基于架构的默认工作空间
                architecture = self.config_manager.get("winpe.architecture", "amd64")
                workspace = Path.cwd() / f"WinPE_{architecture}"

            # 使用UnifiedWIMManager查找所有WIM文件
            all_wim_files = []
            if workspace.exists():
                # 查找工作空间下的所有子目录，每个子目录作为构建目录
                build_dirs = [d for d in workspace.iterdir() if d.is_dir() and d.name != "mount"]

                # 如果工作空间中没有子目录，尝试直接在工作空间中查找
                if not build_dirs:
                    build_dirs = [workspace]

                # 在每个构建目录中查找WIM文件
                for build_dir in build_dirs:
                    wim_files_in_dir = self.wim_manager.find_wim_files(build_dir)
                    all_wim_files.extend(wim_files_in_dir)

            # 按大小排序
            all_wim_files.sort(key=lambda x: x["size"], reverse=True)

            # 添加到列表
            for wim_file in all_wim_files:
                self.add_wim_item(wim_file)

            if not all_wim_files:
                self.dialog.wim_list.addItem("暂无WIM映像文件")

        except Exception as e:
            log_error(e, "刷新WIM文件列表")
            QMessageBox.critical(self.dialog, "错误", f"刷新WIM文件列表时发生错误: {str(e)}")

    def add_wim_item(self, wim_file: Dict):
        """添加WIM文件项到列表"""
        try:
            # 计算文件大小
            size_mb = wim_file["size"] / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{size_mb*1024:.0f} KB"

            # 状态文本
            status_text = "已挂载" if wim_file["mount_status"] else "未挂载"

            # 构建目录信息
            build_dir_name = wim_file["build_dir"].name
            import datetime
            ctime = wim_file["build_dir"].stat().st_ctime
            time_str = datetime.datetime.fromtimestamp(ctime).strftime('%Y-%m-%d %H:%M')

            # WIM相对路径
            wim_relative_path = str(wim_file["path"]).replace(str(wim_file["build_dir"]), "").lstrip("\\/")

            # 为已挂载项添加图标
            display_name = wim_file['name']
            if wim_file["mount_status"] and not display_name.startswith("📂 "):
                display_name = f"📂 {display_name}"

            # 创建显示文本
            item_text = f"{display_name} - {size_str} - {wim_file['type'].upper()} - {status_text} - {build_dir_name} ({time_str}) - {wim_relative_path}"

            from PyQt5.QtWidgets import QListWidgetItem
            list_item = QListWidgetItem(item_text)
            list_item.setData(Qt.UserRole, wim_file)

            # 设置增强的工具提示
            tooltip_info = (
                f"WIM文件: {wim_file['name']}\n"
                f"─────────────────\n"
                f"构建目录: {build_dir_name}\n"
                f"创建时间: {time_str}\n"
                f"文件大小: {size_str}\n"
                f"文件类型: {wim_file['type'].upper()}\n"
                f"挂载状态: {status_text}\n"
                f"相对路径: {wim_relative_path}\n"
                f"─────────────────\n"
                f"完整路径: {wim_file['path']}\n"
                f"构建目录: {wim_file['build_dir']}"
            )
            list_item.setToolTip(tooltip_info)

            # 设置状态样式
            if wim_file["mount_status"]:
                # 已挂载项使用绿色背景和图标
                list_item.setBackground(QColor("#E8F5E8"))
                list_item.setForeground(QColor("#2E7D32"))  # 深绿色文字
                list_item.setData(Qt.UserRole + 1, "mounted")
            else:
                # 未挂载项使用默认样式
                list_item.setForeground(QColor("#333333"))  # 深灰色文字
                list_item.setData(Qt.UserRole + 1, "unmounted")

            self.dialog.wim_list.addItem(list_item)

        except Exception as e:
            log_error(e, "添加WIM文件项")

    def clear_log(self):
        """清空日志"""
        try:
            self.dialog.log_text.clear()
            self.dialog.add_log_message("日志已清空", "info")
        except Exception as e:
            log_error(e, "清空日志")

    def add_log_message(self, message: str, level: str = "info"):
        """添加日志消息到日志窗口"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")

            # 根据日志级别设置颜色
            if level == "error":
                color = "#ff6b6b"
                prefix = "❌"
            elif level == "warning":
                color = "#ffa726"
                prefix = "⚠️"
            elif level == "success":
                color = "#51cf66"
                prefix = "✅"
            else:
                color = "#d4d4d4"
                prefix = "ℹ️"

            # 使用简单文本格式，与系统日志保持一致
            formatted_message = f"[{timestamp}] {prefix} {message}"

            # 添加到日志窗口
            self.dialog.log_text.append(formatted_message)

            # 确保总是显示最后一行
            self.dialog.log_text.moveCursor(self.dialog.log_text.textCursor().End)
            self.dialog.log_text.ensureCursorVisible()
            # 强制滚动到底部
            scrollbar = self.dialog.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

            # 可选：如果需要颜色，可以设置文本格式
            cursor = self.dialog.log_text.textCursor()
            cursor.movePosition(cursor.End)
            cursor.select(cursor.BlockUnderCursor)

            # 根据消息内容设置文本颜色
            if message.startswith("==="):
                # 分隔线，使用蓝色
                self.dialog.log_text.setTextColor(QColor("#0066CC"))
            elif message.startswith("✅"):
                # 成功消息，绿色
                self.dialog.log_text.setTextColor(QColor("green"))
            elif message.startswith("❌"):
                # 错误消息，红色
                self.dialog.log_text.setTextColor(QColor("red"))
            elif message.startswith("⚠️"):
                # 警告消息，橙色
                self.dialog.log_text.setTextColor(QColor("orange"))
            elif message.startswith("ℹ️"):
                # 信息消息，蓝色
                self.dialog.log_text.setTextColor(QColor("#0066CC"))
            elif message.startswith("步骤"):
                # 步骤消息，紫色
                self.dialog.log_text.setTextColor(QColor("#800080"))
            elif message.startswith("🎉"):
                # 完成消息，特殊颜色
                self.dialog.log_text.setTextColor(QColor("#FF1493"))
            else:
                # 普通消息，黑色
                self.dialog.log_text.setTextColor(QColor("black"))

            self.dialog.log_text.setTextCursor(cursor)

        except Exception as e:
            log_error(e, "添加日志消息")

    def on_operation_finished(self, success: bool, message: str):
        """操作完成回调"""
        try:
            # 关闭进度对话框
            if hasattr(self.dialog, 'current_progress'):
                self.dialog.current_progress.close()

            if success:
                QMessageBox.information(self.dialog, "操作成功", f"{self.dialog.current_operation}成功:\n{message}")
                self.parent.log_message(f"{self.dialog.current_operation}成功: {message}")
                self.dialog.refresh_wim_list()
            else:
                QMessageBox.critical(self.dialog, "操作失败", f"{self.dialog.current_operation}失败:\n{message}")
                self.parent.log_message(f"{self.dialog.current_operation}失败: {message}")

        except Exception as e:
            log_error(e, "操作完成回调")
            QMessageBox.critical(self.dialog, "错误", f"处理操作结果时发生错误: {str(e)}")

    def on_operation_error(self, error_message: str):
        """操作错误回调"""
        try:
            # 关闭进度对话框
            if hasattr(self.dialog, 'current_progress'):
                self.dialog.current_progress.close()

            QMessageBox.critical(self.dialog, "操作错误", f"{self.dialog.current_operation}过程中发生错误:\n{error_message}")
            self.parent.log_message(f"{self.dialog.current_operation}过程中发生错误: {error_message}")

        except Exception as e:
            log_error(e, "操作错误回调")
            QMessageBox.critical(self.dialog, "错误", f"处理操作错误时发生错误: {str(e)}")

    def on_item_double_clicked(self, item):
        """双击列表项事件"""
        try:
            wim_file = item.data(Qt.UserRole)
            if not wim_file:
                return

            # 如果已挂载，打开挂载目录
            if wim_file["mount_status"]:
                # 使用统一挂载目录
                mount_dir = self.wim_manager.get_mount_dir(wim_file["build_dir"])

                if mount_dir.exists():
                    # 打开文件管理器
                    if platform.system() == "Windows":
                        subprocess.run(['explorer', str(mount_dir)])
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(['open', str(mount_dir)])
                    else:  # Linux
                        subprocess.run(['xdg-open', str(mount_dir)])

                    self.parent.log_message(f"已打开挂载目录: {mount_dir}")
                else:
                    QMessageBox.warning(self.dialog, "提示", f"挂载目录不存在: {mount_dir}")
            else:
                # 如果未挂载，提示用户
                reply = QMessageBox.question(
                    self.dialog, "提示",
                    f"WIM映像 {wim_file['name']} 未挂载。\n\n是否要挂载此映像？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    # 通过dialog调用mount_wim_image方法
                    self.dialog.mount_wim_image()

        except Exception as e:
            log_error(e, "双击列表项")
            QMessageBox.critical(self.dialog, "错误", f"双击操作时发生错误: {str(e)}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 停止所有线程
            if hasattr(self.dialog, 'operation_thread') and self.dialog.operation_thread.isRunning():
                self.dialog.operation_thread.stop()
                self.dialog.operation_thread.wait(3000)

            event.accept()

        except Exception as e:
            log_error(e, "WIM管理对话框关闭")
            event.accept()

    def restart_as_admin(self):
        """以管理员身份重新启动程序"""
        try:
            # 获取当前程序路径
            if hasattr(sys, 'frozen'):
                current_exe = sys.executable
            else:
                current_exe = str(Path(__file__).parent.parent.parent / "main.py")

            # 请求管理员权限重新启动
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                current_exe,
                " ".join(sys.argv[1:]),
                None,
                1
            )

            # 退出当前程序
            from PyQt5.QtWidgets import QApplication
            QApplication.quit()
            sys.exit(0)

        except Exception as e:
            QMessageBox.critical(self.dialog, "重新启动失败", f"无法以管理员身份重新启动程序: {str(e)}")


def create_wim_manager_dialog(parent, config_manager, adk_manager):
    """创建WIM管理器对话框的工厂函数"""
    from .wim_manager_ui import WIMManagerDialogUI
    from .wim_operations import WIMOperations
    from .wim_dialog_utils import WIMDialogUtils

    class WIMManagerDialog(WIMManagerDialogUI):
        """完整的WIM管理器对话框实现"""

        def __init__(self, parent, config_manager, adk_manager):
            super().__init__(parent, config_manager, adk_manager)

            # 初始化操作和工具类
            self.operations = WIMOperations(self)
            self.utils = WIMDialogUtils(self)

            # 绑定方法到内部实现
            self._refresh_wim_list_impl = self.utils.refresh_wim_list
            self._show_diagnostics_impl = self.operations.show_diagnostics
            self._smart_cleanup_impl = self.operations.smart_cleanup
            self._clear_log_impl = self.utils.clear_log
            self._mount_wim_image_impl = self.operations.mount_wim_image
            self._unmount_wim_commit_impl = self.operations.unmount_wim_commit
            self._unmount_wim_discard_impl = self.operations.unmount_wim_discard
            self._create_iso_impl = self.operations.create_iso
            self._create_usb_bootable_impl = self.operations.create_usb_bootable
            self._quick_check_impl = self.operations.quick_check
            self._on_item_double_clicked_impl = self.utils.on_item_double_clicked
            self._add_log_message_impl = self.utils.add_log_message
            self._execute_wim_operation_impl = self.operations.execute_wim_operation
            self._reject_impl = lambda: self.close()
            self._on_operation_finished_impl = self.utils.on_operation_finished
            self._on_operation_error_impl = self.utils.on_operation_error
            self.closeEvent = self.utils.closeEvent
            self.restart_as_admin = self.utils.restart_as_admin

            # 初始化数据
            self.refresh_wim_list()
            self.add_log_message("WIM管理器已初始化", "info")

        def reject(self):
            """关闭对话框"""
            self.close()

    return WIMManagerDialog(parent, config_manager, adk_manager)