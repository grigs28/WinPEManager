#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口辅助方法模块
提供主窗口的辅助方法和工具函数
"""

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QFont

from core.version_manager import get_version_manager
from core.changelog_manager import get_changelog_manager
from core.winpe_packages import WinPEPackages
from core.simple_icon import get_icon_manager
from utils.logger import log_error


class Helpers:
    """辅助方法类，包含各种辅助方法"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.config_manager = main_window.config_manager
        self.adk_manager = main_window.adk_manager
    
    def set_window_icon(self):
        """设置窗口图标（随机选择PNG文件）"""
        try:
            icon_manager = get_icon_manager()
            if icon_manager.has_icons():
                # 为窗口设置随机PNG图标
                from core.simple_icon import set_random_window_icon
                set_random_window_icon(self.main_window)
            else:
                from utils.logger import logger
                logger.warning("没有找到可用的PNG图标文件")
        except Exception as e:
            # 静默失败，不影响程序启动
            from utils.logger import logger
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
            from utils.logger import logger
            logger.error(f"应用按钮样式时发生错误: {str(e)}")

    def check_adk_status(self):
        """检查ADK状态"""
        try:
            # 检测ADK状态并记录日志
            status = self.adk_manager.get_adk_install_status()

            # 更新状态显示
            if status["adk_installed"] and status["winpe_installed"]:
                self.main_window.adk_status_label.setText("✓ Windows ADK 和 WinPE 加载项已正确安装")
                self.main_window.adk_status_label.setStyleSheet("color: green;")
            else:
                error_messages = []
                if not status["adk_installed"]:
                    error_messages.append("Windows ADK 未安装")
                if not status["winpe_installed"]:
                    error_messages.append("WinPE 加载项未安装")
                self.main_window.adk_status_label.setText("✗ " + "，".join(error_messages))
                self.main_window.adk_status_label.setStyleSheet("color: red;")

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

            self.main_window.adk_details_label.setText("\n".join(details))

            # 更新路径编辑框
            self.main_window.adk_path_edit.setText(status["adk_path"])
            self.main_window.winpe_path_edit.setText(status["winpe_path"])

            # 更新架构选择
            current_arch = self.main_window.arch_combo.currentText()
            self.main_window.arch_combo.clear()
            self.main_window.arch_combo.addItems(status["available_architectures"] or ["amd64"])
            index = self.main_window.arch_combo.findText(current_arch)
            if index >= 0:
                self.main_window.arch_combo.setCurrentIndex(index)

        except Exception as e:
            log_error(e, "检查ADK状态")
            self.main_window.adk_status_label.setText(f"检查ADK状态时发生错误: {str(e)}")
            self.main_window.adk_status_label.setStyleSheet("color: red;")

    def test_dism_tool(self):
        """测试DISM工具是否正常工作"""
        try:
            # 检查当前环境是否就绪
            status = self.adk_manager.get_adk_install_status()

            if not status["environment_ready"]:
                self.main_window.log_message("环境未就绪，正在加载ADK环境变量...")
                env_loaded, env_message = self.adk_manager.load_adk_environment()
                if not env_loaded:
                    self.main_window.log_message(f"警告: {env_message}")
                    QMessageBox.warning(
                        self.main_window, "环境加载失败",
                        f"无法加载ADK环境: {env_message}\n\n这可能影响DISM工具测试。"
                    )
                    return
                else:
                    self.main_window.log_message(f"环境加载: {env_message}")
            else:
                self.main_window.log_message("环境已就绪，直接测试DISM工具")

            # 获取DISM路径
            dism_path = self.adk_manager.get_dism_path()
            if not dism_path:
                QMessageBox.warning(self.main_window, "错误", "找不到DISM工具")
                return

            # 测试DISM命令
            success, stdout, stderr = self.adk_manager.run_dism_command(["/online", "/get-featureinfo", "/featurename:NetFx3"])

            if success:
                QMessageBox.information(
                    self.main_window, "DISM测试成功",
                    f"DISM工具工作正常！\n\n路径: {dism_path}\n\n输出信息已记录到日志。"
                )
                self.main_window.log_message("DISM工具测试成功")
                if stdout and stdout.strip():
                    self.main_window.log_message(f"DISM输出: {stdout.strip()}")
            else:
                error_msg = f"DISM工具测试失败:\n\n{stderr if stderr else '未知错误'}"
                QMessageBox.warning(self.main_window, "DISM测试失败", error_msg)
                self.main_window.log_message(f"DISM工具测试失败: {stderr if stderr else '未知错误'}")

        except Exception as e:
            error_msg = f"测试DISM工具时发生错误: {str(e)}"
            log_error(e, "测试DISM工具")
            QMessageBox.critical(self.main_window, "错误", error_msg)

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

            QMessageBox.about(self.main_window, "关于 WinPE制作管理器", about_text)

        except Exception as e:
            log_error(e, "显示关于对话框")
            QMessageBox.critical(self.main_window, "错误", f"显示关于对话框失败: {str(e)}")

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
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit
            dialog = QDialog(self.main_window)
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
            from ui.button_styler import apply_3d_button_style
            apply_3d_button_style(refresh_btn)  # 应用蓝色立体样式
            button_layout.addWidget(refresh_btn)

            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.accept)
            from ui.button_styler import apply_3d_button_style_alternate
            apply_3d_button_style_alternate(close_btn)  # 应用绿色立体样式
            button_layout.addWidget(close_btn)

            layout.addLayout(button_layout)

            # 显示对话框
            dialog.exec_()

        except Exception as e:
            log_error(e, "显示变更日志对话框")
            QMessageBox.critical(self.main_window, "错误", f"显示变更日志失败: {str(e)}")

    def _refresh_changelog(self, text_edit):
        """刷新变更日志显示"""
        try:
            changelog_manager = get_changelog_manager()
            changelog_content = changelog_manager.changelog_path.read_text(encoding='utf-8')
            text_edit.setPlainText(changelog_content)
            self.main_window.log_message("变更日志已刷新")
        except Exception as e:
            log_error(e, "刷新变更日志")
            QMessageBox.warning(self.main_window, "警告", f"刷新变更日志失败: {str(e)}")

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

            self.main_window.icon_info_label.setText(info_text)

        except Exception as e:
            self.main_window.icon_info_label.setText(f"获取图标信息失败: {str(e)}")

    def update_build_summary(self):
        """更新构建配置摘要"""
        summary_lines = []
        summary_lines.append(f"WinPE 版本: {self.config_manager.get('winpe.version', '10')}")
        summary_lines.append(f"架构: {self.config_manager.get('winpe.architecture', 'amd64')}")
        # 获取语言名称
        language_code = self.config_manager.get('winpe.language', 'zh-CN')
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

        self.main_window.build_summary_text.setText("\n".join(summary_lines))

    def refresh_customization_data(self):
        """刷新定制数据"""
        # 确保语言包与选择的语言同步
        self.sync_language_packages()

        self.main_window.refresh_packages()
        self.main_window.refresh_drivers()
        self.main_window.refresh_scripts()
        self.main_window.refresh_files()

    def sync_language_packages(self):
        """同步语言包选择"""
        try:
            # 获取当前选择的语言
            current_language_code = self.main_window.language_combo.currentData()
            if not current_language_code:
                return

            # 获取语言相关的包
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
            self.main_window.components_tree.build_tree()

            # 恢复之前的选择状态
            selected_packages = self.config_manager.get("customization.packages", [])
            if selected_packages:
                self.main_window.components_tree.select_components(selected_packages)

        except Exception as e:
            log_error(e, "刷新可选组件列表")

    def refresh_drivers(self):
        """刷新驱动程序列表"""
        try:
            drivers = self.config_manager.get("customization.drivers", [])
            self.main_window.drivers_table.setRowCount(len(drivers))
            for row, driver in enumerate(drivers):
                self.main_window.drivers_table.setItem(row, 0, QTableWidgetItem(driver.get("path", "")))
                self.main_window.drivers_table.setItem(row, 1, QTableWidgetItem(driver.get("description", "")))

                # 删除按钮
                from PyQt5.QtWidgets import QPushButton
                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda checked, r=row: self.main_window.delete_driver_row(r))
                from ui.button_styler import apply_3d_button_style_red
                apply_3d_button_style_red(delete_btn)  # 应用红色立体样式
                self.main_window.drivers_table.setCellWidget(row, 2, delete_btn)

        except Exception as e:
            log_error(e, "刷新驱动程序列表")

    def refresh_scripts(self):
        """刷新脚本列表"""
        try:
            scripts = self.config_manager.get("customization.scripts", [])
            self.main_window.scripts_table.setRowCount(len(scripts))

            for row, script in enumerate(scripts):
                self.main_window.scripts_table.setItem(row, 0, QTableWidgetItem(script.get("path", "")))
                self.main_window.scripts_table.setItem(row, 1, QTableWidgetItem(script.get("description", "")))

                # 删除按钮
                from PyQt5.QtWidgets import QPushButton
                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda checked, r=row: self.main_window.delete_script_row(r))
                from ui.button_styler import apply_3d_button_style_red
                apply_3d_button_style_red(delete_btn)  # 应用红色立体样式
                self.main_window.scripts_table.setCellWidget(row, 2, delete_btn)

        except Exception as e:
            log_error(e, "刷新脚本列表")

    def refresh_files(self):
        """刷新文件列表"""
        try:
            files = self.config_manager.get("customization.files", [])
            self.main_window.files_table.setRowCount(len(files))

            for row, file_info in enumerate(files):
                self.main_window.files_table.setItem(row, 0, QTableWidgetItem(file_info.get("path", "")))
                self.main_window.files_table.setItem(row, 1, QTableWidgetItem(file_info.get("description", "")))

                # 删除按钮
                from PyQt5.QtWidgets import QPushButton
                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda checked, r=row: self.main_window.delete_file_row(r))
                from ui.button_styler import apply_3d_button_style_red
                apply_3d_button_style_red(delete_btn)  # 应用红色立体样式
                self.main_window.files_table.setCellWidget(row, 2, delete_btn)

        except Exception as e:
            log_error(e, "刷新文件列表")