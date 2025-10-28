#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WIM操作功能模块
包含WIM管理的所有核心操作功能
"""

import ctypes
from pathlib import Path
from typing import Optional, Dict

from PyQt5.QtWidgets import (
    QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt

from ui.button_styler import apply_3d_button_style_alternate
from utils.logger import log_error
from .wim_thread import WIMOperationThread as OriginalWIMOperationThread
from ui.shared.wim_operations_common import WIMOperationsCommon, WIMSignals
from ui.dialogs.progress_dialog import ProgressDialog, WIMOperationThread


class WIMOperations:
    """WIM操作功能类"""

    def __init__(self, dialog):
        self.dialog = dialog
        self.parent = dialog.parent
        self.config_manager = dialog.config_manager
        self.adk_manager = dialog.adk_manager
        self.wim_manager = dialog.wim_manager

        # 初始化共享的WIM操作功能
        self.wim_ops_common = WIMOperationsCommon(dialog, self.config_manager, self.adk_manager)

        # 创建信号实例
        self.signals = WIMSignals()

        # 设置刷新回调，用于操作完成后刷新WIM管理器列表
        self.wim_ops_common.add_refresh_callback(dialog.refresh_wim_list)

        # 设置WIM操作日志回调，用于在WIM管理器中显示日志
        self.wim_ops_common.set_wim_log_callback(dialog.add_log_message)

    def get_selected_wim(self) -> Optional[Dict]:
        """获取选中的WIM文件"""
        current_item = self.dialog.wim_list.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None

    def mount_wim_image(self):
        """挂载WIM映像"""
        try:
            wim_file = self.wim_ops_common.get_selected_wim_info(self.dialog.wim_list)
            if not wim_file:
                self.wim_ops_common.show_warning("提示", "请先选择要挂载的WIM映像文件")
                return

            # 检查是否已经挂载
            if wim_file.get("mount_status", False):
                self.wim_ops_common.show_info("提示", f"WIM映像 {wim_file['name']} 已经挂载，无需重复挂载。")
                self.dialog.refresh_wim_list()
                return

            # 检查管理员权限
            if not self.wim_ops_common.check_admin_privileges():
                self.wim_ops_common.request_admin_restart(
                    "需要管理员权限",
                    "WIM挂载操作需要管理员权限。\n\n是否以管理员身份重新启动程序？"
                )
                return

            # 使用带进度条的操作执行
            self.execute_wim_operation("mount", wim_file["build_dir"], wim_file_path=wim_file["path"])

        except Exception as e:
            log_error(e, "挂载WIM映像")
            self.wim_ops_common.show_critical("错误", f"挂载WIM映像时发生错误: {str(e)}")

    def unmount_wim_commit(self):
        """卸载WIM映像并保存"""
        self.unmount_wim_image(commit=True)

    def unmount_wim_discard(self):
        """卸载WIM映像不保存"""
        self.unmount_wim_image(commit=False)

    def unmount_wim_image(self, commit: bool = True):
        """卸载WIM映像"""
        try:
            wim_file = self.wim_ops_common.get_selected_wim_info(self.dialog.wim_list)
            if not wim_file:
                self.wim_ops_common.show_warning("提示", "请先选择要卸载的WIM映像文件")
                return

            # 检查是否已经卸载
            if not wim_file.get("mount_status", False):
                self.wim_ops_common.show_info("提示", f"WIM映像 {wim_file['name']} 未挂载，无需卸载。")
                self.dialog.refresh_wim_list()
                return

            # 使用带进度条的操作执行
            operation_type = "unmount_commit" if commit else "unmount_discard"
            self.execute_wim_operation(operation_type, wim_file["build_dir"], commit=commit)

        except Exception as e:
            action = "保存更改" if commit else "放弃更改"
            log_error(e, f"卸载WIM映像并{action}")
            self.wim_ops_common.show_critical("错误", f"卸载WIM映像时发生错误: {str(e)}")

    def create_iso(self):
        """创建ISO"""
        try:
            wim_file = self.get_selected_wim()
            if not wim_file:
                QMessageBox.warning(self.dialog, "提示", "请先选择要创建ISO的WIM映像文件")
                return

            # 选择ISO输出路径
            iso_path, _ = QFileDialog.getSaveFileName(
                self.dialog,
                "选择ISO输出路径",
                str(wim_file["build_dir"] / f"{wim_file['build_dir'].name}.iso"),
                "ISO文件 (*.iso)"
            )

            if not iso_path:
                return

            # 检查管理员权限
            if not ctypes.windll.shell32.IsUserAnAdmin():
                reply = QMessageBox.question(
                    self.dialog, "需要管理员权限",
                    "ISO创建操作需要管理员权限。\n\n是否以管理员身份重新启动程序？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    self.dialog.restart_as_admin()
                return

            # 直接使用UnifiedWIMManager创建ISO
            self.dialog.add_log_message(f"开始创建ISO: {Path(iso_path).name}", "info")
            success, message = self.wim_manager.create_iso(wim_file["build_dir"], Path(iso_path))
            if success:
                self.dialog.add_log_message(f"ISO创建成功: {message}", "success")
                QMessageBox.information(self.dialog, "操作成功", f"ISO创建成功:\n{message}")
                self.parent.log_message(f"ISO创建成功: {message}")
            else:
                self.dialog.add_log_message(f"ISO创建失败: {message}", "error")
                QMessageBox.critical(self.dialog, "操作失败", f"ISO创建失败:\n{message}")
                self.parent.log_message(f"ISO创建失败: {message}")

        except Exception as e:
            log_error(e, "创建ISO")
            QMessageBox.critical(self.dialog, "错误", f"创建ISO时发生错误: {str(e)}")

    def create_usb_bootable(self):
        """制作USB启动盘"""
        try:
            wim_file = self.get_selected_wim()
            if not wim_file:
                QMessageBox.warning(self.dialog, "提示", "请先选择要制作USB启动盘的WIM映像文件")
                return

            # 选择USB驱动器
            usb_path = QFileDialog.getExistingDirectory(
                self.dialog,
                "选择USB驱动器",
                "",
                QFileDialog.ShowDirsOnly
            )

            if not usb_path:
                return

            # 确认制作USB启动盘
            reply = QMessageBox.question(
                self.dialog,
                "确认制作USB启动盘",
                f"即将制作USB启动盘:\n\n"
                f"WIM文件: {wim_file['name']}\n"
                f"USB驱动器: {usb_path}\n\n"
                f"⚠️ 警告: 此操作将格式化USB驱动器并删除所有数据！\n\n"
                f"确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 检查管理员权限
            if not ctypes.windll.shell32.IsUserAnAdmin():
                reply = QMessageBox.question(
                    self.dialog,
                    "需要管理员权限",
                    "USB启动盘制作需要管理员权限。\n\n是否以管理员身份重新启动程序？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    self.dialog.restart_as_admin()
                return

            # 直接使用UnifiedWIMManager制作USB
            self.dialog.add_log_message(f"开始制作USB启动盘: {Path(usb_path).name}", "info")
            success, message = self.wim_manager.create_usb(wim_file["build_dir"], Path(usb_path))
            if success:
                self.dialog.add_log_message(f"USB制作成功: {message}", "success")
                QMessageBox.information(self.dialog, "操作成功", f"USB制作成功:\n{message}")
                self.parent.log_message(f"USB制作成功: {message}")
            else:
                self.dialog.add_log_message(f"USB制作失败: {message}", "error")
                QMessageBox.critical(self.dialog, "操作失败", f"USB制作失败:\n{message}")
                self.parent.log_message(f"USB制作失败: {message}")

        except Exception as e:
            log_error(e, "制作USB启动盘")
            QMessageBox.critical(self.dialog, "错误", f"制作USB启动盘时发生错误: {str(e)}")

    def quick_check(self):
        """快速检查"""
        try:
            wim_file = self.get_selected_wim()
            if not wim_file:
                QMessageBox.warning(self.dialog, "提示", "请先选择要检查的WIM映像文件")
                return

            self.dialog.add_log_message(f"开始快速检查: {wim_file['name']}", "info")
            # 直接使用UnifiedWIMManager执行快速检查
            check_result = self.wim_manager.quick_mount_check(wim_file["build_dir"])

            # 显示检查结果
            result_text = f"快速检查结果:\n\n"
            result_text += f"构建目录: {check_result.get('build_dir', 'N/A')}\n"
            result_text += f"主要WIM文件: {check_result.get('primary_wim', 'N/A')}\n"
            result_text += f"挂载状态: {'已挂载' if check_result.get('mount_status', {}).get('is_mounted', False) else '未挂载'}\n"
            result_text += f"挂载检查: {'通过' if check_result.get('mount_check_passed', False) else '失败'}\n"

            if check_result.get('mount_check_message'):
                result_text += f"检查消息: {check_result['mount_check_message']}\n"

            if check_result.get('recommendations'):
                result_text += f"\n建议:\n"
                for rec in check_result['recommendations']:
                    result_text += f"• {rec}\n"

            QMessageBox.information(self.dialog, "快速检查结果", result_text)

        except Exception as e:
            log_error(e, "快速检查")
            QMessageBox.critical(self.dialog, "错误", f"快速检查时发生错误: {str(e)}")

    def smart_cleanup(self):
        """智能清理"""
        try:
            wim_file = self.get_selected_wim()
            if not wim_file:
                QMessageBox.warning(self.dialog, "提示", "请先选择要清理的构建目录")
                return

            # 确认清理
            reply = QMessageBox.question(
                self.dialog,
                "确认智能清理",
                f"即将对构建目录进行智能清理:\n\n"
                f"构建目录: {wim_file['build_dir'].name}\n\n"
                f"智能清理将:\n"
                f"• 卸载已挂载的WIM镜像\n"
                f"• 清理临时文件和挂载目录\n"
                f"• 验证构建目录结构\n\n"
                f"确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply != QMessageBox.Yes:
                return

            # 直接使用UnifiedWIMManager执行智能清理
            self.dialog.add_log_message(f"开始智能清理: {wim_file['build_dir'].name}", "info")
            cleanup_result = self.wim_manager.smart_cleanup(wim_file["build_dir"])
            if cleanup_result.get("success", False):
                actions = cleanup_result.get("actions_taken", [])
                message = f"智能清理完成，执行了 {len(actions)} 个操作"
                if cleanup_result.get("warnings"):
                    message += f"，有 {len(cleanup_result['warnings'])} 个警告"
                self.dialog.add_log_message(f"智能清理成功: {message}", "success")
                QMessageBox.information(self.dialog, "操作成功", f"智能清理成功:\n{message}")
                self.parent.log_message(f"智能清理成功: {message}")
                self.dialog.refresh_wim_list()
            else:
                warnings = cleanup_result.get("warnings", [])
                message = "智能清理失败"
                if warnings:
                    message += f"，有 {len(warnings)} 个警告"
                self.dialog.add_log_message(f"智能清理失败: {message}", "error")
                QMessageBox.critical(self.dialog, "操作失败", f"智能清理失败:\n{message}")
                self.parent.log_message(f"智能清理失败: {message}")

        except Exception as e:
            log_error(e, "智能清理")
            QMessageBox.critical(self.dialog, "错误", f"智能清理时发生错误: {str(e)}")

    def show_diagnostics(self):
        """显示诊断信息"""
        try:
            wim_file = self.get_selected_wim()
            if not wim_file:
                QMessageBox.warning(self.dialog, "提示", "请先选择要诊断的WIM映像文件")
                return

            # 直接使用UnifiedWIMManager获取诊断信息
            diagnostics = self.wim_manager.get_diagnostics(wim_file["build_dir"])

            # 显示诊断信息
            diag_text = f"诊断信息:\n\n"
            diag_text += f"时间戳: {diagnostics.get('timestamp', 'N/A')}\n"
            diag_text += f"构建目录: {diagnostics.get('build_directory', 'N/A')}\n\n"

            # 构建信息
            build_info = diagnostics.get('build_info', {})
            if build_info:
                diag_text += "构建信息:\n"
                diag_text += f"• WIM文件数量: {len(build_info.get('wim_files', []))}\n"
                diag_text += f"• 创建时间: {build_info.get('created_time', 'N/A')}\n\n"

            # 挂载状态
            mount_status = diagnostics.get('mount_status', {})
            if mount_status:
                diag_text += "挂载状态:\n"
                diag_text += f"• 挂载状态: {'已挂载' if mount_status.get('is_mounted', False) else '未挂载'}\n"
                diag_text += f"• 挂载目录: {mount_status.get('mount_dir', 'N/A')}\n\n"

            # 验证结果
            validation = diagnostics.get('validation', {})
            if validation:
                diag_text += "结构验证:\n"
                diag_text += f"• 验证状态: {'通过' if validation.get('is_valid', False) else '失败'}\n"
                if validation.get('errors'):
                    diag_text += "• 错误:\n"
                    for error in validation['errors']:
                        diag_text += f"  - {error}\n"
                if validation.get('warnings'):
                    diag_text += "• 警告:\n"
                    for warning in validation['warnings']:
                        diag_text += f"  - {warning}\n"
                diag_text += "\n"

            # 系统状态
            system_status = diagnostics.get('system_info', {})
            if system_status:
                diag_text += "系统状态:\n"
                diag_text += f"• Python版本: {system_status.get('python_version', 'N/A')}\n"
                diag_text += f"• 平台: {system_status.get('platform', 'N/A')}\n"
                diag_text += f"• 管理员权限: {'是' if system_status.get('is_admin', False) else '否'}\n"

            QMessageBox.information(self.dialog, "诊断信息", diag_text)

        except Exception as e:
            log_error(e, "显示诊断信息")
            QMessageBox.critical(self.dialog, "错误", f"显示诊断信息时发生错误: {str(e)}")

    def execute_wim_operation(self, operation: str, build_dir: Path, **kwargs):
        """执行WIM操作"""
        try:
            # 操作名称映射
            operation_names = {
                "mount": "挂载WIM映像",
                "unmount_commit": "卸载WIM映像(保存更改)",
                "unmount_discard": "卸载WIM映像(放弃更改)",
                "create_iso": "创建ISO",
                "create_usb": "制作USB启动盘",
                "smart_cleanup": "智能清理"
            }

            operation_name = operation_names.get(operation, operation)

            # 创建新的进度对话框
            progress_dialog = ProgressDialog(
                self.dialog,
                title=operation_name,
                show_log=True,
                can_cancel=True
            )
            progress_dialog.set_title(f"正在{operation_name}")
            progress_dialog.set_current_operation("准备开始...")
            progress_dialog.show()

            # 获取WIM管理器
            wim_manager = self.wim_manager

            # 创建操作线程（使用新的WIMOperationThread）
            if operation in ["mount", "unmount_commit", "unmount_discard"]:
                # 对于挂载和卸载操作，使用专门的进度对话框
                if operation == "mount":
                    operation_thread = WIMOperationThread(
                        'mount', wim_manager, build_dir,
                        kwargs.get('wim_file_path')
                    )
                else:  # unmount operations
                    commit_changes = operation == "unmount_commit"
                    operation_thread = WIMOperationThread(
                        'unmount', wim_manager, build_dir, commit_changes
                    )
            else:
                # 对于其他操作，使用原有的线程
                operation_thread = OriginalWIMOperationThread(
                    self.config_manager,
                    self.adk_manager,
                    self.parent,
                    operation,
                    build_dir,
                    **kwargs
                )

            # 连接信号
            if operation in ["mount", "unmount_commit", "unmount_discard"]:
                # 新的WIMOperationThread信号
                operation_thread.progress.connect(progress_dialog.set_progress)
                operation_thread.log.connect(progress_dialog.add_log)
                operation_thread.finished.connect(
                    lambda success, msg: self._on_operation_finished(progress_dialog, success, msg, operation)
                )
                progress_dialog.cancelled.connect(operation_thread.cancel)
            else:
                # 原有的WIMOperationThread信号
                operation_thread.progress_signal.connect(progress_dialog.set_progress)
                operation_thread.log_signal.connect(progress_dialog.add_log)
                operation_thread.finished_signal.connect(
                    lambda success, msg: self._on_operation_finished(progress_dialog, success, msg, operation)
                )
                operation_thread.error_signal.connect(
                    lambda error_msg: self._on_operation_finished(progress_dialog, False, error_msg, operation)
                )

            # 线程完成后删除
            if operation in ["mount", "unmount_commit", "unmount_discard"]:
                operation_thread.finished.connect(operation_thread.deleteLater)
            else:
                operation_thread.finished_signal.connect(operation_thread.deleteLater)

            # 保存进度对话框引用
            self.dialog.current_progress_dialog = progress_dialog
            self.dialog.current_operation = operation_name

            # 启动线程
            operation_thread.start()

        except Exception as e:
            log_error(e, f"执行WIM操作: {operation}")
            QMessageBox.critical(self.dialog, "错误", f"执行WIM操作时发生错误: {str(e)}")

    def _on_operation_finished(self, progress_dialog, success, message, operation):
        """操作完成回调"""
        try:
            progress_dialog.set_completed(success, message)

            if success:
                # 刷新列表
                self.dialog.refresh_wim_list()

                # 显示成功消息
                if operation in ["mount", "unmount_commit", "unmount_discard"]:
                    QMessageBox.information(
                        self.dialog,
                        "操作成功",
                        f"{message}"
                    )
                    self.parent.log_message(f"WIM操作成功: {message} [WIM操作]")
            else:
                # 显示错误消息
                QMessageBox.critical(
                    self.dialog,
                    "操作失败",
                    f"操作失败: {message}"
                )
                self.parent.log_message(f"WIM操作失败: {message} [WIM操作]")

        except Exception as e:
            log_error(e, "处理操作完成回调")
            QMessageBox.critical(self.dialog, "错误", f"处理操作结果时发生错误: {str(e)}")