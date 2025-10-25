#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinPE构建器模块
负责创建和定制Windows PE环境
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

from core.adk_manager import ADKManager
from core.config_manager import ConfigManager

logger = logging.getLogger("WinPEManager")


class WinPEBuilder:
    """WinPE构建器类"""

    def __init__(self, config_manager: ConfigManager, adk_manager: ADKManager, parent_callback=None):
        self.config = config_manager
        self.adk = adk_manager
        self.workspace = Path(config_manager.get("output.workspace", ""))
        self.current_build_path = None
        self.parent_callback = parent_callback  # 用于回调主线程显示错误对话框

    def initialize_workspace(self, use_copype: bool = None) -> Tuple[bool, str]:
        """初始化工作空间

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not self.workspace:
                # 使用默认工作空间
                self.workspace = Path.cwd() / "workspace" / "WinPE_Build"

            # 创建工作空间目录
            self.workspace.mkdir(parents=True, exist_ok=True)
            logger.info(f"工作空间根目录: {self.workspace}")

            # 设置当前构建路径
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_build_path = self.workspace / f"WinPE_{timestamp}"
            self.current_build_path.mkdir(exist_ok=True)
            logger.info(f"创建构建目录: {self.current_build_path}")

            # 创建必要的子目录
            subdirs = ["mount", "drivers", "scripts", "files", "logs"]
            created_dirs = []
            for subdir in subdirs:
                dir_path = self.current_build_path / subdir
                dir_path.mkdir(exist_ok=True)
                if dir_path.exists():
                    created_dirs.append(subdir)

            logger.info(f"创建子目录: {', '.join(created_dirs)}")

            # 检查磁盘空间
            import shutil
            disk_usage = shutil.disk_usage(str(self.current_build_path))
            free_gb = disk_usage.free / (1024**3)
            logger.info(f"可用磁盘空间: {free_gb:.1f}GB")

            if free_gb < 2.0:  # 小于2GB时警告
                logger.warning(f"磁盘空间不足: 仅剩 {free_gb:.1f}GB，建议至少保留2GB")
            else:
                logger.info(f"磁盘空间充足: {free_gb:.1f}GB 可用")

            logger.info(f"工作空间初始化成功: {self.current_build_path}")
            return True, f"工作空间初始化成功: {self.current_build_path}"

        except Exception as e:
            error_msg = f"初始化工作空间失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def copy_base_winpe(self, architecture: str = "amd64") -> Tuple[bool, str]:
        """复制基础WinPE文件

        Args:
            architecture: WinPE架构 (x86, amd64, arm)

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not self.current_build_path:
                return False, "工作空间未初始化"

            # 根据配置选择构建方式
            build_method = self.config.get("winpe.build_method", "copype")
            
            if build_method == "copype":
                logger.info("🚀 使用copype工具创建基础WinPE环境")
                return self._copy_base_winpe_with_copype(architecture)
            else:
                logger.info("🔧 使用传统DISM方式创建基础WinPE环境")
                return self._copy_base_winpe_with_dism(architecture)

        except Exception as e:
            error_msg = f"复制WinPE基础文件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _copy_base_winpe_with_copype(self, architecture: str = "amd64") -> Tuple[bool, str]:
        """使用copype工具创建基础WinPE文件

        Args:
            architecture: WinPE架构 (amd64, x86, arm64)

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            logger.info(f"🔧 使用copype工具创建 {architecture} WinPE基础环境")
            logger.info(f"目标路径: {self.current_build_path}")

            # 检查copype工具可用性
            copype_path = self.adk.get_copype_path()
            if not copype_path:
                logger.error("copype工具不可用，回退到DISM方式")
                return self._copy_base_winpe_with_dism(architecture)

            # 验证架构支持并转换为copype格式
            copype_arch_map = {
                "amd64": "amd64",  # 直接使用amd64
                "x86": "x86",      # 32位系统
                "arm64": "arm64"     # ARM64架构
            }

            if architecture not in copype_arch_map:
                logger.error(f"不支持的架构: {architecture}")
                return False, f"不支持的架构: {architecture}"

            copype_arch = copype_arch_map[architecture]
            logger.info(f"架构映射: {architecture} -> copype格式: {copype_arch}")

            # 确保ADK环境已加载
            adk_status = self.adk.get_adk_install_status()
            if not adk_status["environment_ready"]:
                logger.warning("ADK环境未就绪，尝试加载...")
                env_loaded, env_message = self.adk.load_adk_environment()
                if not env_loaded:
                    logger.warning(f"ADK环境加载失败，但仍尝试使用copype: {env_message}")

            # 删除已存在的构建目录（copype需要创建新目录）
            # 注意：不要在这里创建目录，让copype自己创建
            if self.current_build_path.exists():
                logger.info(f"删除已存在的构建目录: {self.current_build_path}")
                import shutil
                shutil.rmtree(self.current_build_path, ignore_errors=True)
                logger.info("目录已删除，copype将创建新的目录结构")

            # 使用copype创建基础环境
            logger.info(f"执行copype命令: copype {copype_arch} {self.current_build_path}")
            success, stdout, stderr = self.adk.run_copype_command(
                copype_arch,
                self.current_build_path,
                capture_output=True
            )

            if not success:
                logger.error(f"copype命令执行失败")
                logger.error(f"错误输出: {stderr}")

                # copype失败时抛出异常以停止后续操作
                from PyQt5.QtWidgets import QMessageBox
                from PyQt5.QtCore import Qt

                # 创建详细的错误信息
                error_details = f"""
copype工具执行失败！

错误详情：
{stderr}

可能的原因：
1. ADK或WinPE组件未正确安装或损坏
2. 权限不足（请以管理员身份运行）
3. 目标路径权限问题
4. 磁盘空间不足
5. 长文件名路径问题（Windows 8.3格式限制）
6. ADK版本兼容性问题

建议解决方法：
1. 检查ADK安装完整性和版本兼容性
2. 确保以管理员身份运行程序
3. 检查目标路径的写入权限
4. 清理磁盘空间后重试
5. 尝试重新安装ADK和WinPE组件
6. 使用较短的路径（避免8.3字符限制）
"""

                # 在主线程中显示错误对话框
                try:
                    # 尝试获取主窗口引用
                    if hasattr(self, 'parent_callback') and self.parent_callback:
                        # 通过回调函数在主线程中显示错误
                        self.parent_callback('show_error', error_details)
                    else:
                        # 如果没有回调函数，创建独立的消息框
                        import sys
                        from PyQt5.QtWidgets import QApplication
                        app = QApplication.instance()
                        if app is None:
                            app = QApplication(sys.argv)

                        msg_box = QMessageBox()
                        msg_box.setIcon(QMessageBox.Critical)
                        msg_box.setWindowTitle("Copype工具错误")
                        msg_box.setText("copype工具执行失败，无法创建WinPE基础环境")
                        msg_box.setDetailedText(error_details)
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.setDefaultButton(QMessageBox.Ok)
                        msg_box.exec_()
                except Exception as e:
                    logger.error(f"显示错误对话框失败: {e}")

                # 抛出异常停止操作
                raise RuntimeError(f"copype工具执行失败，停止构建过程: {stderr}")

            logger.info("✅ copype命令执行成功")

            # 验证copype创建的目录结构
            expected_dirs = [
                self.current_build_path / "media",
                self.current_build_path / "media" / "sources",
                self.current_build_path / "bootbins"  # 修正：新版本ADK使用bootbins而不是fwfiles
            ]

            missing_dirs = [d for d in expected_dirs if not d.exists()]
            if missing_dirs:
                logger.error(f"copype未创建必要的目录: {missing_dirs}")
                return False, f"copype创建的目录结构不完整: {missing_dirs}"

            # 验证关键文件
            boot_wim = self.current_build_path / "media" / "sources" / "boot.wim"
            if not boot_wim.exists():
                logger.error("copype未创建boot.wim文件")
                return False, "boot.wim文件缺失"

            # 检查文件大小
            boot_wim_size = boot_wim.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"✅ boot.wim已创建，大小: {boot_wim_size:.1f} MB")

            if boot_wim_size < 50:  # 小于50MB可能有问题
                logger.warning(f"⚠️ boot.wim文件较小，可能不完整: {boot_wim_size:.1f} MB")

            # 创建额外的必要目录
            additional_dirs = ["mount", "drivers", "scripts", "files", "logs"]
            for subdir in additional_dirs:
                dir_path = self.current_build_path / subdir
                dir_path.mkdir(exist_ok=True)
                logger.debug(f"创建额外目录: {dir_path}")

            # 验证Media目录完整性
            media_path = self.current_build_path / "media"
            media_files = list(media_path.rglob("*"))
            logger.info(f"✅ Media目录包含 {len(media_files)} 个文件/目录")

            # 检查关键启动文件（根据实际copype结构）
            critical_files = {
                "boot.wim": media_path / "sources" / "boot.wim",
                "bootmgfw.efi": media_path / "EFI" / "Microsoft" / "Boot" / "bootmgfw.efi",  # Microsoft Boot Manager
                "BCD": media_path / "EFI" / "Microsoft" / "Boot" / "BCD"  # 启动配置数据
            }

            missing_critical = [name for name, path in critical_files.items() if not path.exists()]
            if missing_critical:
                logger.warning(f"⚠️ 缺少关键启动文件: {', '.join(missing_critical)}")
                logger.info("📝 这些文件将在后续步骤中创建或修复")

            logger.info(f"✅ copype基础WinPE环境创建成功: {architecture}")
            logger.info(f"📁 基础目录: {self.current_build_path}")
            logger.info(f"📊 boot.wim: {boot_wim_size:.1f} MB")
            logger.info(f"🗂️ Media文件: {len(media_files)} 个")

            return True, f"copype基础WinPE环境创建成功 ({architecture}, {boot_wim_size:.1f}MB)"

        except Exception as e:
            error_msg = f"copype创建基础WinPE失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _manual_copype_implementation(self, architecture: str = "amd64") -> Tuple[bool, str]:
        """手动实现copype功能作为回退方案

        Args:
            architecture: WinPE架构 (amd64, x86, arm64)

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            logger.info(f"🔧 手动实现copype功能: {architecture}")

            # 确保目标目录不存在
            if self.current_build_path.exists():
                import shutil
                shutil.rmtree(self.current_build_path, ignore_errors=True)

            # 创建基本目录结构（根据实际copype结构）
            dirs_to_create = [
                self.current_build_path / "media",
                self.current_build_path / "media" / "sources",
                self.current_build_path / "media" / "Boot",  # 注意：实际路径是Boot（大写）
                self.current_build_path / "media" / "EFI" / "Boot",  # 注意：实际路径是EFI（大写）
                self.current_build_path / "media" / "EFI" / "Microsoft" / "Boot",
                self.current_build_path / "bootbins"  # 修正：新版本ADK使用bootbins而不是fwfiles
            ]

            for dir_path in dirs_to_create:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"创建目录: {dir_path}")

            # 复制WinPE文件
            winpe_source = self.adk.winpe_path / architecture
            if not winpe_source.exists():
                return False, f"WinPE源目录不存在: {winpe_source}"

            # 复制主要WinPE WIM文件
            source_wim = winpe_source / "en-us" / "winpe.wim"
            target_wim = self.current_build_path / "media" / "sources" / "boot.wim"

            if source_wim.exists():
                import shutil
                shutil.copy2(source_wim, target_wim)
                size_mb = source_wim.stat().st_size / (1024 * 1024)
                logger.info(f"✅ 复制winpe.wim ({size_mb:.1f}MB)")
            else:
                # 尝试根目录的winpe.wim
                source_wim_alt = winpe_source / "winpe.wim"
                if source_wim_alt.exists():
                    shutil.copy2(source_wim_alt, target_wim)
                    size_mb = source_wim_alt.stat().st_size / (1024 * 1024)
                    logger.info(f"✅ 复制winpe.wim ({size_mb:.1f}MB)")
                else:
                    return False, "找不到winpe.wim文件"

            # 复制启动文件
            boot_files = [
                (winpe_source / "Media" / "Boot", self.current_build_path / "media" / "boot"),
                (winpe_source / "Media" / "EFI", self.current_build_path / "media" / "efi"),
            ]

            for src_dir, dst_dir in boot_files:
                if src_dir.exists():
                    import shutil
                    for item in src_dir.rglob("*"):
                        if item.is_file():
                            rel_path = item.relative_to(src_dir)
                            dst_file = dst_dir / rel_path
                            dst_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(item, dst_file)
                            logger.debug(f"复制启动文件: {rel_path}")

            # 注释：copype模式自动管理固件文件，无需手动复制
            # bootbins目录和相关文件由copype工具自动创建和管理

            # 注释：copype模式已经创建所有必要的文件，无需从bootbins复制
            # bootbins目录由copype自动管理，不需要手动复制

            # 验证关键文件
            required_files = [
                self.current_build_path / "media" / "sources" / "boot.wim",
                self.current_build_path / "bootbins"  # 修正：新版本ADK使用bootbins而不是fwfiles
            ]

            missing_files = []
            for file_path in required_files:
                if not file_path.exists():
                    missing_files.append(str(file_path))

            if missing_files:
                return False, f"缺少必要文件: {missing_files}"

            logger.info("✅ 手动copype实现完成")
            return True, "手动copype实现成功"

        except Exception as e:
            error_msg = f"手动copype实现失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def apply_winpe_settings(self) -> Tuple[bool, str]:
        """应用WinPE专用设置 - Microsoft官方标准配置

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not self.current_build_path:
                return False, "工作空间未初始化"

            logger.info("🔧 开始应用WinPE专用设置")

            # 从配置中读取WinPE专用设置
            enable_settings = self.config.get("winpe.enable_winpe_settings", True)
            if not enable_settings:
                logger.info("WinPE专用设置已禁用，跳过此步骤")
                return True, "WinPE专用设置已禁用"

            # WinPE标准配置
            winpe_config = {
                'scratch_space': self.config.get("winpe.scratch_space_mb", 128),  # 从配置读取
                'target_path': self.config.get("winpe.target_path", "X:"),      # 从配置读取
                'enable_winpe_networking': True,
                'enable_winpe_wmi': True,
                'enable_winpe_scripting': True
            }

            # 获取挂载路径
            mount_dir = self.current_build_path / "mount"
            if not mount_dir.exists():
                logger.info("WinPE镜像未挂载，尝试挂载...")
                success, message = self.mount_winpe_image()
                if not success:
                    logger.warning(f"无法挂载WinPE镜像: {message}")
                    # 继续执行其他设置
                else:
                    mount_dir = self.current_build_path / "mount"

            # 设置暂存空间
            if mount_dir.exists():
                logger.info(f"设置WinPE暂存空间: {winpe_config['scratch_space']}MB")
                success, stdout, stderr = self.adk.run_dism_command([
                    '/Image:' + str(mount_dir),
                    f'/Set-ScratchSpace:{winpe_config["scratch_space"]}'
                ])

                if success:
                    logger.info(f"✅ 暂存空间设置成功: {winpe_config['scratch_space']}MB")
                else:
                    logger.warning(f"⚠️ 暂存空间设置失败: {stderr}")

                # 设置目标路径
                logger.info(f"设置WinPE目标路径: {winpe_config['target_path']}")
                success, stdout, stderr = self.adk.run_dism_command([
                    '/Image:' + str(mount_dir),
                    f'/Set-TargetPath:{winpe_config["target_path"]}'
                ])

                if success:
                    logger.info(f"✅ 目标路径设置成功: {winpe_config['target_path']}")
                else:
                    logger.warning(f"⚠️ 目标路径设置失败: {stderr}")

            # 配置WinPE启动参数
            self._configure_winpe_boot_settings(winpe_config)

            # 创建WinPE专用配置文件
            self._create_winpe_config_files(winpe_config)

            logger.info("✅ WinPE专用设置应用完成")
            return True, "WinPE专用设置应用成功"

        except Exception as e:
            error_msg = f"应用WinPE设置失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _configure_winpe_boot_settings(self, config: dict) -> None:
        """配置WinPE启动设置"""
        try:
            logger.info("配置WinPE启动设置...")

            # 创建WinPE启动配置文件
            media_path = self.current_build_path / "media"

            # 创建WinPE启动脚本（可选）
            winstart_path = media_path / "Windows" / "System32" / "winpe.cmd"
            if winstart_path.parent.exists():
                winstart_content = '''@echo off
REM WinPE启动脚本
echo 正在启动Windows PE环境...
REM 自定义启动命令可以添加在这里
'''
                try:
                    with open(winstart_path, 'w', encoding='utf-8') as f:
                        f.write(winstart_content)
                    logger.info("✅ WinPE启动脚本已创建")
                except Exception as e:
                    logger.warning(f"创建WinPE启动脚本失败: {e}")

        except Exception as e:
            logger.error(f"配置WinPE启动设置失败: {e}")

    def _create_winpe_config_files(self, config: dict) -> None:
        """创建WinPE配置文件"""
        try:
            logger.info("创建WinPE配置文件...")

            # 创建配置目录
            config_dir = self.current_build_path / "config"
            config_dir.mkdir(exist_ok=True)

            # 保存WinPE配置
            import json
            config_file = config_dir / "winpe_settings.json"

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ WinPE配置文件已保存: {config_file}")

        except Exception as e:
            logger.error(f"创建WinPE配置文件失败: {e}")

    def _copy_base_winpe_with_dism(self, architecture: str = "amd64") -> Tuple[bool, str]:
        """使用传统DISM方式复制基础WinPE文件

        Args:
            architecture: WinPE架构 (x86, amd64, arm)

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 获取WinPE源文件路径
            winpe_arch_path = self.adk.winpe_path / architecture
            logger.info(f"查找WinPE源文件: {winpe_arch_path}")

            if not winpe_arch_path.exists():
                logger.error(f"WinPE架构目录不存在: {winpe_arch_path}")
                return False, f"找不到 {architecture} 架构的WinPE文件"

            # 查找winpe.wim文件
            winpe_wim_sources = [
                winpe_arch_path / "en-us" / "winpe.wim",
                winpe_arch_path / "winpe.wim"
            ]

            winpe_wim = None
            for path in winpe_wim_sources:
                if path.exists():
                    winpe_wim = path
                    logger.info(f"找到WinPE镜像文件: {path}")
                    break

            if not winpe_wim:
                logger.error("未找到winpe.wim文件")
                # 列出可用的文件供调试
                try:
                    available_files = list(winpe_arch_path.rglob("*.wim"))
                    if available_files:
                        logger.info(f"可用的WIM文件: {[str(f) for f in available_files[:5]]}")
                    else:
                        logger.info(f"架构目录内容: {list(winpe_arch_path.iterdir())[:10]}")
                except:
                    pass
                return False, "找不到WinPE基础镜像文件"

            # 检查源文件大小
            source_size = winpe_wim.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"源WinPE镜像大小: {source_size:.1f} MB")

            if source_size < 50:  # 小于50MB可能有问题
                logger.warning(f"WinPE镜像文件可能不完整: 仅 {source_size:.1f} MB")

            # 直接创建boot.wim文件（既是工作镜像也是启动镜像）
            target_media = self.current_build_path / "media"
            target_media.mkdir(parents=True, exist_ok=True)
            boot_wim_target = target_media / "sources" / "boot.wim"

            logger.info(f"创建boot.wim（工作+启动镜像）: {winpe_wim} -> {boot_wim_target}")
            boot_wim_target.parent.mkdir(parents=True, exist_ok=True)

            import time
            start_time = time.time()
            shutil.copy2(winpe_wim, boot_wim_target)
            copy_time = time.time() - start_time

            # 验证复制结果
            if boot_wim_target.exists():
                boot_size = boot_wim_target.stat().st_size / (1024 * 1024)  # MB
                logger.info(f"boot.wim复制完成，耗时: {copy_time:.1f}秒，大小: {boot_size:.1f} MB")
                logger.info("✅ boot.wim创建成功，将用于DISM挂载和ISO制作")

                if abs(source_size - boot_size) > 1:  # 大小差异超过1MB
                    logger.warning(f"复制前后文件大小不一致: 源{source_size:.1f}MB -> 目标{boot_size:.1f}MB")
            else:
                logger.error("boot.wim复制失败: 目标文件不存在")
                return False, "复制boot.wim失败"

            # 按照Microsoft官方规范复制Media文件
            media_path = winpe_arch_path / "Media"
            if media_path.exists():
                target_media = self.current_build_path / "media"  # 使用小写目录名，符合官方标准
                logger.info(f"复制Media文件: {media_path} -> {target_media}")

                try:
                    # 第一步：复制Media目录结构（官方标准）
                    shutil.copytree(media_path, target_media, dirs_exist_ok=True)
                    media_files = len(list(target_media.rglob("*")))
                    logger.info(f"Media目录复制完成，共 {media_files} 个文件")

                    # 第二步：验证Media目录结构完整性（根据实际copype结构）
                    required_dirs = [
                        target_media / "Boot",  # 注意：实际路径是Boot（大写）
                        target_media / "sources",
                        target_media / "EFI",   # 注意：实际路径是EFI（大写）
                        target_media / "EFI" / "Boot",
                        target_media / "EFI" / "Microsoft",
                        target_media / "EFI" / "Microsoft" / "Boot"
                    ]

                    missing_dirs = []
                    for req_dir in required_dirs:
                        if not req_dir.exists():
                            req_dir.mkdir(parents=True, exist_ok=True)
                            logger.info(f"创建标准目录: {req_dir}")
                            missing_dirs.append(str(req_dir.relative_to(target_media)))

                    # 第三步：验证boot.wim已存在（作为工作镜像和启动镜像）
                    boot_wim_target = target_media / "sources" / "boot.wim"
                    if boot_wim_target.exists():
                        boot_size = boot_wim_target.stat().st_size / (1024 * 1024)  # MB
                        logger.info(f"✅ boot.wim已就绪（工作+启动镜像），大小: {boot_size:.1f} MB")
                    else:
                        logger.error("❌ boot.wim不存在，应该在初始复制阶段已创建")
                        return False, "boot.wim文件缺失"

                    # 第四步：验证关键启动文件（根据实际copype创建的文件结构）
                    critical_files = {
                        # BIOS启动文件（需要从bootbins复制）
                        "etfsboot.com": target_media / "Boot" / "etfsboot.com",  # 注意：实际路径是Boot（大写）
                        "boot.sdi": target_media / "Boot" / "boot.sdi",  # 注意：实际路径是Boot不是boot
                        "bootfix.bin": target_media / "Boot" / "bootfix.bin",
                        "bootmgr.efi": target_media / "bootmgr.efi",

                        # UEFI启动文件（根据实际结构）
                        "bootx64.efi": target_media / "EFI" / "Boot" / "bootx64.efi",  # 主要UEFI引导文件
                        "bootmgfw.efi": target_media / "EFI" / "Microsoft" / "Boot" / "bootmgfw.efi",  # Microsoft引导管理器

                        # UEFI启动配置
                        "BCD": target_media / "EFI" / "Microsoft" / "Boot" / "BCD"  # 启动配置数据
                    }

                    missing_files = []
                    existing_files = []

                    for filename, file_path in critical_files.items():
                        if file_path.exists():
                            size = file_path.stat().st_size
                            existing_files.append(f"{filename} ({size} bytes)")
                            logger.info(f"✓ 关键启动文件存在: {filename} ({size} bytes)")
                        else:
                            missing_files.append(filename)
                            logger.warning(f"⚠ 关键启动文件缺失: {filename}")

                    # 第五步：查找并补充缺失的启动文件
                    if missing_files:
                        logger.info(f"查找缺失的启动文件: {', '.join(missing_files)}")
                        self._find_missing_boot_files(target_media, missing_files)

                    # 第六步：最终验证和统计（区分关键和非关键文件）
                    logger.info("验证Media目录完整性...")

                    # 定义关键文件（必须有，缺失则构建失败）- 根据实际copype结构
                    critical_boot_files = [
                        target_media / "sources" / "boot.wim",  # boot.wim是必须的
                        target_media / "Boot" / "etfsboot.com",  # BIOS启动扇区
                        target_media / "EFI" / "Microsoft" / "Boot" / "bootmgfw.efi",  # UEFI启动管理器 - 关键！
                        target_media / "EFI" / "Microsoft" / "Boot" / "BCD"  # UEFI启动配置 - 关键！
                    ]

                    # 定义非关键文件（最好有，但没有也能工作）
                    optional_boot_files = [
                        target_media / "Boot" / "boot.sdi",  # 注意：实际路径是Boot（大写）
                        target_media / "Boot" / "bootfix.bin",
                        target_media / "bootmgr",
                        target_media / "bootmgr.efi"
                    ]

                    # 检查关键文件
                    critical_missing = [str(f.name) for f in critical_boot_files if not f.exists()]
                    optional_missing = [str(f.name) for f in optional_boot_files if not f.exists()]

                    if not critical_missing:
                        total_size = sum(f.stat().st_size for f in target_media.rglob("*") if f.is_file())
                        logger.info(f"✅ Media目录复制成功，包含 {media_files} 个文件/目录，总大小 {total_size/(1024*1024):.1f} MB")
                        logger.info(f"✅ 所有关键启动文件完整: {len(critical_boot_files) - len(critical_missing)} 个")

                        if optional_missing:
                            logger.warning(f"⚠️ 部分可选启动文件缺失（不影响基本功能）: {', '.join(optional_missing)}")
                            logger.info("💡 提示: 缺失的文件将在后续步骤中尝试补充，或使用默认配置")
                        else:
                            logger.info(f"✅ 所有可选启动文件也完整: {len(optional_boot_files)} 个")
                    else:
                        logger.error(f"❌ Media目录缺少关键文件: {', '.join(critical_missing)}")
                        return False, f"Media目录缺少关键文件: {', '.join(critical_missing)}"

                except Exception as e:
                    logger.error(f"启动文件复制失败: {str(e)}")
                    return False, f"启动文件复制失败: {str(e)}"
            else:
                logger.error(f"Media目录不存在: {media_path}")
                # 尝试从其他位置创建Media目录
                logger.info("尝试手动创建Media目录和启动文件...")
                if not self._create_media_directory(winpe_arch_path, self.current_build_path / "media"):
                    return False, "无法创建Media目录，缺少必要的启动文件"

            logger.info(f"WinPE基础文件复制成功: {architecture}")
            return True, f"WinPE基础文件复制成功 ({architecture})"

        except Exception as e:
            error_msg = f"复制WinPE基础文件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def check_and_request_admin_privileges(self) -> bool:
        """检查并请求管理员权限"""
        import ctypes
        from PyQt5.QtWidgets import QMessageBox, QApplication
        import sys

        if ctypes.windll.shell32.IsUserAnAdmin():
            return True

        # 由于我们在WinPEBuilder类中，需要通过其他方式显示消息框
        # 这里先返回False，让上层处理权限请求
        logger.error("DISM操作需要管理员权限，但当前程序没有管理员权限")
        return False

    def mount_winpe_image(self) -> Tuple[bool, str]:
        """挂载WinPE镜像

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not self.current_build_path:
                return False, "工作空间未初始化"

            # 挂载boot.wim（既是工作镜像也是启动镜像）
            wim_file = self.current_build_path / "media" / "sources" / "boot.wim"
            mount_dir = self.current_build_path / "mount"

            logger.info(f"准备挂载boot.wim镜像")
            logger.info(f"镜像文件: {wim_file}")
            logger.info(f"挂载目录: {mount_dir}")

            # 检查WIM文件
            if not wim_file.exists():
                logger.error(f"boot.wim文件不存在: {wim_file}")
                return False, f"boot.wim文件不存在: {wim_file}"

            # 检查WIM文件大小
            wim_size = wim_file.stat().st_size
            logger.info(f"WIM文件大小: {wim_size:,} 字节 ({wim_size/1024/1024:.1f} MB)")
            if wim_size < 100 * 1024 * 1024:  # 小于100MB可能有问题
                logger.warning(f"WIM文件大小异常小: {wim_size/1024/1024:.1f} MB，可能复制不完整")

            # 清理并创建挂载目录
            if mount_dir.exists():
                existing_files = list(mount_dir.iterdir())
                if existing_files:
                    logger.warning(f"检测到挂载目录不为空，包含 {len(existing_files)} 个文件/目录")
                    logger.info("尝试清理挂载目录...")
                    cleanup_success, cleanup_msg = self.unmount_winpe_image(discard=True)
                    if cleanup_success:
                        logger.info("挂载目录清理成功")
                    else:
                        logger.warning(f"挂载目录清理失败: {cleanup_msg}")

                    # 强制删除挂载目录内容
                    import shutil
                    try:
                        shutil.rmtree(mount_dir)
                        logger.info("强制删除挂载目录内容")
                    except Exception as e:
                        logger.warning(f"强制删除挂载目录失败: {e}")

            mount_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"挂载目录已准备: {mount_dir}")

            # 检查挂载目录权限
            try:
                test_file = mount_dir / "test_write.tmp"
                test_file.write_text("test")
                test_file.unlink()
                logger.info("挂载目录写权限检查通过")
            except Exception as e:
                logger.error(f"挂载目录权限检查失败: {str(e)}")
                return False, f"挂载目录权限不足: {str(e)}"

            # 检查管理员权限
            if not self.check_and_request_admin_privileges():
                error_msg = "DISM挂载操作需要管理员权限！请右键点击程序选择'以管理员身份运行'。"
                logger.error(error_msg)
                return False, error_msg

            # 使用DISM挂载镜像
            wim_file_str = str(wim_file)
            mount_dir_str = str(mount_dir)

            # 构建标准的DISM命令格式 - 参照WinPE制作流程完整分析.md
            args = [
                "/mount-wim",
                "/wimfile:" + wim_file_str,
                "/index:1",
                "/mountdir:" + mount_dir_str
            ]

            logger.info("执行DISM挂载命令")
            logger.info(f"命令参数: {' '.join(args)}")

            # 记录开始时间
            import time
            mount_start_time = time.time()

            success, stdout, stderr = self.adk.run_dism_command(args)

            mount_duration = time.time() - mount_start_time
            logger.info(f"DISM命令执行耗时: {mount_duration:.1f} 秒")

            if success:
                logger.info("DISM挂载命令执行成功")
                logger.info("WinPE镜像挂载成功")

                # 验证挂载结果
                if mount_dir.exists():
                    mounted_files = list(mount_dir.iterdir())
                    if mounted_files:
                        file_count = len(list(mount_dir.rglob("*")))
                        folder_count = len([d for d in mount_dir.rglob("*") if d.is_dir()])
                        logger.info(f"挂载验证成功")
                        logger.info(f"挂载目录包含 {folder_count} 个目录, {file_count - folder_count} 个文件")

                        # 显示一些关键目录
                        key_dirs = ["Windows", "Program Files", "Users", "System32"]
                        found_dirs = []
                        for key_dir in key_dirs:
                            if (mount_dir / key_dir).exists():
                                found_dirs.append(key_dir)

                        if found_dirs:
                            logger.info(f"关键系统目录: {', '.join(found_dirs)}")

                        # 检查挂载大小
                        try:
                            import shutil
                            mount_size = sum(f.stat().st_size for f in mount_dir.rglob("*") if f.is_file())
                            mount_size_mb = mount_size / (1024 * 1024)
                            logger.info(f"挂载内容大小: {mount_size_mb:.1f} MB")
                        except Exception as e:
                            logger.warning(f"无法计算挂载大小: {str(e)}")

                        return True, f"WinPE镜像挂载成功 (包含 {file_count} 个文件/目录)"
                    else:
                        logger.error("挂载目录为空，挂载可能失败")
                        return False, "WinPE镜像挂载失败: 挂载目录为空"
                else:
                    logger.error("挂载目录不存在")
                    return False, "WinPE镜像挂载失败: 挂载目录不存在"
            else:
                logger.error(f"DISM挂载失败")
                logger.error(f"标准输出: {stdout}")
                logger.error(f"错误输出: {stderr}")

                # 提供一些常见的错误分析
                if "87" in stderr:
                    logger.error("错误87: 通常是命令参数格式错误")
                elif "740" in stderr:
                    logger.error("错误740: 需要管理员权限")
                elif "2" in stderr:
                    logger.error("错误2: 系统找不到指定文件")
                elif "50" in stderr:
                    logger.error("错误50: 可能是镜像文件损坏或格式不支持")

                return False, f"挂载WinPE镜像失败: {stderr}"

        except Exception as e:
            error_msg = f"挂载WinPE镜像时发生错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def add_packages(self, package_ids: List[str]) -> Tuple[bool, str]:
        """添加WinPE可选组件

        Args:
            package_ids: 包ID列表

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not self.current_build_path:
                return False, "工作空间未初始化"

            mount_dir = self.current_build_path / "mount"
            if not mount_dir.exists() or not list(mount_dir.iterdir()):
                return False, "WinPE镜像未挂载"

            success_count = 0
            error_messages = []

            # 区分语言包和其他组件，以便提供更详细的日志
            from core.winpe_packages import WinPEPackages
            winpe_packages = WinPEPackages()
            current_language = self.config.get("winpe.language", "en-US")
            language_packages = set(winpe_packages.get_language_packages(current_language))

            logger.info(f"开始添加 {len(package_ids)} 个可选组件到WinPE镜像...")
            logger.info(f"当前语言设置: {current_language}")

            language_count = 0
            other_count = 0

            for i, package_id in enumerate(package_ids, 1):
                # 判断是否为语言包
                is_language_package = package_id in language_packages
                package_type = "🌐语言包" if is_language_package else "⚙️ 功能组件"

                logger.info(f"[{i}/{len(package_ids)}] 正在处理 {package_type}: {package_id}")

                # 构建包路径
                package_path = self.adk.adk_path / "Assessment and Deployment Kit" / "Windows Preinstallation Environment" / \
                               self.config.get("winpe.architecture", "amd64") / "WinPE_OCs" / f"{package_id}.cab"

                if not package_path.exists():
                    # 尝试其他可能的路径
                    package_path = self.adk.winpe_path / self.config.get("winpe.architecture", "amd64") / "WinPE_OCs" / f"{package_id}.cab"

                if package_path.exists():
                    package_size = package_path.stat().st_size / (1024 * 1024)  # MB
                    logger.info(f"  📁 找到包文件: {package_path} ({package_size:.1f} MB)")

                    args = [
                        "/image:" + str(mount_dir),
                        "/add-package",
                        "/packagepath:" + str(package_path)
                    ]

                    # 显示完整的DISM命令
                    dism_path = self.adk.get_dism_path()
                    full_command = [str(dism_path)] + args
                    command_str = ' '.join(full_command)
                    logger.info(f"  🚀 执行DISM命令:")
                    logger.info(f"     {command_str}")

                    success, stdout, stderr = self.adk.run_dism_command(args)

                    if success:
                        success_count += 1
                        if is_language_package:
                            language_count += 1
                            logger.info(f"  ✅ 语言包添加成功: {package_id} (语言支持已增强)")
                        else:
                            other_count += 1
                            logger.info(f"  ✅ 功能组件添加成功: {package_id}")
                    else:
                        error_msg = f"添加包失败 {package_id}: {stderr}"
                        error_messages.append(error_msg)
                        logger.error(f"  ❌ {package_type}添加失败: {package_id}")
                        logger.error(f"     错误详情: {stderr}")
                else:
                    error_msg = f"找不到包文件: {package_id}"
                    error_messages.append(error_msg)
                    logger.warning(f"  ⚠️ {package_type}文件缺失: {package_id}")

            # 详细的统计信息
            logger.info(f"📊 组件添加完成统计:")
            logger.info(f"   ✅ 成功: {success_count}/{len(package_ids)} 个")
            logger.info(f"   🌐 语言包: {language_count} 个")
            logger.info(f"   ⚙️  功能组件: {other_count} 个")
            logger.info(f"   ❌ 失败: {len(package_ids) - success_count} 个")

            if success_count > 0:
                message = f"成功添加 {success_count}/{len(package_ids)} 个包 (语言包: {language_count}, 功能组件: {other_count})"
                if error_messages:
                    message += f"，错误: {'; '.join(error_messages)}"
                logger.info(f"🎉 组件添加阶段完成: {message}")
                return True, message
            else:
                error_summary = f"所有包添加失败: {'; '.join(error_messages)}"
                logger.error(f"💥 组件添加阶段失败: {error_summary}")
                return False, error_summary

        except Exception as e:
            error_msg = f"添加包时发生错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def add_drivers(self, driver_paths: List[str]) -> Tuple[bool, str]:
        """添加驱动程序

        Args:
            driver_paths: 驱动程序路径列表

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not self.current_build_path:
                return False, "工作空间未初始化"

            mount_dir = self.current_build_path / "mount"
            if not mount_dir.exists() or not list(mount_dir.iterdir()):
                return False, "WinPE镜像未挂载"

            success_count = 0
            error_messages = []

            for driver_path in driver_paths:
                path = Path(driver_path)
                if not path.exists():
                    error_msg = f"驱动程序路径不存在: {driver_path}"
                    error_messages.append(error_msg)
                    continue

                if path.is_file():
                    # 单个驱动文件
                    args = [
                        "/image:" + str(mount_dir),
                        "/add-driver",
                        "/driver:" + str(path),
                        "/forceunsigned"
                    ]
                else:
                    # 驱动目录
                    args = [
                        "/image:" + str(mount_dir),
                        "/add-driver",
                        "/driver:" + str(path),
                        "/recurse",
                        "/forceunsigned"
                    ]

                success, stdout, stderr = self.adk.run_dism_command(args)
                if success:
                    success_count += 1
                    logger.info(f"成功添加驱动: {driver_path}")
                else:
                    error_msg = f"添加驱动失败 {driver_path}: {stderr}"
                    error_messages.append(error_msg)
                    logger.error(error_msg)

            if success_count > 0:
                message = f"成功添加 {success_count}/{len(driver_paths)} 个驱动"
                if error_messages:
                    message += f"，错误: {'; '.join(error_messages)}"
                return True, message
            else:
                return False, f"所有驱动添加失败: {'; '.join(error_messages)}"

        except Exception as e:
            error_msg = f"添加驱动时发生错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def add_files_and_scripts(self) -> Tuple[bool, str]:
        """添加额外文件和脚本

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not self.current_build_path:
                return False, "工作空间未初始化"

            mount_dir = self.current_build_path / "mount"
            if not mount_dir.exists() or not list(mount_dir.iterdir()):
                return False, "WinPE镜像未挂载"

            success_count = 0
            error_messages = []

            # 复制额外文件
            for file_info in self.config.get("customization.files", []):
                try:
                    src_path = Path(file_info.get("path", ""))
                    if src_path.exists():
                        dst_path = mount_dir / src_path.name
                        if src_path.is_file():
                            shutil.copy2(src_path, dst_path)
                        else:
                            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                        success_count += 1
                        logger.info(f"成功复制文件: {src_path}")
                    else:
                        error_msg = f"文件不存在: {src_path}"
                        error_messages.append(error_msg)
                except Exception as e:
                    error_msg = f"复制文件失败 {file_info.get('path', '')}: {str(e)}"
                    error_messages.append(error_msg)

            # 复制脚本文件
            scripts_dir = mount_dir / "Windows" / "System32" / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)

            for script_info in self.config.get("customization.scripts", []):
                try:
                    src_path = Path(script_info.get("path", ""))
                    if src_path.exists():
                        dst_path = scripts_dir / src_path.name
                        shutil.copy2(src_path, dst_path)
                        success_count += 1
                        logger.info(f"成功复制脚本: {src_path}")
                    else:
                        error_msg = f"脚本不存在: {src_path}"
                        error_messages.append(error_msg)
                except Exception as e:
                    error_msg = f"复制脚本失败 {script_info.get('path', '')}: {str(e)}"
                    error_messages.append(error_msg)

            total_items = len(self.config.get("customization.files", [])) + len(self.config.get("customization.scripts", []))
            if success_count > 0:
                message = f"成功添加 {success_count}/{total_items} 个文件和脚本"
                if error_messages:
                    message += f"，错误: {'; '.join(error_messages)}"
                return True, message
            else:
                return False, f"所有文件和脚本添加失败: {'; '.join(error_messages)}"

        except Exception as e:
            error_msg = f"添加文件和脚本时发生错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def unmount_winpe_image(self, discard: bool = False) -> Tuple[bool, str]:
        """卸载WinPE镜像

        Args:
            discard: 是否放弃更改

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not self.current_build_path:
                return False, "工作空间未初始化"

            # 现在挂载的是boot.wim文件
            mount_dir = self.current_build_path / "mount"

            logger.info(f"准备卸载boot.wim镜像: {mount_dir}")

            if not mount_dir.exists():
                logger.info("挂载目录不存在，无需卸载")
                return True, "挂载目录不存在，无需卸载"

            # 检查是否有挂载的镜像
            if not list(mount_dir.iterdir()):
                logger.info("挂载目录为空，直接删除")
                mount_dir.rmdir()
                return True, "挂载目录为空，已清理"

            # 使用DISM卸载镜像
            mount_dir_str = str(mount_dir)

            if discard:
                args = [
                    "/unmount-wim",
                    "/mountdir:" + mount_dir_str,
                    "/discard"
                ]
                action = "放弃更改并"
            else:
                args = [
                    "/unmount-wim",
                    "/mountdir:" + mount_dir_str,
                    "/commit"
                ]
                action = "提交更改并"

            logger.info(f"执行DISM卸载命令，参数: {' '.join(args)}")
            # 检查构建是否被停止
            if hasattr(self, 'parent_callback') and hasattr(self.parent_callback, 'is_running'):
                if not self.parent_callback.is_running:
                    logger.info("检测到构建停止请求，取消卸载操作")
                    return False, "构建已被用户停止"
            elif hasattr(self, '_build_thread') and hasattr(self._build_thread, 'is_running'):
                if not self._build_thread.is_running:
                    logger.info("检测到构建停止请求，取消卸载操作")
                    return False, "构建已被用户停止"

            success, stdout, stderr = self.adk.run_dism_command(args)

            if success:
                logger.info(f"WinPE镜像{action}卸载成功")
                # 验证卸载结果
                if not list(mount_dir.iterdir()):
                    mount_dir.rmdir()  # 删除空的挂载目录
                    logger.info("挂载目录已清理")
                return True, f"WinPE镜像{action}卸载成功"
            else:
                logger.error(f"DISM卸载失败")
                logger.error(f"标准输出: {stdout}")
                logger.error(f"错误输出: {stderr}")

                # 尝试强制清理
                logger.warning("尝试强制清理挂载目录...")
                try:
                    import shutil
                    shutil.rmtree(mount_dir)
                    logger.info("强制清理挂载目录成功")
                    return True, f"卸载命令失败但已强制清理目录"
                except Exception as cleanup_error:
                    logger.error(f"强制清理失败: {cleanup_error}")
                    return False, f"卸载WinPE镜像失败: {stderr}"

        except Exception as e:
            error_msg = f"卸载WinPE镜像时发生错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def create_bootable_iso(self, iso_path: Optional[str] = None) -> Tuple[bool, str]:
        """创建可启动的ISO文件

        Args:
            iso_path: ISO输出路径，如果为None则使用默认路径

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not self.current_build_path:
                return False, "工作空间未初始化"

            # 确保镜像已卸载（ISO创建前必须卸载）
            logger.info("ISO创建前检查镜像挂载状态...")
            mount_dir = self.current_build_path / "mount"
            if mount_dir.exists() and any(mount_dir.iterdir()):
                logger.info("检测到镜像仍处于挂载状态，正在卸载...")
                unmount_success, unmount_msg = self.unmount_winpe_image(discard=False)
                if not unmount_success:
                    logger.warning(f"卸载镜像失败: {unmount_msg}")
                    # 继续执行，但发出警告
                else:
                    logger.info("✅ 镜像已成功卸载")
            else:
                logger.info("镜像未挂载，可直接进行ISO创建")

            if iso_path is None:
                iso_path = self.config.get("output.iso_path", "")
                if not iso_path:
                    iso_path = self.workspace / "WinPE.iso"

            iso_path = Path(iso_path)

            # 根据配置选择ISO创建方式
            build_method = self.config.get("winpe.build_method", "copype")
            
            if build_method == "copype":
                logger.info("🚀 使用MakeWinPEMedia工具创建ISO（copype模式）")
                return self._create_iso_with_makewinpe_media(self.current_build_path, iso_path)
            else:
                logger.info("🔧 使用Oscdimg工具创建ISO（传统DISM模式）")
                # 查找Oscdimg工具
                oscdimg_path = self._find_oscdimg()
                if not oscdimg_path:
                    return False, "找不到Oscdimg工具"

            # 准备ISO文件内容（使用小写目录名，符合官方标准）
            media_path = self.current_build_path / "media"
            logger.info(f"检查Media目录: {media_path}")

            if not media_path.exists():
                logger.error(f"Media目录不存在: {media_path}")
                return False, "找不到Media文件"

            # 验证boot.wim文件（已通过DISM修改完成）
            boot_wim = media_path / "sources" / "boot.wim"
            logger.info(f"验证boot.wim文件: {boot_wim}")

            if boot_wim.exists():
                wim_size = boot_wim.stat().st_size / (1024 * 1024)  # MB
                logger.info(f"✅ boot.wim文件已就绪（已完成DISM修改），大小: {wim_size:.1f} MB")
            else:
                logger.error("❌ boot.wim文件不存在")
                return False, "boot.wim文件缺失"

            # 使用Oscdimg创建ISO
            bootsector_path = media_path / "Boot" / "etfsboot.com"  # 修正：实际路径是Boot（大写）
            logger.info(f"检查启动扇区文件: {bootsector_path}")

            if not bootsector_path.exists():
                logger.error(f"启动扇区文件不存在: {bootsector_path}")
                logger.error("请确保正确创建了WinPE环境")
                return False, f"启动扇区文件不存在: {bootsector_path}"

            # 检查启动扇区文件大小
            bootsector_size = bootsector_path.stat().st_size
            logger.info(f"启动扇区文件大小: {bootsector_size} 字节")
            if bootsector_size < 1000:  # 小于1KB可能有问题
                logger.warning(f"启动扇区文件大小异常: {bootsector_size} 字节")

            # 检查关键启动文件
            try:
                logger.info("检查关键启动文件...")

                # 检查必需的核心文件
                essential_files = [
                    media_path / "sources" / "boot.wim",       # WinPE镜像（必需）
                    media_path / "Boot" / "etfsboot.com",     # BIOS启动扇区（必需）
                ]

                missing_essential = []
                for file_path in essential_files:
                    if file_path.exists():
                        size_mb = file_path.stat().st_size / (1024 * 1024)
                        logger.info(f"✅ 核心文件存在: {file_path.name} ({size_mb:.1f} MB)")
                    else:
                        missing_essential.append(file_path.name)
                        logger.error(f"❌ 核心文件缺失: {file_path.name}")

                # 如果核心文件缺失，无法创建ISO
                if missing_essential:
                    logger.error(f"核心文件缺失，无法创建ISO: {', '.join(missing_essential)}")
                    return False, f"核心文件缺失，无法创建ISO: {', '.join(missing_essential)}"

                # 检查可选的启动文件并记录
                optional_files = [
                    media_path / "Boot" / "boot.sdi",
                    media_path / "EFI" / "Boot" / "bootx64.efi",
                    media_path / "EFI" / "Microsoft" / "Boot" / "bootmgfw.efi",
                    media_path / "EFI" / "Microsoft" / "Boot" / "BCD",
                    media_path / "bootmgr.efi"
                ]

                existing_optional = []
                for file_path in optional_files:
                    if file_path.exists():
                        size_mb = file_path.stat().st_size / (1024 * 1024) if file_path.stat().st_size > 1024*1024 else file_path.stat().st_size
                        unit = "MB" if file_path.stat().st_size > 1024*1024 else "bytes"
                        logger.info(f"✅ 可选文件存在: {file_path.name} ({size_mb:.1f} {unit})")
                        existing_optional.append(file_path.name)

                logger.info(f"找到 {len(existing_optional)} 个可选启动文件")

                # 统计Media目录内容
                media_files = len(list(media_path.rglob("*")))
                logger.info(f"Media目录包含 {media_files} 个文件/目录")

            except Exception as e:
                logger.warning(f"检查文件时发生错误: {str(e)}")

            # 创建输出目录
            iso_path = Path(iso_path)
            iso_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"ISO输出目录: {iso_path.parent}")

            # 构建Oscdimg命令参数（支持多种bootdata格式）
            bootsector_str = str(bootsector_path)
            logger.info(f"启动扇区文件: {bootsector_str}")

            # 尝试不同的bootdata格式
            bootdata_formats = [
                f"-bootdata:2#p0,e,b{bootsector_str}",  # 标准格式
                f"-bootdata:2#p0,b{bootsector_str}",    # 简化格式（无e）
                f"-b{bootsector_str}",                  # 最简单格式
            ]

            # 先使用标准格式
            selected_format = bootdata_formats[0]
            logger.info(f"使用bootdata格式: {selected_format}")

            args = [
                "-m", "-o", "-u2", "-udfver102",
                selected_format,
                str(media_path),
                str(iso_path)
            ]

            logger.info(f"开始创建ISO文件")
            logger.info(f"目标ISO: {iso_path}")
            logger.info(f"使用启动扇区: {bootsector_path}")

            # 尝试不同的bootdata格式，直到找到可用的
            for i, bootdata_format in enumerate(bootdata_formats):
                logger.info(f"尝试bootdata格式 {i+1}/{len(bootdata_formats)}: {bootdata_format}")

                # 更新args中的bootdata参数
                for j, arg in enumerate(args):
                    if arg.startswith("-bootdata:"):
                        args[j] = bootdata_format
                        break

                success, stdout, stderr = self._run_oscdimg(oscdimg_path, args)

                if success and iso_path.exists():
                    logger.info(f"ISO文件创建成功: {iso_path}")
                    logger.info(f"使用的bootdata格式: {bootdata_format}")
                    return True, f"ISO文件创建成功: {iso_path}"
                else:
                    logger.warning(f"bootdata格式 {i+1} 失败: {stderr}")
                    if i < len(bootdata_formats) - 1:
                        logger.info(f"尝试下一种格式...")
                        # 删除可能产生的不完整ISO文件
                        if iso_path.exists():
                            iso_path.unlink()
                    else:
                        logger.error("所有bootdata格式都失败了")
                        return False, f"创建ISO失败，所有格式都尝试过: {stderr}"

        except Exception as e:
            error_msg = f"创建ISO时发生错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _find_oscdimg(self) -> Optional[Path]:
        """查找Oscdimg工具"""
        try:
            # 在ADK目录中查找
            if self.adk.adk_path:
                deploy_tools = self.adk.adk_path / "Assessment and Deployment Kit" / "Deployment Tools"
                if deploy_tools.exists():
                    for root in deploy_tools.rglob("oscdimg.exe"):
                        return root

            # 在系统中查找
            import shutil
            oscdimg = shutil.which("oscdimg.exe")
            if oscdimg:
                return Path(oscdimg)

        except Exception:
            pass
        return None

    def _run_oscdimg(self, oscdimg_path: Path, args: List[str]) -> Tuple[bool, str, str]:
        """运行Oscdimg命令"""
        try:
            cmd = [str(oscdimg_path)] + args
            logger.info(f"执行Oscdimg命令")
            logger.info(f"工具路径: {oscdimg_path}")
            logger.info(f"命令参数: {' '.join(args)}")

            # 检查源目录和目标文件
            if len(args) >= 2:
                source_dir = args[-2]
                target_file = args[-1]
                logger.info(f"源目录: {source_dir}")
                logger.info(f"目标文件: {target_file}")

                # 验证源目录
                if not Path(source_dir).exists():
                    error_msg = f"源目录不存在: {source_dir}"
                    logger.error(error_msg)
                    return False, "", error_msg

                # 检查目标目录权限
                target_path = Path(target_file)
                target_path.parent.mkdir(parents=True, exist_ok=True)

            # 记录开始时间
            import time
            start_time = time.time()

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=False,  # 使用二进制模式，然后手动解码
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            duration = time.time() - start_time
            logger.info(f"Oscdimg命令执行耗时: {duration:.1f} 秒")

            # 使用编码工具处理输出
            from utils.encoding import safe_decode
            stdout = safe_decode(result.stdout)
            stderr = safe_decode(result.stderr)

            success = result.returncode == 0
            logger.info(f"返回码: {result.returncode}")

            if success:
                logger.info("Oscdimg命令执行成功")
                if stdout:
                    logger.info(f"标准输出: {stdout.strip()}")

                # 验证生成的ISO文件
                if len(args) >= 2:
                    iso_path = Path(args[-1])
                    if iso_path.exists():
                        size_mb = iso_path.stat().st_size / (1024 * 1024)
                        logger.info(f"ISO文件生成成功: {iso_path}")
                        logger.info(f"ISO文件大小: {size_mb:.1f} MB")
                    else:
                        logger.warning(f"ISO文件未生成: {iso_path}")
            else:
                logger.error(f"Oscdimg命令执行失败")
                logger.error(f"返回码: {result.returncode}")
                if stderr:
                    logger.error(f"错误输出: {stderr.strip()}")
                if stdout:
                    logger.info(f"标准输出: {stdout.strip()}")

                # 提供错误分析
                if result.returncode == 1:
                    logger.error("返回码1通常表示参数错误或帮助信息")
                elif result.returncode == 2:
                    logger.error("返回码2通常表示文件不存在或访问被拒绝")
                elif result.returncode == 3:
                    logger.error("返回码3通常表示磁盘空间不足")
                else:
                    logger.error(f"未知返回码: {result.returncode}")

            return success, stdout, stderr

        except Exception as e:
            error_msg = f"执行Oscdimg命令时发生错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, "", error_msg

    def build_winpe_complete(self, iso_path: Optional[str] = None) -> Tuple[bool, str]:
        """完整的WinPE构建流程

        Args:
            iso_path: ISO输出路径

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 1. 初始化工作空间
            success, message = self.initialize_workspace()
            if not success:
                return False, f"初始化工作空间失败: {message}"

            # 2. 复制基础WinPE文件
            architecture = self.config.get("winpe.architecture", "amd64")
            success, message = self.copy_base_winpe(architecture)
            if not success:
                return False, f"复制基础WinPE失败: {message}"

            # 3. 挂载WinPE镜像
            success, message = self.mount_winpe_image()
            if not success:
                return False, f"挂载WinPE镜像失败: {message}"

            # 4. 添加可选组件（包含自动语言包）
            packages = self.config.get("customization.packages", [])

            # 自动添加语言支持包
            from core.winpe_packages import WinPEPackages
            winpe_packages = WinPEPackages()
            current_language = self.config.get("winpe.language", "en-US")
            language_packages = winpe_packages.get_language_packages(current_language)

            logger.info(f"🔍 检查语言配置: {current_language}")
            logger.info(f"   查找语言包: {current_language}")
            logger.info(f"   找到的语言包: {language_packages if language_packages else '无'}")

            if language_packages:
                # 将语言包添加到组件列表中
                original_packages_count = len(packages)
                all_packages = set(packages)
                all_packages.update(language_packages)
                packages = list(all_packages)
                added_packages = len(packages) - original_packages_count

                logger.info(f"🌐 自动添加语言支持包: {current_language}")
                logger.info(f"   原始组件数: {original_packages_count}")
                logger.info(f"   添加语言包数: {added_packages}")
                logger.info(f"   最终组件数: {len(packages)}")
                logger.info(f"   语言包列表: {', '.join(language_packages)}")
            else:
                logger.info(f"ℹ️ 语言 {current_language} 无需额外的语言支持包")

            if packages:
                success, message = self.add_packages(packages)
                if not success:
                    logger.warning(f"添加可选组件失败: {message}")

            # 5. 添加驱动程序
            drivers = [driver.get("path", "") for driver in self.config.get("customization.drivers", [])]
            if drivers:
                success, message = self.add_drivers(drivers)
                if not success:
                    logger.warning(f"添加驱动程序失败: {message}")

            # 6. 设置系统语言和区域设置
            success, message = self.configure_language_settings()
            if not success:
                logger.warning(f"设置语言配置失败: {message}")

            # 7. 添加文件和脚本
            success, message = self.add_files_and_scripts()
            if not success:
                logger.warning(f"添加文件和脚本失败: {message}")

            # 8. 卸载并提交更改
            success, message = self.unmount_winpe_image(discard=False)
            if not success:
                return False, f"卸载WinPE镜像失败: {message}"

            # 8. 创建ISO文件
            success, message = self.create_bootable_iso(iso_path)
            if not success:
                return False, f"创建ISO文件失败: {message}"

            return True, "WinPE构建完成"

        except Exception as e:
            error_msg = f"WinPE构建过程中发生错误: {str(e)}"
            logger.error(error_msg)
            # 尝试清理挂载的镜像
            if self.current_build_path:
                self.unmount_winpe_image(discard=True)
            return False, error_msg

    def _find_missing_boot_files(self, media_dir: Path, missing_files: List[str]) -> None:
        """查找并复制缺失的启动文件"""
        logger.info(f"查找缺失的启动文件: {missing_files}")

        # 可能的启动文件搜索路径（扩大搜索范围）
        search_paths = []
        if self.adk.adk_path:
            adk_paths = [
                self.adk.adk_path / "Assessment and Deployment Kit" / "Windows Preinstallation Environment",
                self.adk.adk_path / "Assessment and Deployment Kit" / "Deployment Tools",
                self.adk.adk_path / "Windows Preinstallation Environment",
                self.adk.adk_path / "Windows Kits" / "10" / "Assessment and Deployment Kit" / "Deployment Tools",
                self.adk.adk_path / "Windows Kits" / "10" / "Windows Preinstallation Environment"
            ]
            search_paths.extend(adk_paths)

        # 搜索架构特定的目录
        for arch in ["amd64", "x86", "arm64"]:
            arch_path = self.adk.winpe_path / arch if self.adk.winpe_path else None
            if arch_path and arch_path.exists():
                search_paths.append(arch_path)
                search_paths.append(arch_path / "Media")
                search_paths.append(arch_path / "en-us")
                search_paths.append(arch_path / "EFI")
                search_paths.append(arch_path / "EFI" / "Boot")

        # 添加额外的Windows系统目录搜索（如果系统中有安装）
        system_paths = [
            Path("C:/Windows/Boot/EFI"),
            Path("C:/Windows/System32/Recovery"),
            Path("C:/Windows/Boot/DVD"),
            Path("C:/EFI/Microsoft/Boot"),
            Path("C:/Windows/Boot/PCAT")
        ]

        for system_path in system_paths:
            if system_path.exists():
                search_paths.append(system_path)

        # 添加ADK部署工具的Oscdimg目录（经常有启动文件）
        if self.adk.adk_path:
            oscdimg_paths = [
                self.adk.adk_path / "Assessment and Deployment Kit" / "Deployment Tools" / "x86" / "Oscdimg",
                self.adk.adk_path / "Assessment and Deployment Kit" / "Deployment Tools" / "amd64" / "Oscdimg",
                self.adk.adk_path / "Deployment Tools" / "x86" / "Oscdimg",
                self.adk.adk_path / "Deployment Tools" / "amd64" / "Oscdimg"
            ]
            search_paths.extend([p for p in oscdimg_paths if p.exists()])

        logger.info(f"启动文件搜索路径数量: {len(search_paths)}")

        for missing_file in missing_files:
            # boot.wim文件应该从定制的WinPE镜像复制，不在这里搜索
            if missing_file == "boot.wim":
                logger.info(f"跳过搜索{missing_file}（应该从定制WinPE镜像复制）")
                continue

            found_file = None
            logger.info(f"搜索文件: {missing_file}")

            # 在所有搜索路径中查找文件
            for search_path in search_paths:
                if search_path and search_path.exists():
                    # 递归搜索文件
                    for found_path in search_path.rglob(missing_file):
                        if found_path.is_file():
                            found_file = found_path
                            logger.info(f"找到文件: {found_path}")
                            break
                    if found_file:
                        break

            # 如果找到文件，复制到目标位置
            if found_file:
                try:
                    # 根据文件类型确定目标目录
                    if missing_file in ["etfsboot.com", "boot.sdi", "bootfix.bin"]:
                        target_path = media_dir / "Boot" / missing_file  # 注意：实际路径是Boot（大写）
                    elif missing_file == "bootmgr":
                        target_path = media_dir / missing_file  # 根目录
                    elif missing_file == "bootmgfw.efi":
                        # UEFI启动管理器 - 根据实际copype结构
                        target_path = media_dir / "EFI" / "Microsoft" / "Boot" / missing_file
                    elif missing_file == "bootmgr.efi":
                        target_path = media_dir / missing_file  # 根目录
                    elif missing_file == "BCD":
                        target_path = media_dir / "EFI" / "Microsoft" / "Boot" / missing_file
                    else:
                        target_path = media_dir / missing_file

                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(found_file, target_path)
                    logger.info(f"成功复制启动文件: {found_path} -> {target_path}")

                    # 特殊处理：为UEFI启动创建多个位置的副本
                    if missing_file == "bootmgfw.efi":
                        try:
                            # 创建标准UEFI启动文件名（根据实际copype结构）
                            bootx64_path = media_dir / "EFI" / "Boot" / "bootx64.efi"
                            if not bootx64_path.exists():
                                shutil.copy2(found_file, bootx64_path)
                                logger.info(f"创建UEFI标准启动文件: {bootx64_path}")

                            # 创建Microsoft位置的副本
                            microsoft_boot_path = media_dir / "EFI" / "Microsoft" / "Boot" / "bootmgfw.efi"
                            if not microsoft_boot_path.exists():
                                microsoft_boot_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(found_file, microsoft_boot_path)
                                logger.info(f"创建Microsoft启动文件: {microsoft_boot_path}")

                        except Exception as e:
                            logger.warning(f"创建UEFI启动文件副本失败: {str(e)}")

                    # 特殊处理：BCD启动配置文件
                    elif missing_file == "BCD":
                        try:
                            # 如果BCD文件不存在或损坏，尝试创建基本的BCD配置
                            self._create_basic_bcd_config(media_dir)
                        except Exception as e:
                            logger.warning(f"创建BCD配置失败: {str(e)}")
                except Exception as e:
                    logger.error(f"复制启动文件失败: {missing_file} - {str(e)}")
            else:
                logger.error(f"未找到启动文件: {missing_file}")

    def _create_media_directory(self, winpe_arch_path: Path, target_media: Path) -> bool:
        """按照Microsoft官方规范手动创建Media目录结构"""
        try:
            logger.info(f"手动创建Media目录: {target_media}")
            target_media.mkdir(parents=True, exist_ok=True)

            # 创建完整的标准目录结构（符合Microsoft规范）
            required_dirs = [
                target_media / "Boot",  # 注意：实际路径是Boot（大写）
                target_media / "sources",
                target_media / "EFI",   # 注意：实际路径是EFI（大写）
                target_media / "EFI" / "Boot",
                target_media / "EFI" / "Microsoft",
                target_media / "EFI" / "Microsoft" / "Boot"
            ]

            for dir_path in required_dirs:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"创建标准目录: {dir_path}")

            # 尝试从不同位置复制启动文件
            success_count = 0
            required_files = {
                # BIOS启动文件
                "etfsboot.com": ["Boot", "启动扇区文件"],  # 注意：实际路径是Boot（大写）
                "boot.sdi": ["Boot", "启动设备信息文件"],  # 注意：实际路径是Boot（大写）
                "bootfix.bin": ["Boot", "启动修复程序"],
                "bootmgr": ["", "BIOS启动管理器"],

                # UEFI启动文件（根据实际copype结构）
                "bootmgfw.efi": ["EFI/Microsoft/Boot", "UEFI启动管理器"],
                "bootmgr.efi": ["", "UEFI启动管理器"],

                # UEFI启动配置
                "BCD": ["EFI/Microsoft/Boot", "启动配置数据"]
            }

            # 搜索路径
            search_paths = []
            if self.adk.adk_path:
                search_paths.extend([
                    self.adk.adk_path / "Assessment and Deployment Kit" / "Deployment Tools",
                    self.adk.adk_path / "Assessment and Deployment Kit" / "Windows Preinstallation Environment"
                ])

            if winpe_arch_path.exists():
                search_paths.extend([
                    winpe_arch_path,
                    winpe_arch_path / "Media",
                    winpe_arch_path / "en-us"
                ])

            # 尝试查找并复制每个文件
            for filename, info in required_files.items():
                target_subdir, description = info
                if target_subdir:
                    target_path = target_media / target_subdir / filename
                else:
                    target_path = target_media / filename

                if target_path.exists():
                    logger.info(f"目标文件已存在: {target_path}")
                    success_count += 1
                    continue

                found_source = None
                for search_path in search_paths:
                    if search_path and search_path.exists():
                        for source_file in search_path.rglob(filename):
                            if source_file.is_file():
                                found_source = source_file
                                break
                    if found_source:
                        break

                if found_source:
                    try:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(found_source, target_path)
                        logger.info(f"成功复制{description}: {found_source} -> {target_path}")
                        success_count += 1
                    except Exception as e:
                        logger.error(f"复制{description}失败: {str(e)}")
                else:
                    logger.warning(f"未找到{description}: {filename}")

            # 验证boot.wim文件（应该在主流程中已创建）
            boot_wim = target_media / "sources" / "boot.wim"
            if boot_wim.exists():
                logger.info(f"boot.wim已存在: {boot_wim}")
                success_count += 1
            else:
                logger.warning(f"boot.wim不存在，应该在主流程中已创建: {boot_wim}")

            total_required = len(required_files) + 1  # +1 for boot.wim
            logger.info(f"Media目录创建完成，成功复制 {success_count}/{total_required} 个文件")

            return success_count >= total_required * 0.7  # 至少70%的文件成功

        except Exception as e:
            logger.error(f"创建Media目录失败: {str(e)}")
            return False

    def _validate_media_directory(self, media_dir: Path) -> bool:
        """验证Media目录的完整性"""
        try:
            if not media_dir.exists():
                logger.error(f"Media目录不存在: {media_dir}")
                return False

            logger.info(f"验证Media目录: {media_dir}")

            # 检查关键文件（按照实际copype结构）
            critical_files = {
                # BIOS启动文件
                "etfsboot.com": media_dir / "Boot" / "etfsboot.com",     # BIOS启动扇区
                "boot.sdi": media_dir / "Boot" / "boot.sdi",          # 启动设备信息
                "bootfix.bin": media_dir / "Boot" / "bootfix.bin",      # 启动修复程序
                "bootmgr.efi": media_dir / "bootmgr.efi",             # 根目录启动管理器

                # UEFI启动文件（实际copype结构）
                "bootmgfw.efi": media_dir / "EFI" / "Microsoft" / "Boot" / "bootmgfw.efi", # Microsoft Boot Manager
                "bootx64.efi": media_dir / "EFI" / "Boot" / "bootx64.efi",          # 标准UEFI启动文件

                # UEFI启动配置
                "BCD": media_dir / "EFI" / "Microsoft" / "Boot" / "BCD",              # 启动配置数据

                # WinPE映像
                "boot.wim": media_dir / "sources" / "boot.wim"                      # WinPE镜像
            }

            missing_files = []
            existing_files = []

            for name, path in critical_files.items():
                if path.exists():
                    size = path.stat().st_size
                    existing_files.append(f"{name} ({size} bytes)")
                    logger.info(f"✓ 关键文件存在: {name} ({size} bytes)")
                else:
                    missing_files.append(name)
                    logger.error(f"✗ 关键文件缺失: {name}")

            # 检查目录结构
            required_dirs = ["boot", "sources", "EFI"]
            for dir_name in required_dirs:
                dir_path = media_dir / dir_name
                if dir_path.exists():
                    logger.info(f"✓ 目录存在: {dir_name}")
                else:
                    logger.warning(f"⚠ 目录缺失: {dir_name}")

            # 统计信息
            total_files = len(list(media_dir.rglob("*")))
            logger.info(f"Media目录包含 {total_files} 个文件/目录")

            # 验证结果
            if len(missing_files) == 0:
                logger.info("✓ Media目录验证通过")
                return True
            else:
                logger.error(f"✗ Media目录验证失败，缺失 {len(missing_files)} 个关键文件: {', '.join(missing_files)}")

                # 对于一些非关键文件，给出警告但继续
                if "bcd" in missing_files and len(missing_files) == 1:
                    logger.warning("⚠ 仅有bcd文件缺失，将尝试使用默认配置")
                    return True
                else:
                    return False

        except Exception as e:
            logger.error(f"验证Media目录时发生错误: {str(e)}")
            return False

    def verify_uefi_boot_files(self, media_dir: Path) -> Tuple[bool, List[str]]:
        """检查UEFI启动文件

        Args:
            media_dir: Media目录路径

        Returns:
            Tuple[bool, List[str]]: (是否通过检查, 缺失的文件列表)
        """
        try:
            logger.info("检查UEFI启动文件...")

            # 检查常见的UEFI启动文件
            uefi_files_to_check = [
                media_dir / "EFI" / "Microsoft" / "Boot" / "bootmgfw.efi",
                media_dir / "EFI" / "Boot" / "bootx64.efi",
                media_dir / "EFI" / "Microsoft" / "Boot" / "BCD",
                media_dir / "sources" / "boot.wim"
            ]

            missing_files = []
            found_files = []

            for file_path in uefi_files_to_check:
                if file_path.exists():
                    size = file_path.stat().st_size
                    logger.info(f"✅ 找到UEFI文件: {file_path.name} ({size:,} bytes)")
                    found_files.append(file_path.name)
                else:
                    missing_files.append(file_path.name)
                    logger.debug(f"UEFI文件不存在: {file_path.name}")

            logger.info(f"UEFI文件检查完成: 找到 {len(found_files)} 个，缺失 {len(missing_files)} 个")
            return len(missing_files) == 0, missing_files

        except Exception as e:
            logger.error(f"检查UEFI文件时发生错误: {str(e)}")
            return False, ["检查过程出错"]
            for dir_path in required_dirs:
                if not dir_path.exists():
                    missing_dirs.append(str(dir_path.relative_to(media_dir)))
                    logger.error(f"❌ UEFI目录缺失: {dir_path.relative_to(media_dir)}")

            # 汇总验证结果
            total_issues = len(missing_files) + len(missing_dirs)
            if total_issues == 0:
                logger.info("✅ UEFI启动文件验证通过")
                return True, []
            else:
                all_issues = missing_files + missing_dirs
                logger.error(f"❌ UEFI启动文件验证失败，缺失 {total_issues} 项: {', '.join(all_issues)}")
                return False, all_issues

        except Exception as e:
            logger.error(f"UEFI启动文件验证时发生错误: {str(e)}")
            return False, [f"验证过程错误: {str(e)}"]

    def _create_basic_bcd_config(self, media_dir: Path) -> bool:
        """创建基本的BCD启动配置

        Args:
            media_dir: Media目录路径

        Returns:
            bool: 是否成功创建
        """
        try:
            bcd_path = media_dir / "EFI" / "Microsoft" / "Boot" / "BCD"  # 根据实际copype结构
            bcd_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"创建基本BCD配置: {bcd_path}")

            # 如果系统中有BCDedit工具，尝试使用它创建配置
            import subprocess
            bcdedit_path = shutil.which("bcdedit.exe")

            if bcdedit_path:
                try:
                    # 创建临时BCD存储
                    temp_bcd = bcd_path.with_suffix(".temp")

                    # 初始化BCD存储
                    init_cmd = [bcdedit_path, "/createstore", str(temp_bcd)]
                    result = subprocess.run(init_cmd, capture_output=True, text=True,
                                          creationflags=subprocess.CREATE_NO_WINDOW)

                    if result.returncode == 0:
                        # 添加WinPE启动项
                        boot_entry_cmd = [
                            bcdedit_path, "/store", str(temp_bcd),
                            "/create", "/d", "Windows PE", "/application", "bootsector"
                        ]
                        result = subprocess.run(boot_entry_cmd, capture_output=True, text=True,
                                              creationflags=subprocess.CREATE_NO_WINDOW)

                        if result.returncode == 0:
                            # 将临时文件复制为最终BCD
                            temp_bcd.rename(bcd_path)
                            logger.info("✅ 成功创建BCD启动配置")
                            return True

                    temp_bcd.unlink(missing_ok=True)

                except Exception as e:
                    logger.warning(f"使用BCDedit创建配置失败: {str(e)}")

            # 如果BCDedit方法失败，创建一个最小的占位符文件
            # 这虽然不是完整的BCD，但至少能让ISO创建过程继续
            bcd_path.write_bytes(b'BCD Placeholder')
            logger.warning("⚠️ 创建了BCD占位符文件（可能需要手动配置）")
            return True

        except Exception as e:
            logger.error(f"创建BCD配置失败: {str(e)}")
            return False

    def cleanup(self):
        """清理构建过程产生的临时文件"""
        try:
            if self.current_build_path and self.current_build_path.exists():
                mount_dir = self.current_build_path / "mount"
                if mount_dir.exists() and list(mount_dir.iterdir()):
                    self.unmount_winpe_image(discard=True)
        except Exception as e:
            logger.error(f"清理时发生错误: {str(e)}")

    def configure_language_settings(self) -> Tuple[bool, str]:
        """配置WinPE系统语言和区域设置

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not self.current_build_path:
                return False, "工作空间未初始化"

            mount_dir = self.current_build_path / "mount"
            if not mount_dir.exists() or not list(mount_dir.iterdir()):
                logger.warning("WinPE镜像未挂载，跳过语言配置")
                return True, "镜像未挂载，跳过语言配置"

            # 获取当前语言设置
            current_language = self.config.get("winpe.language", "en-US")
            logger.info(f"🌐 配置WinPE系统语言设置: {current_language}")

            # 语言映射到DISM参数
            language_mapping = {
                "zh-CN": {
                    "syslocale": "zh-CN",
                    "userlocale": "zh-CN",
                    "inputlocale": "0804:00000804"
                },
                "zh-TW": {
                    "syslocale": "zh-TW",
                    "userlocale": "zh-TW",
                    "inputlocale": "0404:00000404"
                },
                "zh-HK": {
                    "syslocale": "zh-HK",
                    "userlocale": "zh-HK",
                    "inputlocale": "0C04:00000C04"
                },
                "ja-JP": {
                    "syslocale": "ja-JP",
                    "userlocale": "ja-JP",
                    "inputlocale": "0411:00000411"
                },
                "ko-KR": {
                    "syslocale": "ko-KR",
                    "userlocale": "ko-KR",
                    "inputlocale": "0412:00000412"
                },
                "en-US": {
                    "syslocale": "en-US",
                    "userlocale": "en-US",
                    "inputlocale": "0409:00000409"
                }
            }

            lang_config = language_mapping.get(current_language, language_mapping["en-US"])

            logger.info(f"   设置系统区域: {lang_config['syslocale']}")
            logger.info(f"   设置用户区域: {lang_config['userlocale']}")
            logger.info(f"   设置输入法: {lang_config['inputlocale']}")

            # 使用DISM设置系统语言
            # DISM语言设置命令需要指定镜像路径
            mount_dir_str = str(mount_dir)
            dism_commands = [
                ["/image:" + mount_dir_str, "/set-syslocale:" + lang_config["syslocale"]],
                ["/image:" + mount_dir_str, "/set-userlocale:" + lang_config["userlocale"]],
                ["/image:" + mount_dir_str, "/set-inputlocale:" + lang_config["inputlocale"]]
            ]

            success_count = 0
            for cmd_args in dism_commands:
                try:
                    logger.info(f"   执行DISM命令: {' '.join(cmd_args)}")
                    success, stdout, stderr = self.adk.run_dism_command(cmd_args)

                    if success:
                        success_count += 1
                        logger.info(f"   ✅ 语言设置命令成功: {cmd_args[1]}")
                    else:
                        logger.warning(f"   ⚠️ 语言设置命令失败: {cmd_args[1]} - {stderr}")

                except Exception as e:
                    logger.error(f"   ❌ 执行语言设置命令时发生错误: {str(e)}")

            if success_count == len(dism_commands):
                logger.info(f"✅ WinPE语言配置完成: {current_language}")
                return True, f"语言配置成功: {current_language}"
            elif success_count > 0:
                logger.warning(f"⚠️ WinPE语言配置部分完成: {success_count}/{len(dism_commands)} 个命令成功")
                return True, f"语言配置部分完成: {success_count}/{len(dism_commands)} 个命令成功"
            else:
                logger.error(f"❌ WinPE语言配置失败")
                return False, "语言配置失败"

        except Exception as e:
            error_msg = f"配置语言设置时发生错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def create_bootable_iso_makewinpe(self, iso_path: Optional[str] = None) -> Tuple[bool, str]:
        """创建可启动的ISO文件（使用MakeWinPEMedia）

        Args:
            iso_path: ISO输出路径，如果为None则使用默认路径

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not self.current_build_path:
                return False, "工作空间未初始化"

            # 确保镜像已卸载（ISO创建前必须卸载）
            logger.info("ISO创建前检查镜像挂载状态...")
            mount_dir = self.current_build_path / "mount"
            if mount_dir.exists() and any(mount_dir.iterdir()):
                logger.info("检测到镜像仍处于挂载状态，正在卸载...")
                unmount_success, unmount_msg = self.unmount_winpe_image(discard=False)
                if not unmount_success:
                    logger.warning(f"卸载镜像失败: {unmount_msg}")
                    # 继续执行，但发出警告
                else:
                    logger.info("✅ 镜像已成功卸载")
            else:
                logger.info("镜像未挂载，可直接进行ISO创建")

            if iso_path is None:
                iso_path = self.config.get("output.iso_path", "")
                if not iso_path:
                    iso_path = self.workspace / "WinPE.iso"

            iso_path = Path(iso_path)

            # 使用MakeWinPEMedia创建ISO
            return self._create_iso_with_makewinpe_media(self.current_build_path, iso_path)

        except Exception as e:
            error_msg = f"创建ISO文件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _create_iso_with_makewinpe_media(self, source_dir: Path, iso_path: Path) -> Tuple[bool, str]:
        """使用MakeWinPEMedia创建ISO文件

        Args:
            source_dir: WinPE源目录（包含media目录）
            iso_path: ISO输出路径

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            logger.info("使用MakeWinPEMedia创建ISO文件...")
            logger.info(f"源目录: {source_dir}")
            logger.info(f"目标ISO: {iso_path}")

            # 查找MakeWinPEMedia.cmd
            makewinpe_path = self._find_makewinpe_media()
            if not makewinpe_path:
                return False, "找不到MakeWinPEMedia工具"

            # 检查源目录结构
            media_path = source_dir / "media"
            if not media_path.exists():
                return False, f"源目录中缺少media目录: {media_path}"

            # 检查boot.wim文件
            boot_wim = media_path / "sources" / "boot.wim"
            if not boot_wim.exists():
                return False, f"找不到boot.wim文件: {boot_wim}"

            wim_size = boot_wim.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"✅ boot.wim文件已就绪，大小: {wim_size:.1f} MB")

            # 创建输出目录
            iso_path.parent.mkdir(parents=True, exist_ok=True)

            # 如果目标ISO文件已存在，删除它
            if iso_path.exists():
                logger.info(f"删除已存在的ISO文件: {iso_path}")
                iso_path.unlink()

            # 构建MakeWinPEMedia命令
            cmd = [str(makewinpe_path), "/iso", str(source_dir), str(iso_path)]
            logger.info(f"执行命令: {' '.join(cmd)}")

            # 设置环境变量，确保能找到oscdimg
            import os
            old_path = os.environ.get('PATH', '')
            oscdimg_dir = r"C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg"
            new_path = f"{oscdimg_dir};{old_path}"
            os.environ['PATH'] = new_path

            # 执行命令
            import subprocess
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=False,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 恢复原始PATH
            os.environ['PATH'] = old_path

            # 处理输出
            from utils.encoding import safe_decode
            stdout = safe_decode(result.stdout)
            stderr = safe_decode(result.stderr)

            logger.info(f"MakeWinPEMedia返回码: {result.returncode}")

            if result.returncode == 0:
                logger.info("✅ MakeWinPEMedia执行成功")
                if stdout:
                    logger.info(f"输出: {stdout}")

                # 验证生成的ISO文件
                if iso_path.exists():
                    size_mb = iso_path.stat().st_size / (1024 * 1024)
                    logger.info(f"✅ ISO文件创建成功: {iso_path}")
                    logger.info(f"📊 ISO文件大小: {size_mb:.1f} MB")
                    return True, f"ISO创建成功 ({size_mb:.1f}MB)"
                else:
                    return False, "ISO文件未生成"
            else:
                logger.error(f"❌ MakeWinPEMedia执行失败")
                if stderr:
                    logger.error(f"错误输出: {stderr}")
                if stdout:
                    logger.error(f"标准输出: {stdout}")
                return False, f"MakeWinPEMedia失败 (返回码: {result.returncode})"

        except Exception as e:
            error_msg = f"使用MakeWinPEMedia创建ISO失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _find_makewinpe_media(self) -> Optional[Path]:
        """查找MakeWinPEMedia.cmd工具

        Returns:
            Optional[Path]: MakeWinPEMedia.cmd路径，如果找不到则返回None
        """
        try:
            # 查找MakeWinPEMedia.cmd的常见路径
            adk_paths = [
                Path(r"C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment"),
                Path(r"C:\Program Files\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment"),
            ]

            for adk_path in adk_paths:
                makewinpe_path = adk_path / "MakeWinPEMedia.cmd"
                if makewinpe_path.exists():
                    logger.info(f"找到MakeWinPEMedia工具: {makewinpe_path}")
                    return makewinpe_path

            # 在系统PATH中查找
            import shutil
            makewinpe = shutil.which("MakeWinPEMedia.cmd")
            if makewinpe:
                logger.info(f"在系统PATH中找到MakeWinPEMedia: {makewinpe}")
                return Path(makewinpe)

            logger.error("未找到MakeWinPEMedia工具")
            return None

        except Exception as e:
            logger.error(f"查找MakeWinPEMedia工具时发生错误: {str(e)}")
            return None