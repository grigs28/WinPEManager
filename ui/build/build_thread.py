#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinPE构建线程模块
提供WinPE构建的后台线程处理
"""

import sys
import os
import datetime
import shutil
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from core.winpe_builder import WinPEBuilder
from core.config_manager import ConfigManager
from core.winpe_packages import WinPEPackages
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