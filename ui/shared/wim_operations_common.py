#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WIM操作通用功能模块
提供WIM映像管理和开始构建界面的共享功能，避免代码重复
"""

import ctypes
import platform
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any

from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QApplication
from PyQt5.QtCore import Qt

from utils.logger import log_error


class WIMOperationsCommon:
    """WIM操作通用功能类"""

    def __init__(self, parent_widget, config_manager, adk_manager):
        """初始化通用WIM操作

        Args:
            parent_widget: 父窗口控件
            config_manager: 配置管理器
            adk_manager: ADK管理器
        """
        self.parent = parent_widget
        self.config_manager = config_manager
        self.adk_manager = adk_manager

        # 如果有主窗口，使用主窗口的log_message方法
        if hasattr(parent_widget, 'log_message'):
            self.main_log_message = parent_widget.log_message
        else:
            # 否则创建一个简单的日志输出方法
            self.main_log_message = lambda msg: print(f"[WIM Common] {msg}")

        # 创建统一的日志消息方法，同时输出到主窗口日志和WIM操作日志
        self.log_message = self._unified_log_message

        # 刷新回调函数，用于操作完成后刷新列表
        self.refresh_callbacks = []

        # WIM操作日志回调（用于WIM管理器对话框）
        self.wim_log_callback = None

    def set_wim_log_callback(self, callback):
        """设置WIM操作日志回调"""
        self.wim_log_callback = callback

    def _unified_log_message(self, message: str):
        """统一的日志消息方法，同时输出到主窗口日志和WIM操作日志"""
        try:
            # 输出到主窗口（构建日志）
            self.main_log_message(f"[WIM] {message}")

            # 如果有WIM操作日志回调，也输出到WIM操作日志
            if self.wim_log_callback and callable(self.wim_log_callback):
                # 为WIM操作日志添加时间戳和格式
                from datetime import datetime
                timestamp = datetime.now().strftime("%H:%M:%S")

                # 根据消息类型确定前缀
                if "成功" in message:
                    prefix = "✅"
                elif "失败" in message or "错误" in message:
                    prefix = "❌"
                elif "警告" in message:
                    prefix = "⚠️"
                else:
                    prefix = "ℹ️"

                # 使用与WIM管理器一致的格式
                wim_message = f"[{timestamp}] {prefix} {message}"
                self.wim_log_callback(wim_message, "info")
        except Exception as e:
            print(f"[WIM Common] 日志输出错误: {e}")

    def add_refresh_callback(self, callback):
        """添加刷新回调函数

        Args:
            callback: 回调函数，用于操作完成后刷新列表
        """
        if callback not in self.refresh_callbacks:
            self.refresh_callbacks.append(callback)

    def remove_refresh_callback(self, callback):
        """移除刷新回调函数

        Args:
            callback: 要移除的回调函数
        """
        if callback in self.refresh_callbacks:
            self.refresh_callbacks.remove(callback)

    def trigger_refresh(self):
        """触发所有刷新回调函数"""
        try:
            for callback in self.refresh_callbacks:
                if callable(callback):
                    callback()
        except Exception as e:
            log_error(e, "触发刷新回调")

    def get_selected_wim_info(self, list_widget) -> Optional[Dict]:
        """获取列表中选中的WIM文件信息

        Args:
            list_widget: 列表控件

        Returns:
            Dict: WIM文件信息，如果没有选中则返回None
        """
        current_item = list_widget.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None

    def show_warning(self, title: str, message: str):
        """显示警告对话框"""
        QMessageBox.warning(self.parent, title, message)

    def show_info(self, title: str, message: str):
        """显示信息对话框"""
        QMessageBox.information(self.parent, title, message)

    def show_critical(self, title: str, message: str):
        """显示错误对话框"""
        QMessageBox.critical(self.parent, title, message)

    def confirm_operation(self, title: str, message: str) -> bool:
        """确认操作对话框

        Returns:
            bool: 用户是否确认
        """
        reply = QMessageBox.question(
            self.parent, title, message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return reply == QMessageBox.Yes

    def open_directory(self, directory_path: Path):
        """使用系统默认程序打开目录

        Args:
            directory_path: 要打开的目录路径
        """
        try:
            if not directory_path.exists():
                self.show_warning("目录不存在", f"目录不存在: {directory_path}")
                return

            if platform.system() == "Windows":
                subprocess.run(["explorer", str(directory_path)])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(directory_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(directory_path)])

            self.log_message(f"已打开目录: {directory_path}")

        except Exception as e:
            log_error(e, "打开目录")
            self.show_critical("打开失败", f"打开目录失败: {str(e)}")

    def refresh_wim_list(self, list_widget, workspace_path: Optional[Path] = None) -> List[Dict]:
        """刷新WIM文件列表的通用方法

        Args:
            list_widget: 要刷新的列表控件
            workspace_path: 工作空间路径，如果为None则从配置中获取

        Returns:
            List[Dict]: 找到的WIM文件列表
        """
        try:
            list_widget.clear()

            # 获取工作空间路径
            if workspace_path is None:
                configured_workspace = self.config_manager.get("output.workspace", "").strip()
                if configured_workspace:
                    workspace = Path(configured_workspace)
                else:
                    architecture = self.config_manager.get("winpe.architecture", "amd64")
                    workspace = Path.cwd() / f"WinPE_{architecture}"
            else:
                workspace = workspace_path

            # 扫描工作空间中的所有构建目录
            if workspace.exists():
                from core.unified_manager import UnifiedWIMManager
                wim_manager = UnifiedWIMManager(self.config_manager, self.adk_manager, self.parent)
                all_wim_files = self._scan_workspace_for_wim_files(workspace, wim_manager)

                # 按修改时间排序
                all_wim_files.sort(key=lambda x: x["build_dir"].stat().st_mtime, reverse=True)

                # 添加到列表
                self._populate_wim_list(list_widget, all_wim_files)

                return all_wim_files

            return []

        except Exception as e:
            log_error(e, "刷新WIM文件列表")
            return []

    def _scan_workspace_for_wim_files(self, workspace: Path, wim_manager) -> List[Dict]:
        """扫描工作空间中所有构建目录的WIM文件

        Args:
            workspace: 工作空间路径
            wim_manager: UnifiedWIMManager实例

        Returns:
            List[Dict]: 所有找到的WIM文件信息
        """
        all_wim_files = []

        try:
            # 遍历工作空间中的所有子目录
            for build_dir in workspace.iterdir():
                # 只处理目录
                if not build_dir.is_dir():
                    continue

                # 跳过特殊目录（如mount目录）
                if build_dir.name in ['mount', 'temp', 'logs']:
                    continue

                # 检查是否是构建目录（包含WIM文件）
                wim_files_in_dir = wim_manager.find_wim_files(build_dir)
                if wim_files_in_dir:
                    all_wim_files.extend(wim_files_in_dir)

        except Exception as e:
            log_error(e, "扫描工作空间WIM文件")

        return all_wim_files

    def _populate_wim_list(self, list_widget, wim_files: List[Dict]):
        """填充WIM文件列表

        Args:
            list_widget: 列表控件
            wim_files: WIM文件信息列表
        """
        try:
            from PyQt5.QtWidgets import QListWidgetItem
            from PyQt5.QtGui import QColor

            for wim_file in wim_files:
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

                list_widget.addItem(list_item)

            if list_widget.count() == 0:
                list_widget.addItem("暂无WIM映像文件")

        except Exception as e:
            log_error(e, "填充WIM文件列表")

    def get_workspace_path(self) -> Path:
        """获取工作空间路径

        Returns:
            Path: 工作空间路径
        """
        configured_workspace = self.config_manager.get("output.workspace", "").strip()
        if configured_workspace:
            return Path(configured_workspace)
        else:
            architecture = self.config_manager.get("winpe.architecture", "amd64")
            return Path.cwd() / f"WinPE_{architecture}"

    def check_admin_privileges(self) -> bool:
        """检查管理员权限

        Returns:
            bool: 是否具有管理员权限
        """
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            return False

    def request_admin_restart(self, title: str, message: str) -> bool:
        """请求以管理员身份重新启动程序

        Args:
            title: 对话框标题
            message: 对话框消息

        Returns:
            bool: 用户是否同意重新启动
        """
        try:
            reply = QMessageBox.question(
                self.parent, title, message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                # 获取当前程序路径
                import sys
                if hasattr(sys, 'frozen'):
                    current_exe = sys.executable
                else:
                    current_exe = str(Path(__file__).parent.parent.parent / "main.py")

                # 请求管理员权限重新启动
                ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",  # 以管理员身份运行
                    current_exe,
                    " ".join(sys.argv[1:]),  # 传递原有参数
                    None,
                    1
                )

                # 退出当前程序
                from PyQt5.QtWidgets import QApplication
                QApplication.quit()
                sys.exit(0)
                return True
        except Exception as e:
            log_error(e, "请求管理员重新启动")
            return False

        return False

    def mount_wim_with_progress(self, wim_file: Dict, wim_manager, on_finished=None) -> bool:
        """带进度条的挂载WIM映像

        Args:
            wim_file: WIM文件信息
            wim_manager: UnifiedWIMManager实例
            on_finished: 完成回调函数 (success: bool, message: str)

        Returns:
            bool: 挂载操作是否启动成功
        """
        try:
            # 检查是否已经挂载
            if wim_file.get("mount_status", False):
                self.show_info("提示", f"WIM映像 {wim_file['name']} 已经挂载，无需重复挂载。")
                if on_finished:
                    on_finished(True, "已经挂载")
                # 触发刷新
                self.trigger_refresh()
                return True

            # 检查管理员权限
            if not self.check_admin_privileges():
                success = self.request_admin_restart(
                    "需要管理员权限",
                    "WIM挂载操作需要管理员权限。\n\n是否以管理员身份重新启动程序？"
                )
                return success

            # 创建进度对话框
            progress_dialog = QProgressDialog("正在挂载WIM映像...", "取消", 0, 100, self.parent)
            progress_dialog.setWindowTitle("挂载WIM映像")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.show()
            QApplication.processEvents()

            # 添加日志消息
            self.log_message(f"开始挂载WIM映像: {wim_file['name']}")

            # 在后台线程中执行挂载操作
            def mount_operation():
                try:
                    return wim_manager.mount_wim(wim_file["build_dir"], wim_file["path"])
                except Exception as e:
                    log_error(e, "挂载WIM映像")
                    return False, f"挂载失败: {str(e)}"

            # 使用线程实现异步操作，确保进度条正确更新
            import threading
            import time

            def execute_mount():
                try:
                    # 模拟挂载过程的进度更新
                    progress_dialog.setValue(10)
                    progress_dialog.setLabelText("正在检查挂载条件...")
                    QApplication.processEvents()
                    time.sleep(0.1)

                    success, message = mount_operation()

                    if success:
                        progress_dialog.setValue(80)
                        progress_dialog.setLabelText("正在完成挂载操作...")
                        QApplication.processEvents()
                        time.sleep(0.1)

                        progress_dialog.setValue(100)
                        progress_dialog.setLabelText("挂载完成")
                        QApplication.processEvents()

                        self.log_message(f"挂载成功: {message}")
                        self.show_info("操作成功", f"挂载成功:\n{message}")
                    else:
                        progress_dialog.setValue(100)
                        progress_dialog.setLabelText("挂载失败")
                        QApplication.processEvents()

                        self.log_message(f"挂载失败: {message}")
                        self.show_critical("操作失败", f"挂载失败:\n{message}")

                    # 触发刷新
                    self.trigger_refresh()

                    if on_finished:
                        on_finished(success, message)

                except Exception as e:
                    progress_dialog.setValue(100)
                    progress_dialog.setLabelText("操作失败")
                    QApplication.processEvents()

                    log_error(e, "执行挂载操作")
                    self.show_critical("操作失败", f"挂载操作时发生错误: {str(e)}")
                    if on_finished:
                        on_finished(False, str(e))
                finally:
                    time.sleep(0.5)  # 给用户时间看到完成状态
                    progress_dialog.close()

            # 在新线程中执行挂载操作
            mount_thread = threading.Thread(target=execute_mount, daemon=True)
            mount_thread.start()

            return True

        except Exception as e:
            log_error(e, "准备挂载操作")
            self.show_critical("操作失败", f"准备挂载操作时发生错误: {str(e)}")
            return False

    def unmount_wim_with_progress(self, wim_file: Dict, wim_manager, commit: bool = True, on_finished=None) -> bool:
        """带进度条的卸载WIM映像

        Args:
            wim_file: WIM文件信息
            wim_manager: UnifiedWIMManager实例
            commit: 是否保存更改
            on_finished: 完成回调函数 (success: bool, message: str)

        Returns:
            bool: 卸载操作是否启动成功
        """
        try:
            # 检查是否已挂载
            if not wim_file.get("mount_status", False):
                self.show_warning("提示", "选中的WIM映像未挂载")
                if on_finished:
                    on_finished(False, "未挂载")
                # 触发刷新
                self.trigger_refresh()
                return True

            # 检查管理员权限
            if not self.check_admin_privileges():
                success = self.request_admin_restart(
                    "需要管理员权限",
                    f"WIM卸载操作需要管理员权限。\n\n是否以管理员身份重新启动程序？"
                )
                return success

            # 创建进度对话框
            operation_name = "卸载并保存" if commit else "卸载不保存"
            progress_dialog = QProgressDialog(f"正在{operation_name}WIM映像...", "取消", 0, 100, self.parent)
            progress_dialog.setWindowTitle(operation_name)
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.show()
            QApplication.processEvents()

            # 添加日志消息
            self.log_message(f"开始{operation_name}WIM映像: {wim_file['name']}")

            # 在后台线程中执行卸载操作
            def unmount_operation():
                try:
                    return wim_manager.unmount_wim(wim_file["build_dir"], commit)
                except Exception as e:
                    log_error(e, "卸载WIM映像")
                    return False, f"卸载失败: {str(e)}"

            # 使用线程实现异步操作，确保进度条正确更新
            import threading
            import time

            def execute_unmount():
                try:
                    # 模拟卸载过程的进度更新
                    progress_dialog.setValue(10)
                    progress_dialog.setLabelText("正在检查卸载条件...")
                    QApplication.processEvents()
                    time.sleep(0.1)

                    success, message = unmount_operation()

                    if success:
                        progress_dialog.setValue(80)
                        progress_dialog.setLabelText(f"正在完成{operation_name}操作...")
                        QApplication.processEvents()
                        time.sleep(0.1)

                        progress_dialog.setValue(100)
                        progress_dialog.setLabelText(f"{operation_name}完成")
                        QApplication.processEvents()

                        self.log_message(f"{operation_name}成功: {message}")
                        self.show_info("操作成功", f"{operation_name}成功:\n{message}")
                    else:
                        progress_dialog.setValue(100)
                        progress_dialog.setLabelText(f"{operation_name}失败")
                        QApplication.processEvents()

                        self.log_message(f"{operation_name}失败: {message}")
                        self.show_critical("操作失败", f"{operation_name}失败:\n{message}")

                    # 触发刷新
                    self.trigger_refresh()

                    if on_finished:
                        on_finished(success, message)

                except Exception as e:
                    progress_dialog.setValue(100)
                    progress_dialog.setLabelText("操作失败")
                    QApplication.processEvents()

                    log_error(e, "执行卸载操作")
                    self.show_critical("操作失败", f"{operation_name}操作时发生错误: {str(e)}")
                    if on_finished:
                        on_finished(False, str(e))
                finally:
                    time.sleep(0.5)  # 给用户时间看到完成状态
                    progress_dialog.close()

            # 在新线程中执行卸载操作
            unmount_thread = threading.Thread(target=execute_unmount, daemon=True)
            unmount_thread.start()

            return True

        except Exception as e:
            log_error(e, "准备卸载操作")
            self.show_critical("操作失败", f"准备卸载操作时发生错误: {str(e)}")
            return False