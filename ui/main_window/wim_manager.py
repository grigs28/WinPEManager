#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WIM映像管理模块
基于UnifiedWIMManager重建的WIM管理功能
"""

import os
import shutil
import subprocess
import platform
import ctypes
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from PyQt5.QtWidgets import (
    QMessageBox, QProgressDialog, QFileDialog, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QComboBox, QDialog,
    QTextEdit, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont

from ui.button_styler import apply_3d_button_style, apply_3d_button_style_alternate, apply_3d_button_style_red
from utils.logger import log_error


class WIMOperationThread(QThread):
    """WIM操作线程 - 统一处理所有WIM操作"""

    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    error_signal = pyqtSignal(str)

    def __init__(self, config_manager, adk_manager, parent, operation: str, build_dir: Path, **kwargs):
        super().__init__()
        self.config_manager = config_manager
        self.adk_manager = adk_manager
        self.parent = parent
        self.operation = operation
        self.build_dir = build_dir
        self.kwargs = kwargs
        self._is_running = True
    
    def run(self):
        """执行WIM操作"""
        try:
            from core.unified_manager import UnifiedWIMManager
            from utils.logger import get_logger
            
            logger = get_logger("WIMOperationThread")
            logger.info(f"开始执行WIM操作: {self.operation}")
            
            # 创建统一WIM管理器
            self.progress_signal.emit(10)
            wim_manager = UnifiedWIMManager(self.config_manager, self.adk_manager, self.parent)
            self.progress_signal.emit(20)
            
            # 根据操作类型执行相应的方法
            if self.operation == "mount":
                success, message = self._mount_operation(wim_manager, logger)
            elif self.operation == "unmount":
                success, message = self._unmount_operation(wim_manager, logger)
            elif self.operation == "create_iso":
                success, message = self._create_iso_operation(wim_manager, logger)
            elif self.operation == "create_usb":
                success, message = self._create_usb_operation(wim_manager, logger)
            elif self.operation == "smart_cleanup":
                success, message = self._smart_cleanup_operation(wim_manager, logger)
            else:
                success, message = False, f"不支持的操作类型: {self.operation}"
            
            self.progress_signal.emit(100)
            self.finished_signal.emit(success, message)
            
        except Exception as e:
            logger = get_logger("WIMOperationThread")
            logger.error(f"WIM操作异常: {str(e)}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            self.error_signal.emit(f"WIM操作过程中发生错误: {str(e)}")
    
    def _mount_operation(self, wim_manager, logger) -> Tuple[bool, str]:
        """挂载操作"""
        self.progress_signal.emit(30)
        self.log_signal.emit("检查挂载前条件...")
        
        # 执行挂载前检查
        wim_file_path = self.kwargs.get("wim_file_path")
        if not wim_file_path:
            # 获取主要WIM文件
            wim_file_path = wim_manager.get_primary_wim(self.build_dir)
            if not wim_file_path:
                return False, "未找到WIM文件"
        
        self.progress_signal.emit(40)
        self.log_signal.emit(f"开始挂载WIM文件: {wim_file_path.name}")
        
        # 执行挂载
        self.progress_signal.emit(60)
        success, message = wim_manager.mount_wim(self.build_dir, wim_file_path)
        
        self.progress_signal.emit(80)
        self.log_signal.emit("验证挂载结果...")
        
        return success, message
    
    def _unmount_operation(self, wim_manager, logger) -> Tuple[bool, str]:
        """卸载操作"""
        self.progress_signal.emit(30)
        self.log_signal.emit("检查卸载前条件...")
        
        # 执行卸载前检查
        success, message = wim_manager.pre_unmount_checks(self.build_dir)
        if not success:
            return False, message
        
        self.progress_signal.emit(40)
        commit = self.kwargs.get("commit", True)
        action_text = "保存更改并" if commit else "放弃更改并"
        self.log_signal.emit(f"开始{action_text}卸载...")
        
        # 执行卸载
        self.progress_signal.emit(60)
        success, message = wim_manager.unmount_wim(self.build_dir, commit=commit)
        
        self.progress_signal.emit(80)
        self.log_signal.emit("验证卸载结果...")
        
        return success, message
    
    def _create_iso_operation(self, wim_manager, logger) -> Tuple[bool, str]:
        """ISO创建操作"""
        self.progress_signal.emit(30)
        self.log_signal.emit("检查ISO创建前条件...")
        
        # 执行ISO创建前检查
        success, message = wim_manager.pre_iso_checks(self.build_dir)
        if not success:
            return False, message
        
        self.progress_signal.emit(40)
        iso_path = self.kwargs.get("iso_path")
        if not iso_path:
            return False, "未指定ISO输出路径"
        
        self.log_signal.emit(f"开始创建ISO文件: {Path(iso_path).name}")
        
        # 自动卸载已挂载的镜像
        self.progress_signal.emit(50)
        self.log_signal.emit("检查并自动卸载已挂载的镜像...")
        auto_success, auto_message = wim_manager.auto_unmount_before_iso(self.build_dir)
        if not auto_success:
            self.log_signal.emit(f"自动卸载警告: {auto_message}")
        
        # 创建ISO
        self.progress_signal.emit(70)
        success, message = wim_manager.create_iso(self.build_dir, Path(iso_path))
        
        self.progress_signal.emit(80)
        self.log_signal.emit("验证ISO创建结果...")
        
        return success, message
    
    def _create_usb_operation(self, wim_manager, logger) -> Tuple[bool, str]:
        """USB创建操作"""
        self.progress_signal.emit(30)
        self.log_signal.emit("检查USB创建前条件...")
        
        usb_path = self.kwargs.get("usb_path")
        if not usb_path:
            return False, "未指定USB设备路径"
        
        # 执行USB创建前检查
        success, message = wim_manager.pre_usb_checks(self.build_dir, Path(usb_path))
        if not success:
            return False, message
        
        self.progress_signal.emit(40)
        self.log_signal.emit(f"开始制作USB启动盘: {Path(usb_path).name}")
        
        # 创建USB
        self.progress_signal.emit(70)
        success, message = wim_manager.create_usb(self.build_dir, Path(usb_path))
        
        self.progress_signal.emit(80)
        self.log_signal.emit("验证USB创建结果...")
        
        return success, message
    
    def _smart_cleanup_operation(self, wim_manager, logger) -> Tuple[bool, str]:
        """智能清理操作"""
        self.progress_signal.emit(30)
        self.log_signal.emit("开始智能清理...")
        
        # 执行智能清理
        self.progress_signal.emit(60)
        cleanup_result = wim_manager.smart_cleanup(self.build_dir)
        
        self.progress_signal.emit(80)
        self.log_signal.emit("验证清理结果...")
        
        if cleanup_result.get("success", False):
            actions = cleanup_result.get("actions_taken", [])
            message = f"智能清理完成，执行了 {len(actions)} 个操作"
            if cleanup_result.get("warnings"):
                message += f"，有 {len(cleanup_result['warnings'])} 个警告"
            return True, message
        else:
            return False, "智能清理失败"
    
    def stop(self):
        """停止操作"""
        self._is_running = False


class WIMManager:
    """WIM映像管理器"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.config_manager = main_window.config_manager
        self.adk_manager = main_window.adk_manager
        
    def show_wim_manager_dialog(self):
        """显示WIM映像管理对话框"""
        try:
            # 创建WIM管理对话框
            dialog = WIMManagerDialog(self.main_window, self.config_manager, self.adk_manager)
            
            # 显示对话框
            if dialog.exec_() == QDialog.Accepted:
                # 刷新构建目录列表
                if hasattr(self.main_window, 'refresh_builds_list'):
                    self.main_window.refresh_builds_list()
                    
        except Exception as e:
            log_error(e, "显示WIM管理对话框")
            QMessageBox.critical(self.main_window, "错误", f"显示WIM管理对话框时发生错误: {str(e)}")


class WIMManagerDialog(QDialog):
    """WIM映像管理对话框 - 基于UnifiedWIMManager重建"""
    
    def __init__(self, parent, config_manager, adk_manager):
        super().__init__(parent)
        self.parent = parent
        self.config_manager = config_manager
        self.adk_manager = adk_manager
        
        # 创建统一WIM管理器
        self.wim_manager = None
        
        self.setWindowTitle("WIM映像管理")
        self.setModal(True)
        self.resize(1000, 800)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        
        # 创建工具栏
        toolbar_layout = QHBoxLayout()
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.setMinimumHeight(35)
        apply_3d_button_style(refresh_btn)
        refresh_btn.clicked.connect(self.refresh_wim_list)
        
        # 诊断按钮
        diagnose_btn = QPushButton("诊断信息")
        diagnose_btn.setMinimumHeight(35)
        apply_3d_button_style_alternate(diagnose_btn)
        diagnose_btn.clicked.connect(self.show_diagnostics)
        
        # 智能清理按钮
        cleanup_btn = QPushButton("智能清理")
        cleanup_btn.setMinimumHeight(35)
        apply_3d_button_style_red(cleanup_btn)
        cleanup_btn.clicked.connect(self.smart_cleanup)
        
        # 清空日志按钮
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.setMinimumHeight(35)
        apply_3d_button_style_alternate(clear_log_btn)
        clear_log_btn.clicked.connect(self.clear_log)
        
        toolbar_layout.addWidget(refresh_btn)
        toolbar_layout.addWidget(diagnose_btn)
        toolbar_layout.addWidget(cleanup_btn)
        toolbar_layout.addWidget(clear_log_btn)
        toolbar_layout.addStretch()
        
        # 创建WIM操作区域
        wim_group = QGroupBox("WIM映像操作")
        wim_layout = QVBoxLayout()
        
        # 第一行操作按钮
        row1_layout = QHBoxLayout()
        
        # 挂载WIM映像
        mount_btn = QPushButton("挂载WIM映像")
        mount_btn.setMinimumHeight(40)
        apply_3d_button_style(mount_btn)
        mount_btn.clicked.connect(self.mount_wim_image)
        
        # 卸载保存
        unmount_commit_btn = QPushButton("卸载并保存")
        unmount_commit_btn.setMinimumHeight(40)
        apply_3d_button_style_alternate(unmount_commit_btn)
        unmount_commit_btn.clicked.connect(self.unmount_wim_commit)
        
        # 卸载不保存
        unmount_discard_btn = QPushButton("卸载不保存")
        unmount_discard_btn.setMinimumHeight(40)
        apply_3d_button_style_red(unmount_discard_btn)
        unmount_discard_btn.clicked.connect(self.unmount_wim_discard)
        
        row1_layout.addWidget(mount_btn)
        row1_layout.addWidget(unmount_commit_btn)
        row1_layout.addWidget(unmount_discard_btn)
        
        # 第二行操作按钮
        row2_layout = QHBoxLayout()
        
        # 创建ISO
        iso_btn = QPushButton("创建ISO")
        iso_btn.setMinimumHeight(40)
        apply_3d_button_style(iso_btn)
        iso_btn.clicked.connect(self.create_iso)
        
        # 制作USB启动盘
        usb_btn = QPushButton("制作USB启动盘")
        usb_btn.setMinimumHeight(40)
        apply_3d_button_style(usb_btn)
        usb_btn.clicked.connect(self.create_usb_bootable)
        
        # 快速检查
        check_btn = QPushButton("快速检查")
        check_btn.setMinimumHeight(40)
        apply_3d_button_style_alternate(check_btn)
        check_btn.clicked.connect(self.quick_check)
        
        row2_layout.addWidget(iso_btn)
        row2_layout.addWidget(usb_btn)
        row2_layout.addWidget(check_btn)
        
        wim_layout.addLayout(row1_layout)
        wim_layout.addLayout(row2_layout)
        wim_group.setLayout(wim_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 创建状态显示区域
        status_group = QGroupBox("WIM映像列表")
        status_layout = QVBoxLayout()
        
        # WIM映像列表
        self.wim_list = QListWidget()
        self.wim_list.setMinimumHeight(250)
        self.wim_list.setMaximumHeight(300)
        self.wim_list.setStyleSheet("""
            QListWidget {
                font-family: 'Microsoft YaHei UI', 'SimHei';
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
                alternate-background-color: #f9f9f9;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
                border-radius: 3px;
                margin: 1px;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: white;
                font-weight: bold;
                border: 1px solid #005a9e;
            }
            QListWidget::item:hover {
                background-color: #f0f8ff;
                border: 1px solid #b3d9ff;
            }
        """)
        self.wim_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        status_layout.addWidget(QLabel("所有WinPE工作目录中的WIM映像文件:"))
        status_layout.addWidget(self.wim_list)
        
        status_group.setLayout(status_layout)
        
        # 创建日志显示区域
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout()
        
        # 日志文本框 - 使用与系统日志相同的字体和样式
        self.log_text = QTextEdit()
        self.log_text.setMinimumHeight(200)
        self.log_text.setMaximumHeight(250)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        # 移除自定义样式，使用与系统日志一致的默认样式
        
        log_layout.addWidget(QLabel("WIM操作日志信息:"))
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        
        # 添加到分割器
        splitter.addWidget(status_group)
        splitter.addWidget(log_group)
        splitter.setSizes([300, 200])
        
        # 添加到主布局
        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(wim_group)
        main_layout.addWidget(splitter)
        
        # 添加按钮区域
        button_layout = QHBoxLayout()
        
        close_btn = QPushButton("关闭")
        close_btn.setMinimumHeight(40)
        close_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        
        # 初始化数据
        self.init_wim_manager()
        self.refresh_wim_list()
        self.add_log_message("WIM管理器已初始化", "info")
    
    def init_wim_manager(self):
        """初始化统一WIM管理器"""
        try:
            from core.unified_manager import UnifiedWIMManager
            self.wim_manager = UnifiedWIMManager(self.config_manager, self.adk_manager, self.parent)
        except Exception as e:
            log_error(e, "初始化统一WIM管理器")
            QMessageBox.critical(self, "错误", f"初始化WIM管理器失败: {str(e)}")
    
    def refresh_wim_list(self):
        """刷新WIM文件列表 - 使用UnifiedWIMManager"""
        try:
            self.wim_list.clear()
            
            if not self.wim_manager:
                self.init_wim_manager()
            
            if not self.wim_manager:
                self.wim_list.addItem("WIM管理器未初始化")
                return
            
            # 获取工作空间路径
            workspace = Path(self.config_manager.get("output.workspace", ""))
            if not workspace.exists():
                workspace = Path.cwd() / "workspace" / "WinPE_Build"
            
            # 使用UnifiedWIMManager查找所有WIM文件
            all_wim_files = []
            if workspace.exists():
                all_wim_files = self.wim_manager.find_wim_files(workspace)
            
            # 按大小排序
            all_wim_files.sort(key=lambda x: x["size"], reverse=True)
            
            # 添加到列表
            for wim_file in all_wim_files:
                self.add_wim_item(wim_file)
            
            if not all_wim_files:
                self.wim_list.addItem("暂无WIM映像文件")
                
        except Exception as e:
            log_error(e, "刷新WIM文件列表")
            QMessageBox.critical(self, "错误", f"刷新WIM文件列表时发生错误: {str(e)}")
    
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
            
            self.wim_list.addItem(list_item)
            
        except Exception as e:
            log_error(e, "添加WIM文件项")
    
    def get_selected_wim(self) -> Optional[Dict]:
        """获取选中的WIM文件"""
        current_item = self.wim_list.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None
    
    def mount_wim_image(self):
        """挂载WIM映像"""
        try:
            wim_file = self.get_selected_wim()
            if not wim_file:
                QMessageBox.warning(self, "提示", "请先选择要挂载的WIM映像文件")
                return
            
            # 检查是否已经挂载
            if wim_file["mount_status"]:
                QMessageBox.information(self, "提示", f"WIM映像 {wim_file['name']} 已经挂载，无需重复挂载。")
                return
            
            # 检查管理员权限
            if not ctypes.windll.shell32.IsUserAnAdmin():
                reply = QMessageBox.question(
                    self, "需要管理员权限",
                    "WIM挂载操作需要管理员权限。\n\n是否以管理员身份重新启动程序？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.restart_as_admin()
                return
            
            # 直接使用UnifiedWIMManager挂载
            if not self.wim_manager:
                self.init_wim_manager()
                
            if self.wim_manager:
                self.add_log_message(f"开始挂载WIM映像: {wim_file['name']}", "info")
                success, message = self.wim_manager.mount_wim(wim_file["build_dir"], wim_file["path"])
                if success:
                    self.add_log_message(f"挂载成功: {message}", "success")
                    QMessageBox.information(self, "操作成功", f"挂载成功:\n{message}")
                    self.parent.log_message(f"挂载成功: {message}")
                    self.refresh_wim_list()
                else:
                    self.add_log_message(f"挂载失败: {message}", "error")
                    QMessageBox.critical(self, "操作失败", f"挂载失败:\n{message}")
                    self.parent.log_message(f"挂载失败: {message}")
            else:
                self.add_log_message("WIM管理器未初始化", "error")
                QMessageBox.critical(self, "错误", "WIM管理器未初始化")
                
        except Exception as e:
            log_error(e, "挂载WIM映像")
            QMessageBox.critical(self, "错误", f"挂载WIM映像时发生错误: {str(e)}")
    
    def unmount_wim_commit(self):
        """卸载WIM映像并保存"""
        self.unmount_wim_image(commit=True)
    
    def unmount_wim_discard(self):
        """卸载WIM映像不保存"""
        self.unmount_wim_image(commit=False)
    
    def unmount_wim_image(self, commit: bool = True):
        """卸载WIM映像"""
        try:
            wim_file = self.get_selected_wim()
            if not wim_file:
                QMessageBox.warning(self, "提示", "请先选择要卸载的WIM映像文件")
                return
            
            # 检查是否已挂载
            if not wim_file["mount_status"]:
                QMessageBox.warning(self, "提示", "选中的WIM映像未挂载")
                return
            
            # 检查管理员权限
            if not ctypes.windll.shell32.IsUserAnAdmin():
                reply = QMessageBox.question(
                    self, "需要管理员权限",
                    "WIM卸载操作需要管理员权限。\n\n是否以管理员身份重新启动程序？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.restart_as_admin()
                return
            
            # 直接使用UnifiedWIMManager卸载
            if not self.wim_manager:
                self.init_wim_manager()
                
            if self.wim_manager:
                action = "保存" if commit else "放弃"
                self.add_log_message(f"开始卸载WIM映像并{action}: {wim_file['name']}", "info")
                success, message = self.wim_manager.unmount_wim(wim_file["build_dir"], commit=commit)
                if success:
                    self.add_log_message(f"卸载成功: {message}", "success")
                    QMessageBox.information(self, "操作成功", f"卸载成功:\n{message}")
                    self.parent.log_message(f"卸载成功: {message}")
                    self.refresh_wim_list()
                else:
                    self.add_log_message(f"卸载失败: {message}", "error")
                    QMessageBox.critical(self, "操作失败", f"卸载失败:\n{message}")
                    self.parent.log_message(f"卸载失败: {message}")
            else:
                self.add_log_message("WIM管理器未初始化", "error")
                QMessageBox.critical(self, "错误", "WIM管理器未初始化")
                
        except Exception as e:
            log_error(e, f"卸载WIM映像并{action}")
            QMessageBox.critical(self, "错误", f"卸载WIM映像时发生错误: {str(e)}")
    
    def create_iso(self):
        """创建ISO"""
        try:
            wim_file = self.get_selected_wim()
            if not wim_file:
                QMessageBox.warning(self, "提示", "请先选择要创建ISO的WIM映像文件")
                return
            
            # 选择ISO输出路径
            iso_path, _ = QFileDialog.getSaveFileName(
                self,
                "选择ISO输出路径",
                str(wim_file["build_dir"] / f"{wim_file['build_dir'].name}.iso"),
                "ISO文件 (*.iso)"
            )
            
            if not iso_path:
                return
            
            # 检查管理员权限
            if not ctypes.windll.shell32.IsUserAnAdmin():
                reply = QMessageBox.question(
                    self, "需要管理员权限",
                    "ISO创建操作需要管理员权限。\n\n是否以管理员身份重新启动程序？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.restart_as_admin()
                return
            
            # 直接使用UnifiedWIMManager创建ISO
            if not self.wim_manager:
                self.init_wim_manager()
                
            if self.wim_manager:
                self.add_log_message(f"开始创建ISO: {Path(iso_path).name}", "info")
                success, message = self.wim_manager.create_iso(wim_file["build_dir"], Path(iso_path))
                if success:
                    self.add_log_message(f"ISO创建成功: {message}", "success")
                    QMessageBox.information(self, "操作成功", f"ISO创建成功:\n{message}")
                    self.parent.log_message(f"ISO创建成功: {message}")
                else:
                    self.add_log_message(f"ISO创建失败: {message}", "error")
                    QMessageBox.critical(self, "操作失败", f"ISO创建失败:\n{message}")
                    self.parent.log_message(f"ISO创建失败: {message}")
            else:
                self.add_log_message("WIM管理器未初始化", "error")
                QMessageBox.critical(self, "错误", "WIM管理器未初始化")
                
        except Exception as e:
            log_error(e, "创建ISO")
            QMessageBox.critical(self, "错误", f"创建ISO时发生错误: {str(e)}")
    
    def create_usb_bootable(self):
        """制作USB启动盘"""
        try:
            wim_file = self.get_selected_wim()
            if not wim_file:
                QMessageBox.warning(self, "提示", "请先选择要制作USB启动盘的WIM映像文件")
                return
            
            # 选择USB驱动器
            usb_path = QFileDialog.getExistingDirectory(
                self,
                "选择USB驱动器",
                "",
                QFileDialog.ShowDirsOnly
            )
            
            if not usb_path:
                return
            
            # 确认制作USB启动盘
            reply = QMessageBox.question(
                self,
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
                    self,
                    "需要管理员权限",
                    "USB启动盘制作需要管理员权限。\n\n是否以管理员身份重新启动程序？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.restart_as_admin()
                return
            
            # 直接使用UnifiedWIMManager制作USB
            if not self.wim_manager:
                self.init_wim_manager()
                
            if self.wim_manager:
                self.add_log_message(f"开始制作USB启动盘: {Path(usb_path).name}", "info")
                success, message = self.wim_manager.create_usb(wim_file["build_dir"], Path(usb_path))
                if success:
                    self.add_log_message(f"USB制作成功: {message}", "success")
                    QMessageBox.information(self, "操作成功", f"USB制作成功:\n{message}")
                    self.parent.log_message(f"USB制作成功: {message}")
                else:
                    self.add_log_message(f"USB制作失败: {message}", "error")
                    QMessageBox.critical(self, "操作失败", f"USB制作失败:\n{message}")
                    self.parent.log_message(f"USB制作失败: {message}")
            else:
                self.add_log_message("WIM管理器未初始化", "error")
                QMessageBox.critical(self, "错误", "WIM管理器未初始化")
                
        except Exception as e:
            log_error(e, "制作USB启动盘")
            QMessageBox.critical(self, "错误", f"制作USB启动盘时发生错误: {str(e)}")
    
    def quick_check(self):
        """快速检查"""
        try:
            wim_file = self.get_selected_wim()
            if not wim_file:
                QMessageBox.warning(self, "提示", "请先选择要检查的WIM映像文件")
                return
            
            if not self.wim_manager:
                QMessageBox.warning(self, "提示", "WIM管理器未初始化")
                return
            
            self.add_log_message(f"开始快速检查: {wim_file['name']}", "info")
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
            
            QMessageBox.information(self, "快速检查结果", result_text)
                
        except Exception as e:
            log_error(e, "快速检查")
            QMessageBox.critical(self, "错误", f"快速检查时发生错误: {str(e)}")
    
    def smart_cleanup(self):
        """智能清理"""
        try:
            wim_file = self.get_selected_wim()
            if not wim_file:
                QMessageBox.warning(self, "提示", "请先选择要清理的构建目录")
                return
            
            # 确认清理
            reply = QMessageBox.question(
                self,
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
            if not self.wim_manager:
                self.init_wim_manager()
                
            if self.wim_manager:
                self.add_log_message(f"开始智能清理: {wim_file['build_dir'].name}", "info")
                cleanup_result = self.wim_manager.smart_cleanup(wim_file["build_dir"])
                if cleanup_result.get("success", False):
                    actions = cleanup_result.get("actions_taken", [])
                    message = f"智能清理完成，执行了 {len(actions)} 个操作"
                    if cleanup_result.get("warnings"):
                        message += f"，有 {len(cleanup_result['warnings'])} 个警告"
                    self.add_log_message(f"智能清理成功: {message}", "success")
                    QMessageBox.information(self, "操作成功", f"智能清理成功:\n{message}")
                    self.parent.log_message(f"智能清理成功: {message}")
                    self.refresh_wim_list()
                else:
                    warnings = cleanup_result.get("warnings", [])
                    message = "智能清理失败"
                    if warnings:
                        message += f"，有 {len(warnings)} 个警告"
                    self.add_log_message(f"智能清理失败: {message}", "error")
                    QMessageBox.critical(self, "操作失败", f"智能清理失败:\n{message}")
                    self.parent.log_message(f"智能清理失败: {message}")
            else:
                self.add_log_message("WIM管理器未初始化", "error")
                QMessageBox.critical(self, "错误", "WIM管理器未初始化")
                
        except Exception as e:
            log_error(e, "智能清理")
            QMessageBox.critical(self, "错误", f"智能清理时发生错误: {str(e)}")
    
    def show_diagnostics(self):
        """显示诊断信息"""
        try:
            wim_file = self.get_selected_wim()
            if not wim_file:
                QMessageBox.warning(self, "提示", "请先选择要诊断的WIM映像文件")
                return
            
            if not self.wim_manager:
                QMessageBox.warning(self, "提示", "WIM管理器未初始化")
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
            
            QMessageBox.information(self, "诊断信息", diag_text)
                
        except Exception as e:
            log_error(e, "显示诊断信息")
            QMessageBox.critical(self, "错误", f"显示诊断信息时发生错误: {str(e)}")
    
    def clear_log(self):
        """清空日志"""
        try:
            self.log_text.clear()
            self.add_log_message("日志已清空", "info")
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
            self.log_text.append(formatted_message)
            
            # 确保总是显示最后一行
            self.log_text.moveCursor(self.log_text.textCursor().End)
            self.log_text.ensureCursorVisible()
            # 强制滚动到底部
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
            # 可选：如果需要颜色，可以设置文本格式
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.End)
            cursor.select(cursor.BlockUnderCursor)
            
            # 根据消息内容设置文本颜色
            if message.startswith("==="):
                # 分隔线，使用蓝色
                self.log_text.setTextColor(QColor("#0066CC"))
            elif message.startswith("✅"):
                # 成功消息，绿色
                self.log_text.setTextColor(QColor("green"))
            elif message.startswith("❌"):
                # 错误消息，红色
                self.log_text.setTextColor(QColor("red"))
            elif message.startswith("⚠️"):
                # 警告消息，橙色
                self.log_text.setTextColor(QColor("orange"))
            elif message.startswith("ℹ️"):
                # 信息消息，蓝色
                self.log_text.setTextColor(QColor("#0066CC"))
            elif message.startswith("步骤"):
                # 步骤消息，紫色
                self.log_text.setTextColor(QColor("#800080"))
            elif message.startswith("🎉"):
                # 完成消息，特殊颜色
                self.log_text.setTextColor(QColor("#FF1493"))
            else:
                # 普通消息，黑色
                self.log_text.setTextColor(QColor("black"))
            
            self.log_text.setTextCursor(cursor)
            
        except Exception as e:
            log_error(e, "添加日志消息")
    
    def execute_wim_operation(self, operation: str, build_dir: Path, **kwargs):
        """执行WIM操作"""
        try:
            # 创建进度对话框
            operation_names = {
                "mount": "挂载WIM映像",
                "unmount": "卸载WIM映像",
                "create_iso": "创建ISO",
                "create_usb": "制作USB启动盘",
                "smart_cleanup": "智能清理"
            }
            
            operation_name = operation_names.get(operation, operation)
            progress = QProgressDialog(f"正在{operation_name}...", "取消", 0, 100, self)
            progress.setWindowTitle(operation_name)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            # 创建操作线程
            self.operation_thread = WIMOperationThread(
                self.config_manager, 
                self.adk_manager, 
                self.parent, 
                operation, 
                build_dir, 
                **kwargs
            )
            self.operation_thread.progress_signal.connect(progress.setValue)
            self.operation_thread.log_signal.connect(lambda msg: self.parent.log_message(f"[WIM] {msg}"))
            self.operation_thread.finished_signal.connect(self.on_operation_finished)
            self.operation_thread.error_signal.connect(self.on_operation_error)
            
            # 保存进度对话框
            self.current_progress = progress
            self.current_operation = operation_name
            
            # 启动线程
            self.operation_thread.start()
                
        except Exception as e:
            log_error(e, f"执行WIM操作: {operation}")
            QMessageBox.critical(self, "错误", f"执行WIM操作时发生错误: {str(e)}")
    
    def on_operation_finished(self, success: bool, message: str):
        """操作完成回调"""
        try:
            # 关闭进度对话框
            if hasattr(self, 'current_progress'):
                self.current_progress.close()
            
            if success:
                QMessageBox.information(self, "操作成功", f"{self.current_operation}成功:\n{message}")
                self.parent.log_message(f"{self.current_operation}成功: {message}")
                self.refresh_wim_list()
            else:
                QMessageBox.critical(self, "操作失败", f"{self.current_operation}失败:\n{message}")
                self.parent.log_message(f"{self.current_operation}失败: {message}")
                
        except Exception as e:
            log_error(e, "操作完成回调")
            QMessageBox.critical(self, "错误", f"处理操作结果时发生错误: {str(e)}")
    
    def on_operation_error(self, error_message: str):
        """操作错误回调"""
        try:
            # 关闭进度对话框
            if hasattr(self, 'current_progress'):
                self.current_progress.close()
            
            QMessageBox.critical(self, "操作错误", f"{self.current_operation}过程中发生错误:\n{error_message}")
            self.parent.log_message(f"{self.current_operation}过程中发生错误: {error_message}")
                
        except Exception as e:
            log_error(e, "操作错误回调")
            QMessageBox.critical(self, "错误", f"处理操作错误时发生错误: {str(e)}")
    
    def on_item_double_clicked(self, item):
        """双击列表项事件"""
        try:
            wim_file = item.data(Qt.UserRole)
            if not wim_file:
                return
            
            # 如果已挂载，打开挂载目录
            if wim_file["mount_status"]:
                # 使用统一挂载目录
                if self.wim_manager:
                    mount_dir = self.wim_manager.get_mount_dir(wim_file["build_dir"])
                else:
                    mount_dir = wim_file["build_dir"] / "mount"
                
                if mount_dir.exists():
                    # 打开文件管理器
                    import subprocess
                    import platform
                    
                    if platform.system() == "Windows":
                        subprocess.run(['explorer', str(mount_dir)])
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(['open', str(mount_dir)])
                    else:  # Linux
                        subprocess.run(['xdg-open', str(mount_dir)])
                    
                    self.parent.log_message(f"已打开挂载目录: {mount_dir}")
                else:
                    QMessageBox.warning(self, "提示", f"挂载目录不存在: {mount_dir}")
            else:
                # 如果未挂载，提示用户
                reply = QMessageBox.question(
                    self, "提示", 
                    f"WIM映像 {wim_file['name']} 未挂载。\n\n是否要挂载此映像？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.mount_wim_image()
                    
        except Exception as e:
            log_error(e, "双击列表项")
            QMessageBox.critical(self, "错误", f"双击操作时发生错误: {str(e)}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 停止所有线程
            if hasattr(self, 'operation_thread') and self.operation_thread.isRunning():
                self.operation_thread.stop()
                self.operation_thread.wait(3000)
            
            event.accept()
            
        except Exception as e:
            log_error(e, "WIM管理对话框关闭")
            event.accept()
    
    def restart_as_admin(self):
        """以管理员身份重新启动程序"""
        try:
            import sys
            
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
            QMessageBox.critical(self, "重新启动失败", f"无法以管理员身份重新启动程序: {str(e)}")
