#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
包和驱动管理模块
负责WinPE可选组件和驱动的添加
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger("WinPEManager")


class PackageManager:
    """WinPE包和驱动管理器"""

    def __init__(self, config_manager, adk_manager, parent_callback=None):
        self.config = config_manager
        self.adk = adk_manager
        self.parent_callback = parent_callback

    def add_packages(self, current_build_path: Path, package_ids: List[str]) -> Tuple[bool, str]:
        """添加WinPE可选组件

        Args:
            current_build_path: 当前构建路径
            package_ids: 包ID列表

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not current_build_path:
                return False, "工作空间未初始化"

            mount_dir = current_build_path / "mount"
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

    def add_drivers(self, current_build_path: Path, driver_paths: List[str]) -> Tuple[bool, str]:
        """添加驱动程序

        Args:
            current_build_path: 当前构建路径
            driver_paths: 驱动程序路径列表

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not current_build_path:
                return False, "工作空间未初始化"

            mount_dir = current_build_path / "mount"
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

    def add_files_and_scripts(self, current_build_path: Path) -> Tuple[bool, str]:
        """添加额外文件和脚本

        Args:
            current_build_path: 当前构建路径

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not current_build_path:
                return False, "工作空间未初始化"

            mount_dir = current_build_path / "mount"
            if not mount_dir.exists() or not list(mount_dir.iterdir()):
                return False, "WinPE镜像未挂载"

            success_count = 0
            error_messages = []

            # 处理桌面环境集成
            desktop_result = self._integrate_desktop_environment(mount_dir)
            if desktop_result[0]:
                success_count += 1
                logger.info(f"桌面环境集成成功: {desktop_result[1]}")
            else:
                error_messages.append(f"桌面环境集成失败: {desktop_result[1]}")

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

            total_items = len(self.config.get("customization.files", [])) + len(self.config.get("customization.scripts", [])) + 1  # +1 for desktop
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

    def _integrate_desktop_environment(self, mount_dir: Path) -> Tuple[bool, str]:
        """集成桌面环境到WinPE

        Args:
            mount_dir: WinPE挂载目录

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            from core.desktop_manager import DesktopManager
            desktop_manager = DesktopManager(self.config)
            
            # 获取桌面配置
            desktop_config = desktop_manager.get_current_desktop_config()
            desktop_type = desktop_config["type"]
            
            if desktop_type == "disabled":
                return True, "未启用桌面环境"
            
            # 检查是否需要自动下载
            auto_download = self.config.get("winpe.desktop_auto_download", False)
            if auto_download:
                logger.info(f"开始设置桌面环境: {desktop_config['name']}")
                setup_result = desktop_manager.setup_desktop_environment(desktop_type, auto_download)
                if not setup_result[0]:
                    return False, f"桌面环境设置失败: {setup_result[1]}"
            
            # 准备桌面环境到WinPE
            logger.info(f"准备桌面环境到WinPE: {desktop_config['name']}")
            prepare_result = desktop_manager.prepare_desktop_for_winpe(desktop_type, mount_dir)
            
            return prepare_result
            
        except Exception as e:
            error_msg = f"集成桌面环境失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_available_packages(self, architecture: str = "amd64") -> List[Dict[str, Any]]:
        """获取可用的WinPE包列表

        Args:
            architecture: WinPE架构

        Returns:
            List[Dict[str, Any]]: 可用包列表
        """
        try:
            packages = []
            
            # 查找WinPE可选组件目录
            winpe_oc_paths = [
                self.adk.adk_path / "Assessment and Deployment Kit" / "Windows Preinstallation Environment" / architecture / "WinPE_OCs",
                self.adk.winpe_path / architecture / "WinPE_OCs"
            ]

            for oc_path in winpe_oc_paths:
                if oc_path.exists():
                    for cab_file in oc_path.glob("*.cab"):
                        package_info = {
                            "name": cab_file.stem,
                            "path": str(cab_file),
                            "size": cab_file.stat().st_size,
                            "size_mb": round(cab_file.stat().st_size / (1024 * 1024), 2)
                        }
                        packages.append(package_info)

            # 去重（按名称）
            unique_packages = {}
            for package in packages:
                name = package["name"]
                if name not in unique_packages or package["size"] > unique_packages[name]["size"]:
                    unique_packages[name] = package

            return list(unique_packages.values())

        except Exception as e:
            logger.error(f"获取可用包列表时发生错误: {str(e)}")
            return []

    def validate_package_dependencies(self, package_ids: List[str]) -> Tuple[bool, List[str]]:
        """验证包依赖关系

        Args:
            package_ids: 要添加的包ID列表

        Returns:
            Tuple[bool, List[str]]: (是否有效, 缺失的依赖包列表)
        """
        try:
            # 这里可以实现包依赖关系检查逻辑
            # 目前返回True，表示所有包都有效
            # 在实际实现中，可以维护一个包依赖关系映射表
            return True, []
        except Exception as e:
            logger.error(f"验证包依赖关系时发生错误: {str(e)}")
            return False, []

    def get_package_info(self, package_id: str, architecture: str = "amd64") -> Optional[Dict[str, Any]]:
        """获取特定包的详细信息

        Args:
            package_id: 包ID
            architecture: WinPE架构

        Returns:
            Optional[Dict[str, Any]]: 包信息，如果找不到则返回None
        """
        try:
            # 查找包文件
            package_paths = [
                self.adk.adk_path / "Assessment and Deployment Kit" / "Windows Preinstallation Environment" / architecture / "WinPE_OCs" / f"{package_id}.cab",
                self.adk.winpe_path / architecture / "WinPE_OCs" / f"{package_id}.cab"
            ]

            for package_path in package_paths:
                if package_path.exists():
                    return {
                        "name": package_id,
                        "path": str(package_path),
                        "size": package_path.stat().st_size,
                        "size_mb": round(package_path.stat().st_size / (1024 * 1024), 2),
                        "exists": True
                    }

            return None

        except Exception as e:
            logger.error(f"获取包信息时发生错误: {str(e)}")
            return None

    def install_language_packages(self, current_build_path: Path, language: str = "en-US") -> Tuple[bool, str]:
        """安装语言包

        Args:
            current_build_path: 当前构建路径
            language: 语言代码

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            from core.winpe_packages import WinPEPackages
            winpe_packages = WinPEPackages()
            language_packages = winpe_packages.get_language_packages(language)

            if not language_packages:
                logger.info(f"语言 {language} 无需额外的语言支持包")
                return True, f"语言 {language} 无需额外的语言支持包"

            logger.info(f"🌐 安装语言支持包: {language}")
            logger.info(f"   语言包列表: {', '.join(language_packages)}")

            return self.add_packages(current_build_path, language_packages)

        except Exception as e:
            error_msg = f"安装语言包时发生错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg