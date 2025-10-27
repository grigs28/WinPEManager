#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口构建管理模块
提供WinPE构建相关的管理方法
"""

import datetime
import shutil
import ctypes
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt

from ui.build.build_thread import BuildThread
from ui.button_styler import apply_3d_button_style, apply_3d_button_style_alternate, apply_3d_button_style_red
from ui.shared.wim_operations_common import WIMOperationsCommon
from utils.logger import log_error


class BuildManagers:
    """构建管理器类，包含所有构建相关的方法"""

    def __init__(self, main_window):
        self.main_window = main_window
        self.config_manager = main_window.config_manager
        self.adk_manager = main_window.adk_manager
        self.winpe_builder = main_window.winpe_builder

        # 初始化共享的WIM操作功能
        self.wim_ops_common = WIMOperationsCommon(main_window, self.config_manager, self.adk_manager)

        # 设置刷新回调，用于操作完成后刷新构建目录列表
        self.wim_ops_common.add_refresh_callback(self.refresh_builds_list)

        # 为开始构建页面设置WIM操作日志回调，直接使用主窗口的日志
        # 因为在开始构建页面，操作日志应该显示在构建日志中
        self.wim_ops_common.set_wim_log_callback(lambda msg, level: None)  # 不需要额外回调，已经在unified_log_message中处理

    def start_build(self):
        """开始构建WinPE"""
        try:
            # 检查管理员权限
            if not ctypes.windll.shell32.IsUserAnAdmin():
                reply = QMessageBox.question(
                    self.main_window, "需要管理员权限",
                    "WinPE构建需要管理员权限来执行DISM操作。\n\n是否以管理员身份重新启动程序？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    # 以管理员权限重新启动程序
                    try:
                        import sys

                        # 获取当前程序路径
                        if hasattr(sys, 'frozen'):
                            # 打包后的exe
                            current_exe = sys.executable
                        else:
                            # Python脚本
                            current_exe = str(Path(__file__).parent.parent.parent / "main.py")

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
                        from PyQt5.QtWidgets import QApplication
                        QApplication.quit()
                        sys.exit(0)

                    except Exception as e:
                        QMessageBox.critical(
                            self.main_window, "重新启动失败",
                            f"无法以管理员身份重新启动程序。\n\n请手动右键点击程序选择'以管理员身份运行'。\n\n错误详情: {str(e)}"
                        )
                        return
                else:
                    return

            # 检查ADK状态
            adk_status = self.adk_manager.get_adk_install_status()
            if not adk_status["adk_installed"] or not adk_status["winpe_installed"]:
                QMessageBox.warning(
                    self.main_window, "构建错误",
                    "Windows ADK 或 WinPE 加载项未正确安装，无法进行构建。"
                )
                return

            # 检查copype工具
            if not adk_status["copype_path"]:
                self.main_window.log_message("⚠️ 警告: copype工具未找到，将使用传统DISM方式")
                reply = QMessageBox.question(
                    self.main_window, "copype工具缺失",
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
                    self.main_window, "构建错误",
                    "找不到ADK部署工具环境文件 DandISetEnv.bat，请确保ADK安装完整。"
                )
                return

            # 只有当环境未就绪时才加载环境变量
            if not adk_status["environment_ready"]:
                self.main_window.log_message("🔧 正在加载ADK环境变量（copype需要）...")
                env_loaded, env_message = self.adk_manager.load_adk_environment()
                if env_loaded:
                    self.main_window.log_message(f"✅ 环境加载: {env_message}")

                    # 重新获取ADK状态以检查copype工具
                    adk_status = self.adk_manager.get_adk_install_status()
                    if adk_status["copype_path"]:
                        self.main_window.log_message(f"🚀 copype工具已就绪: {adk_status['copype_path']}")
                    else:
                        self.main_window.log_message("⚠️ copype工具仍未找到，将使用传统DISM方式")
                else:
                    QMessageBox.warning(
                        self.main_window, "环境设置错误",
                        f"加载ADK环境失败: {env_message}\n\n"
                        "这将影响copype和DISM等工具的正常运行。\n"
                        "建议重新安装Windows ADK并确保包含部署工具。"
                    )
                    # 询问用户是否继续
                    reply = QMessageBox.question(
                        self.main_window, "环境加载失败",
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
                self.main_window.log_message("ADK环境已就绪，无需重复加载")

            # 检查基本配置
            iso_path = self.config_manager.get("output.iso_path", "")
            if not iso_path:
                QMessageBox.warning(
                    self.main_window, "配置错误",
                    "请先设置ISO输出路径。"
                )
                return

            # 检查ISO文件是否已存在
            iso_file_path = Path(iso_path)
            if iso_file_path.exists():
                reply = QMessageBox.question(
                    self.main_window, "ISO文件已存在",
                    f"ISO文件已存在:\n{iso_path}\n\n文件大小: {iso_file_path.stat().st_size / (1024*1024):.1f} MB\n创建时间: {datetime.datetime.fromtimestamp(iso_file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n\n是否覆盖现有文件？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

            # 确认开始构建
            reply = QMessageBox.question(
                self.main_window, "确认构建",
                f"即将开始构建 WinPE。\n\n输出路径: {iso_path}\n\n确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 清空构建日志
            self.main_window.build_log_text.clear()

            # 创建构建线程
            self.main_window.build_thread = BuildThread(
                self.winpe_builder,
                self.config_manager,
                iso_path
            )
            # 设置构建线程引用，以便WinPEBuilder可以检查停止状态
            self.winpe_builder._build_thread = self.main_window.build_thread
            self.main_window.build_thread.progress_signal.connect(self.main_window.on_build_progress)
            self.main_window.build_thread.log_signal.connect(self.main_window.on_build_log)
            self.main_window.build_thread.finished_signal.connect(self.main_window.on_build_finished)
            self.main_window.build_thread.error_dialog_signal.connect(self.main_window.show_build_error_dialog)
            self.main_window.build_thread.refresh_builds_signal.connect(self.main_window.refresh_builds_list)

            # 更新UI状态
            self.main_window.build_btn.setText("停止构建")
            self.main_window.build_btn.clicked.disconnect()
            self.main_window.build_btn.clicked.connect(self.stop_build)
            self.main_window.progress_bar.setVisible(True)
            self.main_window.progress_bar.setValue(0)
            self.main_window.status_label.setText("正在构建 WinPE...")

            # 开始构建
            self.main_window.build_thread.start()

        except Exception as e:
            log_error(e, "开始构建")
            QMessageBox.critical(self.main_window, "构建错误", f"开始构建时发生错误: {str(e)}")

    def stop_build(self):
        """停止构建"""
        try:
            if self.main_window.build_thread and self.main_window.build_thread.isRunning():
                self.main_window.build_thread.stop()
                self.main_window.build_thread.wait(5000)  # 等待5秒
                self.main_window.on_build_finished(False, "构建已停止")
        except Exception as e:
            log_error(e, "停止构建")

    def refresh_builds_list(self):
        """使用共享功能刷新已构建目录中的WIM文件列表"""
        try:
            # 使用共享的WIM操作功能刷新列表
            self.wim_ops_common.refresh_wim_list(self.main_window.builds_list)
        except Exception as e:
            from utils.logger import log_error
            log_error(e, "刷新构建目录WIM文件列表")

    def _scan_workspace_for_wim_files(self, workspace: Path, wim_manager) -> list:
        """扫描工作空间中所有构建目录的WIM文件

        Args:
            workspace: 工作空间路径
            wim_manager: UnifiedWIMManager实例

        Returns:
            list: 所有找到的WIM文件信息
        """
        all_wim_files = []

        try:
            # 遍历工作空间中的所有子目录
            for build_dir in workspace.iterdir():
                # 只处理目录
                if not build_dir.is_dir():
                    continue

                # 跳过特殊目录（如mount目录）
                if build_dir.name in ['mount', 'temp', 'logs']:
                    continue

                # 检查是否是构建目录（包含WIM文件）
                wim_files_in_dir = wim_manager.find_wim_files(build_dir)
                if wim_files_in_dir:
                    all_wim_files.extend(wim_files_in_dir)

        except Exception as e:
            from utils.logger import log_error
            log_error(e, "扫描工作空间WIM文件")

        return all_wim_files

    # 删除这些重复的函数，因为UnifiedWIMManager已经提供了相应的功能

    def on_build_item_double_clicked(self, item):
        """构建列表项双击事件，仿照WIM管理的逻辑"""
        try:
            from PyQt5.QtCore import Qt
            wim_file = item.data(Qt.UserRole)
            if not wim_file:
                return

            # 如果已挂载，打开挂载目录
            if wim_file["mount_status"]:
                # 使用WIM文件所在目录的mount子目录
                wim_file_path = Path(wim_file["path"])
                mount_dir = wim_file_path.parent / "mount"

                if mount_dir.exists():
                    # 打开文件管理器
                    import subprocess
                    import platform

                    if platform.system() == "Windows":
                        subprocess.run(['explorer', str(mount_dir)])
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(['open', str(mount_dir)])
                    else:  # Linux
                        subprocess.run(['xdg-open', str(mount_dir)])

                    self.main_window.log_message(f"已打开挂载目录: {mount_dir}")
                else:
                    QMessageBox.warning(self.main_window, "提示", f"挂载目录不存在: {mount_dir}")
            else:
                # 如果未挂载，提示用户
                from PyQt5.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self.main_window, "提示",
                    f"WIM文件 {wim_file['name']} 未挂载。\n\n是否要打开文件所在的构建目录？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    # 打开WIM文件所在的构建目录
                    build_dir = wim_file["build_dir"]
                    import subprocess
                    import platform

                    if platform.system() == "Windows":
                        subprocess.run(['explorer', str(build_dir)])
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(['open', str(build_dir)])
                    else:  # Linux
                        subprocess.run(['xdg-open', str(build_dir)])

                    self.main_window.log_message(f"已打开构建目录: {build_dir}")

        except Exception as e:
            from utils.logger import log_error
            log_error(e, "双击构建列表项")
            QMessageBox.critical(self.main_window, "错误", f"双击操作时发生错误: {str(e)}")

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
            current_item = self.main_window.builds_list.currentItem()
            if not current_item:
                QMessageBox.warning(self.main_window, "提示", "请先选择要删除的构建目录")
                return

            # 从数据中获取构建目录路径
            # 使用完整的Qt.UserRole路径避免作用域问题
            from PyQt5.QtCore import Qt
            wim_file = current_item.data(Qt.UserRole)
            if not wim_file or not isinstance(wim_file, dict):
                QMessageBox.warning(self.main_window, "错误", "无效的构建目录数据")
                return

            build_path = wim_file.get("build_dir")
            if not build_path:
                QMessageBox.warning(self.main_window, "错误", "无法获取构建目录路径")
                return

            # 安全检查：确保不是工作空间目录
            configured_workspace = self.config_manager.get("output.workspace", "").strip()
            if configured_workspace:
                workspace = Path(configured_workspace)
            else:
                architecture = self.config_manager.get("winpe.architecture", "amd64")
                workspace = Path.cwd() / f"WinPE_{architecture}"

            build_path_obj = Path(build_path)
            if build_path_obj == workspace or build_path_obj == Path.cwd():
                QMessageBox.critical(self.main_window, "安全错误",
                    f"检测到尝试删除工作空间目录，操作已阻止！\n\n"
                    f"目标路径: {build_path}\n"
                    f"工作空间: {workspace}\n\n"
                    f"为保护数据安全，此操作已被禁止。")
                from utils.logger import log_error
                log_error(f"阻止删除工作空间目录: {build_path}", "安全检查")
                return

            # 确认删除
            reply = QMessageBox.question(
                self.main_window, "确认删除",
                f"确定要删除构建目录吗？\n\n路径: {build_path}\n\n此操作无法撤销！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                try:
                    # 使用强制删除功能处理Windows文件锁定问题
                    from utils.file_utils import force_remove_tree
                    from PyQt5.QtWidgets import QProgressDialog, QApplication

                    # 创建进度对话框
                    progress_dialog = QProgressDialog("正在删除构建目录...", "取消", 0, 0, self.main_window)
                    progress_dialog.setWindowModality(Qt.WindowModal)
                    progress_dialog.show()
                    QApplication.processEvents()  # 确保对话框显示

                    def progress_callback(message):
                        self.main_window.log_message(f"删除进度: {message}")

                    try:
                        success = force_remove_tree(build_path, max_retries=3, delay=1.0,
                                                   progress_callback=progress_callback)
                        progress_dialog.close()

                        if success:
                            self.main_window.log_message(f"已删除构建目录: {build_path}")
                            self.refresh_builds_list()
                            QMessageBox.information(self.main_window, "删除成功", f"构建目录已删除:\n{build_path}")
                        else:
                            error_msg = "删除失败，请检查是否有其他程序正在使用这些文件"
                            QMessageBox.critical(self.main_window, "删除失败", error_msg)

                    except Exception as e:
                        progress_dialog.close()
                        error_msg = f"删除构建目录失败: {str(e)}"
                        from utils.logger import log_error
                        log_error(e, "删除构建目录")
                        QMessageBox.critical(self.main_window, "删除失败", error_msg)

                except Exception as e:
                    from utils.logger import log_error
                    log_error(e, "删除构建目录")

        except Exception as e:
            from utils.logger import log_error
            log_error(e, "删除构建目录")

    def clear_all_builds(self):
        """清空所有构建目录（仅WinPE_开头的目录）"""
        try:
            # 获取工作空间路径
            configured_workspace = self.config_manager.get("output.workspace", "").strip()
            if configured_workspace:
                workspace = Path(configured_workspace)
            else:
                architecture = self.config_manager.get("winpe.architecture", "amd64")
                workspace = Path.cwd() / f"WinPE_{architecture}"

            # 安全检查：获取所有WinPE_开头的构建目录
            all_builds = []
            from PyQt5.QtCore import Qt
            for i in range(self.main_window.builds_list.count()):
                item = self.main_window.builds_list.item(i)
                wim_file = item.data(Qt.UserRole)
                if wim_file and isinstance(wim_file, dict):
                    build_path = wim_file.get("build_dir")
                    if build_path and Path(build_path).exists():
                        build_path_obj = Path(build_path)
                        # 只处理WinPE_开头的目录
                        if build_path_obj.name.startswith("WinPE_"):
                            # 额外安全检查：确保不删除工作空间本身
                            if build_path_obj != workspace and build_path_obj != Path.cwd():
                                all_builds.append(build_path)
                            else:
                                self.main_window.log_message(f"⚠️ 跳过受保护的目录: {build_path}")
                        else:
                            self.main_window.log_message(f"⚠️ 跳过非WinPE目录: {build_path}")

            if not all_builds:
                QMessageBox.information(self.main_window, "提示", "没有找到可删除的构建目录")
                return

            # 统计信息
            total_count = len(all_builds)
            total_size = 0
            try:
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
                self.main_window, "确认清空全部",
                confirm_msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 批量删除
                success_count = 0
                failed_builds = []
                total_freed_space = 0

                self.main_window.log_message("=== 开始清空所有构建目录 ===")
                self.main_window.log_message(f"准备删除 {total_count} 个构建目录，预计释放空间: {size_str}")

                # 创建进度对话框
                progress = QProgressDialog("正在删除构建目录...", "取消", 0, total_count, self.main_window)
                progress.setWindowTitle("清空构建目录")
                progress.setWindowModality(Qt.WindowModal)
                progress.show()

                try:
                    for i, build_path in enumerate(all_builds):
                        # 检查是否取消
                        if progress.wasCanceled():
                            self.main_window.log_message("⚠️ 用户取消了删除操作")
                            break

                        progress.setValue(i)
                        progress.setLabelText(f"正在删除: {Path(build_path).name}")

                        try:
                            # 计算要删除的目录大小
                            dir_size = 0
                            if Path(build_path).exists():
                                dir_size = sum(f.stat().st_size for f in Path(build_path).rglob("*") if f.is_file())

                            # 使用强制删除功能
                            from utils.file_utils import force_remove_tree

                            def progress_callback(message):
                                self.main_window.log_message(f"  📝 {message}")

                            success = force_remove_tree(build_path, max_retries=2, delay=0.5,
                                                       progress_callback=progress_callback)

                            if success:
                                success_count += 1
                                total_freed_space += dir_size

                                # 格式化目录大小
                                if dir_size > 1024 * 1024:
                                    size_info = f"{dir_size / (1024**2):.1f} MB"
                                elif dir_size > 1024:
                                    size_info = f"{dir_size / 1024:.1f} KB"
                                else:
                                    size_info = f"{dir_size} B"

                                self.main_window.log_message(f"✅ 已删除: {Path(build_path).name} ({size_info})")
                            else:
                                failed_builds.append((build_path, "强制删除失败"))
                                self.main_window.log_message(f"❌ 删除失败: {Path(build_path).name} - 强制删除失败")

                        except Exception as e:
                            failed_builds.append((build_path, str(e)))
                            self.main_window.log_message(f"❌ 删除失败: {Path(build_path).name} - {str(e)}")

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

                    self.main_window.log_message(f"=== 清空操作完成 ===")
                    self.main_window.log_message(f"成功删除 {success_count} 个目录，释放空间 {freed_str}")

                    QMessageBox.information(self.main_window, "清空完成", result_msg)

                    # 刷新列表
                    self.refresh_builds_list()

                except Exception as e:
                    error_msg = f"批量删除过程中发生错误: {str(e)}"
                    self.main_window.log_message(f"❌ {error_msg}")
                    QMessageBox.critical(self.main_window, "操作失败", error_msg)

        except Exception as e:
            from utils.logger import log_error
            log_error(e, "清空构建目录")
            QMessageBox.critical(self.main_window, "操作失败", f"清空构建目录时发生错误: {str(e)}")

    def open_selected_build(self):
        """打开选中的构建目录"""
        try:
            # 使用共享的WIM操作功能
            wim_file = self.wim_ops_common.get_selected_wim_info(self.main_window.builds_list)
            if not wim_file:
                self.wim_ops_common.show_warning("提示", "请先选择要打开的构建目录")
                return

            build_path = wim_file.get("build_dir")
            if not build_path or not Path(build_path).exists():
                return

            # 使用共享功能打开目录
            self.wim_ops_common.open_directory(Path(build_path))

        except Exception as e:
            log_error(e, "打开构建目录")
            self.wim_ops_common.show_critical("打开失败", f"打开目录失败: {str(e)}")

    def on_build_progress(self, message: str, value: int):
        """构建进度更新"""
        self.main_window.progress_bar.setValue(value)
        self.main_window.status_label.setText(message)

    def on_build_log(self, message: str):
        """构建日志更新"""
        self.main_window.build_log_text.append(message)
        # 确保总是显示最后一行
        self.main_window.build_log_text.moveCursor(self.main_window.build_log_text.textCursor().End)
        self.main_window.build_log_text.ensureCursorVisible()
        # 强制滚动到底部
        scrollbar = self.main_window.build_log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self.main_window.log_message(f"[构建] {message}")

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
            from utils.logger import logger
            logger.error(f"显示错误对话框失败: {e}")

    def make_iso_direct(self):
        """直接制作ISO"""
        try:
            # 开始日志输出
            self.main_window.log_message("=== 开始直接制作ISO ===")
            
            # 检查管理员权限
            self.main_window.log_message("🔍 检查管理员权限...")
            if not ctypes.windll.shell32.IsUserAnAdmin():
                self.main_window.log_message("❌ 缺少管理员权限，请求用户确认...")
                reply = QMessageBox.question(
                    self.main_window, "需要管理员权限",
                    "ISO制作需要管理员权限。\n\n是否以管理员身份重新启动程序？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    self.main_window.log_message("✅ 用户同意以管理员身份重新启动...")
                    # 以管理员权限重新启动程序
                    try:
                        import sys

                        # 获取当前程序路径
                        if hasattr(sys, 'frozen'):
                            # 打包后的exe
                            current_exe = sys.executable
                        else:
                            # Python脚本
                            current_exe = str(Path(__file__).parent.parent.parent / "main.py")

                        self.main_window.log_message(f"🚀 以管理员身份重新启动: {current_exe}")
                        
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
                        from PyQt5.QtWidgets import QApplication
                        QApplication.quit()
                        sys.exit(0)

                    except Exception as e:
                        self.main_window.log_message(f"❌ 重新启动失败: {str(e)}")
                        QMessageBox.critical(
                            self.main_window, "重新启动失败",
                            f"无法以管理员身份重新启动程序。\n\n请手动右键点击程序选择'以管理员身份运行'。\n\n错误详情: {str(e)}"
                        )
                        return
                else:
                    self.main_window.log_message("❌ 用户取消管理员权限请求")
                    return
            else:
                self.main_window.log_message("✅ 管理员权限检查通过")

            # 获取构建方式
            self.main_window.log_message("📋 读取构建配置...")
            build_method_text = self.config_manager.get("winpe.build_method", "copype")
            build_method = "copype" if build_method_text == "copype" else "dism"
            self.main_window.log_message(f"🔧 构建方式: {build_method.upper()}")

            # 获取工作空间和ISO路径
            self.main_window.log_message("📁 检查路径配置...")
            configured_workspace = self.config_manager.get("output.workspace", "").strip()
            if configured_workspace:
                workspace = Path(configured_workspace)
                self.main_window.log_message(f"📂 工作空间: {workspace}")
            else:
                # 使用基于架构的默认工作空间
                architecture = self.config_manager.get("winpe.architecture", "amd64")
                workspace = Path.cwd() / f"WinPE_{architecture}"
                self.main_window.log_message(f"📂 使用默认工作空间: {workspace}")

            iso_path = self.config_manager.get("output.iso_path", "")
            if not iso_path:
                self.main_window.log_message("❌ ISO输出路径未配置")
                QMessageBox.warning(
                    self.main_window, "配置错误",
                    "请先设置ISO输出路径。"
                )
                return
            else:
                self.main_window.log_message(f"💾 ISO输出路径: {iso_path}")

            # 检查用户是否选定了构建目录
            self.main_window.log_message("🔍 检查用户选定的构建目录...")
            current_item = self.main_window.builds_list.currentItem()
            
            if not current_item:
                self.main_window.log_message("❌ 用户未选定构建目录")
                QMessageBox.warning(
                    self.main_window, "未选定构建目录",
                    "请先在已构建目录列表中选择一个构建目录，然后再制作ISO。\n\n"
                    "如果列表为空，请先构建WinPE。"
                )
                return
            
            from PyQt5.QtCore import Qt
            wim_file = current_item.data(Qt.UserRole)
            if not wim_file or not isinstance(wim_file, dict):
                self.main_window.log_message("❌ 选定的构建数据无效")
                QMessageBox.warning(
                    self.main_window, "无效的构建数据",
                    "选定的构建数据无效。\n\n请重新选择一个有效的构建目录。"
                )
                return

            selected_build = wim_file.get("build_dir")
            if not selected_build or not Path(selected_build).exists():
                self.main_window.log_message("❌ 选定的构建目录无效")
                QMessageBox.warning(
                    self.main_window, "无效的构建目录",
                    "选定的构建目录无效或不存在。\n\n请重新选择一个有效的构建目录。"
                )
                return
            
            selected_build_path = Path(selected_build)
            self.main_window.log_message(f"✅ 用户选定的构建目录: {selected_build_path.name}")

            # 检查构建目录中的WIM文件
            self.main_window.log_message("🔍 检查WIM文件...")
            if build_method == "copype":
                wim_path = selected_build_path / "media" / "sources" / "boot.wim"
                self.main_window.log_message(f"📋 copype模式，检查: {wim_path}")
            else:
                wim_path = selected_build_path / "winpe.wim"
                self.main_window.log_message(f"📋 DISM模式，检查: {wim_path}")

            if not wim_path.exists():
                self.main_window.log_message(f"❌ WIM文件不存在: {wim_path}")
                QMessageBox.warning(
                    self.main_window, "WIM文件不存在",
                    f"在构建目录中未找到WIM文件：\n{wim_path}\n\n请确保构建已完成且成功。"
                )
                return
            else:
                wim_size = wim_path.stat().st_size / (1024 * 1024)
                self.main_window.log_message(f"✅ WIM文件存在，大小: {wim_size:.1f} MB")

            # 确认制作ISO
            self.main_window.log_message("🤔 请求用户确认制作ISO...")
            reply = QMessageBox.question(
                self.main_window, "确认制作ISO",
                f"即将制作ISO文件：\n\n"
                f"构建目录: {selected_build_path}\n"
                f"输出路径: {iso_path}\n"
                f"构建方式: {build_method.upper()}\n\n"
                f"确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                self.main_window.log_message("❌ 用户取消ISO制作")
                return
            else:
                self.main_window.log_message("✅ 用户确认开始制作ISO")

            # 显示进度
            self.main_window.progress_bar.setVisible(True)
            self.main_window.progress_bar.setValue(0)
            self.main_window.status_label.setText("正在制作ISO...")

            # 制作ISO
            self.main_window.log_message("🚀 开始制作ISO...")
            success, message = self._create_iso_from_build(selected_build_path, iso_path, build_method)

            # 恢复UI状态
            self.main_window.progress_bar.setVisible(False)
            self.main_window.status_label.setText("ISO制作完成" if success else "ISO制作失败")

            # 显示结果
            if success:
                self.main_window.log_message("✅ ISO制作成功")
                self.main_window.log_message(f"📄 结果: {message}")
                QMessageBox.information(self.main_window, "ISO制作完成", message)
                # 刷新构建目录列表
                self.refresh_builds_list()
            else:
                self.main_window.log_message("❌ ISO制作失败")
                self.main_window.log_message(f"❌ 错误: {message}")
                QMessageBox.critical(self.main_window, "ISO制作失败", message)

            self.main_window.log_message("=== ISO制作流程结束 ===")

        except Exception as e:
            self.main_window.log_message(f"❌ 制作ISO过程中发生异常: {str(e)}")
            log_error(e, "制作ISO")
            QMessageBox.critical(self.main_window, "制作ISO错误", f"制作ISO时发生错误: {str(e)}")

    def _create_iso_from_build(self, build_dir: Path, iso_path: str, build_method: str) -> tuple[bool, str]:
        """从构建目录制作ISO - 使用统一WIM管理器"""
        try:
            from core.unified_manager import UnifiedWIMManager

            # 创建统一WIM管理器
            self.main_window.log_message("🔧 初始化统一WIM管理器...")
            wim_manager = UnifiedWIMManager(self.config_manager, self.adk_manager, self.main_window)

            self.main_window.log_message(f"📂 构建目录: {build_dir}")
            self.main_window.log_message(f"📄 ISO输出路径: {iso_path}")
            self.main_window.log_message(f"📋 构建方法: {build_method}")

            self.main_window.on_build_log("开始制作ISO...")
            self.main_window.on_build_progress("正在制作ISO...", 30)

            # 使用统一管理器创建ISO
            self.main_window.log_message("🚀 调用统一WIM管理器创建ISO...")
            success, message = wim_manager.create_iso(build_dir, Path(iso_path))
            self.main_window.log_message(f"📊 ISO创建结果: success={success}, message={message}")

            if success:
                self.main_window.on_build_progress("ISO制作完成", 100)
                self.main_window.log_message("✅ ISO制作流程完成")

                # 检查ISO文件
                iso_file = Path(iso_path)
                if iso_file.exists():
                    size_mb = iso_file.stat().st_size / (1024 * 1024)
                    self.main_window.log_message(f"✅ ISO文件验证成功: {iso_path}")
                    self.main_window.log_message(f"📊 ISO文件大小: {size_mb:.1f} MB")
                    return True, f"ISO文件制作成功：\n{iso_path}\n文件大小：{size_mb:.1f} MB"
                else:
                    self.main_window.log_message("❌ ISO文件制作完成但文件不存在")
                    return False, "ISO文件制作完成但文件不存在"
            else:
                self.main_window.log_message(f"❌ ISO制作失败：{message}")
                return False, f"ISO制作失败：{message}"

        except Exception as e:
            self.main_window.log_message(f"❌ 制作ISO过程中发生异常：{str(e)}")
            return False, f"制作ISO过程中发生错误：{str(e)}"

    def on_build_finished(self, success: bool, message: str):
        """构建完成"""
        # 恢复UI状态
        self.main_window.build_btn.setText("开始构建 WinPE")
        self.main_window.build_btn.clicked.disconnect()
        self.main_window.build_btn.clicked.connect(self.start_build)
        self.main_window.progress_bar.setVisible(False)
        self.main_window.status_label.setText("构建完成" if success else "构建失败")

        # 显示结果
        if success:
            QMessageBox.information(self.main_window, "构建完成", message)
            # 构建成功后刷新构建目录列表
            self.refresh_builds_list()
        else:
            QMessageBox.critical(self.main_window, "构建失败", message)

        self.main_window.build_thread = None

    def mount_selected_wim(self):
        """挂载选中的WIM映像"""
        try:
            # 使用共享功能获取选中的WIM文件
            wim_file = self.wim_ops_common.get_selected_wim_info(self.main_window.builds_list)
            if not wim_file:
                self.wim_ops_common.show_warning("提示", "请先选择要挂载的WIM映像文件")
                return

            # 创建UnifiedWIMManager实例
            from core.unified_manager import UnifiedWIMManager
            wim_manager = UnifiedWIMManager(self.config_manager, self.adk_manager, self.main_window)

            # 使用共享功能执行挂载操作
            self.wim_ops_common.mount_wim_with_progress(wim_file, wim_manager)

        except Exception as e:
            log_error(e, "挂载选中的WIM映像")
            self.wim_ops_common.show_critical("操作失败", f"挂载操作时发生错误: {str(e)}")

    def unmount_selected_wim_commit(self):
        """卸载选中的WIM映像并保存更改"""
        self.unmount_selected_wim(commit=True)

    def unmount_selected_wim_discard(self):
        """卸载选中的WIM映像不保存更改"""
        self.unmount_selected_wim(commit=False)

    def unmount_selected_wim(self, commit: bool = True):
        """卸载选中的WIM映像

        Args:
            commit: 是否保存更改
        """
        try:
            # 使用共享功能获取选中的WIM文件
            wim_file = self.wim_ops_common.get_selected_wim_info(self.main_window.builds_list)
            if not wim_file:
                self.wim_ops_common.show_warning("提示", "请先选择要卸载的WIM映像文件")
                return

            # 创建UnifiedWIMManager实例
            from core.unified_manager import UnifiedWIMManager
            wim_manager = UnifiedWIMManager(self.config_manager, self.adk_manager, self.main_window)

            # 使用共享功能执行卸载操作
            self.wim_ops_common.unmount_wim_with_progress(wim_file, wim_manager, commit)

        except Exception as e:
            log_error(e, "卸载选中的WIM映像")
            self.wim_ops_common.show_critical("操作失败", f"卸载操作时发生错误: {str(e)}")
