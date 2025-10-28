#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinPE版本替换UI组件
提供图形化的版本替换操作界面
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

from core.version_replacer import VersionReplacer, create_version_replace_config, ComponentAnalyzer
from core.config_manager import ConfigManager
from utils.logger import get_logger


class VersionReplaceThread(QThread):
    """版本替换工作线程"""

    # 信号定义
    progress_updated = pyqtSignal(int, str)
    log_updated = pyqtSignal(str, str)
    finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, version_replacer: VersionReplacer, config):
        super().__init__()
        self.version_replacer = version_replacer
        self.config = config
        self.is_running = False

    def run(self):
        """执行版本替换"""
        try:
            self.is_running = True

            # 设置回调函数
            self.version_replacer.set_progress_callback(self.on_progress_updated)
            self.version_replacer.set_log_callback(self.on_log_updated)

            # 执行版本替换
            result = self.version_replacer.execute_version_replacement(self.config)

            if self.is_running:
                self.finished.emit(result)

        except Exception as e:
            if self.is_running:
                self.error_occurred.emit(str(e))

    def stop(self):
        """停止线程"""
        self.is_running = False

    def on_progress_updated(self, percent: int, message: str):
        """进度更新回调"""
        self.progress_updated.emit(percent, message)

    def on_log_updated(self, message: str, level: str):
        """日志更新回调"""
        self.log_updated.emit(message, level)


class ComponentAnalysisThread(QThread):
    """组件分析工作线程"""

    progress_updated = pyqtSignal(int, str)
    log_updated = pyqtSignal(str, str)
    analysis_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, source_mount: Path, target_mount: Path):
        super().__init__()
        self.source_mount = source_mount
        self.target_mount = target_mount
        self.is_running = False

    def run(self):
        """执行组件分析"""
        try:
            self.is_running = True

            # 设置回调
            def progress_callback(percent, message):
                if self.is_running:
                    self.progress_updated.emit(percent, message)

            def log_callback(message, level):
                if self.is_running:
                    self.log_updated.emit(message, level)

            # 创建分析器
            analyzer = ComponentAnalyzer()
            analyzer.set_progress_callback = progress_callback
            analyzer.set_log_callback = log_callback

            # 执行分析
            self.progress_updated.emit(10, "开始分析组件差异...")
            analysis = analyzer.analyze_wim_differences(self.source_mount, self.target_mount)
            self.progress_updated.emit(100, "分析完成")

            if self.is_running:
                self.analysis_completed.emit(analysis)

        except Exception as e:
            if self.is_running:
                self.error_occurred.emit(str(e))

    def stop(self):
        """停止分析"""
        self.is_running = False


class VersionReplacerWidget(QWidget):
    """WinPE版本替换UI主组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.logger = get_logger("VersionReplacerWidget")

        # 配置管理器
        self.config_manager = ConfigManager()

        # 版本替换器和线程
        self.version_replacer = None
        self.replace_thread = None
        self.analysis_thread = None

        # UI状态
        self.is_processing = False

        # 自动保存定时器
        self.auto_save_timer = QTimer()
        self.auto_save_timer.setSingleShot(True)  # 单次触发
        self.auto_save_timer.timeout.connect(self.auto_save_config)

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

        # 刷新最近配置列表
        self.refresh_recent_configs()

        self.init_version_replacer()

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题
        title_label = QLabel("WinPE版本替换工具")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 配置标签页
        self.create_config_tab()

        # 分析标签页
        self.create_analysis_tab()

        # 执行标签页
        self.create_execution_tab()

    def create_config_tab(self):
        """创建配置标签页"""
        config_widget = QWidget()
        layout = QVBoxLayout(config_widget)

        # 源目录配置
        source_group = QGroupBox("源目录配置 (0WIN11PE)")
        source_layout = QGridLayout(source_group)

        source_layout.addWidget(QLabel("源目录:"), 0, 0)
        self.source_dir_edit = QLineEdit()
        self.source_dir_edit.setPlaceholderText("选择源WinPE目录 (如: D:\\WinPE_amd64\\0WIN11PE)")
        source_layout.addWidget(self.source_dir_edit, 0, 1)

        self.source_browse_btn = QPushButton("浏览...")
        self.source_browse_btn.clicked.connect(self.browse_source_dir)
        source_layout.addWidget(self.source_browse_btn, 0, 2)

        self.source_wim_label = QLabel("源WIM: boot/boot.wim")
        self.source_wim_label.setStyleSheet("color: gray; font-size: 9pt;")
        source_layout.addWidget(self.source_wim_label, 1, 1)

        layout.addWidget(source_group)

        # 目标目录配置
        target_group = QGroupBox("目标目录配置 (0WIN10OLD)")
        target_layout = QGridLayout(target_group)

        target_layout.addWidget(QLabel("目标目录:"), 0, 0)
        self.target_dir_edit = QLineEdit()
        self.target_dir_edit.setPlaceholderText("选择目标WinPE目录 (如: D:\\WinPE_amd64\\0WIN10OLD)")
        target_layout.addWidget(self.target_dir_edit, 0, 1)

        self.target_browse_btn = QPushButton("浏览...")
        self.target_browse_btn.clicked.connect(self.browse_target_dir)
        target_layout.addWidget(self.target_browse_btn, 0, 2)

        self.target_wim_label = QLabel("目标WIM: boot.wim")
        self.target_wim_label.setStyleSheet("color: gray; font-size: 9pt;")
        target_layout.addWidget(self.target_wim_label, 1, 1)

        layout.addWidget(target_group)

        # 输出目录配置
        output_group = QGroupBox("输出目录配置 (WIN10REPLACED)")
        output_layout = QGridLayout(output_group)

        output_layout.addWidget(QLabel("输出目录:"), 0, 0)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("选择输出目录 (如: D:\\WinPE_amd64\\WIN10REPLACED)")
        output_layout.addWidget(self.output_dir_edit, 0, 1)

        self.output_browse_btn = QPushButton("浏览...")
        self.output_browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.output_browse_btn, 0, 2)

        self.output_wim_label = QLabel("输出WIM: boot/boot.wim")
        self.output_wim_label.setStyleSheet("color: gray; font-size: 9pt;")
        output_layout.addWidget(self.output_wim_label, 1, 1)

        layout.addWidget(output_group)

        # 迁移选项
        options_group = QGroupBox("迁移选项")
        options_layout = QVBoxLayout(options_group)

        self.migrate_external_programs_cb = QCheckBox("迁移外部程序 (WinXShell, Cairo Shell等)")
        self.migrate_external_programs_cb.setChecked(True)
        options_layout.addWidget(self.migrate_external_programs_cb)

        self.migrate_startup_scripts_cb = QCheckBox("迁移启动脚本")
        self.migrate_startup_scripts_cb.setChecked(True)
        options_layout.addWidget(self.migrate_startup_scripts_cb)

        self.migrate_drivers_cb = QCheckBox("迁移驱动程序")
        self.migrate_drivers_cb.setChecked(True)
        options_layout.addWidget(self.migrate_drivers_cb)

        self.migrate_custom_components_cb = QCheckBox("迁移自定义组件 (PEConfig, Programs等)")
        self.migrate_custom_components_cb.setChecked(True)
        options_layout.addWidget(self.migrate_custom_components_cb)

        layout.addWidget(options_group)

        # 最近配置
        recent_group = QGroupBox("最近配置")
        recent_layout = QVBoxLayout(recent_group)

        self.recent_config_combo = QComboBox()
        self.recent_config_combo.setMinimumHeight(30)
        recent_layout.addWidget(self.recent_config_combo)

        recent_button_layout = QHBoxLayout()

        self.load_recent_btn = QPushButton("加载最近配置")
        self.load_recent_btn.clicked.connect(self.load_recent_config)
        recent_button_layout.addWidget(self.load_recent_btn)

        self.refresh_recent_btn = QPushButton("刷新列表")
        self.refresh_recent_btn.clicked.connect(self.refresh_recent_configs)
        recent_button_layout.addWidget(self.refresh_recent_btn)

        recent_layout.addLayout(recent_button_layout)
        layout.addWidget(recent_group)

        # 操作按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.validate_btn = QPushButton("验证配置")
        self.validate_btn.clicked.connect(self.validate_configuration)
        button_layout.addWidget(self.validate_btn)

        self.analyze_btn = QPushButton("分析差异")
        self.analyze_btn.clicked.connect(self.analyze_differences)
        button_layout.addWidget(self.analyze_btn)

        # 配置管理按钮
        self.save_config_btn = QPushButton("保存配置")
        self.save_config_btn.clicked.connect(self.save_configuration)
        self.save_config_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_layout.addWidget(self.save_config_btn)

        self.load_config_btn = QPushButton("加载配置")
        self.load_config_btn.clicked.connect(self.load_configuration)
        self.load_config_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_layout.addWidget(self.load_config_btn)

        layout.addLayout(button_layout)

        self.tab_widget.addTab(config_widget, "配置")

    def create_analysis_tab(self):
        """创建分析标签页"""
        analysis_widget = QWidget()
        layout = QVBoxLayout(analysis_widget)

        # 分析结果显示
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.analysis_text)

        # 控制按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.refresh_analysis_btn = QPushButton("重新分析")
        self.refresh_analysis_btn.clicked.connect(self.analyze_differences)
        button_layout.addWidget(self.refresh_analysis_btn)

        self.save_analysis_btn = QPushButton("保存分析报告")
        self.save_analysis_btn.clicked.connect(self.save_analysis_report)
        button_layout.addWidget(self.save_analysis_btn)

        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("background-color: #ddd; margin: 0 10px;")
        button_layout.addWidget(separator)

        # 一键制作ISO按钮（分析标签页）
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
        button_layout.addWidget(self.quick_iso_analysis_btn)

        layout.addLayout(button_layout)

        self.tab_widget.addTab(analysis_widget, "分析")

    def create_execution_tab(self):
        """创建执行标签页"""
        execution_widget = QWidget()
        layout = QVBoxLayout(execution_widget)

        # 进度条
        progress_group = QGroupBox("进度")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("就绪")
        self.progress_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.progress_label)

        layout.addWidget(progress_group)

        # 日志区域
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        # 设置最小高度，但不限制最大高度，让它能够扩展
        self.log_text.setMinimumHeight(150)
        # 设置大小策略，让它能够垂直扩展
        from PyQt5.QtWidgets import QSizePolicy
        self.log_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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

        self.replace_btn = QPushButton("开始版本替换")
        self.replace_btn.clicked.connect(self.start_version_replace)
        self.replace_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_layout.addWidget(self.replace_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_version_replace)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_layout.addWidget(self.stop_btn)

        # 制作ISO按钮
        self.create_iso_btn = QPushButton("制作ISO")
        self.create_iso_btn.clicked.connect(self.create_iso_from_output)
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
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.create_iso_btn.setEnabled(False)  # 初始禁用，完成替换后启用
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
        self.migrate_external_programs_cb.toggled.connect(self.on_config_changed)
        self.migrate_startup_scripts_cb.toggled.connect(self.on_config_changed)
        self.migrate_drivers_cb.toggled.connect(self.on_config_changed)
        self.migrate_custom_components_cb.toggled.connect(self.on_config_changed)

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

            # 加载迁移选项
            migrate_options = config_data.get("migration_options", {})
            self.migrate_external_programs_cb.setChecked(
                migrate_options.get("migrate_external_programs", True)
            )
            self.migrate_startup_scripts_cb.setChecked(
                migrate_options.get("migrate_startup_scripts", True)
            )
            self.migrate_drivers_cb.setChecked(
                migrate_options.get("migrate_drivers", True)
            )
            self.migrate_custom_components_cb.setChecked(
                migrate_options.get("migrate_custom_components", True)
            )

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

            # 加载迁移选项
            migrate_options = self.config_manager.get("version_replace.migrate_options", {})
            self.migrate_external_programs_cb.setChecked(
                migrate_options.get("startup_scripts", True)  # 映射到外部程序选项
            )
            self.migrate_startup_scripts_cb.setChecked(
                migrate_options.get("startup_scripts", True)
            )
            self.migrate_drivers_cb.setChecked(
                migrate_options.get("drivers", True)
            )
            self.migrate_custom_components_cb.setChecked(
                migrate_options.get("custom_components", True)
            )

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

            # 保存迁移选项
            migrate_options = {
                "startup_scripts": self.migrate_startup_scripts_cb.isChecked(),
                "winxshell_config": self.migrate_external_programs_cb.isChecked(),  # 外部程序包含WinXShell
                "desktop_environment": self.migrate_external_programs_cb.isChecked(),  # 外部程序包含桌面环境
                "drivers": self.migrate_drivers_cb.isChecked(),
                "custom_components": self.migrate_custom_components_cb.isChecked()
            }
            self.config_manager.set("version_replace.migrate_options", migrate_options)

            # 添加到最近配置
            recent_configs = self.config_manager.get("version_replace.recent_configs", [])
            current_config = {
                "source_dir": self.source_dir_edit.text(),
                "target_dir": self.target_dir_edit.text(),
                "output_dir": self.output_dir_edit.text(),
                "timestamp": datetime.now().isoformat()
            }

            # 检查是否已存在相同配置
            for i, config in enumerate(recent_configs):
                if (config.get("source_dir") == current_config["source_dir"] and
                    config.get("target_dir") == current_config["target_dir"]):
                    recent_configs.pop(i)
                    break

            # 添加到开头
            recent_configs.insert(0, current_config)

            # 限制最近配置数量
            recent_configs = recent_configs[:10]

            self.config_manager.set("version_replace.recent_configs", recent_configs)

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

    def load_recent_config(self):
        """加载选中的最近配置"""
        try:
            current_index = self.recent_config_combo.currentIndex()
            if current_index >= 0:
                recent_configs = self.config_manager.get("version_replace.recent_configs", [])
                if current_index < len(recent_configs):
                    config = recent_configs[current_index]

                    # 应用配置
                    self.source_dir_edit.setText(config.get("source_dir", ""))
                    self.target_dir_edit.setText(config.get("target_dir", ""))
                    self.output_dir_edit.setText(config.get("output_dir", ""))

                    # 验证路径
                    self.validate_paths()

                    self.append_log(f"已加载最近配置: {config.get('timestamp', '')}", "success")

        except Exception as e:
            self.append_log(f"加载最近配置失败: {str(e)}", "error")

    def refresh_recent_configs(self):
        """刷新最近配置列表"""
        try:
            self.recent_config_combo.clear()

            recent_configs = self.config_manager.get("version_replace.recent_configs", [])
            for config in recent_configs:
                # 创建显示文本
                source = config.get("source_dir", "").split("\\")[-1] if config.get("source_dir") else "未设置"
                target = config.get("target_dir", "").split("\\")[-1] if config.get("target_dir") else "未设置"
                timestamp = config.get("timestamp", "")[:19] if config.get("timestamp") else ""

                display_text = f"{source} -> {target} ({timestamp})"
                self.recent_config_combo.addItem(display_text)

            self.append_log(f"最近配置列表已刷新，共 {len(recent_configs)} 个配置", "info")

        except Exception as e:
            self.append_log(f"刷新最近配置列表失败: {str(e)}", "error")

    def toggle_auto_save(self, checked: bool):
        """切换自动保存"""
        self.config_manager.set("version_replace.auto_save_config", checked)
        if checked:
            self.append_log("已启用配置自动保存", "info")
        else:
            self.append_log("已禁用配置自动保存", "info")

    def toggle_auto_load(self, checked: bool):
        """切换自动加载"""
        self.config_manager.set("version_replace.auto_load_config", checked)
        if checked:
            self.append_log("已启用启动时自动加载配置", "info")
        else:
            self.append_log("已禁用启动时自动加载配置", "info")

    def init_version_replacer(self):
        """初始化版本替换器"""
        try:
            # 导入必要的模块
            from core.config_manager import ConfigManager
            from core.adk_manager import ADKManager
            from core.unified_manager.wim_manager import UnifiedWIMManager

            # 延迟导入以避免循环依赖
            if hasattr(self.parent_widget, 'config_manager'):
                config_manager = self.parent_widget.config_manager
            else:
                config_manager = ConfigManager()

            if hasattr(self.parent_widget, 'adk_manager'):
                adk_manager = self.parent_widget.adk_manager
            else:
                adk_manager = ADKManager()

            # 初始化统一WIM管理器
            unified_wim_manager = UnifiedWIMManager(config_manager, adk_manager)

            # 创建版本替换器
            self.version_replacer = VersionReplacer(config_manager, adk_manager, unified_wim_manager)
            self.append_log("版本替换器初始化成功", "info")

        except Exception as e:
            self.append_log(f"版本替换器初始化失败: {str(e)}", "error")
            self.logger.error(f"版本替换器初始化失败: {str(e)}")

    def browse_source_dir(self):
        """浏览源目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择源WinPE目录",
            str(Path.cwd()),
            QFileDialog.ShowDirsOnly
        )
        if directory:
            self.source_dir_edit.setText(directory)
            self.validate_paths()

    def browse_target_dir(self):
        """浏览目标目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择目标WinPE目录",
            str(Path.cwd()),
            QFileDialog.ShowDirsOnly
        )
        if directory:
            self.target_dir_edit.setText(directory)
            self.validate_paths()

    def browse_output_dir(self):
        """浏览输出目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择输出目录",
            str(Path.cwd()),
            QFileDialog.ShowDirsOnly
        )
        if directory:
            self.output_dir_edit.setText(directory)
            self.validate_paths()

    def validate_paths(self):
        """验证路径有效性"""
        source_dir = self.source_dir_edit.text().strip()
        target_dir = self.target_dir_edit.text().strip()
        output_dir = self.output_dir_edit.text().strip()

        # 检查路径是否有效
        valid_paths = True
        messages = []

        if source_dir and not Path(source_dir).exists():
            valid_paths = False
            messages.append("源目录不存在")

        if target_dir and not Path(target_dir).exists():
            valid_paths = False
            messages.append("目标目录不存在")

        # 更新按钮状态
        self.analyze_btn.setEnabled(valid_paths and not self.is_processing)
        self.replace_btn.setEnabled(valid_paths and not self.is_processing)

        # 显示验证结果
        if messages:
            self.append_log("路径验证失败: " + "; ".join(messages), "warning")
        elif all([source_dir, target_dir, output_dir]):
            self.append_log("路径验证通过", "info")

    def validate_configuration(self):
        """验证配置"""
        source_dir = self.source_dir_edit.text().strip()
        target_dir = self.target_dir_edit.text().strip()
        output_dir = self.output_dir_edit.text().strip()

        if not all([source_dir, target_dir, output_dir]):
            QMessageBox.warning(self, "配置错误", "请填写所有必需的路径!")
            return False

        try:
            config = create_version_replace_config(
                source_dir=source_dir,
                target_dir=target_dir,
                output_dir=output_dir
            )

            is_valid, errors = config.validate()
            if not is_valid:
                QMessageBox.warning(self, "配置错误", "\n".join(errors))
                return False

            QMessageBox.information(self, "配置验证", "配置验证通过!")
            self.append_log("配置验证成功", "info")
            return True

        except Exception as e:
            QMessageBox.critical(self, "配置错误", f"配置验证失败: {str(e)}")
            self.append_log(f"配置验证失败: {str(e)}", "error")
            return False

    def analyze_differences(self):
        """分析组件差异"""
        if not self.validate_configuration():
            return

        source_dir = self.source_dir_edit.text().strip()
        target_dir = self.target_dir_edit.text().strip()

        try:
            self.append_log("开始分析源和目标WIM的差异...", "info")
            self.is_processing = True
            self.update_ui_state()

            source_mount = Path(source_dir) / "mount"
            target_mount = Path(target_dir) / "mount"

            if not source_mount.exists():
                self.append_log("警告: 源WIM可能未挂载", "warning")
            if not target_mount.exists():
                self.append_log("警告: 目标WIM可能未挂载", "warning")

            # 创建分析线程
            self.analysis_thread = ComponentAnalysisThread(source_mount, target_mount)
            self.analysis_thread.progress_updated.connect(self.on_analysis_progress)
            self.analysis_thread.log_updated.connect(self.append_log)
            self.analysis_thread.analysis_completed.connect(self.on_analysis_completed)
            self.analysis_thread.error_occurred.connect(self.on_analysis_error)

            self.analysis_thread.start()

        except Exception as e:
            self.append_log(f"分析差异失败: {str(e)}", "error")
            self.is_processing = False
            self.update_ui_state()

    def on_analysis_progress(self, percent: int, message: str):
        """分析进度更新"""
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)

    def on_analysis_completed(self, analysis: dict):
        """分析完成处理"""
        self.is_processing = False
        self.update_ui_state()

        try:
            # 显示分析结果
            self.display_analysis_result(analysis)
            self.append_log("组件差异分析完成", "info")

        except Exception as e:
            self.append_log(f"显示分析结果失败: {str(e)}", "error")

    def on_analysis_error(self, error_message: str):
        """分析错误处理"""
        self.is_processing = False
        self.update_ui_state()
        self.append_log(f"分析差异失败: {error_message}", "error")

    def display_analysis_result(self, analysis: dict):
        """显示分析结果"""
        try:
            from core.version_replacer import ComponentAnalyzer
            analyzer = ComponentAnalyzer()
            report = analyzer.generate_analysis_report(analysis)

            self.analysis_text.setPlainText(report)
            self.tab_widget.setCurrentIndex(1)  # 切换到分析标签页

        except Exception as e:
            self.append_log(f"显示分析结果失败: {str(e)}", "error")

    def start_version_replace(self, skip_confirmation: bool = False):
        """开始版本替换"""
        if not self.validate_configuration():
            return

        # 确认对话框（除非跳过）
        if not skip_confirmation:
            reply = QMessageBox.question(
                self, "确认版本替换",
                "确定要开始版本替换吗？\n\n"
                "此操作将:\n"
                "1. 复制源目录结构到输出目录\n"
                "2. 复制目标boot.wim到输出目录\n"
                "3. 挂载输出WIM并迁移组件\n"
                "4. 更新配置文件\n\n"
                "请确保所有WIM已正确挂载。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

        try:
            # 创建配置
            config = create_version_replace_config(
                source_dir=self.source_dir_edit.text(),
                target_dir=self.target_dir_edit.text(),
                output_dir=self.output_dir_edit.text(),
                migrate_options={
                    'migrate_external_programs': self.migrate_external_programs_cb.isChecked(),
                    'migrate_startup_scripts': self.migrate_startup_scripts_cb.isChecked(),
                    'migrate_drivers': self.migrate_drivers_cb.isChecked(),
                    'migrate_custom_components': self.migrate_custom_components_cb.isChecked(),
                    'preserve_source_structure': True,
                    'replace_core_files': False,
                    'update_configurations': True
                }
            )

            # 更新UI状态
            self.is_processing = True
            self.update_ui_state()

            # 创建工作线程
            self.replace_thread = VersionReplaceThread(self.version_replacer, config)
            self.replace_thread.progress_updated.connect(self.on_progress_updated)
            self.replace_thread.log_updated.connect(self.append_log)
            self.replace_thread.finished.connect(self.on_version_replace_finished)
            self.replace_thread.error_occurred.connect(self.on_version_replace_error)

            self.replace_thread.start()
            self.append_log("版本替换线程已启动", "info")

        except Exception as e:
            self.append_log(f"启动版本替换失败: {str(e)}", "error")
            self.is_processing = False
            self.update_ui_state()

    def stop_version_replace(self):
        """停止版本替换"""
        if self.replace_thread and self.replace_thread.isRunning():
            self.replace_thread.stop()
            self.replace_thread.wait(5000)
            self.append_log("版本替换已停止", "warning")
            self.is_processing = False
            self.update_ui_state()

    def on_progress_updated(self, percent: int, message: str):
        """进度更新处理"""
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)

    def on_version_replace_finished(self, result: dict):
        """版本替换完成处理"""
        self.is_processing = False
        self.update_ui_state()

        if result.get("success", False):
            self.append_log("版本替换成功完成!", "info")
            self.append_log(f"输出目录: {result.get('output_path', 'Unknown')}", "info")

            # 启用制作ISO按钮
            self.create_iso_btn.setEnabled(True)
            self.quick_iso_btn.setEnabled(True)
            self.append_log("🚀 现在可以制作ISO文件", "success")

            # 显示迁移摘要
            steps = result.get("steps", {})
            migration_step = steps.get("migration", {})
            migrated_items = migration_step.get("migrated_items", [])

            if migrated_items:
                self.append_log(f"迁移项目共 {len(migrated_items)} 个:", "info")
                for item in migrated_items:
                    self.append_log(f"  - {item}", "info")

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
                self, "版本替换完成",
                "版本替换已成功完成!\n\n是否查看详细报告?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                self.show_detailed_report(result)

        else:
            self.append_log("版本替换失败", "error")
            errors = result.get("errors", [])
            for error in errors:
                self.append_log(f"错误: {error}", "error")

            warnings = result.get("warnings", [])
            for warning in warnings:
                self.append_log(f"警告: {warning}", "warning")

    def on_version_replace_error(self, error_message: str):
        """版本替换错误处理"""
        self.is_processing = False
        self.update_ui_state()
        self.append_log(f"版本替换过程中发生错误: {error_message}", "error")

    def show_detailed_report(self, result: dict):
        """显示详细报告"""
        try:
            # 导入新的详细报告对话框
            from .detailed_report_dialog import EnhancedDetailedReportDialog

            if hasattr(self, 'version_replacer'):
                # 使用增强版详细报告对话框
                dialog = EnhancedDetailedReportDialog(self, result)
                dialog.show_report()
            else:
                QMessageBox.information(self, "报告", "详细报告功能暂不可用")

        except Exception as e:
            self.append_log(f"显示报告失败: {str(e)}", "error")
            # 如果新对话框失败，回退到原来的QMessageBox
            try:
                if hasattr(self, 'version_replacer'):
                    report = self.version_replacer.generate_replacement_report(result)
                    report_window = QMessageBox(self)
                    report_window.setWindowTitle("版本替换详细报告")
                    report_window.setIcon(QMessageBox.Information)
                    report_window.setText("版本替换操作已完成")
                    report_window.setDetailedText(report)
                    report_window.setStandardButtons(QMessageBox.Ok)
                    report_window.exec_()
                else:
                    QMessageBox.information(self, "报告", "详细报告功能暂不可用")
            except Exception as fallback_error:
                self.append_log(f"回退报告显示也失败: {str(fallback_error)}", "error")

    def update_ui_state(self):
        """更新UI状态"""
        # 更新按钮状态
        self.analyze_btn.setEnabled(not self.is_processing)
        self.replace_btn.setEnabled(not self.is_processing)
        self.stop_btn.setEnabled(self.is_processing)

        # 更新输入框状态
        self.source_dir_edit.setReadOnly(self.is_processing)
        self.target_dir_edit.setReadOnly(self.is_processing)
        self.output_dir_edit.setReadOnly(self.is_processing)

        # 更新浏览按钮状态
        self.source_browse_btn.setEnabled(not self.is_processing)
        self.target_browse_btn.setEnabled(not self.is_processing)
        self.output_browse_btn.setEnabled(not self.is_processing)

        # 更新选项框状态
        self.migrate_external_programs_cb.setEnabled(not self.is_processing)
        self.migrate_startup_scripts_cb.setEnabled(not self.is_processing)
        self.migrate_drivers_cb.setEnabled(not self.is_processing)
        self.migrate_custom_components_cb.setEnabled(not self.is_processing)

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

    def save_log(self):
        """保存日志"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存日志",
                str(Path.cwd() / "version_replace_log.txt"),
                "文本文件 (*.txt);;所有文件 (*)"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                self.append_log(f"日志已保存到: {file_path}", "info")

        except Exception as e:
            self.append_log(f"保存日志失败: {str(e)}", "error")

    def save_analysis_report(self):
        """保存分析报告"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存分析报告",
                str(Path.cwd() / "component_analysis_report.txt"),
                "文本文件 (*.txt);;所有文件 (*)"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.analysis_text.toPlainText())
                self.append_log(f"分析报告已保存到: {file_path}", "info")

        except Exception as e:
            self.append_log(f"保存分析报告失败: {str(e)}", "error")

    def save_configuration(self):
        """保存当前配置到文件"""
        try:
            # 获取当前配置
            config_data = self.get_current_configuration()

            # 保存文件对话框
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存版本替换配置",
                str(Path.cwd() / "version_replace_config.json"),
                "JSON文件 (*.json);;所有文件 (*)"
            )

            if not file_path:
                return

            # 确保文件扩展名
            if not file_path.endswith('.json'):
                file_path += '.json'

            # 保存配置到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            self.append_log(f"配置已保存到: {file_path}", "success")
            QMessageBox.information(self, "保存成功", f"配置已成功保存到:\n{file_path}")

        except Exception as e:
            self.append_log(f"保存配置失败: {str(e)}", "error")
            QMessageBox.critical(self, "保存失败", f"保存配置时发生错误:\n{str(e)}")

    def load_configuration(self):
        """从文件加载配置"""
        try:
            # 打开文件对话框
            file_path, _ = QFileDialog.getOpenFileName(
                self, "加载版本替换配置",
                str(Path.cwd()),
                "JSON文件 (*.json);;所有文件 (*)"
            )

            if not file_path:
                return

            # 读取配置文件
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 应用配置到界面
            self.apply_configuration(config_data)

            self.append_log(f"配置已从文件加载: {file_path}", "success")
            QMessageBox.information(self, "加载成功", f"配置已成功从文件加载:\n{file_path}")

        except json.JSONDecodeError as e:
            error_msg = f"配置文件格式错误: {str(e)}"
            self.append_log(error_msg, "error")
            QMessageBox.critical(self, "加载失败", error_msg)
        except Exception as e:
            error_msg = f"加载配置失败: {str(e)}"
            self.append_log(error_msg, "error")
            QMessageBox.critical(self, "加载失败", error_msg)

    def get_current_configuration(self) -> dict:
        """获取当前界面配置"""
        config_data = {
            "version": "1.0",
            "created_time": datetime.now().isoformat(),
            "paths": {
                "source_dir": self.source_dir_edit.text(),
                "target_dir": self.target_dir_edit.text(),
                "output_dir": self.output_dir_edit.text()
            },
            "migration_options": {
                "migrate_external_programs": self.migrate_external_programs_cb.isChecked(),
                "migrate_startup_scripts": self.migrate_startup_scripts_cb.isChecked(),
                "migrate_drivers": self.migrate_drivers_cb.isChecked(),
                "migrate_custom_components": self.migrate_custom_components_cb.isChecked(),
                "preserve_source_structure": True,
                "replace_core_files": False,
                "update_configurations": True
            },
            "description": "WinPE版本替换配置文件"
        }
        return config_data

    def apply_configuration(self, config_data: dict):
        """应用配置到界面"""
        try:
            # 应用路径配置
            paths = config_data.get("paths", {})
            self.source_dir_edit.setText(paths.get("source_dir", ""))
            self.target_dir_edit.setText(paths.get("target_dir", ""))
            self.output_dir_edit.setText(paths.get("output_dir", ""))

            # 应用迁移选项
            migration_options = config_data.get("migration_options", {})
            self.migrate_external_programs_cb.setChecked(
                migration_options.get("migrate_external_programs", True)
            )
            self.migrate_startup_scripts_cb.setChecked(
                migration_options.get("migrate_startup_scripts", True)
            )
            self.migrate_drivers_cb.setChecked(
                migration_options.get("migrate_drivers", True)
            )
            self.migrate_custom_components_cb.setChecked(
                migration_options.get("migrate_custom_components", True)
            )

            # 验证路径
            self.validate_paths()

            self.append_log("配置已应用到界面", "info")

        except Exception as e:
            self.append_log(f"应用配置失败: {str(e)}", "error")
            raise

    def create_quick_config_presets(self):
        """创建快速配置预设"""
        try:
            # 创建预设配置目录
            presets_dir = Path.cwd() / "configs" / "version_replace_presets"
            presets_dir.mkdir(parents=True, exist_ok=True)

            # 预设1: 完整迁移
            full_migration = {
                "version": "1.0",
                "created_time": datetime.now().isoformat(),
                "name": "完整迁移预设",
                "description": "迁移所有组件，保持完整的源WinPE功能",
                "paths": {
                    "source_dir": "",
                    "target_dir": "",
                    "output_dir": ""
                },
                "migration_options": {
                    "migrate_external_programs": True,
                    "migrate_startup_scripts": True,
                    "migrate_drivers": True,
                    "migrate_custom_components": True,
                    "preserve_source_structure": True,
                    "replace_core_files": False,
                    "update_configurations": True
                }
            }

            # 预设2: 仅程序迁移
            program_migration = {
                "version": "1.0",
                "created_time": datetime.now().isoformat(),
                "name": "仅程序迁移预设",
                "description": "只迁移外部程序和桌面环境",
                "paths": {
                    "source_dir": "",
                    "target_dir": "",
                    "output_dir": ""
                },
                "migration_options": {
                    "migrate_external_programs": True,
                    "migrate_startup_scripts": False,
                    "migrate_drivers": False,
                    "migrate_custom_components": True,
                    "preserve_source_structure": True,
                    "replace_core_files": False,
                    "update_configurations": True
                }
            }

            # 保存预设
            with open(presets_dir / "full_migration.json", 'w', encoding='utf-8') as f:
                json.dump(full_migration, f, ensure_ascii=False, indent=2)

            with open(presets_dir / "program_migration.json", 'w', encoding='utf-8') as f:
                json.dump(program_migration, f, ensure_ascii=False, indent=2)

            self.append_log("快速配置预设已创建", "info")

        except Exception as e:
            self.append_log(f"创建配置预设失败: {str(e)}", "error")

    def load_quick_preset(self, preset_name: str):
        """加载快速预设"""
        try:
            presets_dir = Path.cwd() / "configs" / "version_replace_presets"
            preset_file = presets_dir / f"{preset_name}.json"

            if not preset_file.exists():
                self.create_quick_config_presets()

            if preset_file.exists():
                with open(preset_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # 应用预设（不覆盖路径）
                current_config = self.get_current_configuration()
                config_data["paths"] = current_config["paths"]

                self.apply_configuration(config_data)
                self.append_log(f"已加载预设: {preset_name}", "success")

        except Exception as e:
            self.append_log(f"加载预设失败: {str(e)}", "error")

    def create_iso_from_output(self):
        """从输出目录制作ISO文件"""
        try:
            # 获取输出目录
            output_dir = self.output_dir_edit.text().strip()
            if not output_dir:
                QMessageBox.warning(self, "路径错误", "请先完成版本替换或手动设置输出目录")
                return

            output_path = Path(output_dir)
            if not output_path.exists():
                QMessageBox.critical(self, "路径错误", f"输出目录不存在: {output_dir}")
                return

            # 检查是否存在boot.wim
            boot_wim = output_path / "boot" / "boot.wim"
            if not boot_wim.exists():
                QMessageBox.warning(self, "文件缺失", f"在输出目录中未找到boot.wim文件:\n{boot_wim}")
                return

            # 询问ISO保存位置
            iso_file, _ = QFileDialog.getSaveFileName(
                self, "保存ISO文件",
                str(Path.cwd() / f"WinPE_Replaced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.iso"),
                "ISO文件 (*.iso);;所有文件 (*)"
            )

            if not iso_file:
                return

            iso_path = Path(iso_file)

            # 创建ISO制作线程
            self.iso_thread = ISOCreationThread(
                output_dir=output_path,
                iso_path=iso_path,
                parent=self
            )
            self.iso_thread.progress_updated.connect(self.on_iso_progress)
            self.iso_thread.log_updated.connect(self.append_log)
            self.iso_thread.finished.connect(self.on_iso_finished)
            self.iso_thread.error_occurred.connect(self.on_iso_error)

            # 禁用制作ISO按钮
            self.create_iso_btn.setEnabled(False)

            # 启用停止按钮
            self.stop_btn.setEnabled(True)
            self.stop_btn.setText("停止制作")
            self.stop_btn.disconnect()
            self.stop_btn.clicked.connect(self.stop_iso_creation)

            # 连接命令输出信号
            self.iso_thread.command_updated.connect(self.on_iso_command_output)

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
            self.quick_iso_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("停止")
            self.stop_btn.disconnect()
            self.stop_btn.clicked.connect(self.stop_version_replace)

    def on_iso_progress(self, percent: int, message: str):
        """ISO制作进度更新"""
        # 如果不在版本替换处理中，显示ISO进度
        if not self.is_processing:
            self.progress_bar.setValue(percent)
            self.progress_label.setText(f"ISO制作: {message}")
        self.append_log(f"[ISO {percent:3d}%] {message}", "info")

    def on_iso_finished(self, result: dict):
        """ISO制作完成处理"""
        try:
            # 恢复按钮状态
            self.create_iso_btn.setEnabled(True)
            self.quick_iso_btn.setEnabled(True)
            if hasattr(self, 'quick_iso_analysis_btn'):
                self.quick_iso_analysis_btn.setEnabled(True)
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

                # 设置进度条到100%
                self.progress_bar.setValue(100)
                self.progress_label.setText("ISO制作完成")

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
            self.quick_iso_btn.setEnabled(True)
            if hasattr(self, 'quick_iso_analysis_btn'):
                self.quick_iso_analysis_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("停止")
            self.stop_btn.disconnect()
            self.stop_btn.clicked.connect(self.stop_version_replace)

            self.append_log(f"ISO制作过程中发生错误: {error_message}", "error")
            QMessageBox.critical(self, "制作错误", f"ISO制作过程中发生错误:\n{error_message}")

        except Exception as e:
            self.append_log(f"ISO错误处理失败: {str(e)}", "error")

    def quick_create_iso(self):
        """一键制作ISO - 先版本替换再制作ISO"""
        try:
            # 切换到执行标签页
            self.tab_widget.setCurrentIndex(4)  # 执行标签页索引

            # 检查是否已存在有效的版本替换结果
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
                reply = QMessageBox.question(
                    self, "版本替换和ISO制作",
                    f"检测到需要先完成版本替换操作。\n\n"
                    f"系统将按以下顺序执行：\n"
                    f"1. 执行版本替换（从源WIM到目标WIM）\n"
                    f"2. 制作ISO文件\n\n"
                    f"预计总时间：10-20分钟\n\n"
                    f"确定要继续吗？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply != QMessageBox.Yes:
                    return

                # 先执行版本替换
                self.append_log("开始执行版本替换...", "info")
                self.start_version_replace(skip_confirmation=True)

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
            # 获取输出目录
            output_dir = self.output_dir_edit.text().strip()
            output_path = Path(output_dir)

            # 检查关键文件
            boot_wim = output_path / "boot" / "boot.wim"
            if not boot_wim.exists():
                QMessageBox.warning(self, "文件缺失",
                                  f"在输出目录中未找到boot.wim文件:\n{boot_wim}\n\n"
                                  "版本替换可能未成功完成。")
                return

            # 显示确认对话框
            reply = QMessageBox.question(
                self, "确认制作ISO",
                f"准备从以下目录制作ISO文件:\n"
                f"源目录: {output_dir}\n"
                f"boot.wim大小: {boot_wim.stat().st_size:,} bytes\n\n"
                f"这可能会需要几分钟时间。\n\n"
                f"确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 生成自动文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_iso_path = Path.cwd() / "output" / f"WinPE_Replaced_{timestamp}.iso"

            # 确保输出目录存在
            default_iso_path.parent.mkdir(parents=True, exist_ok=True)

            # 创建ISO制作线程
            self.iso_thread = ISOCreationThread(
                output_dir=output_path,
                iso_path=default_iso_path,
                parent=self
            )
            self.iso_thread.progress_updated.connect(self.on_iso_progress)
            self.iso_thread.log_updated.connect(self.append_log)
            self.iso_thread.finished.connect(self.on_iso_finished)
            self.iso_thread.error_occurred.connect(self.on_iso_error)
            self.iso_thread.command_updated.connect(self.on_iso_command_output)

            # 更新UI状态
            self.quick_iso_btn.setEnabled(False)
            if hasattr(self, 'quick_iso_analysis_btn'):
                self.quick_iso_analysis_btn.setEnabled(False)
            self.create_iso_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.stop_btn.setText("停止制作")
            self.stop_btn.disconnect()
            self.stop_btn.clicked.connect(self.stop_iso_creation)

            # 开始制作
            self.iso_thread.start()
            self.append_log("🚀 开始一键制作ISO文件...", "info")
            self.append_log(f"源目录: {output_dir}", "info")
            self.append_log(f"目标ISO: {default_iso_path}", "info")

        except Exception as e:
            self.append_log(f"启动一键ISO制作失败: {str(e)}", "error")
            QMessageBox.critical(self, "制作失败", f"启动一键ISO制作时发生错误:\n{str(e)}")


class ISOCreationThread(QThread):
    """ISO制作工作线程"""

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

                if self.is_running:
                    self.finished.emit(result)
            else:
                error_msg = f"ISO制作失败: {message}"
                self.log_updated.emit(error_msg, "error")
                result = {
                    "success": False,
                    "error": message
                }
                if self.is_running:
                    self.error_occurred.emit(error_msg)

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