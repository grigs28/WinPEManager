#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口事件处理模块
提供主窗口各种事件的处理方法
"""

import datetime
from pathlib import Path

from PyQt5.QtWidgets import QMessageBox, QFileDialog
from PyQt5.QtGui import QColor

from ui.config_dialogs import DriverDialog, ScriptDialog
from ui.button_styler import apply_3d_button_style, apply_3d_button_style_alternate, apply_3d_button_style_red
from utils.logger import log_error


class EventHandlers:
    """事件处理器类，包含所有事件处理方法"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.config_manager = main_window.config_manager
    
    def on_language_changed(self):
        """语言选择变化事件"""
        try:
            # 获取选择的语言代码
            current_language_code = self.main_window.language_combo.currentData()
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
            if hasattr(self.main_window, 'components_tree'):
                self.main_window.refresh_packages()

            # 更新构建摘要
            self.main_window.update_build_summary()

            # 记录详细的日志
            language_info = winpe_packages.get_language_info(current_language_code)
            language_name = language_info["name"] if language_info else current_language_code
            self.main_window.log_message(f"🌐 语言已切换到: {language_name} ({current_language_code})")

            if language_packages:
                self.main_window.log_message(f"📦 自动添加语言支持包 ({len(language_packages)}个):")
                for i, package in enumerate(language_packages, 1):
                    self.main_window.log_message(f"   {i}. {package}")

                # 区分语言包和其他组件
                all_packages = set(self.config_manager.get("customization.packages", []))
                non_language_packages = all_packages - set(language_packages)
                if non_language_packages:
                    self.main_window.log_message(f"📋 其他可选组件 ({len(non_language_packages)}个): {', '.join(list(non_language_packages)[:3])}{'...' if len(non_language_packages) > 3 else ''}")
                else:
                    self.main_window.log_message("📋 暂无其他可选组件")

                self.main_window.log_message(f"📊 组件总数: {len(all_packages)} 个 (语言包: {len(language_packages)}, 其他: {len(non_language_packages)})")
            else:
                self.main_window.log_message(f"⚠️ 语言 {language_name} 无需额外的语言支持包")

        except Exception as e:
            from utils.logger import log_error
            log_error(e, "语言切换")
            QMessageBox.warning(self.main_window, "警告", f"语言切换失败: {str(e)}")

    def on_tab_changed(self, index):
        """标签页切换事件"""
        if index == 2:  # 构建标签页
            self.main_window.update_build_summary()

    def on_tree_selection_changed(self, selected_components):
        """树形控件选择变化事件"""
        try:
            selected_packages = list(selected_components.keys())
            self.config_manager.set("customization.packages", selected_packages)
        except Exception as e:
            log_error(e, "树形控件选择变化")

    def on_package_changed(self):
        """可选组件选择变化事件"""
        try:
            selected_components = self.main_window.components_tree.get_selected_components()
            selected_packages = list(selected_components.keys())
            self.config_manager.set("customization.packages", selected_packages)
        except Exception as e:
            log_error(e, "可选组件选择变化")

    def browse_workspace(self):
        """浏览工作空间目录"""
        try:
            directory = QFileDialog.getExistingDirectory(
                self.main_window, "选择工作空间目录", self.main_window.workspace_edit.text()
            )
            if directory:
                self.main_window.workspace_edit.setText(directory)
        except Exception as e:
            log_error(e, "浏览工作空间目录")

    def browse_iso_path(self):
        """浏览ISO输出路径"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self.main_window, "选择ISO输出路径",
                self.main_window.iso_path_edit.text() or "WinPE.iso",
                "ISO 文件 (*.iso)"
            )
            if file_path:
                self.main_window.iso_path_edit.setText(file_path)
        except Exception as e:
            log_error(e, "浏览ISO路径")

    def save_basic_config(self):
        """保存基本配置"""
        try:
            self.config_manager.set("winpe.architecture", self.main_window.arch_combo.currentText())
            self.config_manager.set("winpe.version", self.main_window.version_combo.currentText())
            self.config_manager.set("winpe.language", self.main_window.language_combo.currentData() or self.main_window.language_combo.currentText())

            # 保存构建设置
            build_method_text = self.main_window.build_method_combo.currentText()
            if "copype" in build_method_text:
                self.config_manager.set("winpe.build_method", "copype")
            else:
                self.config_manager.set("winpe.build_method", "dism")

            # 保存WinPE专用设置
            self.config_manager.set("winpe.enable_winpe_settings", self.main_window.enable_winpe_settings_check.isChecked())
            self.config_manager.set("winpe.scratch_space_mb", self.main_window.scratch_space_spin.value())
            self.config_manager.set("winpe.target_path", self.main_window.target_path_edit.text())

            self.config_manager.set("output.workspace", self.main_window.workspace_edit.text())
            self.config_manager.set("output.iso_path", self.main_window.iso_path_edit.text())
            self.config_manager.save_config()
            self.main_window.status_label.setText("基本配置已保存")
            self.main_window.log_message("基本配置已保存")
            self.main_window.update_build_summary()
        except Exception as e:
            log_error(e, "保存基本配置")

    def save_customization_config(self):
        """保存定制配置"""
        try:
            self.config_manager.save_config()
            self.main_window.status_label.setText("定制配置已保存")
            self.main_window.log_message("定制配置已保存")
        except Exception as e:
            log_error(e, "保存定制配置")

    def add_driver(self):
        """添加驱动程序"""
        try:
            dialog = DriverDialog(self.main_window)
            if dialog.exec_() == DriverDialog.Accepted:
                driver_path, description = dialog.get_driver_info()
                if driver_path:
                    self.config_manager.add_driver(driver_path, description)
                    self.main_window.refresh_drivers()
        except Exception as e:
            log_error(e, "添加驱动程序")

    def remove_driver(self):
        """移除选中的驱动程序"""
        try:
            current_row = self.main_window.drivers_table.currentRow()
            if current_row >= 0:
                self.delete_driver_row(current_row)
        except Exception as e:
            log_error(e, "移除驱动程序")

    def delete_driver_row(self, row):
        """删除驱动行"""
        try:
            driver_path = self.main_window.drivers_table.item(row, 0).text()
            self.config_manager.remove_driver(driver_path)
            self.main_window.refresh_drivers()
        except Exception as e:
            log_error(e, "删除驱动行")

    def add_script(self):
        """添加脚本"""
        try:
            dialog = ScriptDialog(self.main_window)
            if dialog.exec_() == ScriptDialog.Accepted:
                script_path, description = dialog.get_script_info()
                if script_path:
                    self.config_manager.add_script(script_path, description)
                    self.main_window.refresh_scripts()
        except Exception as e:
            log_error(e, "添加脚本")

    def remove_script(self):
        """移除选中的脚本"""
        try:
            current_row = self.main_window.scripts_table.currentRow()
            if current_row >= 0:
                self.delete_script_row(current_row)
        except Exception as e:
            log_error(e, "移除脚本")

    def delete_script_row(self, row):
        """删除脚本行"""
        try:
            scripts = self.config_manager.get("customization.scripts", [])
            if 0 <= row < len(scripts):
                scripts.pop(row)
                self.config_manager.set("customization.scripts", scripts)
                self.main_window.refresh_scripts()
        except Exception as e:
            log_error(e, "删除脚本行")

    def add_file(self):
        """添加文件"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self.main_window, "选择要添加的文件", "", "所有文件 (*.*)"
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
                self.main_window.refresh_files()
        except Exception as e:
            log_error(e, "添加文件")

    def remove_file(self):
        """移除选中的文件"""
        try:
            current_row = self.main_window.files_table.currentRow()
            if current_row >= 0:
                self.delete_file_row(current_row)
        except Exception as e:
            log_error(e, "移除文件")

    def delete_file_row(self, row):
        """删除文件行"""
        try:
            files = self.config_manager.get("customization.files", [])
            if 0 <= row < len(files):
                files.pop(row)
                self.config_manager.set("customization.files", files)
                self.main_window.refresh_files()
        except Exception as e:
            log_error(e, "删除文件行")

    def search_components(self, keyword):
        """搜索组件"""
        try:
            if keyword.strip():
                self.main_window.components_tree.search_components(keyword.strip())
            else:
                self.main_window.components_tree.clear_search_highlight()
        except Exception as e:
            log_error(e, "搜索组件")

    def select_recommended_components(self):
        """选择推荐组件"""
        try:
            self.main_window.components_tree.select_recommended_components()
            # 更新配置
            self.on_package_changed()
        except Exception as e:
            log_error(e, "选择推荐组件")

    def clear_component_selection(self):
        """清空组件选择"""
        try:
            self.main_window.components_tree.clear_selection()
            # 更新配置
            self.on_package_changed()
        except Exception as e:
            log_error(e, "清空组件选择")
