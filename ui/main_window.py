#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口模块
提供WinPE制作管理程序的主要用户界面
"""

import sys
import os
import datetime
import shutil
from pathlib import Path
from typing import Dict, List, Any

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QMessageBox, QFileDialog, QSplitter,
    QCheckBox, QRadioButton, QButtonGroup, QFrame, QScrollArea,
    QFormLayout, QDialog, QListWidget, QListWidgetItem, QApplication, QProgressDialog,
    QAbstractItemView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor, QLinearGradient

from ui.config_dialogs import ConfigDialog, DriverDialog, ScriptDialog
from ui.components_tree_widget import ComponentsTreeWidget
from ui.progress_dialog import ProgressDialog
from ui.button_styler import apply_3d_button_style, apply_3d_button_style_alternate, apply_3d_button_style_red, apply_styled_button
from core.simple_icon import get_icon_manager, set_random_window_icon
from core.adk_manager import ADKManager
from core.winpe_builder import WinPEBuilder
from core.config_manager import ConfigManager
from core.version_manager import get_version_manager
from core.changelog_manager import get_changelog_manager
from utils.logger import log_error


class BuildThread(QThread):
    """WinPE构建线程"""
    progress_signal = pyqtSignal(str, int)  # 进度更新信号
    log_signal = pyqtSignal(str)  # 日志信号
    finished_signal = pyqtSignal(bool, str)  # 完成信号
    error_dialog_signal = pyqtSignal(str)  # 错误对话框信号
    refresh_builds_signal = pyqtSignal()  # 刷新已构建目录信号

    def __init__(self, builder: WinPEBuilder, config_manager: ConfigManager, iso_path: str = None):
        super().__init__()
        self.builder = builder
        self.config_manager = config_manager
        self.iso_path = iso_path
        self.is_running = False

        # 为builder设置错误回调
        self.builder.parent_callback = self.show_error_callback

    def show_error_callback(self, error_type: str, error_details: str):
        """错误回调函数，在主线程中显示错误对话框"""
        if error_type == 'show_error':
            self.error_dialog_signal.emit(error_details)

    def _check_disk_space(self) -> str:
        """检查磁盘空间"""
        try:
            if self.builder.current_build_path:
                disk_usage = shutil.disk_usage(str(self.builder.current_build_path))
                free_gb = disk_usage.free / (1024**3)
                total_gb = disk_usage.total / (1024**3)
                return f"可用空间: {free_gb:.1f}GB / 总空间: {total_gb:.1f}GB"
            else:
                return "无法检查磁盘空间"
        except Exception as e:
            return f"磁盘空间检查失败: {str(e)}"

    def _get_file_size(self, file_path: str) -> str:
        """获取文件大小的友好显示"""
        try:
            from pathlib import Path
            if not file_path or not Path(file_path).exists():
                return "0 B"

            size_bytes = Path(file_path).stat().st_size

            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        except Exception as e:
            return f"大小获取失败"

    def run(self):
        """执行构建过程"""
        self.is_running = True
        try:
            # 步骤1: 初始化工作空间
            self.progress_signal.emit("步骤 1/10: 初始化工作空间...", 10)
            self.log_signal.emit("=" * 60)
            self.log_signal.emit("🚀 WinPE构建管理器 - 开始构建过程")
            self.log_signal.emit("=" * 60)
            self.log_signal.emit(f"📅 构建开始时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_signal.emit(f"🖥️ 操作系统: {os.name} {sys.platform}")
            self.log_signal.emit(f"🐍 Python版本: {sys.version.split()[0]}")
            self.log_signal.emit(f"📁 工作目录: {os.getcwd()}")
            self.log_signal.emit("")
            self.log_signal.emit("🔧 正在初始化工作空间...")

            success, message = self.builder.initialize_workspace()  # 使用配置中的构建设置
            if not success:
                self.log_signal.emit(f"❌ 工作空间初始化失败: {message}")
                self.finished_signal.emit(False, f"初始化工作空间失败: {message}")
                return

            self.log_signal.emit(f"✅ 工作空间初始化成功")
            self.log_signal.emit(f"📁 构建目录: {self.builder.current_build_path}")
            self.log_signal.emit(f"📊 磁盘空间检查: {self._check_disk_space()}")

            if not self.is_running:
                return

            # 步骤2: 复制基础WinPE文件
            self.progress_signal.emit("步骤 2/8: 复制基础WinPE文件...", 20)
            architecture = self.builder.config.get("winpe.architecture", "amd64")

            # 读取并显示构建设置
            build_method = self.config_manager.get("winpe.build_method", "dism")
            build_mode = "copype工具 (推荐)" if build_method == "copype" else "传统DISM"
            self.log_signal.emit(f"🔧 构建模式: {build_mode}")
            self.log_signal.emit(f"正在复制WinPE基础文件 (架构: {architecture})...")
            self.log_signal.emit(f"📋 WinPE源路径: {self.builder.adk.winpe_path}")

            success, message = self.builder.copy_base_winpe(architecture)
            if not success:
                self.log_signal.emit(f"❌ WinPE基础文件复制失败: {message}")
                self.finished_signal.emit(False, f"复制基础WinPE失败: {message}")
                return

            self.log_signal.emit(f"✅ WinPE基础文件复制完成")
            self.log_signal.emit(f"🏗️ 系统架构: {architecture}")

            # 显示构建详情
            if build_method == "copype":
                self.log_signal.emit(f"🚀 使用Microsoft copype工具 - 符合官方标准")
                # copype执行成功后刷新已构建目录列表
                self.refresh_builds_signal.emit()
                self.log_signal.emit(f"📋 已构建目录列表已刷新")
            else:
                self.log_signal.emit(f"🔧 使用传统DISM方式 - 兼容模式")

            if not self.is_running:
                return

            # 步骤3: 挂载boot.wim镜像
            self.progress_signal.emit("步骤 3/8: 挂载boot.wim镜像...", 30)
            self.log_signal.emit("正在挂载boot.wim镜像以便添加组件...")
            self.log_signal.emit("🔧 DISM工具路径检查...")

            # 检查DISM工具状态
            dism_path = self.builder.adk.get_dism_path()
            if dism_path:
                self.log_signal.emit(f"🔧 DISM工具: {dism_path}")
            else:
                self.log_signal.emit("⚠️ 警告: DISM工具路径未找到")

            success, message = self.builder.mount_winpe_image()
            if not success:
                self.log_signal.emit(f"❌ boot.wim镜像挂载失败: {message}")
                self.log_signal.emit("💡 可能原因: 权限不足、磁盘空间不足或镜像文件损坏")
                self.finished_signal.emit(False, f"挂载boot.wim镜像失败: {message}")
                return

            self.log_signal.emit(f"✅ boot.wim镜像挂载成功")
            self.log_signal.emit(f"📂 挂载目录: {self.builder.current_build_path / 'mount'}")

            if not self.is_running:
                return

            # 步骤4: 添加可选组件（包含自动语言包）
            packages = self.builder.config.get("customization.packages", [])

            # 自动添加语言支持包
            from core.winpe_packages import WinPEPackages
            winpe_packages = WinPEPackages()
            current_language = self.builder.config.get("winpe.language", "en-US")
            language_packages = winpe_packages.get_language_packages(current_language)

            self.log_signal.emit(f"🔍 检查语言配置: {current_language}")
            self.log_signal.emit(f"   查找语言包: {current_language}")
            self.log_signal.emit(f"   找到的语言包: {language_packages if language_packages else '无'}")

            if language_packages:
                # 将语言包添加到组件列表中
                original_packages_count = len(packages)
                all_packages = set(packages)
                all_packages.update(language_packages)
                packages = list(all_packages)
                added_packages = len(packages) - original_packages_count

                self.log_signal.emit(f"🌐 自动添加语言支持包: {current_language}")
                self.log_signal.emit(f"   原始组件数: {original_packages_count}")
                self.log_signal.emit(f"   添加语言包数: {added_packages}")
                self.log_signal.emit(f"   最终组件数: {len(packages)}")
                self.log_signal.emit(f"   语言包列表: {', '.join(language_packages)}")
            else:
                self.log_signal.emit(f"ℹ️ 语言 {current_language} 无需额外的语言支持包")

            if packages:
                # 区分语言包和其他组件
                language_packages_set = set(language_packages)
                language_pkg_list = [p for p in packages if p in language_packages_set]
                other_pkg_list = [p for p in packages if p not in language_packages_set]

                self.progress_signal.emit(f"步骤 4/8: 添加 {len(packages)} 个可选组件...", 40)
                self.log_signal.emit(f"🔧 开始添加可选组件 ({len(packages)}个)...")

                # 详细显示语言包
                if language_pkg_list:
                    self.log_signal.emit(f"🌐 语言支持包 ({len(language_pkg_list)}个):")
                    for i, pkg in enumerate(language_pkg_list, 1):
                        self.log_signal.emit(f"   {i}. {pkg}")

                # 详细显示其他组件
                if other_pkg_list:
                    self.log_signal.emit(f"⚙️  其他功能组件 ({len(other_pkg_list)}个):")
                    for i, pkg in enumerate(other_pkg_list, 1):
                        self.log_signal.emit(f"   {i}. {pkg}")
                else:
                    self.log_signal.emit("⚙️  其他功能组件: 无")

                self.log_signal.emit(f"📊 组件分类统计: 语言包 {len(language_pkg_list)} 个 + 其他组件 {len(other_pkg_list)} 个 = 总计 {len(packages)} 个")
                self.log_signal.emit("⏳ 正在通过DISM添加组件到WinPE镜像...")

                success, message = self.builder.add_packages(packages)
                if success:
                    self.log_signal.emit(f"✅ 所有可选组件添加成功")
                    if language_pkg_list:
                        self.log_signal.emit(f"✅ 语言支持已集成: {current_language} ({len(language_pkg_list)}个语言包)")
                else:
                    self.log_signal.emit(f"⚠️ 部分组件添加失败: {message}")
                    # 不返回错误，继续执行
            else:
                self.log_signal.emit("ℹ️ 未配置可选组件，跳过此步骤")

            if not self.is_running:
                return

            # 步骤5: 添加驱动程序
            drivers = [driver.get("path", "") for driver in self.builder.config.get("customization.drivers", [])]
            if drivers:
                self.progress_signal.emit(f"步骤 5/8: 添加 {len(drivers)} 个驱动程序...", 60)
                self.log_signal.emit(f"正在添加驱动程序 ({len(drivers)}个)...")

                # 显示驱动程序信息
                from pathlib import Path
                driver_info = []
                for driver_path in drivers:
                    driver_name = Path(driver_path).name
                    driver_size = self._get_file_size(driver_path)
                    driver_info.append(f"{driver_name} ({driver_size})")

                self.log_signal.emit(f"🚗 驱动列表: {', '.join(driver_info[:2])}{'...' if len(driver_info) > 2 else ''}")

                success, message = self.builder.add_drivers(drivers)
                if success:
                    self.log_signal.emit(f"✅ 驱动程序添加成功")
                else:
                    self.log_signal.emit(f"⚠️ 驱动程序添加部分失败: {message}")
                    # 不返回错误，继续执行
            else:
                self.log_signal.emit("ℹ️ 未配置驱动程序，跳过此步骤")

            if not self.is_running:
                return

            # 步骤6: 配置系统语言和区域设置
            self.progress_signal.emit("步骤 6/8: 配置系统语言设置...", 70)
            self.log_signal.emit("正在配置WinPE系统语言和区域设置...")

            # 显示当前语言设置
            current_language = self.builder.config.get("winpe.language", "en-US")
            from core.winpe_packages import WinPEPackages
            winpe_packages = WinPEPackages()
            language_info = winpe_packages.get_language_info(current_language)
            language_name = language_info["name"] if language_info else current_language

            self.log_signal.emit(f"🌐 当前语言设置: {language_name} ({current_language})")

            success, message = self.builder.configure_language_settings()
            if success:
                self.log_signal.emit(f"✅ 语言配置成功: {language_name}")
            else:
                self.log_signal.emit(f"⚠️ 语言配置失败: {message}")

            if not self.is_running:
                return

            # 步骤7: 添加文件和脚本
            self.progress_signal.emit("步骤 7/8: 添加自定义文件和脚本...", 80)
            self.log_signal.emit("正在添加自定义文件和脚本...")

            # 检查自定义文件和脚本
            files_count = len(self.builder.config.get("customization.files", []))
            scripts_count = len(self.builder.config.get("customization.scripts", []))

            if files_count > 0 or scripts_count > 0:
                self.log_signal.emit(f"📄 自定义文件: {files_count}个, 📜 自定义脚本: {scripts_count}个")
            else:
                self.log_signal.emit("ℹ️ 未配置自定义文件或脚本")

            success, message = self.builder.add_files_and_scripts()
            if success:
                self.log_signal.emit(f"✅ 文件和脚本添加成功")
            else:
                self.log_signal.emit(f"⚠️ 文件和脚本添加部分失败: {message}")

            if not self.is_running:
                return

            # 步骤8: 应用WinPE专用设置
            self.progress_signal.emit("步骤 8/9: 应用WinPE专用设置...", 85)
            self.log_signal.emit("正在应用Microsoft官方WinPE标准设置...")

            # 读取配置
            enable_settings = self.config_manager.get("winpe.enable_winpe_settings", True)
            scratch_space = self.config_manager.get("winpe.scratch_space_mb", 128)
            target_path = self.config_manager.get("winpe.target_path", "X:")

            # 显示构建模式
            if hasattr(self.builder, 'use_copype') and self.builder.use_copype:
                self.log_signal.emit("🚀 copype模式 - 应用WinPE专用配置")
            else:
                self.log_signal.emit("🔧 传统模式 - 应用WinPE兼容设置")

            # 显示设置状态
            if not enable_settings:
                self.log_signal.emit("ℹ️ WinPE专用设置已禁用，跳过此步骤")
            else:
                self.log_signal.emit(f"🔧 WinPE专用设置: 暂存空间{scratch_space}MB, 目标路径{target_path}")

            if enable_settings:
                success, message = self.builder.apply_winpe_settings()
                if success:
                    self.log_signal.emit(f"✅ WinPE专用设置应用成功")
                    self.log_signal.emit(f"🔧 配置项: 暂存空间{scratch_space}MB, 目标路径{target_path}, 启动参数")
                else:
                    self.log_signal.emit(f"⚠️ WinPE设置应用失败: {message}")
                    # 不返回错误，继续执行

            if not self.is_running:
                return

            # 步骤9: 卸载并保存WinPE镜像
            self.progress_signal.emit("步骤 9/9: 卸载并保存WinPE镜像...", 90)
            self.log_signal.emit("正在卸载并保存WinPE镜像...")
            self.log_signal.emit("💾 所有更改将被提交到镜像文件")

            success, message = self.builder.unmount_winpe_image(discard=False)
            if not success:
                self.log_signal.emit(f"❌ 保存WinPE镜像失败: {message}")
                self.finished_signal.emit(False, f"保存WinPE镜像失败: {message}")
                return

            self.log_signal.emit(f"✅ WinPE镜像保存成功")

            if not self.is_running:
                return

            # 步骤10: 创建ISO文件
            self.progress_signal.emit("步骤 10/10: 创建可启动ISO文件...", 95)
            iso_path = self.builder.config.get('output.iso_path', '未知')
            self.log_signal.emit("正在创建可启动ISO文件...")
            self.log_signal.emit(f"💿 输出路径: {iso_path}")

            success, message = self.builder.create_bootable_iso(self.iso_path)
            if success:
                from pathlib import Path
                iso_size = self._get_file_size(iso_path) if Path(iso_path).exists() else "未知"
                build_time = datetime.datetime.now().strftime('%H:%M:%S')

                self.log_signal.emit(f"✅ WinPE构建完成！")
                self.log_signal.emit(f"🎯 ISO文件: {iso_path}")
                self.log_signal.emit(f"📏 ISO大小: {iso_size}")
                self.log_signal.emit(f"⏱️ 构建完成时间: {build_time}")
                self.log_signal.emit("=" * 50)

                self.progress_signal.emit("🎉 构建完成！", 100)
                self.finished_signal.emit(True, f"WinPE构建成功！\nISO文件: {iso_path}\n大小: {iso_size}")
            else:
                self.log_signal.emit(f"❌ ISO文件创建失败: {message}")
                self.finished_signal.emit(False, f"创建ISO失败: {message}")

        except Exception as e:
            log_error(e, "WinPE构建线程")
            self.finished_signal.emit(False, f"构建过程中发生错误: {str(e)}")

    def stop(self):
        """停止构建"""
        self.is_running = False


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

        # 设置窗口图标
        self.set_window_icon()

        # 初始化界面
        self.init_ui()

        # 启动时立即检查ADK状态
        self.check_adk_status()

    def set_window_icon(self):
        """设置窗口图标（随机选择PNG文件）"""
        try:
            icon_manager = get_icon_manager()
            if icon_manager.has_icons():
                # 为窗口设置随机PNG图标
                set_random_window_icon(self)
            else:
                logger.warning("没有找到可用的PNG图标文件")
        except Exception as e:
            # 静默失败，不影响程序启动
            logger.error(f"设置窗口图标失败: {str(e)}")

    def apply_button_styles(self):
        """为所有按钮应用立体样式"""
        try:
            # 这里可以集中管理所有按钮样式
            # 大部分按钮使用蓝色立体样式
            button_style_mapping = {
                # 浏览按钮
                'workspace_btn': '3d_blue',
                'iso_btn': '3d_blue',

                # 状态和测试按钮
                'refresh_btn': '3d_blue',
                'test_dism_btn': '3d_blue',

                # 关于和帮助按钮
                'about_btn': '3d_blue',
                'changelog_btn': '3d_blue',

                # 配置按钮
                'save_btn': '3d_blue',

                # 驱动按钮
                'add_driver_btn': '3d_blue',
                'remove_driver_btn': '3d_blue',

                # 脚本按钮
                'add_script_btn': '3d_blue',
                'remove_script_btn': '3d_blue',

                # 文件按钮
                'add_file_btn': '3d_blue',
                'remove_file_btn': '3d_blue',

                # 包管理按钮
                'refresh_packages_btn': '3d_blue',
                'select_recommended_btn': '3d_green',
                'clear_selection_btn': '3d_blue',

                # 构建管理按钮
                'refresh_builds_btn': '3d_blue',
                'delete_build_btn': '3d_blue',
                'open_build_btn': '3d_blue',

                # 日志按钮
                'clear_log_btn': '3d_blue',
                'save_log_btn': '3d_blue',

                # 构建按钮（特殊绿色）
                'build_btn': '3d_green',

                # 清空按钮（红色）
                'clear_all_builds_btn': 'special_red'
            }

            # 由于按钮在UI初始化过程中创建，这里不直接应用
            # 样式应用会在按钮创建时进行
            pass

        except Exception as e:
            logger.error(f"应用按钮样式时发生错误: {str(e)}")

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
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # WinPE基本配置组
        basic_group = QGroupBox("WinPE 基本配置")
        basic_layout = QFormLayout(basic_group)

        # 架构选择
        self.arch_combo = QComboBox()
        self.arch_combo.addItems(["amd64", "x86", "arm64"])
        current_arch = self.config_manager.get("winpe.architecture", "amd64")
        index = self.arch_combo.findText(current_arch)
        if index >= 0:
            self.arch_combo.setCurrentIndex(index)
        basic_layout.addRow("架构:", self.arch_combo)

        # 版本选择
        self.version_combo = QComboBox()
        self.version_combo.addItems(["10", "11"])
        current_version = self.config_manager.get("winpe.version", "10")
        index = self.version_combo.findText(current_version)
        if index >= 0:
            self.version_combo.setCurrentIndex(index)
        basic_layout.addRow("版本:", self.version_combo)

        # 构建设置
        self.build_method_combo = QComboBox()
        self.build_method_combo.addItems(["copype (推荐)", "传统DISM"])
        current_build_method = self.config_manager.get("winpe.build_method", "copype")
        method_map = {"copype": "copype (推荐)", "dism": "传统DISM"}
        method_text = method_map.get(current_build_method, "copype (推荐)")
        index = self.build_method_combo.findText(method_text)
        if index >= 0:
            self.build_method_combo.setCurrentIndex(index)
        basic_layout.addRow("构建方式:", self.build_method_combo)

        # WinPE专用设置
        settings_group = QGroupBox("WinPE 专用设置")
        settings_layout = QFormLayout()

        # 启用WinPE设置
        self.enable_winpe_settings_check = QCheckBox("启用 WinPE 专用设置")
        self.enable_winpe_settings_check.setChecked(
            self.config_manager.get("winpe.enable_winpe_settings", True)
        )
        settings_layout.addRow("", self.enable_winpe_settings_check)

        # 暂存空间设置
        self.scratch_space_spin = QSpinBox()
        self.scratch_space_spin.setRange(32, 1024)
        self.scratch_space_spin.setValue(
            self.config_manager.get("winpe.scratch_space_mb", 128)
        )
        self.scratch_space_spin.setSuffix(" MB")
        settings_layout.addRow("暂存空间:", self.scratch_space_spin)

        # 目标路径设置
        self.target_path_edit = QLineEdit()
        self.target_path_edit.setText(
            self.config_manager.get("winpe.target_path", "X:")
        )
        settings_layout.addRow("目标路径:", self.target_path_edit)

        settings_group.setLayout(settings_layout)
        basic_layout.addRow(settings_group)

        # 语言选择
        self.language_combo = QComboBox()
        # 从WinPE包管理器获取可用语言
        from core.winpe_packages import WinPEPackages
        winpe_packages = WinPEPackages()
        available_languages = winpe_packages.get_available_languages()

        for lang in available_languages:
            self.language_combo.addItem(lang["name"], lang["code"])

        current_lang = self.config_manager.get("winpe.language", "zh-CN")
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == current_lang:
                self.language_combo.setCurrentIndex(i)
                break

        # 连接语言变化信号
        self.language_combo.currentTextChanged.connect(self.on_language_changed)
        basic_layout.addRow("语言:", self.language_combo)

        layout.addWidget(basic_group)

        # 输出配置组
        output_group = QGroupBox("输出配置")
        output_layout = QFormLayout(output_group)

        # 工作空间行 - 文本框和浏览按钮在同一行
        workspace_layout = QHBoxLayout()
        self.workspace_edit = QLineEdit()
        self.workspace_edit.setText(self.config_manager.get("output.workspace", ""))
        self.workspace_edit.setPlaceholderText("选择WinPE构建工作空间")
        workspace_layout.addWidget(self.workspace_edit)
        
        workspace_btn = QPushButton("浏览...")
        workspace_btn.clicked.connect(self.browse_workspace)
        apply_3d_button_style(workspace_btn)  # 应用蓝色立体样式
        workspace_btn.setMaximumWidth(80)  # 限制按钮宽度
        workspace_layout.addWidget(workspace_btn)
        
        output_layout.addRow("工作空间:", workspace_layout)

        # ISO路径行 - 文本框和浏览按钮在同一行
        iso_layout = QHBoxLayout()
        self.iso_path_edit = QLineEdit()
        self.iso_path_edit.setText(self.config_manager.get("output.iso_path", ""))
        self.iso_path_edit.setPlaceholderText("选择ISO输出路径")
        iso_layout.addWidget(self.iso_path_edit)
        
        iso_btn = QPushButton("浏览...")
        iso_btn.clicked.connect(self.browse_iso_path)
        apply_3d_button_style(iso_btn)  # 应用蓝色立体样式
        iso_btn.setMaximumWidth(80)  # 限制按钮宽度
        iso_layout.addWidget(iso_btn)
        
        output_layout.addRow("ISO 路径:", iso_layout)

        layout.addWidget(output_group)

        # ADK配置组
        config_group = QGroupBox("ADK 配置")
        config_layout = QFormLayout(config_group)

        self.adk_path_edit = QLineEdit()
        self.adk_path_edit.setReadOnly(True)
        config_layout.addRow("ADK 路径:", self.adk_path_edit)

        self.winpe_path_edit = QLineEdit()
        self.winpe_path_edit.setReadOnly(True)
        config_layout.addRow("WinPE 路径:", self.winpe_path_edit)

        layout.addWidget(config_group)

        # ADK状态组
        adk_group = QGroupBox("Windows ADK 状态")
        adk_layout = QVBoxLayout(adk_group)

        self.adk_status_label = QLabel("正在检查ADK状态...")
        adk_layout.addWidget(self.adk_status_label)

        self.adk_details_label = QLabel("")
        self.adk_details_label.setWordWrap(True)
        adk_layout.addWidget(self.adk_details_label)

        # ADK状态组 - 移除按钮，按钮将在底部统一处理
        layout.addWidget(adk_group)

        # 添加弹性空间，将按钮推到底部
        layout.addStretch()

        # 创建统一的按钮行布局 - 放在最底部
        unified_btn_layout = QHBoxLayout()

        # ADK状态按钮
        refresh_btn = QPushButton("刷新状态")
        refresh_btn.clicked.connect(self.check_adk_status)
        apply_3d_button_style(refresh_btn)  # 应用蓝色立体样式
        unified_btn_layout.addWidget(refresh_btn)

        test_dism_btn = QPushButton("测试DISM工具")
        test_dism_btn.clicked.connect(self.test_dism_tool)
        apply_3d_button_style(test_dism_btn)  # 应用蓝色立体样式
        unified_btn_layout.addWidget(test_dism_btn)

        # 关于和帮助按钮
        about_btn = QPushButton("关于程序")
        about_btn.clicked.connect(self.show_about_dialog)
        apply_3d_button_style(about_btn)  # 应用蓝色立体样式
        unified_btn_layout.addWidget(about_btn)

        changelog_btn = QPushButton("更新日志")
        changelog_btn.clicked.connect(self.show_changelog_dialog)
        apply_3d_button_style(changelog_btn)  # 应用蓝色立体样式
        unified_btn_layout.addWidget(changelog_btn)

        # 保存配置按钮
        save_btn = QPushButton("保存基本配置")
        save_btn.clicked.connect(self.save_basic_config)
        apply_3d_button_style_alternate(save_btn)  # 应用绿色立体样式
        unified_btn_layout.addWidget(save_btn)

        layout.addLayout(unified_btn_layout)

        layout.addStretch()
        self.tab_widget.addTab(widget, "基本配置")

        # 初始化ADK状态
        self.check_adk_status()

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

        self.drivers_table = QTableWidget()
        self.drivers_table.setColumnCount(3)
        self.drivers_table.setHorizontalHeaderLabels(["路径", "描述", "操作"])
        self.drivers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.drivers_table.setAlternatingRowColors(True)
        drivers_layout.addWidget(self.drivers_table)

        drivers_btn_layout = QHBoxLayout()
        add_driver_btn = QPushButton("添加驱动")
        add_driver_btn.clicked.connect(self.add_driver)
        apply_3d_button_style(add_driver_btn)  # 应用蓝色立体样式
        remove_driver_btn = QPushButton("移除驱动")
        remove_driver_btn.clicked.connect(self.remove_driver)
        apply_3d_button_style_red(remove_driver_btn)  # 应用红色立体样式
        drivers_btn_layout.addWidget(add_driver_btn)
        drivers_btn_layout.addWidget(remove_driver_btn)
        drivers_layout.addLayout(drivers_btn_layout)

        left_layout.addWidget(drivers_group)

        # 自定义脚本
        scripts_group = QGroupBox("自定义脚本")
        scripts_layout = QVBoxLayout(scripts_group)

        self.scripts_table = QTableWidget()
        self.scripts_table.setColumnCount(3)
        self.scripts_table.setHorizontalHeaderLabels(["路径", "描述", "操作"])
        self.scripts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.scripts_table.setAlternatingRowColors(True)
        scripts_layout.addWidget(self.scripts_table)

        scripts_btn_layout = QHBoxLayout()
        add_script_btn = QPushButton("添加脚本")
        add_script_btn.clicked.connect(self.add_script)
        apply_3d_button_style(add_script_btn)  # 应用蓝色立体样式
        remove_script_btn = QPushButton("移除脚本")
        remove_script_btn.clicked.connect(self.remove_script)
        apply_3d_button_style_red(remove_script_btn)  # 应用红色立体样式
        scripts_btn_layout.addWidget(add_script_btn)
        scripts_btn_layout.addWidget(remove_script_btn)
        scripts_layout.addLayout(scripts_btn_layout)

        left_layout.addWidget(scripts_group)

        # 额外文件
        files_group = QGroupBox("额外文件")
        files_layout = QVBoxLayout(files_group)

        self.files_table = QTableWidget()
        self.files_table.setColumnCount(3)
        self.files_table.setHorizontalHeaderLabels(["路径", "描述", "操作"])
        self.files_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.files_table.setAlternatingRowColors(True)
        files_layout.addWidget(self.files_table)

        files_btn_layout = QHBoxLayout()
        add_file_btn = QPushButton("添加文件")
        add_file_btn.clicked.connect(self.add_file)
        apply_3d_button_style(add_file_btn)  # 应用蓝色立体样式
        remove_file_btn = QPushButton("移除文件")
        remove_file_btn.clicked.connect(self.remove_file)
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
        self.search_edit = SearchLineEdit()
        self.search_edit.setPlaceholderText("搜索组件...")
        self.search_edit.textChanged.connect(self.search_components)
        self.search_edit.setMaximumWidth(200)
        packages_btn_layout.addWidget(QLabel("搜索:"))
        packages_btn_layout.addWidget(self.search_edit)

        packages_btn_layout.addStretch()

        # 操作按钮
        refresh_packages_btn = QPushButton("刷新")
        refresh_packages_btn.clicked.connect(self.refresh_packages)
        refresh_packages_btn.setMaximumWidth(80)
        apply_3d_button_style(refresh_packages_btn)  # 应用蓝色立体样式
        packages_btn_layout.addWidget(refresh_packages_btn)

        select_recommended_btn = QPushButton("选择推荐")
        select_recommended_btn.clicked.connect(self.select_recommended_components)
        select_recommended_btn.setMaximumWidth(80)
        apply_3d_button_style_alternate(select_recommended_btn)  # 应用绿色立体样式
        packages_btn_layout.addWidget(select_recommended_btn)
        clear_selection_btn = QPushButton("清空选择")
        clear_selection_btn.clicked.connect(self.clear_component_selection)
        clear_selection_btn.setMaximumWidth(80)
        apply_3d_button_style_red(clear_selection_btn)  # 应用红色立体样式
        packages_btn_layout.addWidget(clear_selection_btn)

        packages_layout.addLayout(packages_btn_layout)

        # 创建树形控件（占满剩余空间）
        self.components_tree = ComponentsTreeWidget()
        # 连接选择变化信号
        self.components_tree.component_selection_changed.connect(self.on_tree_selection_changed)
        packages_layout.addWidget(self.components_tree)

        # 保存定制配置按钮
        save_btn = QPushButton("保存定制配置")
        save_btn.clicked.connect(self.save_customization_config)
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
        self.refresh_customization_data()

        self.tab_widget.addTab(widget, "定制选项")

    def create_build_tab(self):
        """创建构建标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 构建配置组
        build_group = QGroupBox("构建配置")
        build_layout = QFormLayout(build_group)

        # 显示当前配置
        self.build_summary_text = QTextEdit()
        self.build_summary_text.setReadOnly(True)
        self.build_summary_text.setMaximumHeight(80)  # 减小高度
        build_layout.addRow(self.build_summary_text)

        layout.addWidget(build_group)

        # 已构建目录管理组
        builds_group = QGroupBox("已构建目录")
        builds_layout = QVBoxLayout(builds_group)

        # 构建目录列表
        self.builds_list = QListWidget()
        # 优化列表框显示
        self.builds_list.setAlternatingRowColors(True)  # 交替行颜色
        self.builds_list.setSelectionMode(QAbstractItemView.SingleSelection)  # 单选模式
        self.builds_list.setUniformItemSizes(True)  # 统一项大小
        self.builds_list.setSpacing(1)  # 设置项间距
        builds_layout.addWidget(self.builds_list)
        builds_layout.setStretchFactor(self.builds_list, 1)  # 让列表框占满剩余空间

        # 构建目录操作按钮
        builds_btn_layout = QHBoxLayout()

        refresh_builds_btn = QPushButton("刷新")
        refresh_builds_btn.clicked.connect(self.refresh_builds_list)
        apply_3d_button_style(refresh_builds_btn)  # 应用蓝色立体样式
        builds_btn_layout.addWidget(refresh_builds_btn)

        delete_build_btn = QPushButton("删除选中")
        delete_build_btn.clicked.connect(self.delete_selected_build)
        apply_3d_button_style_red(delete_build_btn)  # 应用红色立体样式
        builds_btn_layout.addWidget(delete_build_btn)

        open_build_btn = QPushButton("打开目录")
        open_build_btn.clicked.connect(self.open_selected_build)
        apply_3d_button_style(open_build_btn)  # 应用蓝色立体样式
        builds_btn_layout.addWidget(open_build_btn)

        # 清空全部按钮
        clear_all_builds_btn = QPushButton("清空全部")
        clear_all_builds_btn.clicked.connect(self.clear_all_builds)
        apply_3d_button_style_red(clear_all_builds_btn)  # 应用红色立体样式
        builds_btn_layout.addWidget(clear_all_builds_btn)

        builds_layout.addLayout(builds_btn_layout)
        layout.addWidget(builds_group)

        # 构建控制组
        control_group = QGroupBox("构建控制")
        control_layout = QVBoxLayout(control_group)

        # 构建按钮
        self.build_btn = QPushButton("开始构建 WinPE")
        self.build_btn.setMinimumHeight(50)
        self.build_btn.clicked.connect(self.start_build)
        apply_3d_button_style_alternate(self.build_btn)  # 应用绿色立体样式
        control_layout.addWidget(self.build_btn)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)

        layout.addWidget(control_group)

        # 构建日志组
        log_group = QGroupBox("构建日志")
        log_layout = QVBoxLayout(log_group)

        self.build_log_text = QTextEdit()
        self.build_log_text.setReadOnly(True)
        # 让日志文本框占据剩余空间
        log_layout.addWidget(self.build_log_text)

        layout.addWidget(log_group)

        # 更新配置摘要
        self.update_build_summary()

        # 加载已构建目录列表
        self.refresh_builds_list()

        self.tab_widget.addTab(widget, "开始构建")

    def create_log_tab(self):
        """创建日志标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)

        # 日志控制按钮
        control_layout = QHBoxLayout()
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self.clear_log)
        apply_3d_button_style_red(clear_log_btn)  # 应用红色立体样式

        save_log_btn = QPushButton("保存日志")
        save_log_btn.clicked.connect(self.save_log)
        apply_3d_button_style(save_log_btn)  # 应用蓝色立体样式
        control_layout.addWidget(clear_log_btn)
        control_layout.addWidget(save_log_btn)
        control_layout.addStretch()
        layout.addLayout(control_layout)

        self.tab_widget.addTab(widget, "系统日志")

    def create_status_bar(self):
        """创建状态栏"""
        self.status_label = QLabel("就绪")
        self.statusBar().addWidget(self.status_label)

    def check_adk_status(self):
        """检查ADK状态"""
        try:
            # 检测ADK状态并记录日志
            status = self.adk_manager.get_adk_install_status()

            # 更新状态显示
            if status["adk_installed"] and status["winpe_installed"]:
                self.adk_status_label.setText("✓ Windows ADK 和 WinPE 加载项已正确安装")
                self.adk_status_label.setStyleSheet("color: green;")
            else:
                error_messages = []
                if not status["adk_installed"]:
                    error_messages.append("Windows ADK 未安装")
                if not status["winpe_installed"]:
                    error_messages.append("WinPE 加载项未安装")
                self.adk_status_label.setText("✗ " + "，".join(error_messages))
                self.adk_status_label.setStyleSheet("color: red;")

            # 更新详细信息
            details = []
            if status["adk_path"]:
                details.append(f"ADK 路径: {status['adk_path']}")
            if status["winpe_path"]:
                details.append(f"WinPE 路径: {status['winpe_path']}")
            if status["available_architectures"]:
                details.append(f"支持架构: {', '.join(status['available_architectures'])}")
            if status["dism_path"]:
                details.append(f"DISM 路径: {status['dism_path']}")
            if status["environment_ready"]:
                details.append("部署工具环境: 已就绪")
            elif status["has_dandisetenv"]:
                details.append("部署工具环境: 需要加载环境变量")
            else:
                details.append("部署工具环境: 未找到DandISetEnv.bat")
            if status["has_admin"]:
                details.append("管理员权限: 是")
            else:
                details.append("管理员权限: 否")

            self.adk_details_label.setText("\n".join(details))

            # 更新路径编辑框
            self.adk_path_edit.setText(status["adk_path"])
            self.winpe_path_edit.setText(status["winpe_path"])

            # 更新架构选择
            current_arch = self.arch_combo.currentText()
            self.arch_combo.clear()
            self.arch_combo.addItems(status["available_architectures"] or ["amd64"])
            index = self.arch_combo.findText(current_arch)
            if index >= 0:
                self.arch_combo.setCurrentIndex(index)

        except Exception as e:
            log_error(e, "检查ADK状态")
            self.adk_status_label.setText(f"检查ADK状态时发生错误: {str(e)}")
            self.adk_status_label.setStyleSheet("color: red;")

    def test_dism_tool(self):
        """测试DISM工具是否正常工作"""
        try:
            # 检查当前环境是否就绪
            status = self.adk_manager.get_adk_install_status()

            if not status["environment_ready"]:
                self.log_message("环境未就绪，正在加载ADK环境变量...")
                env_loaded, env_message = self.adk_manager.load_adk_environment()
                if not env_loaded:
                    self.log_message(f"警告: {env_message}")
                    QMessageBox.warning(
                        self, "环境加载失败",
                        f"无法加载ADK环境: {env_message}\n\n这可能影响DISM工具测试。"
                    )
                    return
                else:
                    self.log_message(f"环境加载: {env_message}")
            else:
                self.log_message("环境已就绪，直接测试DISM工具")

            # 获取DISM路径
            dism_path = self.adk_manager.get_dism_path()
            if not dism_path:
                QMessageBox.warning(self, "错误", "找不到DISM工具")
                return

            # 测试DISM命令
            success, stdout, stderr = self.adk_manager.run_dism_command(["/online", "/get-featureinfo", "/featurename:NetFx3"])

            if success:
                QMessageBox.information(
                    self, "DISM测试成功",
                    f"DISM工具工作正常！\n\n路径: {dism_path}\n\n输出信息已记录到日志。"
                )
                self.log_message("DISM工具测试成功")
                if stdout and stdout.strip():
                    self.log_message(f"DISM输出: {stdout.strip()}")
            else:
                error_msg = f"DISM工具测试失败:\n\n{stderr if stderr else '未知错误'}"
                QMessageBox.warning(self, "DISM测试失败", error_msg)
                self.log_message(f"DISM工具测试失败: {stderr if stderr else '未知错误'}")

        except Exception as e:
            error_msg = f"测试DISM工具时发生错误: {str(e)}"
            log_error(e, "测试DISM工具")
            QMessageBox.critical(self, "错误", error_msg)

    # 版本管理和帮助方法
    def show_about_dialog(self):
        """显示关于对话框"""
        try:
            version_manager = get_version_manager()
            version_info = version_manager.get_version_info_dict()

            about_text = f"""
<b>WinPE制作管理器</b><br><br>
版本: {version_info['version']}<br>
构建时间: {version_info['build_info']['build_time']}<br>
平台: {version_info['build_info']['platform']}<br><br>

<b>功能特性:</b><br>
• Windows ADK 环境检测和管理<br>
• 自定义 WinPE 环境构建<br>
• 驱动程序和软件包集成<br>
• 图形化用户界面<br>
• 随机图标管理<br>
• 完整的构建日志系统<br><br>

<b>技术栈:</b><br>
• Python {version_info['build_info']['python_version']}<br>
• PyQt5 GUI 框架<br>
• Windows ADK API<br><br>

© 2024 WinPE管理工具<br>
基于 MIT 许可证发布
            """

            QMessageBox.about(self, "关于 WinPE制作管理器", about_text)

        except Exception as e:
            log_error(e, "显示关于对话框")
            QMessageBox.critical(self, "错误", f"显示关于对话框失败: {str(e)}")

    def show_changelog_dialog(self):
        """显示变更日志对话框"""
        try:
            changelog_manager = get_changelog_manager()
            changelog_path = changelog_manager.changelog_path

            # 确保变更日志文件存在
            if not changelog_path.exists():
                changelog_manager.create_changelog()
            # 读取变更日志内容
            changelog_content = changelog_path.read_text(encoding='utf-8')

            # 创建对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("更新日志")
            dialog.setMinimumSize(800, 600)

            layout = QVBoxLayout(dialog)

            # 文本显示区域
            text_edit = QTextEdit()
            text_edit.setPlainText(changelog_content)
            text_edit.setReadOnly(True)
            text_edit.setFont(QFont("Consolas", 9))  # 使用等宽字体
            layout.addWidget(text_edit)

            # 按钮区域
            button_layout = QHBoxLayout()

            refresh_btn = QPushButton("刷新")
            refresh_btn.clicked.connect(lambda: self._refresh_changelog(text_edit))
            apply_3d_button_style(refresh_btn)  # 应用蓝色立体样式
            button_layout.addWidget(refresh_btn)

            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.accept)
            apply_3d_button_style_alternate(close_btn)  # 应用绿色立体样式
            button_layout.addWidget(close_btn)

            layout.addLayout(button_layout)

            # 显示对话框
            dialog.exec_()

        except Exception as e:
            log_error(e, "显示变更日志对话框")
            QMessageBox.critical(self, "错误", f"显示变更日志失败: {str(e)}")

    def _refresh_changelog(self, text_edit):
        """刷新变更日志显示"""
        try:
            changelog_manager = get_changelog_manager()
            changelog_content = changelog_manager.changelog_path.read_text(encoding='utf-8')
            text_edit.setPlainText(changelog_content)
            self.log_message("变更日志已刷新")
        except Exception as e:
            log_error(e, "刷新变更日志")
            QMessageBox.warning(self, "警告", f"刷新变更日志失败: {str(e)}")

    # 图标管理方法
    def update_icon_info(self):
        """更新图标信息显示"""
        try:
            icon_manager = get_icon_manager()
            info = icon_manager.get_current_icon_info()

            if info["total_icons"] > 0:
                from pathlib import Path
                current_icon_name = Path(info["current_icon"]).name if info["current_icon"] else "未设置"
                info_text = f"当前图标: {current_icon_name}\n"
                info_text += f"可用PNG图标: {info['total_icons']} 个\n"
                info_text += f"每次启动随机选择"
            else:
                info_text = f"未找到PNG图标文件\n"
                info_text += f"请将 .png 文件放入 ico 目录"

            self.icon_info_label.setText(info_text)

        except Exception as e:
            self.icon_info_label.setText(f"获取图标信息失败: {str(e)}")

    
    
    def on_language_changed(self):
        """语言选择变化事件"""
        try:
            # 获取选择的语言代码
            current_language_code = self.language_combo.currentData()
            if not current_language_code:
                return

            # 保存语言配置
            self.config_manager.set("winpe.language", current_language_code)

            # 获取语言相关的包
            from core.winpe_packages import WinPEPackages
            winpe_packages = WinPEPackages()
            language_packages = winpe_packages.get_language_packages(current_language_code)

            # 获取当前已选择的包
            current_packages = set(self.config_manager.get("customization.packages", []))

            # 移除所有语言相关的包
            all_language_packages = set()
            for lang_code in winpe_packages.get_language_support_mapping().keys():
                all_language_packages.update(winpe_packages.get_language_packages(lang_code))

            current_packages -= all_language_packages

            # 添加新语言的包
            current_packages.update(language_packages)

            # 保存更新后的包列表
            self.config_manager.set("customization.packages", list(current_packages))

            # 刷新可选组件树形控件
            if hasattr(self, 'components_tree'):
                self.refresh_packages()

            # 更新构建摘要
            self.update_build_summary()

            # 记录详细的日志
            language_info = winpe_packages.get_language_info(current_language_code)
            language_name = language_info["name"] if language_info else current_language_code
            self.log_message(f"🌐 语言已切换到: {language_name} ({current_language_code})")

            if language_packages:
                self.log_message(f"📦 自动添加语言支持包 ({len(language_packages)}个):")
                for i, package in enumerate(language_packages, 1):
                    self.log_message(f"   {i}. {package}")

                # 区分语言包和其他组件
                all_packages = set(self.config_manager.get("customization.packages", []))
                non_language_packages = all_packages - set(language_packages)
                if non_language_packages:
                    self.log_message(f"📋 其他可选组件 ({len(non_language_packages)}个): {', '.join(list(non_language_packages)[:3])}{'...' if len(non_language_packages) > 3 else ''}")
                else:
                    self.log_message("📋 暂无其他可选组件")

                self.log_message(f"📊 组件总数: {len(all_packages)} 个 (语言包: {len(language_packages)}, 其他: {len(non_language_packages)})")
            else:
                self.log_message(f"⚠️ 语言 {language_name} 无需额外的语言支持包")

        except Exception as e:
            from utils.logger import log_error
            log_error(e, "语言切换")
            QMessageBox.warning(self, "警告", f"语言切换失败: {str(e)}")

    def on_tab_changed(self, index):
        """标签页切换事件"""
        if index == 2:  # 构建标签页
            self.update_build_summary()

    def update_build_summary(self):
        """更新构建配置摘要"""
        summary_lines = []
        summary_lines.append(f"WinPE 版本: {self.config_manager.get('winpe.version', '10')}")
        summary_lines.append(f"架构: {self.config_manager.get('winpe.architecture', 'amd64')}")
        # 获取语言名称
        language_code = self.config_manager.get('winpe.language', 'zh-CN')
        from core.winpe_packages import WinPEPackages
        winpe_packages = WinPEPackages()
        language_info = winpe_packages.get_language_info(language_code)
        language_name = language_info["name"] if language_info else language_code
        summary_lines.append(f"语言: {language_name}")

        # 构建设置
        build_method = self.config_manager.get("winpe.build_method", "dism")
        build_mode_text = "copype (推荐)" if build_method == "copype" else "传统DISM"
        summary_lines.append(f"构建方式: {build_mode_text}")

        # WinPE专用设置
        enable_settings = self.config_manager.get("winpe.enable_winpe_settings", True)
        if enable_settings:
            scratch_space = self.config_manager.get("winpe.scratch_space_mb", 128)
            target_path = self.config_manager.get("winpe.target_path", "X:")
            summary_lines.append(f"暂存空间: {scratch_space}MB")
            summary_lines.append(f"目标路径: {target_path}")
        else:
            summary_lines.append("WinPE专用设置: 已禁用")

        packages = self.config_manager.get("customization.packages", [])
        summary_lines.append(f"可选组件: {len(packages)} 个")

        drivers = self.config_manager.get("customization.drivers", [])
        summary_lines.append(f"驱动程序: {len(drivers)} 个")

        scripts = self.config_manager.get("customization.scripts", [])
        summary_lines.append(f"自定义脚本: {len(scripts)} 个")

        files = self.config_manager.get("customization.files", [])
        summary_lines.append(f"额外文件: {len(files)} 个")

        iso_path = self.config_manager.get("output.iso_path", "未设置")
        summary_lines.append(f"ISO输出路径: {iso_path}")

        workspace = self.config_manager.get("output.workspace", "未设置")
        summary_lines.append(f"工作空间: {workspace}")

        self.build_summary_text.setText("\n".join(summary_lines))

    def refresh_customization_data(self):
        """刷新定制数据"""
        # 确保语言包与选择的语言同步
        self.sync_language_packages()

        self.refresh_packages()
        self.refresh_drivers()
        self.refresh_scripts()
        self.refresh_files()

    def sync_language_packages(self):
        """同步语言包选择"""
        try:
            # 获取当前选择的语言
            current_language_code = self.language_combo.currentData()
            if not current_language_code:
                return

            # 获取语言相关的包
            from core.winpe_packages import WinPEPackages
            winpe_packages = WinPEPackages()
            language_packages = winpe_packages.get_language_packages(current_language_code)

            # 获取当前已选择的包
            current_packages = set(self.config_manager.get("customization.packages", []))

            # 移除所有语言相关的包
            all_language_packages = set()
            for lang_code in winpe_packages.get_language_support_mapping().keys():
                all_language_packages.update(winpe_packages.get_language_packages(lang_code))

            current_packages -= all_language_packages

            # 添加当前语言的包
            current_packages.update(language_packages)

            # 保存更新后的包列表
            self.config_manager.set("customization.packages", list(current_packages))

        except Exception as e:
            from utils.logger import log_error
            log_error(e, "同步语言包")

    def refresh_packages(self):
        """刷新可选组件列表"""
        try:
            # 重新构建树形组件
            self.components_tree.build_tree()

            # 恢复之前的选择状态
            selected_packages = self.config_manager.get("customization.packages", [])
            if selected_packages:
                self.components_tree.select_components(selected_packages)

        except Exception as e:
            log_error(e, "刷新可选组件列表")

    def on_package_changed(self):
        """可选组件选择变化事件"""
        try:
            selected_components = self.components_tree.get_selected_components()
            selected_packages = list(selected_components.keys())
            self.config_manager.set("customization.packages", selected_packages)
        except Exception as e:
            log_error(e, "可选组件选择变化")

    def on_tree_selection_changed(self, selected_components):
        """树形控件选择变化事件"""
        try:
            selected_packages = list(selected_components.keys())
            self.config_manager.set("customization.packages", selected_packages)
        except Exception as e:
            log_error(e, "树形控件选择变化")

    def refresh_drivers(self):
        """刷新驱动程序列表"""
        try:
            drivers = self.config_manager.get("customization.drivers", [])
            self.drivers_table.setRowCount(len(drivers))
            for row, driver in enumerate(drivers):
                self.drivers_table.setItem(row, 0, QTableWidgetItem(driver.get("path", "")))
                self.drivers_table.setItem(row, 1, QTableWidgetItem(driver.get("description", "")))

                # 删除按钮
                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda checked, r=row: self.delete_driver_row(r))
                apply_3d_button_style_red(delete_btn)  # 应用红色立体样式
                self.drivers_table.setCellWidget(row, 2, delete_btn)

        except Exception as e:
            log_error(e, "刷新驱动程序列表")

    def refresh_scripts(self):
        """刷新脚本列表"""
        try:
            scripts = self.config_manager.get("customization.scripts", [])
            self.scripts_table.setRowCount(len(scripts))

            for row, script in enumerate(scripts):
                self.scripts_table.setItem(row, 0, QTableWidgetItem(script.get("path", "")))
                self.scripts_table.setItem(row, 1, QTableWidgetItem(script.get("description", "")))

                # 删除按钮
                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda checked, r=row: self.delete_script_row(r))
                apply_3d_button_style_red(delete_btn)  # 应用红色立体样式
                self.scripts_table.setCellWidget(row, 2, delete_btn)

        except Exception as e:
            log_error(e, "刷新脚本列表")

    def refresh_files(self):
        """刷新文件列表"""
        try:
            files = self.config_manager.get("customization.files", [])
            self.files_table.setRowCount(len(files))

            for row, file_info in enumerate(files):
                self.files_table.setItem(row, 0, QTableWidgetItem(file_info.get("path", "")))
                self.files_table.setItem(row, 1, QTableWidgetItem(file_info.get("description", "")))

                # 删除按钮
                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda checked, r=row: self.delete_file_row(r))
                apply_3d_button_style_red(delete_btn)  # 应用红色立体样式
                self.files_table.setCellWidget(row, 2, delete_btn)

        except Exception as e:
            log_error(e, "刷新文件列表")

    def delete_driver_row(self, row):
        """删除驱动行"""
        try:
            driver_path = self.drivers_table.item(row, 0).text()
            self.config_manager.remove_driver(driver_path)
            self.refresh_drivers()
        except Exception as e:
            log_error(e, "删除驱动行")

    def delete_script_row(self, row):
        """删除脚本行"""
        try:
            scripts = self.config_manager.get("customization.scripts", [])
            if 0 <= row < len(scripts):
                scripts.pop(row)
                self.config_manager.set("customization.scripts", scripts)
                self.refresh_scripts()
        except Exception as e:
            log_error(e, "删除脚本行")

    def search_components(self, keyword):
        """搜索组件"""
        try:
            if keyword.strip():
                self.components_tree.search_components(keyword.strip())
            else:
                self.components_tree.clear_search_highlight()
        except Exception as e:
            log_error(e, "搜索组件")

    def select_recommended_components(self):
        """选择推荐组件"""
        try:
            self.components_tree.select_recommended_components()
            # 更新配置
            self.on_package_changed()
        except Exception as e:
            log_error(e, "选择推荐组件")

    def clear_component_selection(self):
        """清空组件选择"""
        try:
            self.components_tree.clear_selection()
            # 更新配置
            self.on_package_changed()
        except Exception as e:
            log_error(e, "清空组件选择")

    def delete_file_row(self, row):
        """删除文件行"""
        try:
            files = self.config_manager.get("customization.files", [])
            if 0 <= row < len(files):
                files.pop(row)
                self.config_manager.set("customization.files", files)
                self.refresh_files()
        except Exception as e:
            log_error(e, "删除文件行")

    def add_driver(self):
        """添加驱动程序"""
        try:
            dialog = DriverDialog(self)
            if dialog.exec_() == DriverDialog.Accepted:
                driver_path, description = dialog.get_driver_info()
                if driver_path:
                    self.config_manager.add_driver(driver_path, description)
                    self.refresh_drivers()
        except Exception as e:
            log_error(e, "添加驱动程序")

    def remove_driver(self):
        """移除选中的驱动程序"""
        try:
            current_row = self.drivers_table.currentRow()
            if current_row >= 0:
                self.delete_driver_row(current_row)
        except Exception as e:
            log_error(e, "移除驱动程序")

    def add_script(self):
        """添加脚本"""
        try:
            dialog = ScriptDialog(self)
            if dialog.exec_() == ScriptDialog.Accepted:
                script_path, description = dialog.get_script_info()
                if script_path:
                    self.config_manager.add_script(script_path, description)
                    self.refresh_scripts()
        except Exception as e:
            log_error(e, "添加脚本")

    def remove_script(self):
        """移除选中的脚本"""
        try:
            current_row = self.scripts_table.currentRow()
            if current_row >= 0:
                self.delete_script_row(current_row)
        except Exception as e:
            log_error(e, "移除脚本")

    def add_file(self):
        """添加文件"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择要添加的文件", "", "所有文件 (*.*)"
            )
            if file_path:
                from pathlib import Path
                file_info = {
                    "path": file_path,
                    "description": Path(file_path).name
                }
                files = self.config_manager.get("customization.files", [])
                files.append(file_info)
                self.config_manager.set("customization.files", files)
                self.refresh_files()
        except Exception as e:
            log_error(e, "添加文件")

    def remove_file(self):
        """移除选中的文件"""
        try:
            current_row = self.files_table.currentRow()
            if current_row >= 0:
                self.delete_file_row(current_row)
        except Exception as e:
            log_error(e, "移除文件")

    def browse_workspace(self):
        """浏览工作空间目录"""
        try:
            directory = QFileDialog.getExistingDirectory(
                self, "选择工作空间目录", self.workspace_edit.text()
            )
            if directory:
                self.workspace_edit.setText(directory)
        except Exception as e:
            log_error(e, "浏览工作空间目录")

    def browse_iso_path(self):
        """浏览ISO输出路径"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "选择ISO输出路径",
                self.iso_path_edit.text() or "WinPE.iso",
                "ISO 文件 (*.iso)"
            )
            if file_path:
                self.iso_path_edit.setText(file_path)
        except Exception as e:
            log_error(e, "浏览ISO路径")

    def save_basic_config(self):
        """保存基本配置"""
        try:
            self.config_manager.set("winpe.architecture", self.arch_combo.currentText())
            self.config_manager.set("winpe.version", self.version_combo.currentText())
            self.config_manager.set("winpe.language", self.language_combo.currentData() or self.language_combo.currentText())

            # 保存构建设置
            build_method_text = self.build_method_combo.currentText()
            if "copype" in build_method_text:
                self.config_manager.set("winpe.build_method", "copype")
            else:
                self.config_manager.set("winpe.build_method", "dism")

            # 保存WinPE专用设置
            self.config_manager.set("winpe.enable_winpe_settings", self.enable_winpe_settings_check.isChecked())
            self.config_manager.set("winpe.scratch_space_mb", self.scratch_space_spin.value())
            self.config_manager.set("winpe.target_path", self.target_path_edit.text())

            self.config_manager.set("output.workspace", self.workspace_edit.text())
            self.config_manager.set("output.iso_path", self.iso_path_edit.text())
            self.config_manager.save_config()
            self.status_label.setText("基本配置已保存")
            self.log_message("基本配置已保存")
            self.update_build_summary()
        except Exception as e:
            log_error(e, "保存基本配置")

    def save_customization_config(self):
        """保存定制配置"""
        try:
            self.config_manager.save_config()
            self.status_label.setText("定制配置已保存")
            self.log_message("定制配置已保存")
        except Exception as e:
            log_error(e, "保存定制配置")

    def start_build(self):
        """开始构建WinPE"""
        try:
            # 检查管理员权限
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                reply = QMessageBox.question(
                    self, "需要管理员权限",
                    "WinPE构建需要管理员权限来执行DISM操作。\n\n是否以管理员身份重新启动程序？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    # 以管理员权限重新启动程序
                    try:
                        import sys
                        from pathlib import Path

                        # 获取当前程序路径
                        if hasattr(sys, 'frozen'):
                            # 打包后的exe
                            current_exe = sys.executable
                        else:
                            # Python脚本
                            current_exe = str(Path(__file__).parent.parent / "main.py")

                        # 请求管理员权限重新启动
                        ctypes.windll.shell32.ShellExecuteW(
                            None,
                            "runas",  # 以管理员身份运行
                            current_exe,
                            " ".join(sys.argv[1:]),  # 传递原有参数
                            None,
                            1
                        )

                        # 退出当前程序
                        QApplication.quit()
                        sys.exit(0)

                    except Exception as e:
                        QMessageBox.critical(
                            self, "重新启动失败",
                            f"无法以管理员身份重新启动程序。\n\n请手动右键点击程序选择'以管理员身份运行'。\n\n错误详情: {str(e)}"
                        )
                        return
                else:
                    return

            # 检查ADK状态
            adk_status = self.adk_manager.get_adk_install_status()
            if not adk_status["adk_installed"] or not adk_status["winpe_installed"]:
                QMessageBox.warning(
                    self, "构建错误",
                    "Windows ADK 或 WinPE 加载项未正确安装，无法进行构建。"
                )
                return

            # 检查copype工具
            if not adk_status["copype_path"]:
                self.log_message("⚠️ 警告: copype工具未找到，将使用传统DISM方式")
                reply = QMessageBox.question(
                    self, "copype工具缺失",
                    "未找到copype工具，这将使用较慢的传统DISM方式构建WinPE。\n\n"
                    "建议安装完整的ADK部署工具以获得最佳体验。\n\n"
                    "是否继续构建？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.No:
                    return

            # 检查并加载ADK环境
            if not adk_status["has_dandisetenv"]:
                QMessageBox.warning(
                    self, "构建错误",
                    "找不到ADK部署工具环境文件 DandISetEnv.bat，请确保ADK安装完整。"
                )
                return

            # 只有当环境未就绪时才加载环境变量
            if not adk_status["environment_ready"]:
                self.log_message("🔧 正在加载ADK环境变量（copype需要）...")
                env_loaded, env_message = self.adk_manager.load_adk_environment()
                if env_loaded:
                    self.log_message(f"✅ 环境加载: {env_message}")

                    # 重新获取ADK状态以检查copype工具
                    adk_status = self.adk_manager.get_adk_install_status()
                    if adk_status["copype_path"]:
                        self.log_message(f"🚀 copype工具已就绪: {adk_status['copype_path']}")
                    else:
                        self.log_message("⚠️ copype工具仍未找到，将使用传统DISM方式")
                else:
                    QMessageBox.warning(
                        self, "环境设置错误",
                        f"加载ADK环境失败: {env_message}\n\n"
                        "这将影响copype和DISM等工具的正常运行。\n"
                        "建议重新安装Windows ADK并确保包含部署工具。"
                    )
                    # 询问用户是否继续
                    reply = QMessageBox.question(
                        self, "环境加载失败",
                        f"ADK环境加载失败，copype工具可能无法正常工作。\n\n"
                        "是否继续使用传统DISM方式构建？\n\n"
                        f"错误详情: {env_message}",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return
                    # 不直接返回，让用户选择是否继续
            else:
                self.log_message("ADK环境已就绪，无需重复加载")

            # 检查基本配置
            iso_path = self.config_manager.get("output.iso_path", "")
            if not iso_path:
                QMessageBox.warning(
                    self, "配置错误",
                    "请先设置ISO输出路径。"
                )
                return

            # 检查ISO文件是否已存在
            from pathlib import Path
            iso_file_path = Path(iso_path)
            if iso_file_path.exists():
                reply = QMessageBox.question(
                    self, "ISO文件已存在",
                    f"ISO文件已存在:\n{iso_path}\n\n文件大小: {iso_file_path.stat().st_size / (1024*1024):.1f} MB\n创建时间: {datetime.datetime.fromtimestamp(iso_file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n\n是否覆盖现有文件？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

            # 确认开始构建
            reply = QMessageBox.question(
                self, "确认构建",
                f"即将开始构建 WinPE。\n\n输出路径: {iso_path}\n\n确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 清空构建日志
            self.build_log_text.clear()

            # 创建构建线程
            self.build_thread = BuildThread(
                self.winpe_builder,
                self.config_manager,
                iso_path
            )
            # 设置构建线程引用，以便WinPEBuilder可以检查停止状态
            self.winpe_builder._build_thread = self.build_thread
            self.build_thread.progress_signal.connect(self.on_build_progress)
            self.build_thread.log_signal.connect(self.on_build_log)
            self.build_thread.finished_signal.connect(self.on_build_finished)
            self.build_thread.error_dialog_signal.connect(self.show_build_error_dialog)
            self.build_thread.refresh_builds_signal.connect(self.refresh_builds_list)

            # 更新UI状态
            self.build_btn.setText("停止构建")
            self.build_btn.clicked.disconnect()
            self.build_btn.clicked.connect(self.stop_build)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("正在构建 WinPE...")

            # 开始构建
            self.build_thread.start()

        except Exception as e:
            log_error(e, "开始构建")
            QMessageBox.critical(self, "构建错误", f"开始构建时发生错误: {str(e)}")

    def stop_build(self):
        """停止构建"""
        try:
            if self.build_thread and self.build_thread.isRunning():
                self.build_thread.stop()
                self.build_thread.wait(5000)  # 等待5秒
                self.on_build_finished(False, "构建已停止")
        except Exception as e:
            log_error(e, "停止构建")

    def refresh_builds_list(self):
        """刷新已构建目录列表"""
        try:
            self.builds_list.clear()

            # 获取工作空间路径
            from pathlib import Path
            workspace = Path(self.config_manager.get("output.workspace", ""))
            if not workspace.exists():
                workspace = Path.cwd() / "workspace" / "WinPE_Build"

            # 查找所有WinPE构建目录
            if workspace.exists():
                winpe_builds = []
                for item in workspace.iterdir():
                    if item.is_dir() and item.name.startswith("WinPE_"):
                        try:
                            # 获取目录创建时间
                            create_time = item.stat().st_ctime
                            from datetime import datetime
                            create_dt = datetime.fromtimestamp(create_time)

                            # 检查目录大小和文件数量
                            file_count = len(list(item.rglob("*")))
                            
                            # 检查WinPE镜像文件（支持copype和传统DISM模式）
                            media_path = item / "media"
                            boot_wim = media_path / "sources" / "boot.wim" if media_path.exists() else None
                            winpe_wim = item / "winpe.wim"  # 传统DISM模式
                            
                            # 检查是否有有效的WinPE镜像文件
                            has_wim = False
                            if boot_wim and boot_wim.exists():
                                has_wim = True  # copype模式
                            elif winpe_wim and winpe_wim.exists():
                                has_wim = True  # 传统DISM模式
                            
                            has_iso = any(item.glob("*.iso"))

                            # 确定构建模式
                            build_mode = "copype" if (boot_wim and boot_wim.exists()) else "dism"
                            
                            build_info = {
                                "path": item,
                                "name": item.name,
                                "date": create_dt.strftime("%Y-%m-%d %H:%M:%S"),
                                "file_count": file_count,
                                "has_wim": has_wim,
                                "has_iso": has_iso,
                                "build_mode": build_mode,
                                "size_mb": self._get_directory_size(item) / 1024 / 1024
                            }
                            winpe_builds.append(build_info)
                        except Exception as e:
                            logger.warning(f"读取构建目录信息失败 {item}: {str(e)}")

                # 按创建时间排序
                winpe_builds.sort(key=lambda x: x["date"], reverse=True)

                # 添加到列表
                for build in winpe_builds:
                    status_parts = []
                    if build["has_wim"]:
                        status_parts.append("WIM")
                    if build["has_iso"]:
                        status_parts.append("ISO")

                    status = "已就绪" if status_parts else "不完整"
                    if status_parts:
                        status += f" ({', '.join(status_parts)})"

                    # 优化显示格式：使用更简洁的日期和状态格式
                    date_short = build['date'].split(' ')[1][:5]  # 只显示时间 HH:MM
                    size_short = f"{build['size_mb']:.0f}MB" if build['size_mb'] >= 1 else f"{build['size_mb']*1024:.0f}KB"

                    # 创建主要显示文本（包含构建模式）
                    mode_text = "copype" if build.get('build_mode') == 'copype' else "dism"
                    main_text = f"{build['name']} - {date_short} - {size_short} - {status} ({mode_text})"

                    list_item = QListWidgetItem(main_text)
                    list_item.setData(Qt.UserRole, build["path"])

                    # 设置工具提示显示完整信息
                    tooltip_info = (
                        f"完整名称: {build['name']}\n"
                        f"创建时间: {build['date']}\n"
                        f"目录大小: {build['size_mb']:.1f} MB\n"
                        f"文件数量: {build['file_count']} 个\n"
                        f"构建模式: {build.get('build_mode', 'unknown')}\n"
                        f"状态: {status}\n"
                        f"路径: {build['path']}"
                    )
                    list_item.setToolTip(tooltip_info)

                    # 根据状态设置不同的颜色
                    if status.startswith("已就绪"):
                        list_item.setForeground(QColor("#2e7d32"))  # 绿色 - 已就绪
                    elif build['has_wim']:
                        list_item.setForeground(QColor("#f57c00"))  # 橙色 - 部分完成
                    else:
                        list_item.setForeground(QColor("#d32f2f"))  # 红色 - 不完整

                    self.builds_list.addItem(list_item)

            if self.builds_list.count() == 0:
                self.builds_list.addItem("暂无已构建的目录")

        except Exception as e:
            from utils.logger import log_error
            log_error(e, "刷新构建目录列表")

    def _get_directory_size(self, directory: Path) -> int:
        """获取目录大小（字节）"""
        try:
            total_size = 0
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except Exception:
            return 0

    def delete_selected_build(self):
        """删除选中的构建目录"""
        try:
            current_item = self.builds_list.currentItem()
            if not current_item:
                QMessageBox.warning(self, "提示", "请先选择要删除的构建目录")
                return

            build_path = current_item.data(Qt.UserRole)
            if not build_path:
                return

            # 确认删除
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除构建目录吗？\n\n路径: {build_path}\n\n此操作无法撤销！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                try:
                    import shutil
                    shutil.rmtree(build_path)
                    self.log_message(f"已删除构建目录: {build_path}")
                    self.refresh_builds_list()
                    QMessageBox.information(self, "删除成功", f"构建目录已删除:\n{build_path}")
                except Exception as e:
                    error_msg = f"删除构建目录失败: {str(e)}"
                    from utils.logger import log_error
                    log_error(e, "删除构建目录")
                    QMessageBox.critical(self, "删除失败", error_msg)

        except Exception as e:
            from utils.logger import log_error
            log_error(e, "删除构建目录")

    def clear_all_builds(self):
        """清空所有构建目录"""
        try:
            # 获取所有构建目录
            from pathlib import Path
            all_builds = []
            for i in range(self.builds_list.count()):
                item = self.builds_list.item(i)
                build_path = item.data(Qt.UserRole)
                if build_path and Path(build_path).exists():
                    all_builds.append(build_path)

            if not all_builds:
                QMessageBox.information(self, "提示", "没有找到可删除的构建目录")
                return

            # 统计信息
            total_count = len(all_builds)
            total_size = 0
            try:
                import shutil
                for build_path in all_builds:
                    if Path(build_path).exists():
                        total_size += sum(f.stat().st_size for f in Path(build_path).rglob("*") if f.is_file())
            except:
                pass

            # 格式化大小显示
            if total_size > 1024 * 1024 * 1024:
                size_str = f"{total_size / (1024**3):.1f} GB"
            elif total_size > 1024 * 1024:
                size_str = f"{total_size / (1024**2):.1f} MB"
            elif total_size > 1024:
                size_str = f"{total_size / 1024:.1f} KB"
            else:
                size_str = f"{total_size} B"

            # 显示确认对话框
            confirm_msg = f"确定要删除所有构建目录吗？\n\n"
            confirm_msg += f"📁 目录数量: {total_count} 个\n"
            confirm_msg += f"💾 占用空间: 约 {size_str}\n\n"
            confirm_msg += f"⚠️ 此操作无法撤销！请确认要继续删除所有构建目录。"

            reply = QMessageBox.question(
                self, "确认清空全部",
                confirm_msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 批量删除
                success_count = 0
                failed_builds = []
                total_freed_space = 0

                self.log_message("=== 开始清空所有构建目录 ===")
                self.log_message(f"准备删除 {total_count} 个构建目录，预计释放空间: {size_str}")

                # 创建进度对话框
                from PyQt5.QtWidgets import QProgressDialog
                progress = QProgressDialog("正在删除构建目录...", "取消", 0, total_count, self)
                progress.setWindowTitle("清空构建目录")
                progress.setWindowModality(Qt.WindowModal)
                progress.show()

                try:
                    for i, build_path in enumerate(all_builds):
                        # 检查是否取消
                        if progress.wasCanceled():
                            self.log_message("⚠️ 用户取消了删除操作")
                            break

                        progress.setValue(i)
                        progress.setLabelText(f"正在删除: {Path(build_path).name}")

                        try:
                            # 计算要删除的目录大小
                            dir_size = 0
                            if Path(build_path).exists():
                                dir_size = sum(f.stat().st_size for f in Path(build_path).rglob("*") if f.is_file())

                            # 删除目录
                            shutil.rmtree(build_path)
                            success_count += 1
                            total_freed_space += dir_size

                            # 格式化目录大小
                            if dir_size > 1024 * 1024:
                                size_info = f"{dir_size / (1024**2):.1f} MB"
                            elif dir_size > 1024:
                                size_info = f"{dir_size / 1024:.1f} KB"
                            else:
                                size_info = f"{dir_size} B"

                            self.log_message(f"✅ 已删除: {Path(build_path).name} ({size_info})")

                        except Exception as e:
                            failed_builds.append((build_path, str(e)))
                            self.log_message(f"❌ 删除失败: {Path(build_path).name} - {str(e)}")

                    progress.setValue(total_count)

                    # 格式化释放的空间
                    if total_freed_space > 1024 * 1024 * 1024:
                        freed_str = f"{total_freed_space / (1024**3):.1f} GB"
                    elif total_freed_space > 1024 * 1024:
                        freed_str = f"{total_freed_space / (1024**2):.1f} MB"
                    elif total_freed_space > 1024:
                        freed_str = f"{total_freed_space / 1024:.1f} KB"
                    else:
                        freed_str = f"{total_freed_space} B"

                    # 显示结果
                    result_msg = f"✅ 清空操作完成！\n\n"
                    result_msg += f"📊 成功删除: {success_count} 个目录\n"
                    result_msg += f"💾 释放空间: {freed_str}\n"

                    if failed_builds:
                        result_msg += f"⚠️ 删除失败: {len(failed_builds)} 个目录\n\n"
                        result_msg += "失败的目录:\n"
                        for build_path, error in failed_builds[:5]:  # 只显示前5个
                            result_msg += f"• {Path(build_path).name}: {error}\n"
                        if len(failed_builds) > 5:
                            result_msg += f"• ... 还有 {len(failed_builds) - 5} 个目录失败\n"

                    self.log_message(f"=== 清空操作完成 ===")
                    self.log_message(f"成功删除 {success_count} 个目录，释放空间 {freed_str}")

                    QMessageBox.information(self, "清空完成", result_msg)

                    # 刷新列表
                    self.refresh_builds_list()

                except Exception as e:
                    error_msg = f"批量删除过程中发生错误: {str(e)}"
                    self.log_message(f"❌ {error_msg}")
                    QMessageBox.critical(self, "操作失败", error_msg)

        except Exception as e:
            from utils.logger import log_error
            log_error(e, "清空构建目录")
            QMessageBox.critical(self, "操作失败", f"清空构建目录时发生错误: {str(e)}")

    def open_selected_build(self):
        """打开选中的构建目录"""
        try:
            current_item = self.builds_list.currentItem()
            if not current_item:
                QMessageBox.warning(self, "提示", "请先选择要打开的构建目录")
                return

            build_path = current_item.data(Qt.UserRole)
            if not build_path or not build_path.exists():
                return

            # 使用系统默认程序打开目录
            import subprocess
            import platform

            if platform.system() == "Windows":
                subprocess.run(["explorer", str(build_path)])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(build_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(build_path)])

        except Exception as e:
            from utils.logger import log_error
            log_error(e, "打开构建目录")
            QMessageBox.warning(self, "打开失败", f"打开目录失败: {str(e)}")

    def on_build_progress(self, message: str, value: int):
        """构建进度更新"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def on_build_log(self, message: str):
        """构建日志更新"""
        self.build_log_text.append(message)
        # 确保总是显示最后一行
        self.build_log_text.moveCursor(self.build_log_text.textCursor().End)
        self.build_log_text.ensureCursorVisible()
        # 强制滚动到底部
        scrollbar = self.build_log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self.log_message(f"[构建] {message}")

    def show_build_error_dialog(self, error_details: str):
        """显示构建错误对话框"""
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("构建错误")
            msg_box.setText("WinPE构建过程中发生错误")
            msg_box.setDetailedText(error_details)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.setDefaultButton(QMessageBox.Ok)
            msg_box.exec_()
        except Exception as e:
            logger.error(f"显示错误对话框失败: {e}")

    def on_build_finished(self, success: bool, message: str):
        """构建完成"""
        # 恢复UI状态
        self.build_btn.setText("开始构建 WinPE")
        self.build_btn.clicked.disconnect()
        self.build_btn.clicked.connect(self.start_build)
        self.progress_bar.setVisible(False)
        self.status_label.setText("构建完成" if success else "构建失败")

        # 显示结果
        if success:
            QMessageBox.information(self, "构建完成", message)
            # 构建成功后刷新构建目录列表
            self.refresh_builds_list()
        else:
            QMessageBox.critical(self, "构建失败", message)

        self.build_thread = None

    def log_message(self, message: str):
        """添加日志消息"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"

        # 简单的文本格式（不使用HTML，保持兼容性）
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

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.log_message("=== 日志已清空 ===")

    def save_log(self):
        """保存日志"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"winpe_build_log_{timestamp}.txt"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存日志", default_name, "文本文件 (*.txt);;所有文件 (*)"
            )
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # 保存纯文本格式的日志
                    plain_text = self.log_text.toPlainText()
                    f.write(plain_text)
                    # 添加额外的信息
                    f.write(f"\n\n=== 日志保存信息 ===\n")
                    f.write(f"保存时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"程序版本: WinPE制作管理器\n")
                self.log_message(f"✅ 日志已保存到: {file_path}")
                QMessageBox.information(self, "保存成功", f"日志已保存到: {file_path}")
        except Exception as e:
            self.log_message(f"❌ 保存日志失败: {str(e)}")
            log_error(e, "保存日志")

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