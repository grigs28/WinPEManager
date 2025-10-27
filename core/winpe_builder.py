#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinPE构建器模块
负责创建和定制Windows PE环境
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

from core.adk_manager import ADKManager
from core.config_manager import ConfigManager
from core.winpe import (
    BaseImageManager,
    PackageManager,
    LanguageConfig,
    BootManager
)
from core.unified_manager import UnifiedWIMManager
from core.winpe.boot_config import BootConfig

# 导入增强的日志功能
try:
    from utils.logger import (
        log_build_step,
        log_system_event,
        log_command,
        start_build_session,
        end_build_session,
        update_log_context
    )
    ENHANCED_LOGGING_AVAILABLE = True
except ImportError:
    ENHANCED_LOGGING_AVAILABLE = False

logger = logging.getLogger("WinPEManager")


class WinPEBuilder:
    """WinPE构建器类"""

    def __init__(self, config_manager: ConfigManager, adk_manager: ADKManager, parent_callback=None):
        self.config = config_manager
        self.adk = adk_manager
        self.workspace = Path(config_manager.get("output.workspace", ""))
        self.current_build_path = None
        self.parent_callback = parent_callback  # 用于回调主线程显示错误对话框

        # 初始化各个管理器
        self.base_image_manager = BaseImageManager(config_manager, adk_manager, parent_callback)
        self.package_manager = PackageManager(config_manager, adk_manager, parent_callback)
        self.language_config = LanguageConfig(config_manager, adk_manager, parent_callback)
        self.boot_manager = BootManager(config_manager, adk_manager, parent_callback)
        self.boot_config = BootConfig(config_manager, adk_manager, parent_callback)
        
        # 使用统一WIM管理器替换重复的挂载、卸载、ISO创建功能
        self.wim_manager = UnifiedWIMManager(config_manager, adk_manager, parent_callback)

    def initialize_workspace(self, use_copype: bool = None) -> Tuple[bool, str]:
        """初始化工作空间 - 简化版本

        工作空间逻辑：
        1. 优先使用用户配置的工作空间路径
        2. 如果未配置，自动使用基于架构的工作空间 (WinPE_{architecture})
        3. 直接在工作空间下创建时间戳构建目录

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 优先使用用户配置的工作空间
            configured_workspace = self.config.get("output.workspace", "").strip()
            if configured_workspace:
                self.workspace = Path(configured_workspace)
                logger.info(f"使用用户配置的工作空间: {self.workspace}")
            else:
                # 回退到基于架构的默认工作空间
                architecture = self.config.get("winpe.architecture", "amd64")
                self.workspace = Path.cwd() / f"WinPE_{architecture}"
                logger.info(f"使用默认工作空间: {self.workspace}")

            # 创建工作空间目录
            self.workspace.mkdir(parents=True, exist_ok=True)

            # 创建时间戳构建目录
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_build_path = self.workspace / f"WinPE_{timestamp}"
            self.current_build_path.mkdir(exist_ok=True)

            # 使用基础镜像管理器初始化构建目录的子目录
            success, message = self.base_image_manager.initialize_workspace(self.current_build_path)
            if not success:
                return False, message

            logger.info(f"工作空间初始化完成: {self.workspace}")
            logger.info(f"构建目录: {self.current_build_path}")

            return True, f"工作空间初始化成功: {self.workspace}"

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

            # 使用基础镜像管理器复制WinPE文件
            return self.base_image_manager.copy_base_winpe(self.current_build_path, architecture)

        except Exception as e:
            error_msg = f"复制WinPE基础文件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def mount_winpe_image(self) -> Tuple[bool, str]:
        """挂载WinPE镜像

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not self.current_build_path:
                return False, "工作空间未初始化"

            # 使用统一WIM管理器挂载镜像
            return self.wim_manager.mount_wim(self.current_build_path)

        except Exception as e:
            error_msg = f"挂载WinPE镜像失败: {str(e)}"
            logger.error(error_msg)
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

            # 使用包管理器添加组件
            return self.package_manager.add_packages(self.current_build_path, package_ids)

        except Exception as e:
            error_msg = f"添加包失败: {str(e)}"
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

            # 使用包管理器添加驱动
            return self.package_manager.add_drivers(self.current_build_path, driver_paths)

        except Exception as e:
            error_msg = f"添加驱动失败: {str(e)}"
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

            # 使用包管理器添加文件和脚本
            return self.package_manager.add_files_and_scripts(self.current_build_path)

        except Exception as e:
            error_msg = f"添加文件和脚本失败: {str(e)}"
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

            # 使用统一WIM管理器卸载镜像
            return self.wim_manager.unmount_wim(self.current_build_path, commit=not discard)

        except Exception as e:
            error_msg = f"卸载WinPE镜像失败: {str(e)}"
            logger.error(error_msg)
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

            # 使用统一WIM管理器创建ISO
            return self.wim_manager.create_iso(self.current_build_path, Path(iso_path) if iso_path else None)

        except Exception as e:
            error_msg = f"创建ISO失败: {str(e)}"
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

            # 使用语言配置管理器应用WinPE设置
            return self.language_config.apply_winpe_settings(self.current_build_path)

        except Exception as e:
            error_msg = f"应用WinPE设置失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def configure_language_settings(self) -> Tuple[bool, str]:
        """配置WinPE系统语言和区域设置

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not self.current_build_path:
                return False, "工作空间未初始化"

            # 使用语言配置管理器配置语言设置
            return self.language_config.configure_language_settings(self.current_build_path)

        except Exception as e:
            error_msg = f"配置语言设置失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def build_winpe_complete(self, iso_path: Optional[str] = None) -> Tuple[bool, str]:
        """完整的WinPE构建流程

        Args:
            iso_path: ISO输出路径

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        build_info = {
            "architecture": self.config.get("winpe.architecture", "amd64"),
            "language": self.config.get("winpe.language", "en-US"),
            "iso_path": iso_path or "默认路径",
            "timestamp": logger.handlers[0].formatter.formatTime(logger.makeRecord(
                "WinPEManager", logging.INFO, "", 0, "", (), None
            )) if logger.handlers else "未知"
        }
        
        # 开始构建会话
        if ENHANCED_LOGGING_AVAILABLE:
            start_build_session(build_info)
            log_system_event("WinPE构建", "开始完整的WinPE构建流程", "info")
            update_log_context(build_phase="complete_build")
        
        try:
            # 1. 初始化工作空间
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("初始化工作空间", "开始初始化构建工作空间")
            
            success, message = self.initialize_workspace()
            if not success:
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("初始化工作空间", f"失败: {message}", "error")
                    end_build_session(False, f"初始化工作空间失败: {message}")
                return False, f"初始化工作空间失败: {message}"
            
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("初始化工作空间", "工作空间初始化成功")

            # 2. 复制基础WinPE文件
            architecture = self.config.get("winpe.architecture", "amd64")
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("复制基础文件", f"架构: {architecture}")
            
            success, message = self.copy_base_winpe(architecture)
            if not success:
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("复制基础文件", f"失败: {message}", "error")
                    end_build_session(False, f"复制基础WinPE失败: {message}")
                return False, f"复制基础WinPE失败: {message}"
            
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("复制基础文件", "基础WinPE文件复制成功")

            # 3. 挂载WinPE镜像
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("挂载镜像", "开始挂载WinPE镜像")
            
            success, message = self.mount_winpe_image()
            if not success:
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("挂载镜像", f"失败: {message}", "error")
                    end_build_session(False, f"挂载WinPE镜像失败: {message}")
                return False, f"挂载WinPE镜像失败: {message}"
            
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("挂载镜像", "WinPE镜像挂载成功")

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
            
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("语言配置", f"当前语言: {current_language}")
                log_build_step("语言包检查", f"找到语言包: {len(language_packages) if language_packages else 0} 个")

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
                
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("语言包添加", f"添加了 {added_packages} 个语言包")
            else:
                logger.info(f"ℹ️ 语言 {current_language} 无需额外的语言支持包")
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("语言包检查", f"语言 {current_language} 无需额外语言包")

            if packages:
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("添加可选组件", f"准备添加 {len(packages)} 个组件")
                
                success, message = self.add_packages(packages)
                if not success:
                    logger.warning(f"添加可选组件失败: {message}")
                    if ENHANCED_LOGGING_AVAILABLE:
                        log_build_step("添加可选组件", f"失败: {message}", "warning")
                else:
                    if ENHANCED_LOGGING_AVAILABLE:
                        log_build_step("添加可选组件", f"成功添加 {len(packages)} 个组件")

            # 5. 添加驱动程序
            drivers = [driver.get("path", "") for driver in self.config.get("customization.drivers", [])]
            if drivers:
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("添加驱动程序", f"准备添加 {len(drivers)} 个驱动")
                
                success, message = self.add_drivers(drivers)
                if not success:
                    logger.warning(f"添加驱动程序失败: {message}")
                    if ENHANCED_LOGGING_AVAILABLE:
                        log_build_step("添加驱动程序", f"失败: {message}", "warning")
                else:
                    if ENHANCED_LOGGING_AVAILABLE:
                        log_build_step("添加驱动程序", f"成功添加 {len(drivers)} 个驱动")

            # 6. 设置系统语言和区域设置
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("语言设置", "配置系统语言和区域设置")
            
            success, message = self.configure_language_settings()
            if not success:
                logger.warning(f"设置语言配置失败: {message}")
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("语言设置", f"失败: {message}", "warning")
            else:
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("语言设置", "语言和区域设置配置成功")

            # 7. 添加文件和脚本
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("添加文件脚本", "添加额外文件和脚本")
            
            success, message = self.add_files_and_scripts()
            if not success:
                logger.warning(f"添加文件和脚本失败: {message}")
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("添加文件脚本", f"失败: {message}", "warning")
            else:
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("添加文件脚本", "文件和脚本添加成功")

            # 7.5. 配置启动设置（隐藏cmd.exe窗口）
            desktop_type = self.config.get("winpe.desktop_type", "disabled")
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("启动配置", f"配置WinPE启动设置，桌面类型: {desktop_type}")
            
            success, message = self.boot_config.configure_winpe_startup(self.current_build_path, desktop_type)
            if not success:
                logger.warning(f"配置启动设置失败: {message}")
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("启动配置", f"失败: {message}", "warning")
            else:
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("启动配置", "WinPE启动配置完成，cmd.exe窗口将被隐藏")

            # 8. 卸载并提交更改
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("卸载镜像", "卸载镜像并提交更改")
            
            success, message = self.unmount_winpe_image(discard=False)
            if not success:
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("卸载镜像", f"失败: {message}", "error")
                    end_build_session(False, f"卸载WinPE镜像失败: {message}")
                return False, f"卸载WinPE镜像失败: {message}"
            
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("卸载镜像", "镜像卸载成功，更改已提交")

            # 9. 创建ISO文件
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("创建ISO", f"开始创建ISO文件: {iso_path or '默认路径'}")
            
            success, message = self.create_bootable_iso(iso_path)
            if not success:
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("创建ISO", f"失败: {message}", "error")
                    end_build_session(False, f"创建ISO文件失败: {message}")
                return False, f"创建ISO文件失败: {message}"
            
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("创建ISO", "ISO文件创建成功")
                log_system_event("WinPE构建完成", "完整的WinPE构建流程成功完成", "info")
                end_build_session(True, "WinPE构建完成")

            return True, "WinPE构建完成"

        except Exception as e:
            error_msg = f"WinPE构建过程中发生错误: {str(e)}"
            logger.error(error_msg)
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("构建异常", error_msg, "error")
                log_system_event("WinPE构建异常", error_msg, "error")
                end_build_session(False, error_msg)
            
            # 尝试清理挂载的镜像
            if self.current_build_path:
                self.unmount_winpe_image(discard=True)
            return False, error_msg

    def cleanup(self):
        """清理构建过程产生的临时文件"""
        try:
            if self.current_build_path and self.current_build_path.exists():
                # 使用统一WIM管理器进行智能清理
                success, message = self.wim_manager.smart_cleanup(self.current_build_path)
                if not success:
                    logger.warning(f"智能清理部分失败: {message}")
        except Exception as e:
            logger.error(f"清理时发生错误: {str(e)}")

    def get_build_status(self) -> Dict[str, Any]:
        """获取构建状态信息

        Returns:
            Dict[str, Any]: 构建状态信息
        """
        try:
            status = {
                "workspace": str(self.workspace),
                "current_build_path": str(self.current_build_path) if self.current_build_path else None,
                "is_mounted": False,
                "media_exists": False,
                "boot_wim_exists": False,
                "iso_ready": False
            }

            if self.current_build_path and self.current_build_path.exists():
                # 使用统一WIM管理器检查挂载状态
                mount_status = self.wim_manager.get_mount_status(self.current_build_path)
                status["is_mounted"] = mount_status.get("is_mounted", False)
                
                # 检查Media目录
                media_path = self.current_build_path / "media"
                status["media_exists"] = media_path.exists()
                
                # 检查boot.wim文件
                boot_wim = media_path / "sources" / "boot.wim"
                status["boot_wim_exists"] = boot_wim.exists()
                
                # 使用统一WIM管理器检查ISO创建条件
                validation = self.wim_manager.validate_build_structure(self.current_build_path)
                status["iso_ready"] = validation.get("is_valid", False)
                status["missing_for_iso"] = validation.get("errors", [])

            return status

        except Exception as e:
            logger.error(f"获取构建状态时发生错误: {str(e)}")
            return {}

    def get_available_packages(self, architecture: str = "amd64") -> List[Dict[str, Any]]:
        """获取可用的WinPE包列表

        Args:
            architecture: WinPE架构

        Returns:
            List[Dict[str, Any]]: 可用包列表
        """
        try:
            return self.package_manager.get_available_packages(architecture)
        except Exception as e:
            logger.error(f"获取可用包列表时发生错误: {str(e)}")
            return []

    def get_supported_languages(self) -> List[Dict[str, Any]]:
        """获取支持的语言列表

        Returns:
            List[Dict[str, Any]]: 支持的语言列表
        """
        try:
            return self.language_config.get_supported_languages()
        except Exception as e:
            logger.error(f"获取支持的语言列表时发生错误: {str(e)}")
            return []

    def estimate_iso_size(self) -> Optional[int]:
        """估算ISO文件大小

        Returns:
            Optional[int]: 估算的ISO大小（字节），如果无法估算则返回None
        """
        try:
            if not self.current_build_path:
                return None
            # 使用统一WIM管理器获取构建信息来估算ISO大小
            build_info = self.wim_manager.get_build_info(self.current_build_path)
            return build_info.get("total_wim_size", 0)
        except Exception as e:
            logger.error(f"估算ISO大小时发生错误: {str(e)}")
            return None
