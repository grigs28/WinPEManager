#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口模块
提供WinPE制作管理程序的主要用户界面
"""

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.adk_manager import ADKManager
from core.winpe_builder import WinPEBuilder
from core.config_manager import ConfigManager
from core.version_manager import get_version_manager
from utils.logger import log_error

# 导入拆分的功能模块
from ui.main_window.ui_creators import UICreators
from ui.main_window.event_handlers import EventHandlers
from ui.main_window.build_managers import BuildManagers
from ui.main_window.log_managers import LogManagers
from ui.main_window.helpers import Helpers


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.adk_manager = ADKManager()
        self.winpe_builder = WinPEBuilder(config_manager, self.adk_manager, parent_callback=None)
        self.build_thread = None

        # 设置包含版本信息的窗口标题
        version_manager = get_version_manager()
        current_version = version_manager.get_version_string()
        self.setWindowTitle(f"WinPE制作管理器 v{current_version}")
        self.setMinimumSize(1200, 800)

        # 初始化功能模块
        self.ui_creators = UICreators(self)
        self.event_handlers = EventHandlers(self)
        self.build_managers = BuildManagers(self)
        self.log_managers = LogManagers(self)
        self.helpers = Helpers(self)

        # 设置窗口图标
        self.set_window_icon()

        # 初始化界面
        self.init_ui()

        # 启动时立即检查ADK状态
        self.check_adk_status()
        
        # 启动时自动检测桌面环境
        self.event_handlers.auto_detect_desktop_on_startup()

    def set_window_icon(self):
        """设置窗口图标（随机选择PNG文件）"""
        self.helpers.set_window_icon()

    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 创建标题
        title_label = QLabel("Windows PE 制作管理器")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tab_widget)

        # 创建各个标签页
        self.create_basic_config_tab()
        self.create_customization_tab()
        self.create_build_tab()
        self.create_log_tab()

        # 创建状态栏
        self.create_status_bar()

    def create_basic_config_tab(self):
        """创建基本配置标签页"""
        self.ui_creators.create_basic_config_tab()

    def create_customization_tab(self):
        """创建定制选项标签页"""
        self.ui_creators.create_customization_tab()

    def create_build_tab(self):
        """创建构建标签页"""
        self.ui_creators.create_build_tab()

    def create_log_tab(self):
        """创建日志标签页"""
        self.ui_creators.create_log_tab()

    def create_status_bar(self):
        """创建状态栏"""
        self.ui_creators.create_status_bar()

    # 事件处理方法 - 委托给EventHandlers
    def on_language_changed(self):
        """语言选择变化事件"""
        self.event_handlers.on_language_changed()

    def on_tab_changed(self, index):
        """标签页切换事件"""
        self.event_handlers.on_tab_changed(index)

    def on_tree_selection_changed(self, selected_components):
        """树形控件选择变化事件"""
        self.event_handlers.on_tree_selection_changed(selected_components)

    def on_package_changed(self):
        """可选组件选择变化事件"""
        self.event_handlers.on_package_changed()

    def browse_workspace(self):
        """浏览工作空间目录"""
        self.event_handlers.browse_workspace()

    def browse_iso_path(self):
        """浏览ISO输出路径"""
        self.event_handlers.browse_iso_path()

    def browse_adk_path(self):
        """浏览ADK路径"""
        self.event_handlers.browse_adk_path()

    def browse_winpe_path(self):
        """浏览WinPE路径"""
        self.event_handlers.browse_winpe_path()

    def save_basic_config(self):
        """保存基本配置"""
        self.event_handlers.save_basic_config()

    def on_desktop_type_changed(self):
        """桌面类型选择变化事件"""
        self.event_handlers.on_desktop_type_changed()

    def browse_desktop_program(self):
        """浏览桌面程序路径"""
        self.event_handlers.browse_desktop_program()

    def browse_desktop_directory(self):
        """浏览桌面目录路径"""
        self.event_handlers.browse_desktop_directory()

    def save_customization_config(self):
        """保存定制配置"""
        self.event_handlers.save_customization_config()

    def add_driver(self):
        """添加驱动程序"""
        self.event_handlers.add_driver()

    def remove_driver(self):
        """移除选中的驱动程序"""
        self.event_handlers.remove_driver()

    def delete_driver_row(self, row):
        """删除驱动行"""
        self.event_handlers.delete_driver_row(row)

    def add_script(self):
        """添加脚本"""
        self.event_handlers.add_script()

    def remove_script(self):
        """移除选中的脚本"""
        self.event_handlers.remove_script()

    def delete_script_row(self, row):
        """删除脚本行"""
        self.event_handlers.delete_script_row(row)

    def add_file(self):
        """添加文件"""
        self.event_handlers.add_file()

    def remove_file(self):
        """移除选中的文件"""
        self.event_handlers.remove_file()

    def delete_file_row(self, row):
        """删除文件行"""
        self.event_handlers.delete_file_row(row)

    def search_components(self, keyword):
        """搜索组件"""
        self.event_handlers.search_components(keyword)

    def select_recommended_components(self):
        """选择推荐组件"""
        self.event_handlers.select_recommended_components()

    def clear_component_selection(self):
        """清空组件选择"""
        self.event_handlers.clear_component_selection()

    def clear_log(self):
        """清空日志"""
        self.log_managers.clear_log()

    def save_log(self):
        """保存日志"""
        self.log_managers.save_log()

    # 构建管理方法 - 委托给BuildManagers
    def start_build(self):
        """开始构建WinPE"""
        self.build_managers.start_build()

    def stop_build(self):
        """停止构建"""
        self.build_managers.stop_build()

    def make_iso_direct(self):
        """直接制作ISO"""
        self.build_managers.make_iso_direct()

    def refresh_builds_list(self):
        """刷新已构建目录列表"""
        self.build_managers.refresh_builds_list()

    def delete_selected_build(self):
        """删除选中的构建目录"""
        self.build_managers.delete_selected_build()

    def clear_all_builds(self):
        """清空所有构建目录"""
        self.build_managers.clear_all_builds()

    def open_selected_build(self):
        """打开选中的构建目录"""
        self.build_managers.open_selected_build()

    def on_build_progress(self, message: str, value: int):
        """构建进度更新"""
        self.build_managers.on_build_progress(message, value)

    def on_build_log(self, message: str):
        """构建日志更新"""
        self.build_managers.on_build_log(message)

    def show_build_error_dialog(self, error_details: str):
        """显示构建错误对话框"""
        self.build_managers.show_build_error_dialog(error_details)

    def on_build_finished(self, success: bool, message: str):
        """构建完成"""
        self.build_managers.on_build_finished(success, message)

    # 日志管理方法 - 委托给LogManagers
    def log_message(self, message: str):
        """添加日志消息"""
        self.log_managers.log_message(message)

    # 辅助方法 - 委托给Helpers
    def check_adk_status(self):
        """检查ADK状态"""
        self.helpers.check_adk_status()

    def test_dism_tool(self):
        """测试DISM工具是否正常工作"""
        self.helpers.test_dism_tool()

    def show_about_dialog(self):
        """显示关于对话框"""
        self.helpers.show_about_dialog()

    def show_changelog_dialog(self):
        """显示变更日志对话框"""
        self.helpers.show_changelog_dialog()

    def update_icon_info(self):
        """更新图标信息显示"""
        self.helpers.update_icon_info()

    def update_build_summary(self):
        """更新构建配置摘要"""
        self.helpers.update_build_summary()

    def refresh_customization_data(self):
        """刷新定制数据"""
        self.helpers.refresh_customization_data()

    def sync_language_packages(self):
        """同步语言包选择"""
        self.helpers.sync_language_packages()

    def refresh_packages(self):
        """刷新可选组件列表"""
        self.helpers.refresh_packages()

    def refresh_drivers(self):
        """刷新驱动程序列表"""
        self.helpers.refresh_drivers()

    def refresh_scripts(self):
        """刷新脚本列表"""
        self.helpers.refresh_scripts()

    def refresh_files(self):
        """刷新文件列表"""
        self.helpers.refresh_files()

    def show_desktop_config_dialog(self):
        """显示桌面环境配置对话框"""
        self.event_handlers.show_desktop_config_dialog()

    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 停止构建线程
            if self.build_thread and self.build_thread.isRunning():
                self.build_thread.stop()
                self.build_thread.wait(3000)

            # 清理WinPE构建器
            if self.winpe_builder:
                self.winpe_builder.cleanup()

            # 保存配置
            self.config_manager.save_config()

            event.accept()

        except Exception as e:
            log_error(e, "窗口关闭")
            event.accept()  # 即使出错也允许关闭
