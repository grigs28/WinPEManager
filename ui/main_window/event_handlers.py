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
from PyQt5.QtCore import Qt

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

    def browse_adk_path(self):
        """浏览ADK路径"""
        try:
            directory = QFileDialog.getExistingDirectory(
                self.main_window, "选择ADK安装目录", self.main_window.adk_path_edit.text()
            )
            if directory:
                self.main_window.adk_path_edit.setText(directory)
        except Exception as e:
            log_error(e, "浏览ADK路径")

    def browse_winpe_path(self):
        """浏览WinPE路径"""
        try:
            directory = QFileDialog.getExistingDirectory(
                self.main_window, "选择WinPE路径", self.main_window.winpe_path_edit.text()
            )
            if directory:
                self.main_window.winpe_path_edit.setText(directory)
        except Exception as e:
            log_error(e, "浏览WinPE路径")

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

            # 保存桌面配置
            desktop_type = self.main_window.desktop_type_combo.currentData()
            self.config_manager.set("winpe.desktop_type", desktop_type)
            self.config_manager.set("winpe.desktop_program_path", self.main_window.desktop_program_edit.text())
            self.config_manager.set("winpe.desktop_directory_path", self.main_window.desktop_directory_edit.text())

            self.config_manager.set("output.workspace", self.main_window.workspace_edit.text())
            self.config_manager.set("output.iso_path", self.main_window.iso_path_edit.text())
            
            # 立即保存配置以确保所有设置都被保存
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

    def auto_detect_desktop_on_startup(self):
        """程序启动时自动检测桌面环境"""
        try:
            from core.desktop_manager import DesktopManager
            desktop_manager = DesktopManager(self.config_manager)
            
            # 获取当前配置的桌面类型
            current_desktop_type = self.config_manager.get("winpe.desktop_type", "cairo")
            
            # 只有在桌面类型未设置时才进行自动检测
            # 如果用户明确选择了"disabled"，则不进行自动检测
            if not current_desktop_type:
                # 检查所有桌面环境类型
                desktop_types = ["cairo", "winxshell"]
                detected_desktop = None
                
                for desktop_type in desktop_types:
                    desktop_info = desktop_manager.get_desktop_info(desktop_type)
                    if desktop_info and desktop_info.get("installed", False):
                        detected_desktop = desktop_type
                        self.main_window.log_message(f"🔍 检测到已安装的桌面环境: {desktop_info['name']}")
                        break
                
                # 如果检测到桌面环境，自动设置
                if detected_desktop:
                    # 更新下拉框选择
                    for i in range(self.main_window.desktop_type_combo.count()):
                        if self.main_window.desktop_type_combo.itemData(i) == detected_desktop:
                            self.main_window.desktop_type_combo.setCurrentIndex(i)
                            break
                    
                    # 自动定位路径
                    self._auto_locate_desktop_paths(detected_desktop)
                    
                    # 保存配置
                    self.config_manager.set("winpe.desktop_type", detected_desktop)
                    self.config_manager.save_config()
                    
                    self.main_window.log_message(f"✅ 已自动设置桌面环境为: {desktop_manager.get_desktop_types()[detected_desktop]['name']}")
                else:
                    self.main_window.log_message("ℹ️ 未检测到已安装的桌面环境")
            else:
                # 如果用户已经配置了桌面环境（包括"disabled"），只进行路径自动定位（如果路径为空）
                self._auto_locate_desktop_paths(current_desktop_type)
                
                if current_desktop_type == "disabled":
                    self.main_window.log_message("ℹ️ 桌面环境已禁用")
                else:
                    desktop_name = desktop_manager.get_desktop_types().get(current_desktop_type, {}).get('name', current_desktop_type)
                    self.main_window.log_message(f"ℹ️ 使用已配置的桌面环境: {desktop_name}")
                
        except Exception as e:
            log_error(e, "程序启动时自动检测桌面环境")

    def on_desktop_type_changed(self):
        """桌面类型选择变化事件"""
        try:
            # 获取选择的桌面类型
            desktop_type = self.main_window.desktop_type_combo.currentData()
            if not desktop_type:
                return

            # 保存桌面配置
            self.config_manager.set("winpe.desktop_type", desktop_type)

            # 根据桌面类型启用/禁用控件
            is_disabled = desktop_type == "disabled"
            self.main_window.desktop_program_edit.setEnabled(not is_disabled)
            self.main_window.desktop_directory_edit.setEnabled(not is_disabled)

            # 自动定位程序和目录路径（仅在桌面类型切换时）
            # 注意：程序启动时的自动定位在auto_detect_desktop_on_startup方法中处理

            # 更新桌面状态显示
            self._update_desktop_status()

            # 记录日志
            from core.desktop_manager import DesktopManager
            desktop_manager = DesktopManager(self.config_manager)
            desktop_types = desktop_manager.get_desktop_types()
            desktop_name = desktop_types.get(desktop_type, {}).get("name", "未知")
            
            self.main_window.log_message(f"🖥️ 桌面环境已切换到: {desktop_name}")

        except Exception as e:
            log_error(e, "桌面类型切换")

    def _auto_locate_desktop_paths(self, desktop_type: str):
        """自动定位桌面环境的程序和目录路径"""
        try:
            from core.desktop_manager import DesktopManager
            desktop_manager = DesktopManager(self.config_manager)
            
            # 获取桌面信息
            desktop_info = desktop_manager.get_desktop_info(desktop_type)
            if not desktop_info or not desktop_info.get("installed", False):
                return
            
            # 获取当前配置的路径（不是UI控件的值）
            current_program_path = self.config_manager.get("winpe.desktop_program_path", "").strip()
            current_directory_path = self.config_manager.get("winpe.desktop_directory_path", "").strip()
            
            # 只有在配置路径为空时才自动定位
            if not current_program_path and desktop_info.get("executable"):
                self.main_window.desktop_program_edit.setText(desktop_info["executable"])
                self.config_manager.set("winpe.desktop_program_path", desktop_info["executable"])
                self.main_window.log_message(f"🔍 自动定位程序路径: {desktop_info['executable']}")
            else:
                # 如果配置中已有路径，使用配置的路径
                self.main_window.desktop_program_edit.setText(current_program_path)
            
            if not current_directory_path and desktop_info.get("directory"):
                self.main_window.desktop_directory_edit.setText(desktop_info["directory"])
                self.config_manager.set("winpe.desktop_directory_path", desktop_info["directory"])
                self.main_window.log_message(f"🔍 自动定位目录路径: {desktop_info['directory']}")
            else:
                # 如果配置中已有路径，使用配置的路径
                self.main_window.desktop_directory_edit.setText(current_directory_path)
                
        except Exception as e:
            log_error(e, "自动定位桌面路径")

    def browse_desktop_program(self):
        """浏览桌面程序路径"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self.main_window, "选择桌面环境主程序",
                self.main_window.desktop_program_edit.text(),
                "可执行文件 (*.exe);;所有文件 (*.*)"
            )
            if file_path:
                self.main_window.desktop_program_edit.setText(file_path)
                self.config_manager.set("winpe.desktop_program_path", file_path)
                self._update_desktop_status()
        except Exception as e:
            log_error(e, "浏览桌面程序路径")

    def browse_desktop_directory(self):
        """浏览桌面目录路径"""
        try:
            directory = QFileDialog.getExistingDirectory(
                self.main_window, "选择桌面环境目录",
                self.main_window.desktop_directory_edit.text()
            )
            if directory:
                self.main_window.desktop_directory_edit.setText(directory)
                self.config_manager.set("winpe.desktop_directory_path", directory)
                self._update_desktop_status()
        except Exception as e:
            log_error(e, "浏览桌面目录路径")

    def _update_desktop_status(self):
        """更新桌面状态显示"""
        try:
            from core.desktop_manager import DesktopManager
            desktop_manager = DesktopManager(self.config_manager)
            desktop_config = desktop_manager.get_current_desktop_config()
            
            desktop_type = desktop_config["type"]
            desktop_name = desktop_config["name"]
            
            if desktop_type == "disabled":
                status_text = "桌面环境状态: 已禁用"
                self.main_window.desktop_status_label.setStyleSheet("color: #666; font-style: italic;")
            else:
                # 获取桌面信息
                desktop_info = desktop_manager.get_desktop_info(desktop_type)
                if desktop_info and desktop_info.get("installed", False):
                    status_text = f"桌面环境状态: {desktop_name} 已安装 (版本: {desktop_info.get('version', 'Unknown')}, 大小: {desktop_info.get('size_mb', 0)} MB)"
                    self.main_window.desktop_status_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
                else:
                    status_text = f"桌面环境状态: {desktop_name} 未安装"
                    self.main_window.desktop_status_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
            
            self.main_window.desktop_status_label.setText(status_text)
            
        except Exception as e:
            log_error(e, "更新桌面状态")

    def show_desktop_config_dialog(self):
        """显示桌面环境配置对话框"""
        try:
            from ui.desktop_config_dialog import DesktopConfigDialog
            
            # 创建配置对话框
            dialog = DesktopConfigDialog(parent=self.main_window, config_manager=self.config_manager)
            
            # 显示对话框
            if dialog.exec_() == DesktopConfigDialog.Accepted:
                # 配置已保存，更新UI显示
                self._update_desktop_status()
                self.main_window.log_message("桌面环境配置已更新")
            
        except Exception as e:
            log_error(e, "显示桌面配置对话框")
            QMessageBox.warning(self.main_window, "错误", f"显示桌面配置对话框失败: {str(e)}")

    def _open_url(self, url: str):
        """打开URL"""
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            log_error(e, "打开URL")
            QMessageBox.warning(self.main_window, "错误", f"无法打开链接: {str(e)}")

    def show_wim_manager(self):
        """显示WIM管理对话框"""
        try:
            from ui.main_window.wim_manager import WIMManager
            
            # 创建WIM管理器
            wim_manager = WIMManager(self.main_window)
            
            # 显示WIM管理对话框
            wim_manager.show_wim_manager_dialog()
            
        except Exception as e:
            log_error(e, "显示WIM管理对话框")
            QMessageBox.warning(self.main_window, "错误", f"显示WIM管理对话框失败: {str(e)}")

    def make_usb_bootable(self):
        """制作USB启动盘 - 使用统一WIM管理器"""
        try:
            # 获取当前选中的构建目录
            current_item = self.main_window.builds_list.currentItem()
            if not current_item:
                QMessageBox.warning(self.main_window, "提示", "请先选择一个构建目录")
                return

            # 获取构建目录路径
            build_dir = Path(current_item.text().split(" - ")[0])

            # 检查构建目录是否存在
            if not build_dir.exists():
                QMessageBox.warning(self.main_window, "错误", f"构建目录不存在: {build_dir}")
                return

            # 选择USB驱动器
            usb_path = QFileDialog.getExistingDirectory(
                self.main_window,
                "选择USB驱动器",
                "",
                QFileDialog.ShowDirsOnly
            )

            if not usb_path:
                return

            usb_path = Path(usb_path)

            # 确认制作USB启动盘
            reply = QMessageBox.question(
                self.main_window,
                "确认制作USB启动盘",
                f"即将制作USB启动盘:\n\n"
                f"构建目录: {build_dir.name}\n"
                f"USB驱动器: {usb_path}\n\n"
                f"⚠️ 警告: 此操作将格式化USB驱动器并删除所有数据！\n\n"
                f"确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 检查管理员权限
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                reply = QMessageBox.question(
                    self.main_window,
                    "需要管理员权限",
                    "USB启动盘制作需要管理员权限。\n\n是否以管理员身份重新启动程序？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    self.restart_as_admin()
                return

            self.main_window.log_message(f"开始制作USB启动盘: {build_dir.name} -> {usb_path}")

            # 创建进度对话框
            from PyQt5.QtWidgets import QProgressDialog
            progress = QProgressDialog("正在制作USB启动盘...", "取消", 0, 100, self.main_window)
            progress.setWindowTitle("制作USB启动盘")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            try:
                # 导入新的USB线程
                from ui.main_window.usb_thread import USBBootableThread

                # 创建并启动USB制作线程
                usb_thread = USBBootableThread(
                    build_dir,
                    usb_path,
                    self.main_window,
                    self.config_manager,
                    self.adk_manager
                )
                usb_thread.progress_signal.connect(progress.setValue)
                usb_thread.finished_signal.connect(self._on_usb_finished)
                usb_thread.error_signal.connect(self._on_usb_error)
                usb_thread.start()

                # 等待线程完成 (在实际应用中，可能需要添加取消功能)
                while usb_thread.isRunning():
                    if progress.wasCanceled():
                        usb_thread.stop()
                        usb_thread.wait(3000)
                        break
                    self.main_window.thread().msleep(100)  # 短暂休眠避免CPU占用过高

                progress.close()

            except Exception as e:
                progress.close()
                log_error(e, "制作USB启动盘")
                QMessageBox.critical(self.main_window, "错误", f"制作USB启动盘时发生错误: {str(e)}")

        except Exception as e:
            log_error(e, "制作USB启动盘")
            QMessageBox.critical(self.main_window, "错误", f"制作USB启动盘时发生错误: {str(e)}")

    def _on_usb_finished(self, success: bool, message: str):
        """USB制作完成回调"""
        try:
            if success:
                QMessageBox.information(self.main_window, "制作成功", f"USB启动盘制作成功:\n{message}")
                self.main_window.log_message(f"USB启动盘制作成功: {message}")
            else:
                QMessageBox.critical(self.main_window, "制作失败", f"USB启动盘制作失败:\n{message}")
                self.main_window.log_message(f"USB启动盘制作失败: {message}")

        except Exception as e:
            log_error(e, "USB制作完成回调")
            QMessageBox.critical(self.main_window, "错误", f"处理USB制作结果时发生错误: {str(e)}")

    def _on_usb_error(self, error_message: str):
        """USB制作错误回调"""
        try:
            QMessageBox.critical(self.main_window, "操作错误", f"USB启动盘制作过程中发生错误:\n{error_message}")
            self.main_window.log_message(f"USB启动盘制作错误: {error_message}")

        except Exception as e:
            log_error(e, "USB制作错误回调")
            QMessageBox.critical(self.main_window, "错误", f"处理USB制作错误时发生错误: {str(e)}")
    
    def restart_as_admin(self):
        """以管理员身份重新启动程序"""
        try:
            import sys
            import ctypes
            from pathlib import Path
            
            # 获取当前程序路径
            if hasattr(sys, 'frozen'):
                current_exe = sys.executable
            else:
                current_exe = str(Path(__file__).parent.parent.parent / "main.py")
            
            # 请求管理员权限重新启动
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                current_exe,
                " ".join(sys.argv[1:]),
                None,
                1
            )
            
            # 退出当前程序
            from PyQt5.QtWidgets import QApplication
            QApplication.quit()
            sys.exit(0)
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "重新启动失败", f"无法以管理员身份重新启动程序: {str(e)}")
