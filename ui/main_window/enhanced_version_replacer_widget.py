#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版WinPE版本替换UI组件
集成DISM精确比较和添加功能
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QProgressBar, QTextEdit, QGroupBox, QGridLayout, QFileDialog,
    QCheckBox, QMessageBox, QFrame, QSplitter, QTabWidget, QComboBox
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QDateTime, QTimer
from PyQt5.QtGui import QFont, QTextCharFormat, QColor

from core.version_replacer import EnhancedVersionReplacer, create_version_replace_config
from core.config_manager import ConfigManager
from utils.logger import get_logger


class EnhancedVersionReplaceThread(QThread):
    """增强版版本替换工作线程"""

    # 信号定义
    progress_updated = pyqtSignal(int, str)
    log_updated = pyqtSignal(str, str)
    finished = pyqtSignal(bool, str, dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, enhanced_replacer: EnhancedVersionReplacer, config: dict):
        super().__init__()
        self.enhanced_replacer = enhanced_replacer
        self.config = config
        self.is_running = False

    def run(self):
        """执行增强版版本替换"""
        try:
            self.is_running = True

            # 设置回调函数
            self.enhanced_replacer.set_progress_callback(self.on_progress_updated)
            self.enhanced_replacer.set_log_callback(self.on_log_updated)

            # 执行增强版版本替换
            success, message, result = self.enhanced_replacer.execute_enhanced_version_replacement(
                self.config["source_dir"],
                self.config["target_dir"],
                self.config["output_dir"]
            )

            if self.is_running:
                self.finished.emit(success, message, result)

        except Exception as e:
            if self.is_running:
                self.error_occurred.emit(str(e))

    def stop(self):
        """停止执行"""
        self.is_running = False

    def on_progress_updated(self, percent: int, message: str):
        """进度更新回调"""
        if self.is_running:
            self.progress_updated.emit(percent, message)

    def on_log_updated(self, message: str, level: str):
        """日志更新回调"""
        if self.is_running:
            self.log_updated.emit(message, level)


class EnhancedVersionReplacerWidget(QWidget):
    """增强版WinPE版本替换UI主组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.logger = get_logger("EnhancedVersionReplacerWidget")

        # 配置管理器
        self.config_manager = ConfigManager()

        # 版本替换器和线程
        self.enhanced_replacer = None
        self.replace_thread = None

        # UI状态
        self.is_processing = False

        # 初始化UI
        self.init_ui()
        self.setup_connections()

        # 自动加载配置（优先从JSON文件加载）
        if self.config_manager.get("version_replace.auto_load_config", True):
            # 先尝试从JSON配置文件加载
            if not self.load_config_from_json_file():
                # 如果JSON文件不存在或加载失败，则从系统配置加载
                self.load_config_from_system()

        # 设置配置变更监听
        self.setup_config_watchers()

        self.init_enhanced_version_replacer()

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)

        # 创建标签页
        self.tab_widget = QTabWidget()

        # 创建配置标签页
        self.create_config_tab()

        # 创建分析标签页
        self.create_analysis_tab()

        # 创建执行标签页
        self.create_execution_tab()

        layout.addWidget(self.tab_widget)

    def create_config_tab(self):
        """创建配置标签页"""
        config_widget = QWidget()
        layout = QVBoxLayout(config_widget)

        # 路径配置组
        paths_group = QGroupBox("路径配置")
        paths_layout = QGridLayout(paths_group)

        # 源目录
        paths_layout.addWidget(QLabel("源目录 (0WIN11PE):"), 0, 0)
        self.source_dir_edit = QLineEdit()
        self.source_dir_edit.setPlaceholderText("选择源WinPE目录...")
        paths_layout.addWidget(self.source_dir_edit, 0, 1)
        self.source_browse_btn = QPushButton("浏览")
        self.source_browse_btn.clicked.connect(self.browse_source_dir)
        paths_layout.addWidget(self.source_browse_btn, 0, 2)

        # 目标目录
        paths_layout.addWidget(QLabel("目标目录 (0WIN10OLD):"), 1, 0)
        self.target_dir_edit = QLineEdit()
        self.target_dir_edit.setPlaceholderText("选择目标WinPE目录...")
        paths_layout.addWidget(self.target_dir_edit, 1, 1)
        self.target_browse_btn = QPushButton("浏览")
        self.target_browse_btn.clicked.connect(self.browse_target_dir)
        paths_layout.addWidget(self.target_browse_btn, 1, 2)

        # 输出目录
        paths_layout.addWidget(QLabel("输出目录 (WIN10REPLACED):"), 2, 0)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("选择输出目录...")
        paths_layout.addWidget(self.output_dir_edit, 2, 1)
        self.output_browse_btn = QPushButton("浏览")
        self.output_browse_btn.clicked.connect(self.browse_output_dir)
        paths_layout.addWidget(self.output_browse_btn, 2, 2)

        layout.addWidget(paths_group)

        # DISM选项组
        dism_options_group = QGroupBox("DISM选项")
        dism_options_layout = QVBoxLayout(dism_options_group)

        self.use_dism_cb = QCheckBox("使用DISM进行精确操作")
        self.use_dism_cb.setChecked(True)
        self.use_dism_cb.setToolTip("使用DISM工具进行WIM文件的精确比较和组件添加")
        dism_options_layout.addWidget(self.use_dism_cb)

        self.deep_analysis_cb = QCheckBox("深度分析挂载目录差异")
        self.deep_analysis_cb.setChecked(True)
        self.deep_analysis_cb.setToolTip("深度比较源和目标挂载目录中的所有文件和配置")
        dism_options_layout.addWidget(self.deep_analysis_cb)

        self.copy_external_cb = QCheckBox("完整复制外部程序")
        self.copy_external_cb.setChecked(True)
        self.copy_external_cb.setToolTip("将源目录中的所有外部程序完整复制到目标目录")
        dism_options_layout.addWidget(self.copy_external_cb)

        self.verify_after_copy_cb = QCheckBox("复制后验证完整性")
        self.verify_after_copy_cb.setChecked(True)
        self.verify_after_copy_cb.setToolTip("复制完成后验证文件完整性")
        dism_options_layout.addWidget(self.verify_after_copy_cb)

        layout.addWidget(dism_options_group)

        # 操作按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.validate_btn = QPushButton("验证配置")
        self.validate_btn.clicked.connect(self.validate_configuration)
        button_layout.addWidget(self.validate_btn)

        self.quick_analysis_btn = QPushButton("快速分析")
        self.quick_analysis_btn.clicked.connect(self.quick_analysis)
        button_layout.addWidget(self.quick_analysis_btn)

        layout.addLayout(button_layout)

        self.tab_widget.addTab(config_widget, "配置")

    def create_analysis_tab(self):
        """创建分析标签页"""
        analysis_widget = QWidget()
        layout = QVBoxLayout(analysis_widget)

        # WIM分析组
        wim_group = QGroupBox("WIM文件分析")
        wim_layout = QVBoxLayout(wim_group)

        self.wim_analysis_text = QTextEdit()
        self.wim_analysis_text.setReadOnly(True)
        self.wim_analysis_text.setMaximumHeight(200)
        wim_layout.addWidget(self.wim_analysis_text)

        wim_button_layout = QHBoxLayout()
        self.analyze_wim_btn = QPushButton("分析WIM差异")
        self.analyze_wim_btn.clicked.connect(self.analyze_wim_differences)
        wim_button_layout.addWidget(self.analyze_wim_btn)

        self.export_wim_btn = QPushButton("导出WIM报告")
        self.export_wim_btn.clicked.connect(self.export_wim_report)
        wim_button_layout.addWidget(self.export_wim_btn)

        wim_layout.addLayout(wim_button_layout)
        layout.addWidget(wim_group)

        # 挂载目录分析组
        mount_group = QGroupBox("挂载目录深度分析")
        mount_layout = QVBoxLayout(mount_group)

        self.mount_analysis_text = QTextEdit()
        self.mount_analysis_text.setReadOnly(True)
        self.mount_analysis_text.setMaximumHeight(200)
        mount_layout.addWidget(self.mount_analysis_text)

        mount_button_layout = QHBoxLayout()
        self.analyze_mount_btn = QPushButton("分析挂载差异")
        self.analyze_mount_btn.clicked.connect(self.analyze_mount_differences)
        mount_button_layout.addWidget(self.analyze_mount_btn)

        self.export_mount_btn = QPushButton("导出挂载报告")
        self.export_mount_btn.clicked.connect(self.export_mount_report)
        mount_button_layout.addWidget(self.export_mount_btn)

        mount_layout.addLayout(mount_button_layout)
        layout.addWidget(mount_group)

        # 外部程序分析组
        external_group = QGroupBox("外部程序分析")
        external_layout = QVBoxLayout(external_group)

        self.external_analysis_text = QTextEdit()
        self.external_analysis_text.setReadOnly(True)
        self.external_analysis_text.setMaximumHeight(200)
        external_layout.addWidget(self.external_analysis_text)

        # 添加一键制作ISO按钮
        iso_button_layout = QHBoxLayout()
        iso_button_layout.addStretch()

        self.quick_iso_analysis_btn = QPushButton("🚀 一键制作ISO")
        self.quick_iso_analysis_btn.clicked.connect(self.quick_create_iso)
        self.quick_iso_analysis_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #E55A2B;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.quick_iso_analysis_btn.setToolTip("快速制作ISO文件（需要完成版本替换）")
        iso_button_layout.addWidget(self.quick_iso_analysis_btn)

        external_layout.addLayout(iso_button_layout)

        self.tab_widget.addTab(analysis_widget, "分析")

    def create_execution_tab(self):
        """创建执行标签页"""
        execution_widget = QWidget()
        layout = QVBoxLayout(execution_widget)

        # 进度显示
        progress_group = QGroupBox("执行进度")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("准备就绪")
        progress_layout.addWidget(self.progress_label)

        layout.addWidget(progress_group)

        # 执行日志
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(300)
        log_layout.addWidget(self.log_text)

        # 日志控制按钮
        log_button_layout = QHBoxLayout()
        log_button_layout.addStretch()

        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.clicked.connect(self.clear_log)
        log_button_layout.addWidget(self.clear_log_btn)

        self.save_log_btn = QPushButton("保存日志")
        self.save_log_btn.clicked.connect(self.save_log)
        log_button_layout.addWidget(self.save_log_btn)

        self.auto_scroll_cb = QCheckBox("自动滚动")
        self.auto_scroll_cb.setChecked(True)
        self.auto_scroll_cb.setStyleSheet("QCheckBox { padding: 5px; }")
        log_button_layout.addWidget(self.auto_scroll_cb)

        log_layout.addLayout(log_button_layout)
        layout.addWidget(log_group)

        # 操作按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.start_btn = QPushButton("开始增强版版本替换")
        self.start_btn.clicked.connect(self.start_enhanced_version_replace)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
            }
        """)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_version_replace)
        self.stop_btn.setEnabled(False)

        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)

        # ISO制作按钮
        self.create_iso_btn = QPushButton("制作ISO")
        self.create_iso_btn.clicked.connect(self.create_iso_from_output)
        self.create_iso_btn.setEnabled(False)
        self.create_iso_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
            }
        """)

        button_layout.addWidget(self.create_iso_btn)

        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #ddd; margin: 10px 0;")
        button_layout.addWidget(separator)

        # 一键制作ISO按钮（独立功能）
        self.quick_iso_btn = QPushButton("🚀 一键制作ISO")
        self.quick_iso_btn.clicked.connect(self.quick_create_iso)
        self.quick_iso_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #E55A2B;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.quick_iso_btn.setToolTip("快速制作ISO文件（需要完成版本替换）")
        button_layout.addWidget(self.quick_iso_btn)

        layout.addLayout(button_layout)

        self.tab_widget.addTab(execution_widget, "执行")

    def setup_connections(self):
        """设置信号连接"""
        # 连接配置变更信号
        self.source_dir_edit.textChanged.connect(self.on_config_changed)
        self.target_dir_edit.textChanged.connect(self.on_config_changed)
        self.output_dir_edit.textChanged.connect(self.on_config_changed)
        self.use_dism_cb.toggled.connect(self.on_config_changed)
        self.deep_analysis_cb.toggled.connect(self.on_config_changed)
        self.copy_external_cb.toggled.connect(self.on_config_changed)
        self.verify_after_copy_cb.toggled.connect(self.on_config_changed)

    def setup_config_watchers(self):
        """设置配置监听器"""
        # 配置自动保存定时器
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save_config)
        self.auto_save_timer.setSingleShot(True)

    def on_config_changed(self):
        """配置变更时的处理"""
        # 启动自动保存定时器（延迟2秒保存）
        if self.config_manager.get("version_replace.auto_save_config", True):
            self.auto_save_timer.start(2000)  # 2秒后保存

    def load_config_from_json_file(self):
        """从config/version_replace_config.json加载配置"""
        try:
            config_file = Path("config/version_replace_config.json")

            if not config_file.exists():
                self.append_log("未找到版本替换配置文件: config/version_replace_config.json", "info")
                return False

            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 加载路径配置
            paths = config_data.get("paths", {})
            source_dir = paths.get("source_dir", "")
            target_dir = paths.get("target_dir", "")
            output_dir = paths.get("output_dir", "")

            # 应用到UI
            if source_dir:
                self.source_dir_edit.setText(source_dir)
            if target_dir:
                self.target_dir_edit.setText(target_dir)
            if output_dir:
                self.output_dir_edit.setText(output_dir)

            # 获取配置信息
            version = config_data.get("version", "未知")
            created_time = config_data.get("created_time", "未知")
            description = config_data.get("description", "")

            self.append_log(f"已加载版本替换配置 v{version} (创建时间: {created_time})", "success")
            if description:
                self.append_log(f"配置描述: {description}", "info")

            return True

        except json.JSONDecodeError as e:
            self.append_log(f"配置文件格式错误: {str(e)}", "error")
            return False
        except Exception as e:
            self.append_log(f"加载配置文件失败: {str(e)}", "error")
            return False

    def load_config_from_system(self):
        """从系统配置加载版本替换配置"""
        try:
            # 获取版本替换配置
            source_dir = self.config_manager.get("version_replace.source_dir", "")
            target_dir = self.config_manager.get("version_replace.target_dir", "")
            output_dir = self.config_manager.get("version_replace.output_dir", "")

            # 应用到UI
            if source_dir:
                self.source_dir_edit.setText(source_dir)
            if target_dir:
                self.target_dir_edit.setText(target_dir)
            if output_dir:
                self.output_dir_edit.setText(output_dir)

            self.append_log("配置已从系统自动加载", "info")

        except Exception as e:
            self.append_log(f"自动加载配置失败: {str(e)}", "warning")

    def save_config_to_system(self):
        """保存当前配置到系统配置"""
        try:
            # 保存路径配置
            self.config_manager.set("version_replace.source_dir", self.source_dir_edit.text())
            self.config_manager.set("version_replace.target_dir", self.target_dir_edit.text())
            self.config_manager.set("version_replace.output_dir", self.output_dir_edit.text())

            # 保存DISM选项
            dism_options = {
                "use_dism": self.use_dism_cb.isChecked(),
                "deep_analysis": self.deep_analysis_cb.isChecked(),
                "copy_external": self.copy_external_cb.isChecked(),
                "verify_after_copy": self.verify_after_copy_cb.isChecked()
            }
            self.config_manager.set("version_replace.dism_options", dism_options)

            # 保存配置到文件
            if self.config_manager.save_config():
                self.append_log("配置已自动保存到系统", "info")
            else:
                self.append_log("配置保存失败", "warning")

        except Exception as e:
            self.append_log(f"保存配置到系统失败: {str(e)}", "error")

    def auto_save_config(self):
        """自动保存配置"""
        if self.config_manager.get("version_replace.auto_save_config", True):
            self.save_config_to_system()

    def init_enhanced_version_replacer(self):
        """初始化增强版版本替换器"""
        try:
            # 这里需要传入适当的参数
            # 暂时使用None，实际使用时需要从主窗口获取
            self.enhanced_replacer = EnhancedVersionReplacer(
                config_manager=self.config_manager,
                adk_manager=None,  # 需要从主窗口获取
                unified_wim_manager=None  # 需要从主窗口获取
            )
            self.append_log("增强版版本替换器初始化成功", "success")
        except Exception as e:
            self.append_log(f"增强版版本替换器初始化失败: {str(e)}", "error")

    def browse_source_dir(self):
        """浏览源目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择源目录")
        if directory:
            self.source_dir_edit.setText(directory)

    def browse_target_dir(self):
        """浏览目标目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择目标目录")
        if directory:
            self.target_dir_edit.setText(directory)

    def browse_output_dir(self):
        """浏览输出目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self.output_dir_edit.setText(directory)

    def validate_configuration(self):
        """验证配置"""
        try:
            messages = []

            source_dir = self.source_dir_edit.text().strip()
            target_dir = self.target_dir_edit.text().strip()
            output_dir = self.output_dir_edit.text().strip()

            if not source_dir:
                messages.append("源目录不能为空")
            elif not Path(source_dir).exists():
                messages.append(f"源目录不存在: {source_dir}")

            if not target_dir:
                messages.append("目标目录不能为空")
            elif not Path(target_dir).exists():
                messages.append(f"目标目录不存在: {target_dir}")

            if not output_dir:
                messages.append("输出目录不能为空")

            # 显示验证结果
            if messages:
                self.append_log("路径验证失败: " + "; ".join(messages), "warning")
                QMessageBox.warning(self, "配置验证", "\n".join(messages))
            else:
                self.append_log("路径验证通过", "success")
                QMessageBox.information(self, "配置验证", "配置验证通过！")

        except Exception as e:
            self.append_log(f"验证配置失败: {str(e)}", "error")

    def quick_analysis(self):
        """快速分析"""
        try:
            if not self.enhanced_replacer:
                self.init_enhanced_version_replacer()

            if not self.enhanced_replacer:
                raise Exception("增强版版本替换器未初始化")

            source_dir = self.source_dir_edit.text().strip()
            target_dir = self.target_dir_edit.text().strip()

            if not source_dir or not target_dir:
                raise Exception("请先设置源目录和目标目录")

            self.append_log("开始快速分析...", "info")

            # 快速检查WIM文件
            source_wim = Path(source_dir) / "boot" / "boot.wim"
            target_wim = Path(target_dir) / "boot" / "boot.wim"

            analysis_results = []

            if source_wim.exists():
                analysis_results.append(f"✅ 源WIM文件存在: {source_wim}")
                analysis_results.append(f"   文件大小: {source_wim.stat().st_size:,} bytes")
            else:
                analysis_results.append(f"❌ 源WIM文件不存在: {source_wim}")

            if target_wim.exists():
                analysis_results.append(f"✅ 目标WIM文件存在: {target_wim}")
                analysis_results.append(f"   文件大小: {target_wim.stat().st_size:,} bytes")
            else:
                analysis_results.append(f"❌ 目标WIM文件不存在: {target_wim}")

            # 快速检查挂载目录
            source_mount = Path(source_dir) / "mount"
            target_mount = Path(target_dir) / "mount"

            if source_mount.exists():
                analysis_results.append(f"✅ 源挂载目录存在: {source_mount}")
                # 快速统计文件
                file_count = sum(1 for _ in source_mount.rglob("*") if _.is_file())
                analysis_results.append(f"   文件数量: {file_count:,}")
            else:
                analysis_results.append(f"❌ 源挂载目录不存在: {source_mount}")

            if target_mount.exists():
                analysis_results.append(f"✅ 目标挂载目录存在: {target_mount}")
                file_count = sum(1 for _ in target_mount.rglob("*") if _.is_file())
                analysis_results.append(f"   文件数量: {file_count:,}")
            else:
                analysis_results.append(f"❌ 目标挂载目录不存在: {target_mount}")

            # 显示结果
            result_text = "\n".join(analysis_results)
            self.wim_analysis_text.setText(result_text)
            self.append_log("快速分析完成", "success")

        except Exception as e:
            self.append_log(f"快速分析失败: {str(e)}", "error")

    def analyze_wim_differences(self):
        """分析WIM差异"""
        try:
            if not self.enhanced_replacer:
                raise Exception("增强版版本替换器未初始化")

            source_dir = self.source_dir_edit.text().strip()
            target_dir = self.target_dir_edit.text().strip()

            source_wim = Path(source_dir) / "boot" / "boot.wim"
            target_wim = Path(target_dir) / "boot" / "boot.wim"

            if not source_wim.exists() or not target_wim.exists():
                raise Exception("WIM文件不存在，无法分析")

            self.append_log("开始分析WIM文件差异...", "info")

            # 使用增强版替换器分析WIM差异
            differences = self.enhanced_replacer.compare_wims_with_dism(
                str(source_wim), str(target_wim)
            )

            # 格式化显示结果
            result_text = f"WIM差异分析结果:\n"
            result_text += f"源WIM: {source_wim}\n"
            result_text += f"目标WIM: {target_wim}\n\n"

            # 显示源WIM信息
            source_analysis = differences.get("source_analysis", {})
            source_images = source_analysis.get("images", [])
            result_text += f"源WIM包含 {len(source_images)} 个镜像:\n"
            for img in source_images:
                result_text += f"  - 镜像 {img.get('index', 'N/A')}: {img.get('name', 'N/A')}\n"
                result_text += f"    大小: {img.get('size', 'N/A')}\n"

            result_text += "\n"

            # 显示目标WIM信息
            target_analysis = differences.get("target_analysis", {})
            target_images = target_analysis.get("images", [])
            result_text += f"目标WIM包含 {len(target_images)} 个镜像:\n"
            for img in target_images:
                result_text += f"  - 镜像 {img.get('index', 'N/A')}: {img.get('name', 'N/A')}\n"
                result_text += f"    大小: {img.get('size', 'N/A')}\n"

            # 显示差异
            missing_items = differences.get("missing_in_target", [])
            if missing_items:
                result_text += "\n发现的差异:\n"
                for item in missing_items:
                    result_text += f"  - {item}\n"

            self.wim_analysis_text.setText(result_text)
            self.append_log("WIM差异分析完成", "success")

        except Exception as e:
            self.append_log(f"WIM差异分析失败: {str(e)}", "error")

    def analyze_mount_differences(self):
        """分析挂载目录差异"""
        try:
            if not self.enhanced_replacer:
                raise Exception("增强版版本替换器未初始化")

            source_dir = self.source_dir_edit.text().strip()
            target_dir = self.target_dir_edit.text().strip()

            source_mount = Path(source_dir) / "mount"
            target_mount = Path(target_dir) / "mount"

            if not source_mount.exists() or not target_mount.exists():
                raise Exception("挂载目录不存在，无法分析")

            self.append_log("开始分析挂载目录差异...", "info")

            # 使用增强版替换器分析挂载目录差异
            differences = self.enhanced_replacer.analyze_mount_differences(
                str(source_mount), str(target_mount)
            )

            # 格式化显示结果
            result_text = f"挂载目录差异分析结果:\n"
            result_text += f"源挂载目录: {source_mount}\n"
            result_text += f"目标挂载目录: {target_mount}\n\n"

            # 显示外部程序差异
            external_programs = differences.get("external_programs", [])
            result_text += f"发现 {len(external_programs)} 个外部程序:\n"
            for program in external_programs:
                result_text += f"  - {program['name']}\n"
                if not program.get("exists_in_target", False):
                    result_text += f"    状态: 需要复制到目标\n"
                else:
                    result_text += f"    状态: 目标中已存在\n"

            # 显示启动配置差异
            startup_configs = differences.get("startup_configs", [])
            result_text += f"\n发现 {len(startup_configs)} 个启动配置:\n"
            for config in startup_configs:
                result_text += f"  - {config['name']}\n"
                if not config.get("exists_in_target", False):
                    result_text += f"    状态: 需要复制到目标\n"
                elif not config.get("content_match", False):
                    result_text += f"    状态: 内容不同，需要更新\n"
                else:
                    result_text += f"    状态: 目标中已存在且内容相同\n"

            # 显示文件差异统计
            missing_files = differences.get("missing_in_target", [])
            result_text += f"\n文件差异统计:\n"
            result_text += f"  - 目标中缺失的文件/目录: {len(missing_files)}\n"

            self.mount_analysis_text.setText(result_text)
            self.append_log("挂载目录差异分析完成", "success")

        except Exception as e:
            self.append_log(f"挂载目录差异分析失败: {str(e)}", "error")

    def export_wim_report(self):
        """导出WIM分析报告"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存WIM分析报告",
                str(Path.cwd() / "wim_analysis_report.txt"),
                "文本文件 (*.txt);;所有文件 (*)"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.wim_analysis_text.toPlainText())
                self.append_log(f"WIM分析报告已保存到: {file_path}", "info")

        except Exception as e:
            self.append_log(f"保存WIM分析报告失败: {str(e)}", "error")

    def export_mount_report(self):
        """导出挂载分析报告"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存挂载分析报告",
                str(Path.cwd() / "mount_analysis_report.txt"),
                "文本文件 (*.txt);;所有文件 (*)"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.mount_analysis_text.toPlainText())
                self.append_log(f"挂载分析报告已保存到: {file_path}", "info")

        except Exception as e:
            self.append_log(f"保存挂载分析报告失败: {str(e)}", "error")

    def start_enhanced_version_replace(self, skip_confirmation: bool = False):
        """开始增强版版本替换"""
        try:
            # 验证配置
            source_dir = self.source_dir_edit.text().strip()
            target_dir = self.target_dir_edit.text().strip()
            output_dir = self.output_dir_edit.text().strip()

            if not all([source_dir, target_dir, output_dir]):
                raise Exception("请填写完整的路径配置")

            if not all(Path(p).exists() for p in [source_dir, target_dir]):
                raise Exception("源目录或目标目录不存在")

            # 确保输出目录存在
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            # 创建配置
            config = {
                "source_dir": source_dir,
                "target_dir": target_dir,
                "output_dir": output_dir,
                "use_dism": self.use_dism_cb.isChecked(),
                "deep_analysis": self.deep_analysis_cb.isChecked(),
                "copy_external": self.copy_external_cb.isChecked(),
                "verify_after_copy": self.verify_after_copy_cb.isChecked()
            }

            # 更新UI状态
            self.is_processing = True
            self.update_ui_state()

            # 创建工作线程
            self.replace_thread = EnhancedVersionReplaceThread(self.enhanced_replacer, config)
            self.replace_thread.progress_updated.connect(self.on_progress_updated)
            self.replace_thread.log_updated.connect(self.append_log)
            self.replace_thread.finished.connect(self.on_enhanced_version_replace_finished)
            self.replace_thread.error_occurred.connect(self.on_enhanced_version_replace_error)

            self.replace_thread.start()

            self.append_log("增强版版本替换已启动", "info")

        except Exception as e:
            self.append_log(f"启动增强版版本替换失败: {str(e)}", "error")
            QMessageBox.critical(self, "启动错误", f"启动增强版版本替换失败:\n{str(e)}")

    def stop_version_replace(self):
        """停止版本替换"""
        try:
            if self.replace_thread and self.replace_thread.isRunning():
                self.replace_thread.stop()
                self.append_log("正在停止版本替换...", "warning")

            self.is_processing = False
            self.update_ui_state()

        except Exception as e:
            self.append_log(f"停止版本替换失败: {str(e)}", "error")

    def on_progress_updated(self, percent: int, message: str):
        """进度更新处理"""
        self.progress_bar.setValue(percent)
        self.progress_label.setText(f"增强版版本替换: {message}")
        self.append_log(f"[{percent:3d}%] {message}", "info")

    def on_enhanced_version_replace_finished(self, success: bool, message: str, result: dict):
        """增强版版本替换完成处理"""
        try:
            # 恢复按钮状态
            self.is_processing = False
            self.update_ui_state()

            if success:
                self.append_log(f"增强版版本替换完成: {message}", "success")
                self.append_log(f"输出WIM: {result.get('output_wim', 'N/A')}", "info")
                self.append_log(f"外部程序复制数量: {result.get('external_programs_copied', 0)}", "info")

                # 启用ISO制作按钮
                self.create_iso_btn.setEnabled(True)
                self.quick_iso_btn.setEnabled(True)
                if hasattr(self, 'quick_iso_analysis_btn'):
                    self.quick_iso_analysis_btn.setEnabled(True)

                # 生成报告
                report_path = Path(self.output_dir_edit.text()) / "enhanced_replacement_report.json"
                if self.enhanced_replacer:
                    report_file = self.enhanced_replacer.generate_enhanced_report(result, str(report_path))
                    if report_file:
                        self.append_log(f"详细报告已生成: {report_file}", "info")

                # 检查是否需要自动制作ISO
                auto_create_iso = getattr(self, 'auto_create_iso_after_replace', False)
                if auto_create_iso:
                    self.auto_create_iso_after_replace = False  # 重置标志
                    self.append_log("版本替换完成，自动开始ISO制作...", "info")

                    # 延迟一下让用户看到版本替换完成的日志
                    QTimer.singleShot(2000, self._proceed_iso_creation)
                    return

                # 询问是否查看详细报告
                reply = QMessageBox.question(
                    self, "增强版版本替换完成",
                    "增强版版本替换已成功完成!\n\n是否查看详细报告?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    self.show_enhanced_detailed_report(result)
            else:
                self.append_log(f"增强版版本替换失败: {message}", "error")
                QMessageBox.critical(self, "替换失败", f"增强版版本替换失败:\n{message}")

        except Exception as e:
            self.append_log(f"处理完成结果时发生错误: {str(e)}", "error")

    def on_enhanced_version_replace_error(self, error_message: str):
        """增强版版本替换错误处理"""
        try:
            # 恢复按钮状态
            self.is_processing = False
            self.update_ui_state()

            self.append_log(f"增强版版本替换过程中发生错误: {error_message}", "error")
            QMessageBox.critical(self, "替换错误", f"增强版版本替换过程中发生错误:\n{error_message}")

        except Exception as e:
            self.append_log(f"错误处理失败: {str(e)}", "error")

    def create_iso_from_output(self):
        """从输出生成ISO"""
        try:
            output_dir = self.output_dir_edit.text().strip()
            if not output_dir:
                raise Exception("输出目录未设置")

            output_wim = Path(output_dir) / "boot" / "boot.wim"
            if not output_wim.exists():
                raise Exception(f"输出WIM文件不存在: {output_wim}")

            # 选择ISO保存位置
            iso_path, _ = QFileDialog.getSaveFileName(
                self, "保存ISO文件",
                str(Path(output_dir) / "WIN10REPLACED.iso"),
                "ISO文件 (*.iso);;所有文件 (*)"
            )

            if iso_path:
                # 创建ISO制作线程
                self.iso_thread = ISOCreationThread(output_dir, Path(iso_path), self)

                # 连接信号
                self.iso_thread.progress_updated.connect(self.on_progress_updated)
                self.iso_thread.log_updated.connect(self.append_log)
                self.iso_thread.command_updated.connect(self.on_iso_command_output)
                self.iso_thread.finished.connect(self.on_iso_finished)
                self.iso_thread.error_occurred.connect(self.on_iso_error)

                # 禁用制作ISO按钮
                self.create_iso_btn.setEnabled(False)

                # 启用停止按钮
                self.stop_btn.setEnabled(True)
                self.stop_btn.setText("停止制作")
                self.stop_btn.disconnect()
                self.stop_btn.clicked.connect(self.stop_iso_creation)

                # 开始制作
                self.iso_thread.start()
                self.append_log("开始制作ISO文件...", "info")

        except Exception as e:
            self.append_log(f"启动ISO制作失败: {str(e)}", "error")
            QMessageBox.critical(self, "制作失败", f"启动ISO制作时发生错误:\n{str(e)}")

    def stop_iso_creation(self):
        """停止ISO制作"""
        if hasattr(self, 'iso_thread') and self.iso_thread and self.iso_thread.isRunning():
            self.iso_thread.stop()
            self.iso_thread.wait(5000)
            self.append_log("ISO制作已停止", "warning")

            # 恢复按钮状态
            self.create_iso_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("停止")
            self.stop_btn.disconnect()
            self.stop_btn.clicked.connect(self.stop_version_replace)

    def on_iso_command_output(self, command: str, output: str):
        """ISO制作命令输出处理"""
        try:
            # 命令输出使用特殊格式，便于用户识别
            self.append_log(f"[命令] {command}: {output}", "command")
        except Exception as e:
            self.append_log(f"命令输出处理失败: {str(e)}", "error")

    def on_iso_error(self, error_message: str):
        """ISO制作错误处理"""
        try:
            # 恢复按钮状态
            self.create_iso_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("停止")
            self.stop_btn.disconnect()
            self.stop_btn.clicked.connect(self.stop_version_replace)

            self.append_log(f"ISO制作过程中发生错误: {error_message}", "error")
            QMessageBox.critical(self, "制作错误", f"ISO制作过程中发生错误:\n{error_message}")

        except Exception as e:
            self.append_log(f"ISO错误处理失败: {str(e)}", "error")

    def on_iso_finished(self, result: dict):
        """ISO制作完成处理"""
        try:
            # 恢复按钮状态
            self.create_iso_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("停止")
            self.stop_btn.disconnect()
            self.stop_btn.clicked.connect(self.stop_version_replace)

            if result.get("success", False):
                self.append_log("ISO文件制作成功!", "success")
                iso_path = result.get("iso_path", "")
                file_size = result.get("file_size", 0)
                if file_size > 0:
                    size_mb = file_size / (1024 * 1024)
                    self.append_log(f"ISO文件大小: {size_mb:.1f} MB", "info")
                self.append_log(f"保存位置: {iso_path}", "info")

                QMessageBox.information(
                    self, "制作完成",
                    f"ISO文件制作成功!\n\n文件位置: {iso_path}\n文件大小: {size_mb:.1f} MB"
                )
            else:
                self.append_log("ISO文件制作失败", "error")
                errors = result.get("errors", [])
                for error in errors:
                    self.append_log(f"错误: {error}", "error")

                QMessageBox.critical(
                    self, "制作失败",
                    "ISO文件制作失败，请检查日志信息获取详细错误原因。"
                )

        except Exception as e:
            self.append_log(f"ISO制作完成处理失败: {str(e)}", "error")

    def update_ui_state(self):
        """更新UI状态"""
        # 更新路径输入框
        self.source_dir_edit.setEnabled(not self.is_processing)
        self.target_dir_edit.setEnabled(not self.is_processing)
        self.output_dir_edit.setEnabled(not self.is_processing)

        # 更新浏览按钮
        self.source_browse_btn.setEnabled(not self.is_processing)
        self.target_browse_btn.setEnabled(not self.is_processing)
        self.output_browse_btn.setEnabled(not self.is_processing)

        # 更新选项框
        self.use_dism_cb.setEnabled(not self.is_processing)
        self.deep_analysis_cb.setEnabled(not self.is_processing)
        self.copy_external_cb.setEnabled(not self.is_processing)
        self.verify_after_copy_cb.setEnabled(not self.is_processing)

        # 更新操作按钮
        self.start_btn.setEnabled(not self.is_processing)
        self.stop_btn.setEnabled(self.is_processing)

        # 更新分析按钮
        self.validate_btn.setEnabled(not self.is_processing)
        self.quick_analysis_btn.setEnabled(not self.is_processing)
        self.analyze_wim_btn.setEnabled(not self.is_processing)
        self.analyze_mount_btn.setEnabled(not self.is_processing)

    def append_log(self, message: str, level: str = "info"):
        """添加日志消息"""
        # 添加到文本控件
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)

        # 根据级别设置颜色和图标
        format = QTextCharFormat()
        icon = ""

        if level == "error":
            format.setForeground(QColor("#E74C3C"))  # 红色
            icon = "❌ "
            format.setFontWeight(QFont.Bold)
        elif level == "warning":
            format.setForeground(QColor("#F39C12"))  # 橙色
            icon = "⚠️ "
        elif level == "success":
            format.setForeground(QColor("#27AE60"))  # 绿色
            icon = "✅ "
        elif level == "command":
            format.setForeground(QColor("#8E44AD"))  # 紫色
            icon = "🔧 "
        else:  # info
            format.setForeground(QColor("#2C3E50"))  # 深蓝色
            icon = "ℹ️ "

        # 添加时间戳
        timestamp = QDateTime.currentDateTime().toString('hh:mm:ss.zzz')[:-3]

        # 设置格式并插入文本
        cursor.setCharFormat(format)
        cursor.insertText(f"[{timestamp}] {icon}[{level.upper():<8}] {message}\n")

        # 自动滚动到底部（如果启用）
        if hasattr(self, 'auto_scroll_cb') and self.auto_scroll_cb.isChecked():
            self.log_text.ensureCursorVisible()

        # 限制日志行数
        self.limit_log_lines()

    def toggle_auto_scroll(self, state):
        """切换自动滚动"""
        if state == 2:  # Qt.Checked
            self.log_text.ensureCursorVisible()

    def limit_log_lines(self, max_lines: int = 1000):
        """限制日志行数"""
        document = self.log_text.document()
        if document.blockCount() > max_lines:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.select(cursor.BlockUnderCursor)
            cursor.removeText()
            cursor.deletePreviousChar()

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.append_log("日志已清空", "info")

    def save_log(self):
        """保存日志"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存日志",
                str(Path.cwd() / f"enhanced_version_replacement_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"),
                "文本文件 (*.txt);;所有文件 (*)"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                self.append_log(f"日志已保存到: {file_path}", "info")

        except Exception as e:
            self.append_log(f"保存日志失败: {str(e)}", "error")

    def quick_create_iso(self):
        """一键制作ISO - 先版本替换再制作ISO"""
        try:
            # 切换到执行标签页
            tab_widget = self.parent()
            while tab_widget and not hasattr(tab_widget, 'setCurrentIndex'):
                tab_widget = tab_widget.parent()

            if tab_widget and hasattr(tab_widget, 'setCurrentIndex'):
                # 查找执行标签页的索引
                for i in range(tab_widget.count()):
                    if tab_widget.tabText(i) == "执行":
                        tab_widget.setCurrentIndex(i)
                        break

            # 检查是否已完成版本替换
            output_dir = self.output_dir_edit.text().strip()
            need_version_replace = False

            if not output_dir:
                need_version_replace = True
            else:
                output_path = Path(output_dir)
                if not output_path.exists():
                    need_version_replace = True
                else:
                    # 检查关键文件
                    boot_wim = output_path / "boot" / "boot.wim"
                    if not boot_wim.exists():
                        need_version_replace = True

            if need_version_replace:
                # 需要先进行版本替换
                source_wim = self.source_wim_edit.text().strip()
                target_wim = self.target_wim_edit.text().strip()

                # 验证配置
                if not source_wim or not Path(source_wim).exists():
                    QMessageBox.warning(self, "配置错误", "源WIM文件不存在，请先选择有效的WIM文件！")
                    return

                if not target_wim or not Path(target_wim).exists():
                    QMessageBox.warning(self, "配置错误", "目标WIM文件不存在，请先选择有效的WIM文件！")
                    return

                # 询问用户确认
                reply = QMessageBox.question(
                    self, "版本替换和ISO制作",
                    f"检测到需要先完成版本替换操作。\n\n"
                    f"系统将按以下顺序执行：\n"
                    f"1. 执行增强版本替换（从源WIM到目标WIM）\n"
                    f"2. 制作ISO文件\n\n"
                    f"预计总时间：10-20分钟\n\n"
                    f"确定要继续吗？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply != QMessageBox.Yes:
                    return

                # 先执行版本替换
                self.append_log("开始执行增强版本替换...", "info")
                self.start_enhanced_version_replace(skip_confirmation=True)

                # 版本替换完成后会自动触发ISO制作
                self.auto_create_iso_after_replace = True
                return

            # 已有版本替换结果，直接制作ISO
            self._proceed_iso_creation()

        except Exception as e:
            self.append_log(f"一键制作ISO失败: {str(e)}", "error")
            QMessageBox.critical(self, "错误", f"一键制作ISO失败: {str(e)}")

    def _proceed_iso_creation(self):
        """继续ISO制作流程"""
        try:
            output_dir = self.output_dir_edit.text().strip()

            # 询问用户确认
            reply = QMessageBox.question(
                self,
                "确认制作ISO",
                f"准备从以下目录制作ISO文件：\n\n输出目录: {output_dir}\n\n"
                f"这可能会需要几分钟时间。\n\n"
                f"确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 开始制作ISO
            self.append_log("开始一键制作ISO...", "info")

            # 生成ISO路径
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            iso_path = Path(output_dir) / f"WinPE_Enhanced_{timestamp}.iso"

            # 确保ISO目录存在
            iso_path.parent.mkdir(parents=True, exist_ok=True)

            # 创建ISO制作线程
            self.iso_thread = ISOCreationThread(str(output_dir), iso_path, self)

            # 连接信号
            self.iso_thread.progress_updated.connect(self.on_progress_updated)
            self.iso_thread.log_updated.connect(self.append_log)
            self.iso_thread.command_updated.connect(self.on_command_updated)
            self.iso_thread.finished.connect(self.on_iso_finished)
            self.iso_thread.error_occurred.connect(self.on_iso_error)

            # 禁用按钮
            self.quick_iso_btn.setEnabled(False)
            if hasattr(self, 'quick_iso_analysis_btn'):
                self.quick_iso_analysis_btn.setEnabled(False)
            self.quick_iso_btn.setText("🔄 正在制作...")

            # 启动线程
            self.iso_thread.start()

        except Exception as e:
            self.append_log(f"一键制作ISO失败: {str(e)}", "error")
            QMessageBox.critical(self, "错误", f"一键制作ISO失败: {str(e)}")

    def on_iso_finished(self, result: dict):
        """ISO制作完成"""
        # 恢复按钮
        self.quick_iso_btn.setEnabled(True)
        if hasattr(self, 'quick_iso_analysis_btn'):
            self.quick_iso_analysis_btn.setEnabled(True)
        self.quick_iso_btn.setText("🚀 一键制作ISO")

        success = result.get('success', False)
        message = result.get('message', '')
        iso_path = result.get('iso_path', '')

        if success:
            self.append_log(f"ISO制作完成: {iso_path}", "success")

            # 设置进度条到100%
            self.progress_bar.setValue(100)
            self.progress_label.setText("ISO制作完成")

            QMessageBox.information(self, "完成", f"ISO制作成功！\n文件位置: {iso_path}")
        else:
            self.append_log(f"ISO制作失败: {message}", "error")
            QMessageBox.warning(self, "失败", f"ISO制作失败！\n{message}")

    def on_iso_error(self, error_message: str):
        """ISO制作错误"""
        # 恢复按钮
        self.quick_iso_btn.setEnabled(True)
        if hasattr(self, 'quick_iso_analysis_btn'):
            self.quick_iso_analysis_btn.setEnabled(True)
        self.quick_iso_btn.setText("🚀 一键制作ISO")

        self.append_log(f"ISO制作错误: {error_message}", "error")
        QMessageBox.critical(self, "错误", f"ISO制作过程中发生错误:\n{error_message}")

    def on_command_updated(self, command: str, output: str):
        """处理命令输出更新"""
        # 这里可以添加命令输出的处理逻辑
        pass


class ISOCreationThread(QThread):
    """ISO制作工作线程"""

    # 信号定义
    progress_updated = pyqtSignal(int, str)
    log_updated = pyqtSignal(str, str)
    command_updated = pyqtSignal(str, str)  # 命令输出信号
    finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, output_dir: str, iso_path: Path, parent=None):
        super().__init__()
        self.output_dir = Path(output_dir)
        self.iso_path = iso_path
        self.parent = parent
        self.is_running = False

    def run(self):
        """执行ISO制作"""
        try:
            self.is_running = True

            # 导入必要的模块
            from core.config_manager import ConfigManager
            from core.adk_manager import ADKManager
            from core.unified_manager.wim_manager import UnifiedWIMManager

            # 初始化管理器
            config_manager = ConfigManager()
            adk_manager = ADKManager()
            unified_wim_manager = UnifiedWIMManager(config_manager, adk_manager)

            # 设置回调函数
            def progress_callback(percent, message):
                if self.is_running:
                    self.progress_updated.emit(percent, message)

            def log_callback(message, level):
                if self.is_running:
                    self.log_updated.emit(message, level)

            def command_callback(command, output):
                """命令输出回调"""
                if self.is_running:
                    self.command_updated.emit(command, output)

            # 设置回调到ADK管理器以捕获命令输出
            adk_manager.set_command_callback(command_callback)

            result = None  # 初始化result变量
            self.progress_updated.emit(5, "初始化ISO制作...")
            self.log_updated.emit("开始ISO制作流程", "info")

            self.progress_updated.emit(10, "验证环境和文件...")

            # 验证输出目录和WIM文件
            if not self.output_dir.exists():
                raise Exception(f"输出目录不存在: {self.output_dir}")

            boot_wim = self.output_dir / "boot" / "boot.wim"
            if not boot_wim.exists():
                raise Exception(f"boot.wim文件不存在: {boot_wim}")

            self.log_updated.emit(f"找到WIM文件: {boot_wim}", "info")
            self.command_updated.emit("检查文件", f"WIM文件大小: {boot_wim.stat().st_size:,} bytes")

            self.progress_updated.emit(20, "准备ISO制作环境...")

            # 确保ISO目录存在
            self.iso_path.parent.mkdir(parents=True, exist_ok=True)

            # 使用统一管理器创建ISO
            self.progress_updated.emit(30, "开始创建ISO文件...")
            self.log_updated.emit(f"目标ISO文件: {self.iso_path}", "info")
            self.command_updated.emit("ISO制作", f"输出路径: {self.iso_path}")

            success, message = unified_wim_manager.create_iso(self.output_dir, self.iso_path)

            if success:
                self.progress_updated.emit(90, "ISO文件创建完成")
                self.log_updated.emit("ISO文件创建成功", "success")

                # 检查ISO文件大小
                if self.iso_path.exists():
                    file_size = self.iso_path.stat().st_size
                    size_mb = file_size / (1024 * 1024)
                    self.log_updated.emit(f"ISO文件大小: {size_mb:.1f} MB", "info")
                    self.command_updated.emit("文件验证", f"ISO文件大小: {size_mb:.1f} MB")

                # 发送100%完成进度
                self.progress_updated.emit(100, "ISO制作完成")

                # 准备结果
                result = {
                    "success": True,
                    "iso_path": str(self.iso_path),
                    "file_size": self.iso_path.stat().st_size if self.iso_path.exists() else 0,
                    "message": message
                }
            else:
                error_msg = f"ISO制作失败: {message}"
                self.log_updated.emit(error_msg, "error")
                result = {
                    "success": False,
                    "error": message
                }

            if self.is_running:
                if result:
                    self.finished.emit(result)

        except Exception as e:
            error_msg = f"ISO制作过程中发生错误: {str(e)}"
            self.log_updated.emit(error_msg, "error")
            if self.is_running:
                self.error_occurred.emit(error_msg)

    def stop(self):
        """停止ISO制作"""
        self.is_running = False

    def show_enhanced_detailed_report(self, result: dict):
        """显示增强版详细报告"""
        try:
            # 导入详细报告对话框
            from .detailed_report_dialog import EnhancedDetailedReportDialog

            dialog = EnhancedDetailedReportDialog(self, result)
            dialog.show_report()

        except Exception as e:
            self.append_log(f"显示详细报告失败: {str(e)}", "error")
            # 回退到简单报告显示
            try:
                report_text = self._format_simple_report(result)
                from .detailed_report_dialog import DetailedReportDialog
                dialog = DetailedReportDialog(self, "增强版版本替换报告", report_text)
                dialog.show_report()
            except Exception as fallback_error:
                self.append_log(f"回退报告显示也失败: {str(fallback_error)}", "error")
                QMessageBox.information(self, "报告", "详细报告功能暂不可用")

    def _format_simple_report(self, result: dict):
        """格式化简单报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("增强版WinPE版本替换报告")
        lines.append("=" * 60)
        lines.append(f"时间: {result.get('timestamp', 'N/A')}")
        lines.append(f"状态: {'成功' if result.get('success', False) else '失败'}")
        lines.append(f"源WIM: {result.get('source_wim', 'N/A')}")
        lines.append(f"目标WIM: {result.get('target_wim', 'N/A')}")
        lines.append(f"输出WIM: {result.get('output_wim', 'N/A')}")
        lines.append(f"外部程序复制: {result.get('external_programs_copied', 0)} 个")
        lines.append("=" * 60)
        return "\n".join(lines)