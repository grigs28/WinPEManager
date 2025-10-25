#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口UI创建模块
提供主窗口各个标签页和UI组件的创建方法
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QSplitter, QCheckBox, QFormLayout,
    QListWidget, QAbstractItemView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from ui.components_tree_widget import ComponentsTreeWidget
from ui.button_styler import apply_3d_button_style, apply_3d_button_style_alternate, apply_3d_button_style_red


class UICreators:
    """UI创建器类，包含所有UI组件的创建方法"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.config_manager = main_window.config_manager
    
    def create_basic_config_tab(self):
        """创建基本配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # WinPE基本配置组
        basic_group = QGroupBox("WinPE 基本配置")
        basic_layout = QVBoxLayout(basic_group)

        # 架构和版本在同一行，各占50%
        arch_version_layout = QHBoxLayout()
        
        # 架构选择
        arch_version_layout.addWidget(QLabel("架构:"))
        self.main_window.arch_combo = QComboBox()
        self.main_window.arch_combo.addItems(["amd64", "x86", "arm64"])
        current_arch = self.config_manager.get("winpe.architecture", "amd64")
        index = self.main_window.arch_combo.findText(current_arch)
        if index >= 0:
            self.main_window.arch_combo.setCurrentIndex(index)
        arch_version_layout.addWidget(self.main_window.arch_combo)
        
        arch_version_layout.addWidget(QLabel("  版本:"))  # 添加间距
        # 版本选择
        self.main_window.version_combo = QComboBox()
        self.main_window.version_combo.addItems(["10", "11"])
        current_version = self.config_manager.get("winpe.version", "10")
        index = self.main_window.version_combo.findText(current_version)
        if index >= 0:
            self.main_window.version_combo.setCurrentIndex(index)
        arch_version_layout.addWidget(self.main_window.version_combo)
        
        # 设置各占50%宽度
        arch_version_layout.setStretch(1, 1)  # 架构下拉框
        arch_version_layout.setStretch(3, 1)  # 版本下拉框
        basic_layout.addLayout(arch_version_layout)

        # 语言和构建方式在同一行，各占50%
        lang_build_layout = QHBoxLayout()
        
        # 语言选择
        lang_build_layout.addWidget(QLabel("语言:"))
        self.main_window.language_combo = QComboBox()
        # 从WinPE包管理器获取可用语言
        from core.winpe_packages import WinPEPackages
        winpe_packages = WinPEPackages()
        available_languages = winpe_packages.get_available_languages()

        for lang in available_languages:
            self.main_window.language_combo.addItem(lang["name"], lang["code"])

        current_lang = self.config_manager.get("winpe.language", "zh-CN")
        for i in range(self.main_window.language_combo.count()):
            if self.main_window.language_combo.itemData(i) == current_lang:
                self.main_window.language_combo.setCurrentIndex(i)
                break

        # 连接语言变化信号
        self.main_window.language_combo.currentTextChanged.connect(self.main_window.on_language_changed)
        lang_build_layout.addWidget(self.main_window.language_combo)
        
        lang_build_layout.addWidget(QLabel("  方式:"))  # 添加间距
        # 构建设置
        self.main_window.build_method_combo = QComboBox()
        self.main_window.build_method_combo.addItems(["copype (推荐)", "传统DISM"])
        current_build_method = self.config_manager.get("winpe.build_method", "copype")
        method_map = {"copype": "copype (推荐)", "dism": "传统DISM"}
        method_text = method_map.get(current_build_method, "copype (推荐)")
        index = self.main_window.build_method_combo.findText(method_text)
        if index >= 0:
            self.main_window.build_method_combo.setCurrentIndex(index)
        lang_build_layout.addWidget(self.main_window.build_method_combo)
        
        # 设置各占50%宽度
        lang_build_layout.setStretch(1, 1)  # 语言下拉框
        lang_build_layout.setStretch(3, 1)  # 构建方式下拉框
        basic_layout.addLayout(lang_build_layout)

        # WinPE专用设置 - 启用Winpe专用配置、暂存控件、目标路径占满1行各33%
        settings_group = QGroupBox("WinPE 专用设置")
        settings_layout = QVBoxLayout(settings_group)

        # 三个控件在同一行，各占33%
        settings_row_layout = QHBoxLayout()
        
        # 启用WinPE设置
        self.main_window.enable_winpe_settings_check = QCheckBox("启用 WinPE 专用设置")
        self.main_window.enable_winpe_settings_check.setChecked(
            self.config_manager.get("winpe.enable_winpe_settings", True)
        )
        settings_row_layout.addWidget(self.main_window.enable_winpe_settings_check)

        # 暂存空间设置
        settings_row_layout.addWidget(QLabel("暂存空间:"))
        self.main_window.scratch_space_spin = QSpinBox()
        self.main_window.scratch_space_spin.setRange(32, 1024)
        self.main_window.scratch_space_spin.setValue(
            self.config_manager.get("winpe.scratch_space_mb", 128)
        )
        self.main_window.scratch_space_spin.setSuffix(" MB")
        settings_row_layout.addWidget(self.main_window.scratch_space_spin)

        # 目标路径设置
        settings_row_layout.addWidget(QLabel("目标路径:"))
        self.main_window.target_path_edit = QLineEdit()
        self.main_window.target_path_edit.setText(
            self.config_manager.get("winpe.target_path", "X:")
        )
        settings_row_layout.addWidget(self.main_window.target_path_edit)
        
        # 设置各占33%宽度
        settings_row_layout.setStretch(0, 1)  # 启用WinPE设置
        settings_row_layout.setStretch(2, 1)  # 暂存空间
        settings_row_layout.setStretch(4, 1)  # 目标路径
        
        settings_layout.addLayout(settings_row_layout)
        settings_group.setLayout(settings_layout)
        basic_layout.addWidget(settings_group)


        layout.addWidget(basic_group)

        # 输出配置组
        output_group = QGroupBox("输出配置")
        output_layout = QFormLayout(output_group)

        # 工作空间行 - 文本框和浏览按钮在同一行
        workspace_layout = QHBoxLayout()
        self.main_window.workspace_edit = QLineEdit()
        self.main_window.workspace_edit.setText(self.config_manager.get("output.workspace", ""))
        self.main_window.workspace_edit.setPlaceholderText("选择WinPE构建工作空间")
        workspace_layout.addWidget(self.main_window.workspace_edit)
        
        workspace_btn = QPushButton("浏览...")
        workspace_btn.clicked.connect(self.main_window.browse_workspace)
        apply_3d_button_style(workspace_btn)  # 应用蓝色立体样式
        workspace_btn.setMaximumWidth(80)  # 限制按钮宽度
        workspace_layout.addWidget(workspace_btn)
        
        output_layout.addRow("工作空间:", workspace_layout)

        # ISO路径行 - 文本框和浏览按钮在同一行
        iso_layout = QHBoxLayout()
        self.main_window.iso_path_edit = QLineEdit()
        self.main_window.iso_path_edit.setText(self.config_manager.get("output.iso_path", ""))
        self.main_window.iso_path_edit.setPlaceholderText("选择ISO输出路径")
        iso_layout.addWidget(self.main_window.iso_path_edit)
        
        iso_btn = QPushButton("浏览...")
        iso_btn.clicked.connect(self.main_window.browse_iso_path)
        apply_3d_button_style(iso_btn)  # 应用蓝色立体样式
        iso_btn.setMaximumWidth(80)  # 限制按钮宽度
        iso_layout.addWidget(iso_btn)
        
        output_layout.addRow("ISO 路径:", iso_layout)

        layout.addWidget(output_group)

        # ADK配置组
        config_group = QGroupBox("ADK 配置")
        config_layout = QFormLayout(config_group)

        # ADK路径行 - 文本框和浏览按钮在同一行
        adk_layout = QHBoxLayout()
        self.main_window.adk_path_edit = QLineEdit()
        self.main_window.adk_path_edit.setReadOnly(True)
        adk_layout.addWidget(self.main_window.adk_path_edit)
        
        adk_btn = QPushButton("浏览...")
        adk_btn.clicked.connect(self.main_window.browse_adk_path)
        apply_3d_button_style(adk_btn)  # 应用蓝色立体样式
        adk_btn.setMaximumWidth(80)  # 限制按钮宽度
        adk_layout.addWidget(adk_btn)
        
        config_layout.addRow("ADK 路径:", adk_layout)

        # WinPE路径行 - 文本框和浏览按钮在同一行
        winpe_layout = QHBoxLayout()
        self.main_window.winpe_path_edit = QLineEdit()
        self.main_window.winpe_path_edit.setReadOnly(True)
        winpe_layout.addWidget(self.main_window.winpe_path_edit)
        
        winpe_btn = QPushButton("浏览...")
        winpe_btn.clicked.connect(self.main_window.browse_winpe_path)
        apply_3d_button_style(winpe_btn)  # 应用蓝色立体样式
        winpe_btn.setMaximumWidth(80)  # 限制按钮宽度
        winpe_layout.addWidget(winpe_btn)
        
        config_layout.addRow("WinPE 路径:", winpe_layout)

        layout.addWidget(config_group)

        # ADK状态组
        adk_group = QGroupBox("Windows ADK 状态")
        adk_layout = QVBoxLayout(adk_group)

        self.main_window.adk_status_label = QLabel("正在检查ADK状态...")
        adk_layout.addWidget(self.main_window.adk_status_label)

        self.main_window.adk_details_label = QLabel("")
        self.main_window.adk_details_label.setWordWrap(True)
        adk_layout.addWidget(self.main_window.adk_details_label)

        # ADK状态组 - 移除按钮，按钮将在底部统一处理
        layout.addWidget(adk_group)

        # 添加弹性空间，将按钮推到底部
        layout.addStretch()

        # 创建统一的按钮行布局 - 放在最底部
        unified_btn_layout = QHBoxLayout()

        # ADK状态按钮
        refresh_btn = QPushButton("刷新状态")
        refresh_btn.clicked.connect(self.main_window.check_adk_status)
        apply_3d_button_style(refresh_btn)  # 应用蓝色立体样式
        unified_btn_layout.addWidget(refresh_btn)

        test_dism_btn = QPushButton("测试DISM工具")
        test_dism_btn.clicked.connect(self.main_window.test_dism_tool)
        apply_3d_button_style(test_dism_btn)  # 应用蓝色立体样式
        unified_btn_layout.addWidget(test_dism_btn)

        # 关于和帮助按钮
        about_btn = QPushButton("关于程序")
        about_btn.clicked.connect(self.main_window.show_about_dialog)
        apply_3d_button_style(about_btn)  # 应用蓝色立体样式
        unified_btn_layout.addWidget(about_btn)

        changelog_btn = QPushButton("更新日志")
        changelog_btn.clicked.connect(self.main_window.show_changelog_dialog)
        apply_3d_button_style(changelog_btn)  # 应用蓝色立体样式
        unified_btn_layout.addWidget(changelog_btn)

        # 保存配置按钮
        save_btn = QPushButton("保存基本配置")
        save_btn.clicked.connect(self.main_window.save_basic_config)
        apply_3d_button_style_alternate(save_btn)  # 应用绿色立体样式
        unified_btn_layout.addWidget(save_btn)

        layout.addLayout(unified_btn_layout)

        layout.addStretch()
        self.main_window.tab_widget.addTab(widget, "基本配置")

        # 初始化ADK状态
        self.main_window.check_adk_status()

    def create_customization_tab(self):
        """创建定制选项标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # 左侧：驱动程序、自定义脚本、额外文件
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # 驱动程序
        drivers_group = QGroupBox("驱动程序")
        drivers_layout = QVBoxLayout(drivers_group)

        self.main_window.drivers_table = QTableWidget()
        self.main_window.drivers_table.setColumnCount(3)
        self.main_window.drivers_table.setHorizontalHeaderLabels(["路径", "描述", "操作"])
        self.main_window.drivers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.main_window.drivers_table.setAlternatingRowColors(True)
        drivers_layout.addWidget(self.main_window.drivers_table)

        drivers_btn_layout = QHBoxLayout()
        add_driver_btn = QPushButton("添加驱动")
        add_driver_btn.clicked.connect(self.main_window.add_driver)
        apply_3d_button_style(add_driver_btn)  # 应用蓝色立体样式
        remove_driver_btn = QPushButton("移除驱动")
        remove_driver_btn.clicked.connect(self.main_window.remove_driver)
        apply_3d_button_style_red(remove_driver_btn)  # 应用红色立体样式
        drivers_btn_layout.addWidget(add_driver_btn)
        drivers_btn_layout.addWidget(remove_driver_btn)
        drivers_layout.addLayout(drivers_btn_layout)

        left_layout.addWidget(drivers_group)

        # 自定义脚本
        scripts_group = QGroupBox("自定义脚本")
        scripts_layout = QVBoxLayout(scripts_group)

        self.main_window.scripts_table = QTableWidget()
        self.main_window.scripts_table.setColumnCount(3)
        self.main_window.scripts_table.setHorizontalHeaderLabels(["路径", "描述", "操作"])
        self.main_window.scripts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.main_window.scripts_table.setAlternatingRowColors(True)
        scripts_layout.addWidget(self.main_window.scripts_table)

        scripts_btn_layout = QHBoxLayout()
        add_script_btn = QPushButton("添加脚本")
        add_script_btn.clicked.connect(self.main_window.add_script)
        apply_3d_button_style(add_script_btn)  # 应用蓝色立体样式
        remove_script_btn = QPushButton("移除脚本")
        remove_script_btn.clicked.connect(self.main_window.remove_script)
        apply_3d_button_style_red(remove_script_btn)  # 应用红色立体样式
        scripts_btn_layout.addWidget(add_script_btn)
        scripts_btn_layout.addWidget(remove_script_btn)
        scripts_layout.addLayout(scripts_btn_layout)

        left_layout.addWidget(scripts_group)

        # 额外文件
        files_group = QGroupBox("额外文件")
        files_layout = QVBoxLayout(files_group)

        self.main_window.files_table = QTableWidget()
        self.main_window.files_table.setColumnCount(3)
        self.main_window.files_table.setHorizontalHeaderLabels(["路径", "描述", "操作"])
        self.main_window.files_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.main_window.files_table.setAlternatingRowColors(True)
        files_layout.addWidget(self.main_window.files_table)

        files_btn_layout = QHBoxLayout()
        add_file_btn = QPushButton("添加文件")
        add_file_btn.clicked.connect(self.main_window.add_file)
        apply_3d_button_style(add_file_btn)  # 应用蓝色立体样式
        remove_file_btn = QPushButton("移除文件")
        remove_file_btn.clicked.connect(self.main_window.remove_file)
        apply_3d_button_style_red(remove_file_btn)  # 应用红色立体样式
        files_btn_layout.addWidget(add_file_btn)
        files_btn_layout.addWidget(remove_file_btn)
        files_layout.addLayout(files_btn_layout)

        left_layout.addWidget(files_group)

        # 右侧：可选组件（占满）
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # 可选组件 - 占满右侧空间
        packages_group = QGroupBox("可选组件")
        packages_layout = QVBoxLayout(packages_group)

        # 组件操作按钮（放在顶部）
        packages_btn_layout = QHBoxLayout()

        # 搜索框
        from PyQt5.QtWidgets import QLineEdit as SearchLineEdit
        self.main_window.search_edit = SearchLineEdit()
        self.main_window.search_edit.setPlaceholderText("搜索组件...")
        self.main_window.search_edit.textChanged.connect(self.main_window.search_components)
        self.main_window.search_edit.setMaximumWidth(200)
        packages_btn_layout.addWidget(QLabel("搜索:"))
        packages_btn_layout.addWidget(self.main_window.search_edit)

        packages_btn_layout.addStretch()

        # 操作按钮
        refresh_packages_btn = QPushButton("刷新")
        refresh_packages_btn.clicked.connect(self.main_window.refresh_packages)
        refresh_packages_btn.setMaximumWidth(80)
        apply_3d_button_style(refresh_packages_btn)  # 应用蓝色立体样式
        packages_btn_layout.addWidget(refresh_packages_btn)

        select_recommended_btn = QPushButton("选择推荐")
        select_recommended_btn.clicked.connect(self.main_window.select_recommended_components)
        select_recommended_btn.setMaximumWidth(80)
        apply_3d_button_style_alternate(select_recommended_btn)  # 应用绿色立体样式
        packages_btn_layout.addWidget(select_recommended_btn)
        clear_selection_btn = QPushButton("清空选择")
        clear_selection_btn.clicked.connect(self.main_window.clear_component_selection)
        clear_selection_btn.setMaximumWidth(80)
        apply_3d_button_style_red(clear_selection_btn)  # 应用红色立体样式
        packages_btn_layout.addWidget(clear_selection_btn)

        packages_layout.addLayout(packages_btn_layout)

        # 创建树形控件（占满剩余空间）
        self.main_window.components_tree = ComponentsTreeWidget()
        # 连接选择变化信号
        self.main_window.components_tree.component_selection_changed.connect(self.main_window.on_tree_selection_changed)
        packages_layout.addWidget(self.main_window.components_tree)

        # 保存定制配置按钮
        save_btn = QPushButton("保存定制配置")
        save_btn.clicked.connect(self.main_window.save_customization_config)
        apply_3d_button_style_alternate(save_btn)  # 应用绿色立体样式
        packages_layout.addWidget(save_btn)

        right_layout.addWidget(packages_group)
        # 设置右侧组件的伸缩因子，让它能够占满空间
        right_layout.setStretchFactor(packages_group, 1)

        # 添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 600])  # 右侧组件需要更多空间显示树形结构

        # 初始化定制选项
        self.main_window.refresh_customization_data()

        self.main_window.tab_widget.addTab(widget, "定制选项")

    def create_build_tab(self):
        """创建构建标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 构建配置组
        build_group = QGroupBox("构建配置")
        build_layout = QFormLayout(build_group)

        # 显示当前配置
        self.main_window.build_summary_text = QTextEdit()
        self.main_window.build_summary_text.setReadOnly(True)
        self.main_window.build_summary_text.setMaximumHeight(80)  # 减小高度
        build_layout.addRow(self.main_window.build_summary_text)

        layout.addWidget(build_group)

        # 已构建目录管理组
        builds_group = QGroupBox("已构建目录")
        builds_layout = QVBoxLayout(builds_group)

        # 构建目录列表
        self.main_window.builds_list = QListWidget()
        # 优化列表框显示
        self.main_window.builds_list.setAlternatingRowColors(True)  # 交替行颜色
        self.main_window.builds_list.setSelectionMode(QAbstractItemView.SingleSelection)  # 单选模式
        self.main_window.builds_list.setUniformItemSizes(True)  # 统一项大小
        self.main_window.builds_list.setSpacing(1)  # 设置项间距
        builds_layout.addWidget(self.main_window.builds_list)
        builds_layout.setStretchFactor(self.main_window.builds_list, 1)  # 让列表框占满剩余空间

        # 构建目录操作按钮
        builds_btn_layout = QHBoxLayout()

        refresh_builds_btn = QPushButton("刷新")
        refresh_builds_btn.clicked.connect(self.main_window.refresh_builds_list)
        apply_3d_button_style(refresh_builds_btn)  # 应用蓝色立体样式
        builds_btn_layout.addWidget(refresh_builds_btn)

        delete_build_btn = QPushButton("删除选中")
        delete_build_btn.clicked.connect(self.main_window.delete_selected_build)
        apply_3d_button_style_red(delete_build_btn)  # 应用红色立体样式
        builds_btn_layout.addWidget(delete_build_btn)

        open_build_btn = QPushButton("打开目录")
        open_build_btn.clicked.connect(self.main_window.open_selected_build)
        apply_3d_button_style(open_build_btn)  # 应用蓝色立体样式
        builds_btn_layout.addWidget(open_build_btn)

        # 清空全部按钮
        clear_all_builds_btn = QPushButton("清空全部")
        clear_all_builds_btn.clicked.connect(self.main_window.clear_all_builds)
        apply_3d_button_style_red(clear_all_builds_btn)  # 应用红色立体样式
        builds_btn_layout.addWidget(clear_all_builds_btn)

        builds_layout.addLayout(builds_btn_layout)
        layout.addWidget(builds_group)

        # 构建控制组
        control_group = QGroupBox("构建控制")
        control_layout = QVBoxLayout(control_group)

        # 构建按钮
        self.main_window.build_btn = QPushButton("开始构建 WinPE")
        self.main_window.build_btn.setMinimumHeight(50)
        self.main_window.build_btn.clicked.connect(self.main_window.start_build)
        apply_3d_button_style_alternate(self.main_window.build_btn)  # 应用绿色立体样式
        control_layout.addWidget(self.main_window.build_btn)

        # 进度条
        self.main_window.progress_bar = QProgressBar()
        self.main_window.progress_bar.setVisible(False)
        control_layout.addWidget(self.main_window.progress_bar)

        layout.addWidget(control_group)

        # 构建日志组
        log_group = QGroupBox("构建日志")
        log_layout = QVBoxLayout(log_group)

        self.main_window.build_log_text = QTextEdit()
        self.main_window.build_log_text.setReadOnly(True)
        # 让日志文本框占据剩余空间
        log_layout.addWidget(self.main_window.build_log_text)

        layout.addWidget(log_group)

        # 更新配置摘要
        self.main_window.update_build_summary()

        # 加载已构建目录列表
        self.main_window.refresh_builds_list()

        self.main_window.tab_widget.addTab(widget, "开始构建")

    def create_log_tab(self):
        """创建日志标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 日志显示区域
        self.main_window.log_text = QTextEdit()
        self.main_window.log_text.setReadOnly(True)
        self.main_window.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.main_window.log_text)

        # 日志控制按钮
        control_layout = QHBoxLayout()
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self.main_window.clear_log)
        apply_3d_button_style_red(clear_log_btn)  # 应用红色立体样式

        save_log_btn = QPushButton("保存日志")
        save_log_btn.clicked.connect(self.main_window.save_log)
        apply_3d_button_style(save_log_btn)  # 应用蓝色立体样式
        control_layout.addWidget(clear_log_btn)
        control_layout.addWidget(save_log_btn)
        control_layout.addStretch()
        layout.addLayout(control_layout)

        self.main_window.tab_widget.addTab(widget, "系统日志")

    def create_status_bar(self):
        """创建状态栏"""
        self.main_window.status_label = QLabel("就绪")
        self.main_window.statusBar().addWidget(self.main_window.status_label)