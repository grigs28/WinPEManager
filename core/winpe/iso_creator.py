#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISO创建模块
负责可启动ISO文件的创建
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger("WinPEManager")


class ISOCreator:
    """WinPE ISO创建器"""

    def __init__(self, config_manager, adk_manager, parent_callback=None):
        self.config = config_manager
        self.adk = adk_manager
        self.parent_callback = parent_callback

    def create_bootable_iso(self, current_build_path: Path, iso_path: Optional[str] = None) -> Tuple[bool, str]:
        """创建可启动的ISO文件

        Args:
            current_build_path: 当前构建路径
            iso_path: ISO输出路径，如果为None则使用默认路径

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not current_build_path:
                return False, "工作空间未初始化"

            # 确保镜像已卸载（ISO创建前必须卸载）
            logger.info("ISO创建前检查镜像挂载状态...")
            mount_dir = current_build_path / "mount"
            if mount_dir.exists() and any(mount_dir.iterdir()):
                logger.info("检测到镜像仍处于挂载状态，正在卸载...")
                from .mount_manager import MountManager
                mount_manager = MountManager(self.config, self.adk, self.parent_callback)
                unmount_success, unmount_msg = mount_manager.unmount_winpe_image(current_build_path, discard=False)
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
                    workspace = self.config.get("output.workspace", "")
                    if not workspace:
                        workspace = Path.cwd() / "workspace" / "WinPE_Build"
                    iso_path = workspace / "WinPE.iso"

            iso_path = Path(iso_path)

            # 根据配置选择ISO创建方式
            build_method = self.config.get("winpe.build_method", "copype")
            
            if build_method == "copype":
                logger.info("🚀 使用MakeWinPEMedia工具创建ISO（copype模式）")
                return self._create_iso_with_makewinpe_media(current_build_path, iso_path)
            else:
                logger.info("🔧 使用Oscdimg工具创建ISO（传统DISM模式）")
                # 查找Oscdimg工具
                oscdimg_path = self._find_oscdimg()
                if not oscdimg_path:
                    return False, "找不到Oscdimg工具"

                return self._create_iso_with_oscdimg(current_build_path, iso_path, oscdimg_path)

        except Exception as e:
            error_msg = f"创建ISO时发生错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _create_iso_with_oscdimg(self, current_build_path: Path, iso_path: Path, oscdimg_path: Path) -> Tuple[bool, str]:
        """使用Oscdimg工具创建ISO文件

        Args:
            current_build_path: 当前构建路径
            iso_path: ISO输出路径
            oscdimg_path: Oscdimg工具路径

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 准备ISO文件内容（使用小写目录名，符合官方标准）
            media_path = current_build_path / "media"
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
            error_msg = f"使用Oscdimg创建ISO时发生错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _create_iso_with_makewinpe_media(self, current_build_path: Path, iso_path: Path) -> Tuple[bool, str]:
        """使用MakeWinPEMedia创建ISO文件

        Args:
            current_build_path: 当前构建路径
            iso_path: ISO输出路径

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            logger.info("使用MakeWinPEMedia创建ISO文件...")
            logger.info(f"源目录: {current_build_path}")
            logger.info(f"目标ISO: {iso_path}")

            # 查找MakeWinPEMedia.cmd
            makewinpe_path = self._find_makewinpe_media()
            if not makewinpe_path:
                return False, "找不到MakeWinPEMedia工具"

            # 检查源目录结构
            media_path = current_build_path / "media"
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
            cmd = [str(makewinpe_path), "/iso", str(current_build_path), str(iso_path)]
            logger.info(f"执行命令: {' '.join(cmd)}")

            # 设置环境变量，确保能找到oscdimg
            old_path = os.environ.get('PATH', '')
            oscdimg_dir = r"C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg"
            new_path = f"{oscdimg_dir};{old_path}"
            os.environ['PATH'] = new_path

            # 执行命令
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

    def validate_iso_requirements(self, current_build_path: Path) -> Tuple[bool, List[str]]:
        """验证ISO创建的先决条件

        Args:
            current_build_path: 当前构建路径

        Returns:
            Tuple[bool, List[str]]: (是否满足条件, 缺失的项目列表)
        """
        try:
            missing_items = []
            media_path = current_build_path / "media"

            # 检查Media目录
            if not media_path.exists():
                missing_items.append("Media目录")
                return False, missing_items

            # 检查关键文件
            critical_files = [
                media_path / "sources" / "boot.wim",
                media_path / "Boot" / "etfsboot.com"
            ]

            for file_path in critical_files:
                if not file_path.exists():
                    missing_items.append(str(file_path.relative_to(media_path)))

            # 检查挂载状态
            mount_dir = current_build_path / "mount"
            if mount_dir.exists() and any(mount_dir.iterdir()):
                missing_items.append("镜像需要先卸载")

            return len(missing_items) == 0, missing_items

        except Exception as e:
            logger.error(f"验证ISO创建条件时发生错误: {str(e)}")
            return False, ["验证过程出错"]

    def estimate_iso_size(self, current_build_path: Path) -> Optional[int]:
        """估算ISO文件大小

        Args:
            current_build_path: 当前构建路径

        Returns:
            Optional[int]: 估算的ISO大小（字节），如果无法估算则返回None
        """
        try:
            media_path = current_build_path / "media"
            if not media_path.exists():
                return None

            # 计算Media目录中所有文件的总大小
            total_size = 0
            for file_path in media_path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size

            # 添加ISO文件系统开销（约5%）
            estimated_size = int(total_size * 1.05)
            return estimated_size

        except Exception as e:
            logger.error(f"估算ISO大小时发生错误: {str(e)}")
            return None