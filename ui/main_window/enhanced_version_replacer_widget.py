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
    QCheckBox, QMessageBox, QFrame, QSplitter, QTabWidget, QComboBox,
    QSizePolicy
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QDateTime, QTimer
from PyQt5.QtGui import QFont, QTextCharFormat, QColor

from core.version_replacer.enhanced_replacer import EnhancedVersionReplacer
from core.version_replacer import create_version_replace_config
from core.config_manager import ConfigManager
from utils.logger import get_logger
from ui.button_styler import apply_3d_button_style, apply_3d_button_style_alternate, apply_3d_button_style_red


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

        # 设置配置变更监听（必须在setup_connections之前）
        self.setup_config_watchers()
        self.setup_connections()

        # 自动加载配置（优先从JSON文件加载）
        if self.config_manager.get("version_replace.auto_load_config", True):
            # 先尝试从JSON配置文件加载
            if not self.load_config_from_json_file():
                # 如果JSON文件不存在或加载失败，则从系统配置加载
                self.load_config_from_system()

        self.init_enhanced_version_replacer()

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)

        # 创建整版布局
        self.create_unified_layout()

        layout.addLayout(self.main_layout)

    def create_config_section(self):
        """创建配置区域"""
        config_widget = QWidget()
        layout = QVBoxLayout(config_widget)
        layout.setContentsMargins(2, 2, 2, 2)  # 减小边距
        layout.setSpacing(2)  # 减小间距
        
        # 路径配置 - 紧凑布局
        paths_group = QGroupBox("路径配置")
        paths_layout = QGridLayout(paths_group)
        paths_layout.setContentsMargins(3, 3, 3, 3)  # 减小边距
        paths_layout.setSpacing(2)  # 减小间距
        
        # 第一行：源目录和目标目录
        self.source_dir_edit = QLineEdit()
        self.source_dir_edit.setText("D:\\APP\\WinPEManager\\WinPE_amd64\\0WIN11PE")  # 默认值
        self.source_dir_edit.setMaximumHeight(24)  # 限制高度
        self.target_dir_edit = QLineEdit()
        self.target_dir_edit.setText("D:\\APP\\WinPEManager\\WinPE_amd64\\0WIN10OLD")  # 默认值
        self.target_dir_edit.setMaximumHeight(24)  # 限制高度
        
        paths_layout.addWidget(QLabel("源:"), 0, 0)
        paths_layout.addWidget(self.source_dir_edit, 0, 1)
        self.source_browse_btn = QPushButton("...")
        self.source_browse_btn.setMaximumWidth(30)  # 减小按钮宽度
        self.source_browse_btn.setMaximumHeight(24)  # 限制高度
        self.source_browse_btn.clicked.connect(self.browse_source_dir)
        paths_layout.addWidget(self.source_browse_btn, 0, 2)
        
        paths_layout.addWidget(QLabel("目标:"), 0, 3)
        paths_layout.addWidget(self.target_dir_edit, 0, 4)
        self.target_browse_btn = QPushButton("...")
        self.target_browse_btn.setMaximumWidth(30)  # 减小按钮宽度
        self.target_browse_btn.setMaximumHeight(24)  # 限制高度
        self.target_browse_btn.clicked.connect(self.browse_target_dir)
        paths_layout.addWidget(self.target_browse_btn, 0, 5)
        
        # 第二行：输出目录和选项
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setText("D:\\APP\\WinPEManager\\WinPE_amd64\\WIN10REPLACED")  # 默认值
        self.output_dir_edit.setMaximumHeight(24)  # 限制高度
        
        paths_layout.addWidget(QLabel("输出:"), 1, 0)
        paths_layout.addWidget(self.output_dir_edit, 1, 1)
        self.output_browse_btn = QPushButton("...")
        self.output_browse_btn.setMaximumWidth(30)  # 减小按钮宽度
        self.output_browse_btn.setMaximumHeight(24)  # 限制高度
        self.output_browse_btn.clicked.connect(self.browse_output_dir)
        paths_layout.addWidget(self.output_browse_btn, 1, 2)
        
        # 选项配置 - 紧凑布局
        options_layout = QHBoxLayout()
        options_layout.setSpacing(5)  # 减小间距
        self.use_dism_cb = QCheckBox("DISM")
        self.use_dism_cb.setChecked(True)  # 默认选中
        self.deep_analysis_cb = QCheckBox("深度")
        self.deep_analysis_cb.setChecked(True)  # 默认选中
        self.copy_external_cb = QCheckBox("外部")
        self.verify_after_copy_cb = QCheckBox("验证")
        options_layout.addWidget(self.use_dism_cb)
        options_layout.addWidget(self.deep_analysis_cb)
        options_layout.addWidget(self.copy_external_cb)
        options_layout.addWidget(self.verify_after_copy_cb)
        options_layout.addStretch()
        
        paths_layout.addLayout(options_layout, 1, 3, 1, 3)
        
        layout.addWidget(paths_group)
        
        return config_widget
    def create_execution_section(self):
        """创建执行区域"""
        execution_widget = QWidget()
        layout = QVBoxLayout(execution_widget)
        layout.setContentsMargins(2, 2, 2, 2)  # 减小边距
        layout.setSpacing(2)  # 减小间距
        
        # 执行进度 - 紧凑布局
        progress_group = QGroupBox("执行进度")
        progress_group.setMaximumHeight(60)  # 限制高度
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(3, 3, 3, 3)  # 减小边距
        progress_layout.setSpacing(2)  # 减小间距
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(20)  # 限制进度条高度
        progress_layout.addWidget(self.progress_bar)
        
        # 执行控制 - 紧凑布局
        control_layout = QHBoxLayout()
        self.stop_replace_btn = QPushButton("停止")
        self.stop_replace_btn.setMaximumHeight(24)  # 限制按钮高度
        self.stop_replace_btn.clicked.connect(self.stop_version_replace)
        self.stop_replace_btn.setEnabled(False)
        control_layout.addWidget(self.stop_replace_btn)
        control_layout.addStretch()
        progress_layout.addLayout(control_layout)
        
        layout.addWidget(progress_group)
        
        # 主要操作按钮行 - 紧凑布局
        main_control_layout = QHBoxLayout()
        main_control_layout.setSpacing(2)  # 减小间距
        self.save_config_btn = QPushButton("保存配置")
        self.create_iso_btn = QPushButton("创建ISO")
        self.start_replace_btn = QPushButton("开始版本替换")
        
        # 设置按钮高度
        self.save_config_btn.setMaximumHeight(28)
        self.create_iso_btn.setMaximumHeight(28)
        self.start_replace_btn.setMaximumHeight(28)
        self.stop_replace_btn.setMaximumHeight(28)
        
        self.save_config_btn.clicked.connect(self.save_config_to_json_file)
        self.create_iso_btn.clicked.connect(self.create_iso_from_output)
        self.start_replace_btn.clicked.connect(self.start_enhanced_version_replace)
        
        # 应用按钮样式
        from ui.button_styler import apply_3d_button_style, apply_3d_button_style_alternate
        apply_3d_button_style(self.save_config_btn)
        apply_3d_button_style(self.create_iso_btn)
        apply_3d_button_style_alternate(self.start_replace_btn)  # 绿色样式
        apply_3d_button_style_red(self.stop_replace_btn)  # 红色样式
        
        # 四个按钮平分占满一行
        main_control_layout.addWidget(self.save_config_btn)
        main_control_layout.addWidget(self.create_iso_btn)
        main_control_layout.addWidget(self.start_replace_btn)
        main_control_layout.addWidget(self.stop_replace_btn)
        
        layout.addLayout(main_control_layout)
        
        # 执行日志 - 占满剩余高度，使用与系统日志一致的标签
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(3, 3, 3, 3)  # 减小边距
        log_layout.setSpacing(2)  # 减小间距
        
        self.execution_log_text = QTextEdit()
        self.execution_log_text.setReadOnly(True)
        # 与系统日志完全一致的字体设置
        from PyQt5.QtGui import QFont
        self.execution_log_text.setFont(QFont("Consolas", 9))
        # 移除自定义样式，使用与系统日志一致的默认样式
        # 设置日志文本框为可扩展，占满剩余空间
        self.execution_log_text.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        log_layout.addWidget(self.execution_log_text)
        
        # 日志控制和操作按钮行 - 紧凑布局
        log_control_layout = QHBoxLayout()
        log_control_layout.setSpacing(2)  # 减小间距
        self.clear_log_btn = QPushButton("清空")
        self.save_log_btn = QPushButton("保存")
        self.quick_analysis_btn = QPushButton("快速分析")
        self.analyze_wim_btn = QPushButton("WIM分析")
        self.analyze_mount_btn = QPushButton("挂载分析")
        self.export_wim_report_btn = QPushButton("WIM报告")
        self.export_mount_report_btn = QPushButton("挂载报告")
        self.detailed_report_btn = QPushButton("详细报告")
        self.auto_scroll_cb = QCheckBox("自动滚动")
        self.auto_scroll_cb.setChecked(True)  # 默认选中
        
        # 设置按钮高度
        for btn in [self.clear_log_btn, self.save_log_btn, self.quick_analysis_btn,
                   self.analyze_wim_btn, self.analyze_mount_btn, self.export_wim_report_btn,
                   self.export_mount_report_btn, self.detailed_report_btn]:
            btn.setMaximumHeight(24)
        
        # 连接信号
        self.clear_log_btn.clicked.connect(self.clear_log)
        self.save_log_btn.clicked.connect(self.save_log)
        self.quick_analysis_btn.clicked.connect(self.quick_analysis)
        self.analyze_wim_btn.clicked.connect(self.analyze_wim_differences)
        self.analyze_mount_btn.clicked.connect(self.analyze_mount_differences)
        self.export_wim_report_btn.clicked.connect(self.export_wim_report)
        self.export_mount_report_btn.clicked.connect(self.export_mount_report)
        self.detailed_report_btn.clicked.connect(lambda: self.show_enhanced_detailed_report({}))
        
        # 应用按钮样式
        apply_3d_button_style(self.clear_log_btn)
        apply_3d_button_style(self.save_log_btn)
        apply_3d_button_style(self.quick_analysis_btn)
        apply_3d_button_style(self.analyze_wim_btn)
        apply_3d_button_style(self.analyze_mount_btn)
        apply_3d_button_style(self.export_wim_report_btn)
        apply_3d_button_style(self.export_mount_report_btn)
        apply_3d_button_style(self.detailed_report_btn)
        
        # 清空日志到自动滚动占满一行，自动滚动放到最右边
        log_control_layout.addWidget(self.clear_log_btn)
        log_control_layout.addWidget(self.save_log_btn)
        log_control_layout.addWidget(self.quick_analysis_btn)
        log_control_layout.addWidget(self.analyze_wim_btn)
        log_control_layout.addWidget(self.analyze_mount_btn)
        log_control_layout.addWidget(self.export_wim_report_btn)
        log_control_layout.addWidget(self.export_mount_report_btn)
        log_control_layout.addWidget(self.detailed_report_btn)
        log_control_layout.addWidget(self.auto_scroll_cb)  # 自动滚动放到最右边
        
        log_layout.addLayout(log_control_layout)
        
        layout.addWidget(log_group)
        
        return execution_widget
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
        """从项目config目录加载版本替换配置文件"""
        try:
            config_file = Path("config/version_replace_config.json")

            if not config_file.exists():
                self.append_log("未找到版本替换配置文件，将使用默认配置", "info")
                return False

            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 从配置中提取路径
            source_dir = config_data.get("source_dir", "")
            target_dir = config_data.get("target_dir", "")
            output_dir = config_data.get("output_dir", "")
            
            # 应用到UI
            if source_dir:
                self.source_dir_edit.setText(source_dir)
            if target_dir:
                self.target_dir_edit.setText(target_dir)
            if output_dir:
                self.output_dir_edit.setText(output_dir)
            
            # 应用选项配置
            use_dism = config_data.get("use_dism")
            if use_dism is not None:
                self.use_dism_cb.setChecked(use_dism)
                
            deep_analysis = config_data.get("deep_analysis")
            if deep_analysis is not None:
                self.deep_analysis_cb.setChecked(deep_analysis)
                
            copy_external = config_data.get("copy_external")
            if copy_external is not None:
                self.copy_external_cb.setChecked(copy_external)
                
            verify_after_copy = config_data.get("verify_after_copy")
            if verify_after_copy is not None:
                self.verify_after_copy_cb.setChecked(verify_after_copy)

            self.append_log(f"配置已从JSON文件自动加载: {config_file}", "info")
            return True

        except FileNotFoundError:
            return False
        except json.JSONDecodeError as e:
            self.append_log(f"配置文件JSON格式错误: {str(e)}", "error")
            return False
        except Exception as e:
            self.append_log(f"加载配置文件失败: {str(e)}", "error")
            return False

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

    def save_config_to_json_file(self):
        """保存当前配置到JSON文件"""
        try:
            # 保存到项目根config目录
            config_file = Path("config/version_replace_config.json")
            
            # 确保配置目录存在
            config_file.parent.mkdir(exist_ok=True, parents=True)
            
            # 准备配置数据
            config_data = {
                "source_dir": self.source_dir_edit.text(),
                "target_dir": self.target_dir_edit.text(),
                "output_dir": self.output_dir_edit.text(),
                "use_dism": self.use_dism_cb.isChecked(),
                "deep_analysis": self.deep_analysis_cb.isChecked(),
                "copy_external": self.copy_external_cb.isChecked(),
                "verify_after_copy": self.verify_after_copy_cb.isChecked()
            }
            
            # 保存到JSON文件
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.append_log(f"配置已保存到: {config_file}", "success")
            return True
            
        except Exception as e:
            self.append_log(f"保存配置到JSON文件失败: {str(e)}", "error")
            return False

    def auto_save_config(self):
        """自动保存配置"""
        if self.config_manager.get("version_replace.auto_save_config", True):
            # 优先保存到JSON文件（多位置）
            json_saved = self.save_config_to_json_file()
            # 同时保存到系统配置作为备份
            system_saved = self.save_config_to_system()
            
            if json_saved or system_saved:
                self.append_log("配置已自动保存", "info")
            else:
                self.append_log("配置自动保存失败", "warning")

    def init_enhanced_version_replacer(self):
        """初始化增强版版本替换器"""
        try:
            # 导入必要的模块
            from core.adk_manager import ADKManager
            from core.unified_manager.wim_manager import UnifiedWIMManager

            # 初始化ADK管理器
            adk_manager = ADKManager()
            unified_wim_manager = UnifiedWIMManager(self.config_manager, adk_manager)

            self.enhanced_replacer = EnhancedVersionReplacer(
                config_manager=self.config_manager,
                adk_manager=adk_manager,
                unified_wim_manager=unified_wim_manager
            )
            self.append_log("增强版版本替换器初始化成功", "success")
        except Exception as e:
            self.append_log(f"增强版版本替换器初始化失败: {str(e)}", "error")
            import traceback
            traceback.print_exc()

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
            if not hasattr(self, 'wim_analysis_text'):
                self.wim_analysis_text = QTextEdit()
                self.wim_analysis_text.setReadOnly(True)
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

            if not hasattr(self, 'wim_analysis_text'):
                self.wim_analysis_text = QTextEdit()
                self.wim_analysis_text.setReadOnly(True)
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

            if not hasattr(self, 'mount_analysis_text'):
                self.mount_analysis_text = QTextEdit()
                self.mount_analysis_text.setReadOnly(True)
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
        if hasattr(self, 'progress_label'):
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
                if hasattr(self, 'quick_iso_btn'):
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
                from ui.main_window.usb_thread import ISOCreationThread
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
                if hasattr(self, 'stop_btn'):
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
            if hasattr(self, 'stop_btn'):
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
            if hasattr(self, 'stop_btn'):
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
            if hasattr(self, 'stop_btn'):
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
        if hasattr(self, 'start_btn'):
            self.start_btn.setEnabled(not self.is_processing)
        if hasattr(self, 'stop_btn'):
            self.stop_btn.setEnabled(self.is_processing)

        # 更新分析按钮
        if hasattr(self, 'validate_btn'):
            self.validate_btn.setEnabled(not self.is_processing)
        self.quick_analysis_btn.setEnabled(not self.is_processing)
        self.analyze_wim_btn.setEnabled(not self.is_processing)
        self.analyze_mount_btn.setEnabled(not self.is_processing)

    def append_log(self, message: str, level: str = "info"):
        """添加日志消息"""
        # 添加到文本控件
        if hasattr(self, 'execution_log_text'):
            cursor = self.execution_log_text.textCursor()
            cursor.movePosition(cursor.End)
            cursor.insertText(message + "\n")
            # 自动滚动到底部
            if hasattr(self, 'auto_scroll_cb') and self.auto_scroll_cb.isChecked():
                self.execution_log_text.ensureCursorVisible()
            # 限制日志行数
            if hasattr(self, 'limit_log_lines'):
                self.limit_log_lines()
        
        # 同时输出到控制台（可选）
        print(f"[{level.upper()}] {message}")

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
            from ui.main_window.usb_thread import ISOCreationThread
            self.iso_thread = ISOCreationThread(str(output_dir), iso_path, self)

            # 连接信号
            self.iso_thread.progress_updated.connect(self.on_progress_updated)
            self.iso_thread.log_updated.connect(self.append_log)
            self.iso_thread.command_updated.connect(self.on_command_updated)
            self.iso_thread.finished.connect(self.on_iso_finished)
            self.iso_thread.error_occurred.connect(self.on_iso_error)

            # 禁用按钮
            if hasattr(self, 'quick_iso_btn'):
                self.quick_iso_btn.setEnabled(False)
                self.quick_iso_btn.setText("🔄 正在制作...")
            if hasattr(self, 'quick_iso_analysis_btn'):
                self.quick_iso_analysis_btn.setEnabled(False)

            # 启动线程
            self.iso_thread.start()

        except Exception as e:
            self.append_log(f"一键制作ISO失败: {str(e)}", "error")
            QMessageBox.critical(self, "错误", f"一键制作ISO失败: {str(e)}")

    def on_iso_finished(self, result: dict):
        """ISO制作完成"""
        # 恢复按钮
        if hasattr(self, 'quick_iso_btn'):
            self.quick_iso_btn.setEnabled(True)
            self.quick_iso_btn.setText("🚀 一键制作ISO")
        if hasattr(self, 'quick_iso_analysis_btn'):
            self.quick_iso_analysis_btn.setEnabled(True)

        success = result.get('success', False)
        message = result.get('message', '')
        iso_path = result.get('iso_path', '')

        if success:
            self.append_log(f"ISO制作完成: {iso_path}", "success")

            # 设置进度条到100%
            self.progress_bar.setValue(100)
            if hasattr(self, 'progress_label'):
                self.progress_label.setText("ISO制作完成")

            QMessageBox.information(self, "完成", f"ISO制作成功！\n文件位置: {iso_path}")
        else:
            self.append_log(f"ISO制作失败: {message}", "error")
            QMessageBox.warning(self, "失败", f"ISO制作失败！\n{message}")

    def on_iso_error(self, error_message: str):
        """ISO制作错误"""
        # 恢复按钮
        if hasattr(self, 'quick_iso_btn'):
            self.quick_iso_btn.setEnabled(True)
            self.quick_iso_btn.setText("🚀 一键制作ISO")
        if hasattr(self, 'quick_iso_analysis_btn'):
            self.quick_iso_analysis_btn.setEnabled(True)

        self.append_log(f"ISO制作错误: {error_message}", "error")
        QMessageBox.critical(self, "错误", f"ISO制作过程中发生错误:\n{error_message}")

    def on_command_updated(self, command: str, output: str):
        """处理命令输出更新"""
        # 这里可以添加命令输出的处理逻辑
        pass

    def create_unified_layout(self):
        """创建紧凑版整版布局"""
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(2, 2, 2, 2)  # 减小边距
        self.main_layout.setSpacing(2)  # 减小间距
        
        # 创建垂直分隔器 - 现在只有配置和执行两个区域
        splitter = QSplitter(Qt.Vertical)
        
        # 添加配置区域（紧凑）
        config_widget = self.create_config_section()
        config_widget.setMaximumHeight(120)  # 限制配置区域最大高度
        splitter.addWidget(config_widget)
        
        # 添加执行区域（包含日志和所有按钮）
        execution_widget = self.create_execution_section()
        splitter.addWidget(execution_widget)
        
        # 设置分隔器比例，配置区域很小，执行区域占满剩余空间
        splitter.setSizes([120, 600])  # 配置区域120px，执行区域600px
        splitter.setStretchFactor(0, 0)  # 配置区域不可拉伸
        splitter.setStretchFactor(1, 1)  # 执行区域可拉伸，占满剩余空间
        
        self.main_layout.addWidget(splitter)
        
        return self.main_layout

    def load_config_from_system(self):
        """从系统配置加载配置"""
        try:
            # 从配置管理器加载路径
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
            
            # 加载DISM选项
            dism_options = self.config_manager.get("version_replace.dism_options", {})
            if dism_options:
                self.use_dism_cb.setChecked(dism_options.get("use_dism", False))
                self.deep_analysis_cb.setChecked(dism_options.get("deep_analysis", False))
                self.copy_external_cb.setChecked(dism_options.get("copy_external", False))
                self.verify_after_copy_cb.setChecked(dism_options.get("verify_after_copy", False))
            
            self.append_log("配置已从系统自动加载", "info")
            return True
            
        except Exception as e:
            self.append_log(f"从系统加载配置失败: {str(e)}", "error")
            return False

    def limit_log_lines(self):
        """限制日志行数"""
        try:
            if hasattr(self, 'execution_log_text'):
                document = self.execution_log_text.document()
                max_lines = 1000  # 最大行数
                
                if document.blockCount() > max_lines:
                    cursor = self.execution_log_text.textCursor()
                    cursor.movePosition(cursor.Start)
                    cursor.movePosition(cursor.Down, cursor.KeepAnchor, document.blockCount() - max_lines)
                    cursor.removeSelectedText()
        except Exception as e:
            self.append_log(f"限制日志行数失败: {str(e)}", "error")

    def clear_log(self):
        """清空日志"""
        if hasattr(self, 'execution_log_text'):
            self.execution_log_text.clear()
        self.append_log("日志已清空", "info")

    def save_log(self):
        """保存日志"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存日志文件",
                str(Path.cwd() / f"version_replace_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"),
                "文本文件 (*.txt);;所有文件 (*)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.execution_log_text.toPlainText())
                self.append_log(f"日志已保存到: {file_path}", "info")
        except Exception as e:
            self.append_log(f"保存日志失败: {str(e)}", "error")

    def show_enhanced_detailed_report(self, result: dict):
        """显示增强版详细报告"""
        try:
            # 创建详细报告对话框
            from ui.main_window.detailed_report_dialog import DetailedReportDialog
            dialog = DetailedReportDialog(self, result, "增强版版本替换详细报告")
            dialog.exec_()
        except Exception as e:
            self.append_log(f"显示详细报告失败: {str(e)}", "error")
            QMessageBox.critical(self, "错误", f"显示详细报告失败: {str(e)}")
