#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WIM管理器UI界面模块
包含WIM管理器的主界面和UI初始化
"""

from pathlib import Path

from PyQt5.QtWidgets import (
    QMessageBox, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QComboBox, QDialog,
    QTextEdit, QSplitter
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

from ui.button_styler import apply_3d_button_style, apply_3d_button_style_alternate, apply_3d_button_style_red
from utils.logger import log_error
from core.unified_manager import UnifiedWIMManager
from .wim_dialog_utils import create_wim_manager_dialog


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
            dialog = create_wim_manager_dialog(self.main_window, self.config_manager, self.adk_manager)

            # 显示对话框
            if dialog.exec_() == QDialog.Accepted:
                # 刷新构建目录列表
                if hasattr(self.main_window, 'refresh_builds_list'):
                    self.main_window.refresh_builds_list()

        except Exception as e:
            log_error(e, "显示WIM管理对话框")
            QMessageBox.critical(self.main_window, "错误", f"显示WIM管理对话框时发生错误: {str(e)}")


class WIMManagerDialogUI(QDialog):
    """WIM管理对话框UI基类"""

    def __init__(self, parent, config_manager, adk_manager):
        super().__init__(parent)
        self.parent = parent
        self.config_manager = config_manager
        self.adk_manager = adk_manager

        # 创建统一WIM管理器
        self.wim_manager = UnifiedWIMManager(config_manager, adk_manager, parent)

        self.setup_ui()

    def setup_ui(self):
        """设置UI界面"""
        self.setWindowTitle("WIM映像管理")
        self.setModal(True)
        self.resize(1000, 800)

        # 创建主布局
        main_layout = QVBoxLayout()

        # 创建工具栏
        toolbar_layout = self.create_toolbar()

        # 创建WIM操作区域
        wim_group = self.create_operation_area()

        # 创建分割器和内容区域
        splitter = self.create_content_area()

        # 添加到主布局
        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(wim_group)
        main_layout.addWidget(splitter)

        # 添加按钮区域
        button_layout = self.create_button_area()
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def create_toolbar(self):
        """创建工具栏"""
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

        return toolbar_layout

    def create_operation_area(self):
        """创建WIM操作区域"""
        wim_group = QGroupBox("WIM映像操作")
        wim_layout = QVBoxLayout()

        # 第一行操作按钮
        row1_layout = self.create_first_row_buttons()

        # 第二行操作按钮
        row2_layout = self.create_second_row_buttons()

        wim_layout.addLayout(row1_layout)
        wim_layout.addLayout(row2_layout)
        wim_group.setLayout(wim_layout)

        return wim_group

    def create_first_row_buttons(self):
        """创建第一行操作按钮"""
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

        return row1_layout

    def create_second_row_buttons(self):
        """创建第二行操作按钮"""
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

        return row2_layout

    def create_content_area(self):
        """创建内容区域"""
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)

        # 创建状态显示区域
        status_group = self.create_status_area()

        # 创建日志显示区域
        log_group = self.create_log_area()

        # 添加到分割器
        splitter.addWidget(status_group)
        splitter.addWidget(log_group)
        splitter.setSizes([300, 200])

        return splitter

    def create_status_area(self):
        """创建状态显示区域"""
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
        return status_group

    def create_log_area(self):
        """创建日志显示区域"""
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
        return log_group

    def create_button_area(self):
        """创建按钮区域"""
        button_layout = QHBoxLayout()

        close_btn = QPushButton("关闭")
        close_btn.setMinimumHeight(40)
        close_btn.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        return button_layout

    # 这些方法将在具体的实现类中定义
    def refresh_wim_list(self):
        """刷新WIM文件列表"""
        if hasattr(self, '_refresh_wim_list_impl'):
            return self._refresh_wim_list_impl()
        print("Warning: refresh_wim_list method not implemented")

    def show_diagnostics(self):
        """显示诊断信息"""
        if hasattr(self, '_show_diagnostics_impl'):
            return self._show_diagnostics_impl()
        print("Warning: show_diagnostics method not implemented")

    def smart_cleanup(self):
        """智能清理"""
        if hasattr(self, '_smart_cleanup_impl'):
            return self._smart_cleanup_impl()
        print("Warning: smart_cleanup method not implemented")

    def clear_log(self):
        """清空日志"""
        if hasattr(self, '_clear_log_impl'):
            return self._clear_log_impl()
        print("Warning: clear_log method not implemented")

    def mount_wim_image(self):
        """挂载WIM映像"""
        if hasattr(self, '_mount_wim_image_impl'):
            return self._mount_wim_image_impl()
        print("Warning: mount_wim_image method not implemented")

    def unmount_wim_commit(self):
        """卸载WIM映像并保存"""
        if hasattr(self, '_unmount_wim_commit_impl'):
            return self._unmount_wim_commit_impl()
        print("Warning: unmount_wim_commit method not implemented")

    def unmount_wim_discard(self):
        """卸载WIM映像不保存"""
        if hasattr(self, '_unmount_wim_discard_impl'):
            return self._unmount_wim_discard_impl()
        print("Warning: unmount_wim_discard method not implemented")

    def create_iso(self):
        """创建ISO"""
        if hasattr(self, '_create_iso_impl'):
            return self._create_iso_impl()
        print("Warning: create_iso method not implemented")

    def create_usb_bootable(self):
        """制作USB启动盘"""
        if hasattr(self, '_create_usb_bootable_impl'):
            return self._create_usb_bootable_impl()
        print("Warning: create_usb_bootable method not implemented")

    def quick_check(self):
        """快速检查"""
        if hasattr(self, '_quick_check_impl'):
            return self._quick_check_impl()
        print("Warning: quick_check method not implemented")

    def on_item_double_clicked(self, item):
        """双击列表项事件"""
        if hasattr(self, '_on_item_double_clicked_impl'):
            return self._on_item_double_clicked_impl(item)
        print("Warning: on_item_double_clicked method not implemented")

    def add_log_message(self, message, level="info"):
        """添加日志消息"""
        if hasattr(self, '_add_log_message_impl'):
            return self._add_log_message_impl(message, level)
        print(f"LOG [{level}]: {message}")

    def execute_wim_operation(self, operation, build_dir, **kwargs):
        """执行WIM操作"""
        if hasattr(self, '_execute_wim_operation_impl'):
            return self._execute_wim_operation_impl(operation, build_dir, **kwargs)
        print(f"Warning: execute_wim_operation method not implemented for {operation}")

    def reject(self):
        """关闭对话框"""
        if hasattr(self, '_reject_impl'):
            return self._reject_impl()
        super().reject()

    def on_operation_finished(self, success: bool, message: str):
        """操作完成回调"""
        if hasattr(self, '_on_operation_finished_impl'):
            return self._on_operation_finished_impl(success, message)
        print(f"Operation finished: {success}, {message}")

    def on_operation_error(self, error_message: str):
        """操作错误回调"""
        if hasattr(self, '_on_operation_error_impl'):
            return self._on_operation_error_impl(error_message)
        print(f"Operation error: {error_message}")