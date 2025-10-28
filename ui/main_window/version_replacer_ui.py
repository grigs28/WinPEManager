#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinPE版本替换UI界面
提供完整的WinPE版本替换功能界面
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTextEdit, QProgressBar, QComboBox, QLineEdit,
    QCheckBox, QFileDialog, QMessageBox, QSplitter, QFrame,
    QListWidget, QListWidgetItem, QTabWidget, QGridLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor

from ui.button_styler import apply_3d_button_style, apply_3d_button_style_alternate, apply_3d_button_style_red
from utils.logger import log_error, get_logger
from core.version_replacer import VersionReplacer


class ComponentAnalysisThread(QThread):
    """组件分析线程"""

    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, version_replacer: VersionReplacer, mount_path: Path, output_file: Path):
        super().__init__()
        self.version_replacer = version_replacer
        self.mount_path = mount_path
        self.output_file = output_file
        self._is_running = True

    def run(self):
        """执行组件分析"""
        try:
            self.progress_signal.emit(10)
            self.log_signal.emit("开始分析组件...")

            self.progress_signal.emit(30)
            analysis = self.version_replacer.analyze_components(self.mount_path, self.output_file)

            self.progress_signal.emit(90)
            self.log_signal.emit("组件分析完成")

            self.progress_signal.emit(100)
            self.finished_signal.emit(analysis)

        except Exception as e:
            self.error_signal.emit(f"组件分析失败: {str(e)}")

    def stop(self):
        """停止分析"""
        self._is_running = False


class VersionReplacementThread(QThread):
    """版本替换线程"""

    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, version_replacer: VersionReplacer, config: Dict):
        super().__init__()
        self.version_replacer = version_replacer
        self.config = config
        self._is_running = True

    def run(self):
        """执行版本替换"""
        try:
            self.progress_signal.emit(5)
            self.log_signal.emit("开始WinPE版本替换...")

            source_mount = Path(self.config["source_mount"])
            target_mount = Path(self.config["target_mount"])
            output_dir = Path(self.config["output_dir"])

            self.progress_signal.emit(15)
            self.log_signal.emit(f"源挂载路径: {source_mount}")
            self.log_signal.emit(f"目标挂载路径: {target_mount}")
            self.log_signal.emit(f"输出目录: {output_dir}")

            self.progress_signal.emit(25)
            result = self.version_replacer.execute_version_replacement(
                source_mount, target_mount, output_dir, self.config.get("migration_config", {})
            )

            self.progress_signal.emit(95)
            if result["success"]:
                self.log_signal.emit("版本替换完成")
            else:
                self.log_signal.emit("版本替换失败")

            self.progress_signal.emit(100)
            self.finished_signal.emit(result)

        except Exception as e:
            self.error_signal.emit(f"版本替换失败: {str(e)}")

    def stop(self):
        """停止替换"""
        self._is_running = False


class VersionReplacerUI(QWidget):
    """WinPE版本替换界面"""

    def __init__(self, parent, config_manager, adk_manager):
        super().__init__()
        self.parent = parent
        self.config_manager = config_manager
        self.adk_manager = adk_manager

        # 初始化版本替换器
        self.version_replacer = VersionReplacer(config_manager, adk_manager)
        self.logger = get_logger("VersionReplacerUI")

        # 线程管理
        self.analysis_thread = None
        self.replacement_thread = None

        # 路径配置
        self.source_mount_path = Path("D:/APP/WinPEManager/WinPE_amd64/0WIN11PE/mount")
        self.target_mount_path = Path("D:/APP/WinPEManager/WinPE_amd64/0WIN10OLD/mount")
        self.output_dir_path = Path("D:/APP/WinPEManager/WinPE_amd64/WIN10REPLACED_REPLACED")
        self.docs_dir_path = Path("D:/APP/WinPEManager/docs")

        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        """设置UI界面"""
        # 主布局
        main_layout = QVBoxLayout()

        # 标题
        title_label = QLabel("WinPE版本替换工具")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        main_layout.addWidget(title_label)

        # 创建选项卡
        tab_widget = QTabWidget()

        # 配置选项卡
        config_tab = self.create_config_tab()
        tab_widget.addTab(config_tab, "配置")

        # 分析选项卡
        analysis_tab = self.create_analysis_tab()
        tab_widget.addTab(analysis_tab, "组件分析")

        # 替换选项卡
        replacement_tab = self.create_replacement_tab()
        tab_widget.addTab(replacement_tab, "版本替换")

        main_layout.addWidget(tab_widget)

        self.setLayout(main_layout)

    def create_config_tab(self) -> QWidget:
        """创建配置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()

        # 路径配置组
        path_group = QGroupBox("路径配置")
        path_layout = QGridLayout()

        # 源WIM挂载路径
        path_layout.addWidget(QLabel("源WIM挂载路径:"), 0, 0)
        self.source_mount_edit = QLineEdit(str(self.source_mount_path))
        self.source_mount_edit.setMinimumHeight(30)
        path_layout.addWidget(self.source_mount_edit, 0, 1)

        source_browse_btn = QPushButton("浏览")
        source_browse_btn.setMinimumHeight(30)
        source_browse_btn.clicked.connect(self.browse_source_mount)
        apply_3d_button_style_alternate(source_browse_btn)
        path_layout.addWidget(source_browse_btn, 0, 2)

        # 目标WIM挂载路径
        path_layout.addWidget(QLabel("目标WIM挂载路径:"), 1, 0)
        self.target_mount_edit = QLineEdit(str(self.target_mount_path))
        self.target_mount_edit.setMinimumHeight(30)
        path_layout.addWidget(self.target_mount_edit, 1, 1)

        target_browse_btn = QPushButton("浏览")
        target_browse_btn.setMinimumHeight(30)
        target_browse_btn.clicked.connect(self.browse_target_mount)
        apply_3d_button_style_alternate(target_browse_btn)
        path_layout.addWidget(target_browse_btn, 1, 2)

        # 输出目录
        path_layout.addWidget(QLabel("输出目录:"), 2, 0)
        self.output_dir_edit = QLineEdit(str(self.output_dir_path))
        self.output_dir_edit.setMinimumHeight(30)
        path_layout.addWidget(self.output_dir_edit, 2, 1)

        output_browse_btn = QPushButton("浏览")
        output_browse_btn.setMinimumHeight(30)
        output_browse_btn.clicked.connect(self.browse_output_dir)
        apply_3d_button_style_alternate(output_browse_btn)
        path_layout.addWidget(output_browse_btn, 2, 2)

        # 文档输出目录
        path_layout.addWidget(QLabel("文档输出目录:"), 3, 0)
        self.docs_dir_edit = QLineEdit(str(self.docs_dir_path))
        self.docs_dir_edit.setMinimumHeight(30)
        path_layout.addWidget(self.docs_dir_edit, 3, 1)

        docs_browse_btn = QPushButton("浏览")
        docs_browse_btn.setMinimumHeight(30)
        docs_browse_btn.clicked.connect(self.browse_docs_dir)
        apply_3d_button_style_alternate(docs_browse_btn)
        path_layout.addWidget(docs_browse_btn, 3, 2)

        path_group.setLayout(path_layout)
        layout.addWidget(path_group)

        # 迁移配置组
        migration_group = QGroupBox("迁移配置")
        migration_layout = QVBoxLayout()

        self.migrate_drivers_cb = QCheckBox("迁移驱动程序")
        self.migrate_drivers_cb.setChecked(True)
        migration_layout.addWidget(self.migrate_drivers_cb)

        self.migrate_desktop_cb = QCheckBox("迁移桌面环境")
        self.migrate_desktop_cb.setChecked(True)
        migration_layout.addWidget(self.migrate_desktop_cb)

        self.migrate_scripts_cb = QCheckBox("迁移启动脚本")
        self.migrate_scripts_cb.setChecked(True)
        migration_layout.addWidget(self.migrate_scripts_cb)

        self.migrate_programs_cb = QCheckBox("迁移自定义程序")
        self.migrate_programs_cb.setChecked(True)
        migration_layout.addWidget(self.migrate_programs_cb)

        self.migrate_config_cb = QCheckBox("迁移配置文件")
        self.migrate_config_cb.setChecked(True)
        migration_layout.addWidget(self.migrate_config_cb)

        migration_group.setLayout(migration_layout)
        layout.addWidget(migration_group)

        # 按钮组
        button_layout = QHBoxLayout()

        save_config_btn = QPushButton("保存配置")
        save_config_btn.setMinimumHeight(40)
        save_config_btn.clicked.connect(self.save_config)
        apply_3d_button_style(save_config_btn)
        button_layout.addWidget(save_config_btn)

        load_config_btn = QPushButton("加载配置")
        load_config_btn.setMinimumHeight(40)
        load_config_btn.clicked.connect(self.load_config)
        apply_3d_button_style_alternate(load_config_btn)
        button_layout.addWidget(load_config_btn)

        reset_config_btn = QPushButton("重置配置")
        reset_config_btn.setMinimumHeight(40)
        reset_config_btn.clicked.connect(self.reset_config)
        apply_3d_button_style_red(reset_config_btn)
        button_layout.addWidget(reset_config_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        tab.setLayout(layout)
        return tab

    def create_analysis_tab(self) -> QWidget:
        """创建组件分析选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()

        # 分析控制组
        control_group = QGroupBox("分析控制")
        control_layout = QHBoxLayout()

        # 源分析
        source_layout = QVBoxLayout()
        source_layout.addWidget(QLabel("源WIM组件分析"))

        analyze_source_btn = QPushButton("分析源WIM")
        analyze_source_btn.setMinimumHeight(40)
        analyze_source_btn.clicked.connect(self.analyze_source_components)
        apply_3d_button_style(analyze_source_btn)
        source_layout.addWidget(analyze_source_btn)

        self.source_progress = QProgressBar()
        self.source_progress.setVisible(False)
        source_layout.addWidget(self.source_progress)

        control_layout.addLayout(source_layout)

        # 目标分析
        target_layout = QVBoxLayout()
        target_layout.addWidget(QLabel("目标WIM组件分析"))

        analyze_target_btn = QPushButton("分析目标WIM")
        analyze_target_btn.setMinimumHeight(40)
        analyze_target_btn.clicked.connect(self.analyze_target_components)
        apply_3d_button_style(analyze_target_btn)
        target_layout.addWidget(analyze_target_btn)

        self.target_progress = QProgressBar()
        self.target_progress.setVisible(False)
        target_layout.addWidget(self.target_progress)

        control_layout.addLayout(target_layout)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # 分析结果显示
        result_splitter = QSplitter(Qt.Horizontal)

        # 源分析结果
        source_group = QGroupBox("源WIM分析结果")
        source_layout = QVBoxLayout()

        self.source_result_text = QTextEdit()
        self.source_result_text.setFont(QFont("Consolas", 9))
        self.source_result_text.setReadOnly(True)
        source_layout.addWidget(self.source_result_text)

        source_group.setLayout(source_layout)
        result_splitter.addWidget(source_group)

        # 目标分析结果
        target_group = QGroupBox("目标WIM分析结果")
        target_layout = QVBoxLayout()

        self.target_result_text = QTextEdit()
        self.target_result_text.setFont(QFont("Consolas", 9))
        self.target_result_text.setReadOnly(True)
        target_layout.addWidget(self.target_result_text)

        target_group.setLayout(target_layout)
        result_splitter.addWidget(target_group)

        result_splitter.setSizes([1, 1])
        layout.addWidget(result_splitter)

        # 操作按钮
        button_layout = QHBoxLayout()

        open_reports_btn = QPushButton("打开分析报告")
        open_reports_btn.setMinimumHeight(40)
        open_reports_btn.clicked.connect(self.open_analysis_reports)
        apply_3d_button_style_alternate(open_reports_btn)
        button_layout.addWidget(open_reports_btn)

        clear_results_btn = QPushButton("清空结果")
        clear_results_btn.setMinimumHeight(40)
        clear_results_btn.clicked.connect(self.clear_analysis_results)
        apply_3d_button_style_red(clear_results_btn)
        button_layout.addWidget(clear_results_btn)

        layout.addLayout(button_layout)

        tab.setLayout(layout)
        return tab

    def create_replacement_tab(self) -> QWidget:
        """创建版本替换选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()

        # 替换控制组
        control_group = QGroupBox("版本替换控制")
        control_layout = QVBoxLayout()

        # 版本信息显示
        info_layout = QHBoxLayout()

        source_info_layout = QVBoxLayout()
        source_info_layout.addWidget(QLabel("源WIM信息"))
        self.source_info_label = QLabel("未分析")
        self.source_info_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc; }")
        source_info_layout.addWidget(self.source_info_label)
        info_layout.addLayout(source_info_layout)

        target_info_layout = QVBoxLayout()
        target_info_layout.addWidget(QLabel("目标WIM信息"))
        self.target_info_label = QLabel("未分析")
        self.target_info_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc; }")
        target_info_layout.addWidget(self.target_info_label)
        info_layout.addLayout(target_info_layout)

        control_layout.addLayout(info_layout)

        # 替换按钮
        replace_btn = QPushButton("开始版本替换")
        replace_btn.setMinimumHeight(50)
        replace_btn.clicked.connect(self.start_version_replacement)
        apply_3d_button_style(replace_btn)
        control_layout.addWidget(replace_btn)

        # 进度条
        self.replacement_progress = QProgressBar()
        self.replacement_progress.setVisible(False)
        control_layout.addWidget(self.replacement_progress)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # 日志显示
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # 结果显示
        result_group = QGroupBox("替换结果")
        result_layout = QVBoxLayout()

        self.result_text = QTextEdit()
        self.result_text.setFont(QFont("Consolas", 9))
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        # 操作按钮
        button_layout = QHBoxLayout()

        open_output_btn = QPushButton("打开输出目录")
        open_output_btn.setMinimumHeight(40)
        open_output_btn.clicked.connect(self.open_output_directory)
        apply_3d_button_style_alternate(open_output_btn)
        button_layout.addWidget(open_output_btn)

        create_iso_btn = QPushButton("创建ISO")
        create_iso_btn.setMinimumHeight(40)
        create_iso_btn.clicked.connect(self.create_iso)
        apply_3d_button_style(create_iso_btn)
        button_layout.addWidget(create_iso_btn)

        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.setMinimumHeight(40)
        clear_log_btn.clicked.connect(self.clear_log)
        apply_3d_button_style_red(clear_log_btn)
        button_layout.addWidget(clear_log_btn)

        layout.addLayout(button_layout)

        tab.setLayout(layout)
        return tab

    def browse_source_mount(self):
        """浏览源WIM挂载路径"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择源WIM挂载路径")
        if dir_path:
            self.source_mount_edit.setText(dir_path)

    def browse_target_mount(self):
        """浏览目标WIM挂载路径"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择目标WIM挂载路径")
        if dir_path:
            self.target_mount_edit.setText(dir_path)

    def browse_output_dir(self):
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.output_dir_edit.setText(dir_path)

    def browse_docs_dir(self):
        """浏览文档输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择文档输出目录")
        if dir_path:
            self.docs_dir_edit.setText(dir_path)

    def save_config(self):
        """保存配置"""
        try:
            config = {
                "source_mount": self.source_mount_edit.text(),
                "target_mount": self.target_mount_edit.text(),
                "output_dir": self.output_dir_edit.text(),
                "docs_dir": self.docs_dir_edit.text(),
                "migration_config": {
                    "migrate_drivers": self.migrate_drivers_cb.isChecked(),
                    "migrate_desktop": self.migrate_desktop_cb.isChecked(),
                    "migrate_scripts": self.migrate_scripts_cb.isChecked(),
                    "migrate_programs": self.migrate_programs_cb.isChecked(),
                    "migrate_config": self.migrate_config_cb.isChecked()
                }
            }

            import json
            config_file = Path("version_replacer_config.json")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            QMessageBox.information(self, "成功", "配置已保存")
            self.add_log("配置已保存")

        except Exception as e:
            log_error(e, "保存版本替换配置")
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")

    def load_config(self):
        """加载配置"""
        try:
            config_file = Path("version_replacer_config.json")
            if config_file.exists():
                import json
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                self.source_mount_edit.setText(config.get("source_mount", ""))
                self.target_mount_edit.setText(config.get("target_mount", ""))
                self.output_dir_edit.setText(config.get("output_dir", ""))
                self.docs_dir_edit.setText(config.get("docs_dir", ""))

                migration_config = config.get("migration_config", {})
                self.migrate_drivers_cb.setChecked(migration_config.get("migrate_drivers", True))
                self.migrate_desktop_cb.setChecked(migration_config.get("migrate_desktop", True))
                self.migrate_scripts_cb.setChecked(migration_config.get("migrate_scripts", True))
                self.migrate_programs_cb.setChecked(migration_config.get("migrate_programs", True))
                self.migrate_config_cb.setChecked(migration_config.get("migrate_config", True))

                self.add_log("配置已加载")
                QMessageBox.information(self, "成功", "配置已加载")

        except Exception as e:
            log_error(e, "加载版本替换配置")
            QMessageBox.critical(self, "错误", f"加载配置失败: {str(e)}")

    def reset_config(self):
        """重置配置"""
        reply = QMessageBox.question(self, "确认重置", "确定要重置所有配置吗？",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.source_mount_edit.setText(str(self.source_mount_path))
            self.target_mount_edit.setText(str(self.target_mount_path))
            self.output_dir_edit.setText(str(self.output_dir_path))
            self.docs_dir_edit.setText(str(self.docs_dir_path))

            self.migrate_drivers_cb.setChecked(True)
            self.migrate_desktop_cb.setChecked(True)
            self.migrate_scripts_cb.setChecked(True)
            self.migrate_programs_cb.setChecked(True)
            self.migrate_config_cb.setChecked(True)

            self.add_log("配置已重置")

    def analyze_source_components(self):
        """分析源WIM组件"""
        try:
            mount_path = Path(self.source_mount_edit.text())
            if not mount_path.exists():
                QMessageBox.warning(self, "警告", "源WIM挂载路径不存在")
                return

            output_file = self.docs_dir_path / "source_component_analysis.md"
            self.source_progress.setVisible(True)
            self.source_progress.setValue(0)

            self.analysis_thread = ComponentAnalysisThread(
                self.version_replacer, mount_path, output_file
            )
            self.analysis_thread.progress_signal.connect(self.source_progress.setValue)
            self.analysis_thread.log_signal.connect(self.add_log)
            self.analysis_thread.finished_signal.connect(self.on_source_analysis_finished)
            self.analysis_thread.error_signal.connect(self.on_analysis_error)
            self.analysis_thread.start()

        except Exception as e:
            log_error(e, "分析源WIM组件")
            QMessageBox.critical(self, "错误", f"分析失败: {str(e)}")

    def analyze_target_components(self):
        """分析目标WIM组件"""
        try:
            mount_path = Path(self.target_mount_edit.text())
            if not mount_path.exists():
                QMessageBox.warning(self, "警告", "目标WIM挂载路径不存在")
                return

            output_file = self.docs_dir_path / "target_component_analysis.md"
            self.target_progress.setVisible(True)
            self.target_progress.setValue(0)

            self.analysis_thread = ComponentAnalysisThread(
                self.version_replacer, mount_path, output_file
            )
            self.analysis_thread.progress_signal.connect(self.target_progress.setValue)
            self.analysis_thread.log_signal.connect(self.add_log)
            self.analysis_thread.finished_signal.connect(self.on_target_analysis_finished)
            self.analysis_thread.error_signal.connect(self.on_analysis_error)
            self.analysis_thread.start()

        except Exception as e:
            log_error(e, "分析目标WIM组件")
            QMessageBox.critical(self, "错误", f"分析失败: {str(e)}")

    def on_source_analysis_finished(self, analysis: Dict):
        """源分析完成"""
        self.source_progress.setVisible(False)
        self.source_result_text.clear()
        self.source_result_text.append(self.format_analysis_result(analysis, "源WIM"))

        # 更新版本信息
        version_info = f"文件名: {analysis['basic_info'].get('total_size', 0)} bytes"
        self.source_info_label.setText(version_info)

        self.add_log("源WIM组件分析完成")

    def on_target_analysis_finished(self, analysis: Dict):
        """目标分析完成"""
        self.target_progress.setVisible(False)
        self.target_result_text.clear()
        self.target_result_text.append(self.format_analysis_result(analysis, "目标WIM"))

        # 更新版本信息
        version_info = f"文件名: {analysis['basic_info'].get('total_size', 0)} bytes"
        self.target_info_label.setText(version_info)

        self.add_log("目标WIM组件分析完成")

    def on_analysis_error(self, error_msg: str):
        """分析错误"""
        self.source_progress.setVisible(False)
        self.target_progress.setVisible(False)
        self.add_log(f"分析错误: {error_msg}")
        QMessageBox.critical(self, "错误", error_msg)

    def format_analysis_result(self, analysis: Dict, title: str) -> str:
        """格式化分析结果"""
        result = []
        result.append(f"=== {title}组件分析结果 ===")
        result.append(f"分析时间: {analysis['analysis_time']}")
        result.append("")

        # 基本信息
        basic = analysis['basic_info']
        result.append("【基本信息】")
        result.append(f"Windows目录: {'存在' if basic['windows_dir_exists'] else '不存在'}")
        result.append(f"System32目录: {'存在' if basic['system32_dir_exists'] else '不存在'}")
        result.append(f"总大小: {self.format_size(basic['total_size'])}")
        result.append(f"文件数量: {basic['file_count']:,}")
        result.append("")

        # 核心文件
        result.append("【核心文件】")
        core_files = analysis['core_files']
        for file_name, file_info in core_files.items():
            status = "✓" if file_info['exists'] else "✗"
            result.append(f"{status} {file_name}")
        result.append("")

        # 自定义组件
        result.append("【自定义组件】")
        custom = analysis['custom_components']
        for comp_name, comp_info in custom.items():
            status = "✓" if comp_info['exists'] else "✗"
            file_count = len(comp_info['files']) if comp_info['files'] else 0
            result.append(f"{status} {comp_name} ({file_count} 个文件)")
        result.append("")

        # 驱动程序
        result.append("【驱动程序】")
        drivers = analysis['drivers']
        result.append(f"驱动目录: {'存在' if drivers['drivers_dir_exists'] else '不存在'}")
        result.append(f"驱动总数: {drivers['total_drivers']}")
        if drivers['driver_categories']:
            for category, files in drivers['driver_categories'].items():
                result.append(f"  {category}: {len(files)} 个")
        result.append("")

        # 桌面环境
        result.append("【桌面环境】")
        desktop = analysis['desktop_environment']
        result.append(f"Shell类型: {desktop['shell_type']}")
        result.append("")

        # 完整性检查
        result.append("【完整性检查】")
        integrity = analysis['integrity_check']
        result.append(f"整体状态: {integrity['overall_status']}")
        result.append("")

        return "\n".join(result)

    def format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def clear_analysis_results(self):
        """清空分析结果"""
        self.source_result_text.clear()
        self.target_result_text.clear()
        self.source_info_label.setText("未分析")
        self.target_info_label.setText("未分析")
        self.add_log("分析结果已清空")

    def open_analysis_reports(self):
        """打开分析报告"""
        try:
            docs_dir = Path(self.docs_dir_edit.text())
            if docs_dir.exists():
                import subprocess
                import platform

                if platform.system() == "Windows":
                    subprocess.run(['explorer', str(docs_dir)])
                elif platform.system() == "Darwin":
                    subprocess.run(['open', str(docs_dir)])
                else:
                    subprocess.run(['xdg-open', str(docs_dir)])

                self.add_log(f"已打开分析报告目录: {docs_dir}")
            else:
                QMessageBox.warning(self, "警告", "分析报告目录不存在")

        except Exception as e:
            log_error(e, "打开分析报告")
            QMessageBox.critical(self, "错误", f"打开报告失败: {str(e)}")

    def start_version_replacement(self):
        """开始版本替换"""
        try:
            # 验证路径
            source_mount = Path(self.source_mount_edit.text())
            target_mount = Path(self.target_mount_edit.text())
            output_dir = Path(self.output_dir_edit.text())

            if not source_mount.exists():
                QMessageBox.warning(self, "警告", "源WIM挂载路径不存在")
                return

            if not target_mount.exists():
                QMessageBox.warning(self, "警告", "目标WIM挂载路径不存在")
                return

            # 确认操作
            reply = QMessageBox.question(
                self, "确认版本替换",
                f"即将执行版本替换操作:\n\n"
                f"源WIM: {source_mount}\n"
                f"目标WIM: {target_mount}\n"
                f"输出目录: {output_dir}\n\n"
                f"⚠️ 此操作将创建新的WinPE环境！\n\n"
                f"确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 准备配置
            config = {
                "source_mount": str(source_mount),
                "target_mount": str(target_mount),
                "output_dir": str(output_dir),
                "migration_config": {
                    "migrate_drivers": self.migrate_drivers_cb.isChecked(),
                    "migrate_desktop": self.migrate_desktop_cb.isChecked(),
                    "migrate_scripts": self.migrate_scripts_cb.isChecked(),
                    "migrate_programs": self.migrate_programs_cb.isChecked(),
                    "migrate_config": self.migrate_config_cb.isChecked()
                }
            }

            # 开始替换
            self.replacement_progress.setVisible(True)
            self.replacement_progress.setValue(0)

            self.replacement_thread = VersionReplacementThread(self.version_replacer, config)
            self.replacement_thread.progress_signal.connect(self.replacement_progress.setValue)
            self.replacement_thread.log_signal.connect(self.add_log)
            self.replacement_thread.finished_signal.connect(self.on_replacement_finished)
            self.replacement_thread.error_signal.connect(self.on_replacement_error)
            self.replacement_thread.start()

        except Exception as e:
            log_error(e, "开始版本替换")
            QMessageBox.critical(self, "错误", f"启动替换失败: {str(e)}")

    def on_replacement_finished(self, result: Dict):
        """替换完成"""
        self.replacement_progress.setVisible(False)

        if result["success"]:
            # 显示结果
            result_text = []
            result_text.append("=== 版本替换成功 ===")
            result_text.append(f"完成步骤: {', '.join(result['steps'].keys())}")

            if result["migrated_components"]:
                result_text.append("\n【迁移组件】")
                for comp_type, comp_info in result["migrated_components"].items():
                    result_text.append(f"- {comp_type}: {comp_info}")

            if result["output_wim"]:
                result_text.append(f"\n【输出WIM】: {result['output_wim']}")

            self.result_text.clear()
            self.result_text.append("\n".join(result_text))

            QMessageBox.information(self, "成功", "WinPE版本替换完成！")
            self.add_log("WinPE版本替换完成")
        else:
            error_msg = "版本替换失败:\n" + "\n".join(result.get("errors", []))
            self.result_text.clear()
            self.result_text.append(error_msg)

            QMessageBox.critical(self, "失败", error_msg)
            self.add_log("版本替换失败")

    def on_replacement_error(self, error_msg: str):
        """替换错误"""
        self.replacement_progress.setVisible(False)
        self.add_log(f"替换错误: {error_msg}")
        QMessageBox.critical(self, "错误", error_msg)

    def open_output_directory(self):
        """打开输出目录"""
        try:
            output_dir = Path(self.output_dir_edit.text())
            if output_dir.exists():
                import subprocess
                import platform

                if platform.system() == "Windows":
                    subprocess.run(['explorer', str(output_dir)])
                elif platform.system() == "Darwin":
                    subprocess.run(['open', str(output_dir)])
                else:
                    subprocess.run(['xdg-open', str(output_dir)])

                self.add_log(f"已打开输出目录: {output_dir}")
            else:
                QMessageBox.warning(self, "警告", "输出目录不存在")

        except Exception as e:
            log_error(e, "打开输出目录")
            QMessageBox.critical(self, "错误", f"打开目录失败: {str(e)}")

    def create_iso(self):
        """创建ISO"""
        try:
            output_dir = Path(self.output_dir_edit.text())
            if not output_dir.exists():
                QMessageBox.warning(self, "警告", "输出目录不存在，请先执行版本替换")
                return

            # 查找生成的WIM文件
            wim_files = list(output_dir.glob("*.wim"))
            if not wim_files:
                QMessageBox.warning(self, "警告", "未找到生成的WIM文件")
                return

            # 选择WIM文件
            wim_file = wim_files[0]  # 使用第一个找到的WIM文件

            # 选择ISO输出路径
            iso_path, _ = QFileDialog.getSaveFileName(
                self, "选择ISO输出路径",
                str(output_dir / f"{output_dir.name}.iso"),
                "ISO文件 (*.iso)"
            )

            if not iso_path:
                return

            # 调用ISO创建功能
            self.add_log(f"开始创建ISO: {Path(iso_path).name}")

            # 这里可以调用现有的ISO创建功能
            # 例如: self.parent.create_iso_from_wim(wim_file, iso_path)

            QMessageBox.information(self, "提示", "ISO创建功能需要集成现有的ISO创建模块")
            self.add_log("ISO创建功能待实现")

        except Exception as e:
            log_error(e, "创建ISO")
            QMessageBox.critical(self, "错误", f"创建ISO失败: {str(e)}")

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.result_text.clear()
        self.add_log("日志已清空")

    def add_log(self, message: str):
        """添加日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        self.log_text.append(log_message)
        self.log_text.moveCursor(QTextCursor.End)
        self.log_text.ensureCursorVisible()

        # 同时添加到父窗口的日志
        if hasattr(self.parent, 'log_message'):
            self.parent.log_message(f"[版本替换] {message}")