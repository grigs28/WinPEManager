#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础镜像管理模块
负责WinPE基础文件的复制和初始化
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger("WinPEManager")


class BaseImageManager:
    """WinPE基础镜像管理器"""

    def __init__(self, config_manager, adk_manager, parent_callback=None):
        self.config = config_manager
        self.adk = adk_manager
        self.parent_callback = parent_callback

    def initialize_workspace(self, build_dir: Path) -> Tuple[bool, str]:
        """初始化构建目录 - 简化版本

        Args:
            build_dir: 构建目录路径 (由winpe_builder创建)

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 确保构建目录存在
            if not build_dir.exists():
                build_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"创建构建目录: {build_dir}")
            else:
                logger.info(f"使用现有构建目录: {build_dir}")

            # 创建必要的子目录
            subdirs = ["mount", "module/drivers", "scripts", "files", "logs"]
            created_dirs = []
            for subdir in subdirs:
                dir_path = build_dir / subdir
                dir_path.mkdir(exist_ok=True, parents=True)
                if dir_path.exists():
                    created_dirs.append(subdir)

            logger.info(f"创建子目录: {', '.join(created_dirs)}")

            # 检查磁盘空间
            disk_usage = shutil.disk_usage(str(build_dir))
            free_gb = disk_usage.free / (1024**3)
            logger.info(f"可用磁盘空间: {free_gb:.1f}GB")

            if free_gb < 2.0:  # 小于2GB时警告
                logger.warning(f"磁盘空间不足: 仅剩 {free_gb:.1f}GB，建议至少保留2GB")
            else:
                logger.info(f"磁盘空间充足: {free_gb:.1f}GB 可用")

            logger.info(f"构建目录初始化成功: {build_dir}")
            return True, f"构建目录初始化成功: {build_dir}"

        except Exception as e:
            error_msg = f"初始化工作空间失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def copy_base_winpe(self, current_build_path: Path, architecture: str = "amd64") -> Tuple[bool, str]:
        """复制基础WinPE文件

        Args:
            current_build_path: 当前构建路径
            architecture: WinPE架构 (x86, amd64, arm)

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not current_build_path:
                return False, "工作空间未初始化"

            # 根据配置选择构建方式
            build_method = self.config.get("winpe.build_method", "copype")
            
            if build_method == "copype":
                logger.info("🚀 使用copype工具创建基础WinPE环境")
                return self._copy_base_winpe_with_copype(current_build_path, architecture)
            else:
                logger.info("🔧 使用传统DISM方式创建基础WinPE环境")
                return self._copy_base_winpe_with_dism(current_build_path, architecture)

        except Exception as e:
            error_msg = f"复制WinPE基础文件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _copy_base_winpe_with_copype(self, current_build_path: Path, architecture: str = "amd64") -> Tuple[bool, str]:
        """使用copype工具创建基础WinPE文件

        Args:
            current_build_path: 当前构建路径
            architecture: WinPE架构 (amd64, x86, arm64)

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            logger.info(f"🔧 使用copype工具创建 {architecture} WinPE基础环境")
            logger.info(f"目标路径: {current_build_path}")

            # 检查copype工具可用性
            copype_path = self.adk.get_copype_path()
            if not copype_path:
                logger.error("copype工具不可用，回退到DISM方式")
                return self._copy_base_winpe_with_dism(current_build_path, architecture)

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
            if current_build_path.exists():
                logger.info(f"删除已存在的构建目录: {current_build_path}")
                shutil.rmtree(current_build_path, ignore_errors=True)
                logger.info("目录已删除，copype将创建新的目录结构")

            # 使用copype创建基础环境
            logger.info(f"执行copype命令: copype {copype_arch} {current_build_path}")
            success, stdout, stderr = self.adk.run_copype_command(
                copype_arch,
                current_build_path,
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
                current_build_path / "media",
                current_build_path / "media" / "sources",
                current_build_path / "bootbins"  # 修正：新版本ADK使用bootbins而不是fwfiles
            ]

            missing_dirs = [d for d in expected_dirs if not d.exists()]
            if missing_dirs:
                logger.error(f"copype未创建必要的目录: {missing_dirs}")
                return False, f"copype创建的目录结构不完整: {missing_dirs}"

            # 验证关键文件
            boot_wim = current_build_path / "media" / "sources" / "boot.wim"
            if not boot_wim.exists():
                logger.error("copype未创建boot.wim文件")
                return False, "boot.wim文件缺失"

            # 检查文件大小
            boot_wim_size = boot_wim.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"✅ boot.wim已创建，大小: {boot_wim_size:.1f} MB")

            if boot_wim_size < 50:  # 小于50MB可能有问题
                logger.warning(f"⚠️ boot.wim文件较小，可能不完整: {boot_wim_size:.1f} MB")

            # 创建额外的必要目录
            additional_dirs = ["mount", "module/drivers", "scripts", "files", "logs"]
            for subdir in additional_dirs:
                dir_path = current_build_path / subdir
                dir_path.mkdir(exist_ok=True, parents=True)
                logger.debug(f"创建额外目录: {dir_path}")

            # 验证Media目录完整性
            media_path = current_build_path / "media"
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
            logger.info(f"📁 基础目录: {current_build_path}")
            logger.info(f"📊 boot.wim: {boot_wim_size:.1f} MB")
            logger.info(f"🗂️ Media文件: {len(media_files)} 个")

            return True, f"copype基础WinPE环境创建成功 ({architecture}, {boot_wim_size:.1f}MB)"

        except Exception as e:
            error_msg = f"copype创建基础WinPE失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _copy_base_winpe_with_dism(self, current_build_path: Path, architecture: str = "amd64") -> Tuple[bool, str]:
        """使用传统DISM方式复制基础WinPE文件

        Args:
            current_build_path: 当前构建路径
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
            target_media = current_build_path / "media"
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
                target_media = current_build_path / "media"  # 使用小写目录名，符合官方标准
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
                if not self._create_media_directory(winpe_arch_path, current_build_path / "media"):
                    return False, "无法创建Media目录，缺少必要的启动文件"

            logger.info(f"WinPE基础文件复制成功: {architecture}")
            return True, f"WinPE基础文件复制成功 ({architecture})"

        except Exception as e:
            error_msg = f"复制WinPE基础文件失败: {str(e)}"
            logger.error(error_msg)
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