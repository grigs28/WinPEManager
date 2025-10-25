#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置对话框模块
提供各种配置对话框
"""

import os
from pathlib import Path
from typing import Tuple, Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QFileDialog, QMessageBox, QGroupBox, QCheckBox,
    QComboBox, QSpinBox, QTabWidget, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from ui.button_styler import apply_3d_button_style, apply_3d_button_style_red


class DriverDialog(QDialog):
    """驱动程序选择对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加驱动程序")
        self.setModal(True)
        self.resize(600, 400)

        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 说明信息
        info_label = QLabel("请选择要添加到WinPE的驱动程序文件或文件夹")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 驱动路径组
        path_group = QGroupBox("驱动程序路径")
        path_layout = QFormLayout(path_group)

        self.driver_path_edit = QLineEdit()
        self.driver_path_edit.setPlaceholderText("选择驱动程序文件或包含驱动的文件夹")
        path_layout.addRow("路径:", self.driver_path_edit)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_driver)
        apply_3d_button_style(browse_btn)  # 应用立体样式
        path_layout.addRow("", browse_btn)

        layout.addWidget(path_group)

        # 描述组
        desc_group = QGroupBox("描述")
        desc_layout = QFormLayout(desc_group)

        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("输入驱动程序的描述信息（可选）")
        desc_layout.addRow("描述:", self.description_edit)

        layout.addWidget(desc_group)

        # 选项组
        options_group = QGroupBox("选项")
        options_layout = QVBoxLayout(options_group)

        self.recurse_checkbox = QCheckBox("递归搜索子文件夹中的驱动程序")
        self.recurse_checkbox.setChecked(True)
        options_layout.addWidget(self.recurse_checkbox)

        self.force_unsigned_checkbox = QCheckBox("强制添加未签名的驱动程序")
        self.force_unsigned_checkbox.setChecked(True)
        options_layout.addWidget(self.force_unsigned_checkbox)

        layout.addWidget(options_group)

        # 按钮组
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        apply_3d_button_style(ok_btn)  # 应用立体样式

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        apply_3d_button_style(cancel_btn)  # 应用立体样式
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def browse_driver(self):
        """浏览驱动程序路径"""
        # 让用户选择文件还是文件夹
        choice_dialog = QDialog(self)
        choice_dialog.setWindowTitle("选择类型")
        choice_dialog.setModal(True)
        choice_layout = QVBoxLayout(choice_dialog)

        file_btn = QPushButton("选择驱动文件")
        folder_btn = QPushButton("选择驱动文件夹")

        def select_file():
            self.selected_type = "file"
            choice_dialog.accept()

        def select_folder():
            self.selected_type = "folder"
            choice_dialog.accept()

        file_btn.clicked.connect(select_file)
        folder_btn.clicked.connect(select_folder)
        
        # 应用立体样式
        apply_3d_button_style(file_btn)
        apply_3d_button_style(folder_btn)

        choice_layout.addWidget(file_btn)
        choice_layout.addWidget(folder_btn)

        if choice_dialog.exec_() == QDialog.Accepted:
            if hasattr(self, 'selected_type'):
                if self.selected_type == "file":
                    file_path, _ = QFileDialog.getOpenFileName(
                        self, "选择驱动程序文件", "",
                        "驱动程序文件 (*.inf; *.sys; *.dll);;所有文件 (*.*)"
                    )
                    if file_path:
                        self.driver_path_edit.setText(file_path)
                else:
                    folder_path = QFileDialog.getExistingDirectory(
                        self, "选择驱动程序文件夹"
                    )
                    if folder_path:
                        self.driver_path_edit.setText(folder_path)

    def get_driver_info(self) -> Tuple[str, str]:
        """获取驱动程序信息"""
        return (
            self.driver_path_edit.text().strip(),
            self.description_edit.text().strip()
        )

    def get_options(self) -> dict:
        """获取选项设置"""
        return {
            "recurse": self.recurse_checkbox.isChecked(),
            "force_unsigned": self.force_unsigned_checkbox.isChecked()
        }


class ScriptDialog(QDialog):
    """脚本选择对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加自定义脚本")
        self.setModal(True)
        self.resize(600, 500)

        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 说明信息
        info_label = QLabel("请选择要添加到WinPE的自定义脚本")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 脚本路径组
        path_group = QGroupBox("脚本路径")
        path_layout = QFormLayout(path_group)

        self.script_path_edit = QLineEdit()
        self.script_path_edit.setPlaceholderText("选择脚本文件")
        path_layout.addRow("路径:", self.script_path_edit)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_script)
        apply_3d_button_style(browse_btn)  # 应用立体样式
        path_layout.addRow("", browse_btn)

        layout.addWidget(path_group)

        # 描述组
        desc_group = QGroupBox("描述")
        desc_layout = QFormLayout(desc_group)

        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("输入脚本的描述信息（可选）")
        desc_layout.addRow("描述:", self.description_edit)

        layout.addWidget(desc_group)

        # 脚本预览组
        preview_group = QGroupBox("脚本内容预览")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(200)
        self.preview_text.setFont(QFont("Consolas", 9))
        preview_layout.addWidget(self.preview_text)

        refresh_btn = QPushButton("刷新预览")
        refresh_btn.clicked.connect(self.refresh_preview)
        apply_3d_button_style(refresh_btn)  # 应用立体样式
        preview_layout.addWidget(refresh_btn)

        layout.addWidget(preview_group)

        # 按钮组
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        apply_3d_button_style(ok_btn)  # 应用立体样式

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        apply_3d_button_style(cancel_btn)  # 应用立体样式
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        # 连接路径变化事件
        self.script_path_edit.textChanged.connect(self.refresh_preview)

    def browse_script(self):
        """浏览脚本文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择脚本文件", "",
            "脚本文件 (*.bat; *.cmd; *.ps1; *.vbs);;批处理文件 (*.bat; *.cmd);;"
            "PowerShell 脚本 (*.ps1);;VBScript 脚本 (*.vbs);;所有文件 (*.*)"
        )
        if file_path:
            self.script_path_edit.setText(file_path)

    def refresh_preview(self):
        """刷新脚本预览"""
        script_path = self.script_path_edit.text().strip()
        if script_path and Path(script_path).exists():
            try:
                # 使用编码工具安全读取文件
                from utils.encoding import safe_read_text_file
                content = safe_read_text_file(script_path)
                # 限制预览长度
                if len(content) > 2000:
                    content = content[:2000] + "\n\n...(内容过长，已截断)"
                self.preview_text.setPlainText(content)
            except Exception as e:
                self.preview_text.setPlainText(f"无法读取文件: {str(e)}")
        else:
            self.preview_text.clear()

    def get_script_info(self) -> Tuple[str, str]:
        """获取脚本信息"""
        return (
            self.script_path_edit.text().strip(),
            self.description_edit.text().strip()
        )


class ConfigDialog(QDialog):
    """通用配置对话框基类"""
    pass


class AdvancedConfigDialog(QDialog):
    """高级配置对话框"""

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("高级配置")
        self.setModal(True)
        self.resize(800, 600)

        self.init_ui()
        self.load_config()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # DISM配置标签页
        self.create_dism_tab()

        # 构建选项标签页
        self.create_build_options_tab()

        # 高级选项标签页
        self.create_advanced_tab()

        # 按钮组
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        apply_3d_button_style(ok_btn)  # 应用立体样式
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        apply_3d_button_style(cancel_btn)  # 应用立体样式
        
        reset_btn = QPushButton("重置为默认")
        reset_btn.clicked.connect(self.reset_to_default)
        apply_3d_button_style_red(reset_btn)  # 应用红色立体样式
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def create_dism_tab(self):
        """创建DISM配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # DISM路径配置
        dism_group = QGroupBox("DISM 工具配置")
        dism_layout = QFormLayout(dism_group)

        self.custom_dism_checkbox = QCheckBox("使用自定义 DISM 路径")
        self.custom_dism_checkbox.stateChanged.connect(self.on_custom_dism_changed)
        dism_layout.addRow("", self.custom_dism_checkbox)

        self.dism_path_edit = QLineEdit()
        self.dism_path_edit.setEnabled(False)
        browse_dism_btn = QPushButton("浏览...")
        browse_dism_btn.clicked.connect(self.browse_dism)
        browse_dism_btn.setEnabled(False)
        apply_3d_button_style(browse_dism_btn)  # 应用立体样式

        dism_path_layout = QHBoxLayout()
        dism_path_layout.addWidget(self.dism_path_edit)
        dism_path_layout.addWidget(browse_dism_btn)
        dism_layout.addRow("DISM 路径:", dism_path_layout)

        layout.addWidget(dism_group)

        # DISM选项
        options_group = QGroupBox("DISM 选项")
        options_layout = QFormLayout(options_group)

        self.cleanup_checkbox = QCheckBox("构建后清理临时文件")
        self.cleanup_checkbox.setChecked(True)
        options_layout.addRow("", self.cleanup_checkbox)

        self.verify_checkbox = QCheckBox("验证添加的组件")
        self.verify_checkbox.setChecked(False)
        options_layout.addRow("", self.verify_checkbox)

        layout.addWidget(options_group)

        self.tab_widget.addTab(widget, "DISM 配置")

    def create_build_options_tab(self):
        """创建构建选项标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 并行处理选项
        parallel_group = QGroupBox("并行处理")
        parallel_layout = QFormLayout(parallel_group)

        self.parallel_checkbox = QCheckBox("启用并行处理（如果支持）")
        self.parallel_checkbox.setChecked(False)
        parallel_layout.addRow("", self.parallel_checkbox)

        self.max_threads_spin = QSpinBox()
        self.max_threads_spin.setMinimum(1)
        self.max_threads_spin.setMaximum(16)
        self.max_threads_spin.setValue(4)
        parallel_layout.addRow("最大线程数:", self.max_threads_spin)

        layout.addWidget(parallel_group)

        # 缓存选项
        cache_group = QGroupBox("缓存选项")
        cache_layout = QFormLayout(cache_group)

        self.enable_cache_checkbox = QCheckBox("启用构建缓存")
        self.enable_cache_checkbox.setChecked(True)
        cache_layout.addRow("", self.enable_cache_checkbox)

        self.cache_path_edit = QLineEdit()
        self.cache_path_edit.setPlaceholderText("构建缓存目录路径")
        browse_cache_btn = QPushButton("浏览...")
        browse_cache_btn.clicked.connect(self.browse_cache)
        apply_3d_button_style(browse_cache_btn)  # 应用立体样式

        cache_path_layout = QHBoxLayout()
        cache_path_layout.addWidget(self.cache_path_edit)
        cache_path_layout.addWidget(browse_cache_btn)
        cache_layout.addRow("缓存路径:", cache_path_layout)

        layout.addWidget(cache_group)

        self.tab_widget.addTab(widget, "构建选项")

    def create_advanced_tab(self):
        """创建高级选项标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 日志选项
        log_group = QGroupBox("日志选项")
        log_layout = QFormLayout(log_group)

        self.verbose_logging_checkbox = QCheckBox("启用详细日志记录")
        self.verbose_logging_checkbox.setChecked(False)
        log_layout.addRow("", self.verbose_logging_checkbox)

        self.save_commands_checkbox = QCheckBox("保存执行的命令到日志")
        self.save_commands_checkbox.setChecked(True)
        log_layout.addRow("", self.save_commands_checkbox)

        layout.addWidget(log_group)

        # 实验性功能
        experimental_group = QGroupBox("实验性功能")
        experimental_layout = QVBoxLayout(experimental_group)

        self.experimental_checkbox = QCheckBox("启用实验性功能（可能不稳定）")
        self.experimental_checkbox.setChecked(False)
        experimental_layout.addWidget(self.experimental_checkbox)

        warning_label = QLabel("⚠️ 实验性功能可能导致构建失败或产生不可预期结果")
        warning_label.setStyleSheet("color: orange; font-weight: bold;")
        experimental_layout.addWidget(warning_label)

        layout.addWidget(experimental_group)

        layout.addStretch()
        self.tab_widget.addTab(widget, "高级选项")

    def on_custom_dism_changed(self, state):
        """自定义DISM路径复选框状态变化"""
        enabled = state == Qt.Checked
        self.dism_path_edit.setEnabled(enabled)
        # 这里需要访问browse_dism按钮，但由于没有保存引用，需要其他方式处理

    def browse_dism(self):
        """浏览DISM路径"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 DISM 工具", "",
            "可执行文件 (*.exe);;所有文件 (*.*)"
        )
        if file_path:
            self.dism_path_edit.setText(file_path)

    def browse_cache(self):
        """浏览缓存目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择缓存目录", self.cache_path_edit.text()
        )
        if directory:
            self.cache_path_edit.setText(directory)

    def load_config(self):
        """加载配置"""
        # 这里可以从config_manager加载高级配置
        pass

    def save_config(self):
        """保存配置"""
        # 这里可以将配置保存到config_manager
        pass

    def reset_to_default(self):
        """重置为默认配置"""
        reply = QMessageBox.question(
            self, "确认重置",
            "确定要重置所有高级配置为默认值吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.load_config()  # 重新加载默认配置