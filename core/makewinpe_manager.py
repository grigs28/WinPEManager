#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MakeWinPEMedia统一管理模块
负责管理MakeWinPEMedia命令执行和ISO、WIM映像创建
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable
import logging

logger = logging.getLogger("WinPEManager")


class MakeWinPEMediaManager:
    """MakeWinPEMedia统一管理器类"""

    def __init__(self, adk_manager, progress_callback=None):
        """
        初始化MakeWinPEMedia管理器

        Args:
            adk_manager: ADK管理器实例
            progress_callback: 进度回调函数 (可选)
        """
        self.adk_manager = adk_manager
        self.progress_callback = progress_callback
        self.logger = logger

    def find_makewinpe_path(self) -> Optional[Path]:
        """查找MakeWinPEMedia.cmd路径"""
        try:
            # 首先从ADK管理器获取
            if self.adk_manager:
                makewinpe_path = self.adk_manager.get_make_winpe_media_path()
                if makewinpe_path and makewinpe_path.exists():
                    self.logger.info(f"找到MakeWinPEMedia路径: {makewinpe_path}")
                    return makewinpe_path

            # 手动搜索常见路径
            possible_paths = [
                Path("C:/Program Files (x86)/Windows Kits/10/Assessment and Deployment Kit/Deployment Tools/amd64/MakeWinPEMedia.cmd"),
                Path("C:/Program Files/Windows Kits/10/Assessment and Deployment Kit/Deployment Tools/amd64/MakeWinPEMedia.cmd"),
                Path("C:/Windows/System32/MakeWinPEMedia.cmd")
            ]

            for path in possible_paths:
                if path.exists():
                    self.logger.info(f"手动找到MakeWinPEMedia路径: {path}")
                    return path

            print("未找到MakeWinPEMedia工具")
            return None

        except Exception as e:
            print(f"查找MakeWinPEMedia路径时发生错误: {e} [异常]")
            self.logger.error(f"查找MakeWinPEMedia路径时发生错误: {str(e)}")
            return None

    def run_makewinpe(self, args: List[str], working_dir: Optional[Path] = None) -> Tuple[bool, str]:
        """
        运行MakeWinPEMedia命令

        Args:
            args: MakeWinPEMedia命令参数
            working_dir: 工作目录

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        makewinpe_path = self.find_makewinpe_path()
        if not makewinpe_path:
            return False, "找不到MakeWinPEMedia工具"

        try:
            # 构建完整命令
            cmd = [str(makewinpe_path)] + args
            print(f"执行命令: {' '.join(cmd)} [MakeWinPEMedia]")
            self.logger.info(f"执行MakeWinPEMedia命令: {' '.join(cmd)}")

            # 执行命令
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=False,
                timeout=600,  # 10分钟超时
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            success = result.returncode == 0

            # 处理输出
            from utils.encoding import safe_decode
            stdout = safe_decode(result.stdout) if result.stdout else ""
            stderr = safe_decode(result.stderr) if result.stderr else ""

            if success:
                success_msg = "MakeWinPEMedia命令执行成功"
                print(f"{success_msg} [成功]")
                self.logger.info(success_msg)
                if stdout:
                    print(f"输出: {stdout[:100]}... [MakeWinPEMedia]")
                return True, success_msg
            else:
                error_msg = f"MakeWinPEMedia命令执行失败，返回码: {result.returncode}"
                print(f"{error_msg} [失败]")
                if stderr:
                    print(f"错误详情: {stderr[:200]} [错误]")
                self.logger.error(f"{error_msg}\n错误输出: {stderr}")
                return False, error_msg

        except subprocess.TimeoutExpired:
            error_msg = "MakeWinPEMedia命令执行超时（10分钟）"
            print(f"{error_msg} [错误]")
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"执行MakeWinPEMedia命令时发生错误: {str(e)}"
            print(f"{error_msg} [异常]")
            self.logger.error(error_msg)
            return False, error_msg

    def create_winpe_iso(self, workspace_path: Path, iso_path: Path,
                        progress_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """
        创建WinPE ISO文件

        Args:
            workspace_path: WinPE工作空间路径
            iso_path: 输出ISO文件路径
            progress_callback: 进度回调函数

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        if not workspace_path.exists():
            error_msg = f"WinPE工作空间不存在: {workspace_path}"
            print(f"{error_msg} [错误]")
            return False, error_msg

        if not workspace_path / "media":
            error_msg = f"WinPE media目录不存在: {workspace_path / 'media'}"
            print(f"{error_msg} [错误]")
            return False, error_msg

        # 确保ISO输出目录存在
        iso_path.parent.mkdir(parents=True, exist_ok=True)

        # 如果ISO文件已存在，先删除
        if iso_path.exists():
            try:
                iso_path.unlink()
                print(f"删除已存在的ISO文件: {iso_path} [清理]")
            except Exception as e:
                print(f"无法删除已存在的ISO文件: {e} [警告]")

        # 构建MakeWinPEMedia命令
        args = ["/ISO", str(workspace_path), str(iso_path)]

        print(f"开始创建WinPE ISO [MakeWinPEMedia]")
        print(f"工作空间: {workspace_path} [MakeWinPEMedia]")
        print(f"输出ISO: {iso_path} [MakeWinPEMedia]")

        # 执行命令
        success, message = self.run_makewinpe(args)

        if success:
            # 验证ISO文件是否创建成功
            if iso_path.exists():
                file_size = iso_path.stat().st_size / (1024 * 1024)  # MB
                success_msg = f"ISO创建成功，文件大小: {file_size:.1f} MB"
                print(f"{success_msg} [成功]")
                return True, success_msg
            else:
                error_msg = "MakeWinPEMedia执行成功但ISO文件不存在"
                print(f"{error_msg} [错误]")
                return False, error_msg
        else:
            return False, message

    def create_bootable_usb(self, workspace_path: Path, usb_drive: str,
                           progress_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """
        创建可启动U盘

        Args:
            workspace_path: WinPE工作空间路径
            usb_drive: U盘驱动器号 (如 "E:")
            progress_callback: 进度回调函数

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        if not workspace_path.exists():
            error_msg = f"WinPE工作空间不存在: {workspace_path}"
            print(f"{error_msg} [错误]")
            return False, error_msg

        # 验证U盘驱动器
        if not usb_drive.endswith(':'):
            usb_drive += ':'

        # 构建MakeWinPEMedia命令
        args = ["/USB", str(workspace_path), usb_drive]

        print(f"开始创建可启动U盘 [MakeWinPEMedia]")
        print(f"工作空间: {workspace_path} [MakeWinPEMedia]")
        print(f"U盘驱动器: {usb_drive} [MakeWinPEMedia]")
        print("警告: 此操作将格式化U盘，请确保U盘中没有重要数据 [警告]")

        # 执行命令
        success, message = self.run_makewinpe(args)

        if success:
            success_msg = f"可启动U盘创建成功: {usb_drive}"
            print(f"{success_msg} [成功]")
            return True, success_msg
        else:
            return False, message

    def create_wim_from_media(self, media_path: Path, wim_path: Path,
                            progress_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """
        从媒体创建WIM文件

        Args:
            media_path: 媒体路径
            wim_path: 输出WIM文件路径
            progress_callback: 进度回调函数

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        if not media_path.exists():
            error_msg = f"媒体路径不存在: {media_path}"
            print(f"{error_msg} [错误]")
            return False, error_msg

        # 确保WIM输出目录存在
        wim_path.parent.mkdir(parents=True, exist_ok=True)

        # 如果WIM文件已存在，先删除
        if wim_path.exists():
            try:
                wim_path.unlink()
                print(f"删除已存在的WIM文件: {wim_path} [清理]")
            except Exception as e:
                print(f"无法删除已存在的WIM文件: {e} [警告]")

        # 使用DISM创建WIM文件
        if self.adk_manager:
            print(f"开始从媒体创建WIM文件 [MakeWinPEMedia]")
            print(f"源路径: {media_path} [MakeWinPEMedia]")
            print(f"输出WIM: {wim_path} [MakeWinPEMedia]")

            args = ["/Capture-Image", "/ImageFile:" + str(wim_path),
                   "/CaptureDir:" + str(media_path), "/Name:WinPE"]

            success, stdout, stderr = self.adk_manager.run_dism_command(args)

            if success:
                # 验证WIM文件是否创建成功
                if wim_path.exists():
                    file_size = wim_path.stat().st_size / (1024 * 1024)  # MB
                    success_msg = f"WIM文件创建成功，文件大小: {file_size:.1f} MB"
                    print(f"{success_msg} [成功]")
                    return True, success_msg
                else:
                    error_msg = "DISM执行成功但WIM文件不存在"
                    print(f"{error_msg} [错误]")
                    return False, error_msg
            else:
                error_msg = f"DISM创建WIM失败: {stderr}"
                print(f"{error_msg} [失败]")
                return False, error_msg
        else:
            error_msg = "ADK管理器不可用，无法执行DISM命令"
            print(f"{error_msg} [错误]")
            return False, error_msg

    def cleanup_temp_files(self, workspace_path: Path) -> Tuple[bool, str]:
        """
        清理临时文件

        Args:
            workspace_path: 工作空间路径

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if workspace_path.exists():
                shutil.rmtree(workspace_path, ignore_errors=True)
                success_msg = f"已清理临时目录: {workspace_path}"
                print(f"{success_msg} [清理]")
                return True, success_msg
            else:
                success_msg = "临时目录不存在，无需清理"
                print(f"{success_msg} [清理]")
                return True, success_msg
        except Exception as e:
            error_msg = f"清理临时文件时发生错误: {str(e)}"
            print(f"{error_msg} [异常]")
            return False, error_msg

    def validate_winpe_workspace(self, workspace_path: Path) -> Tuple[bool, str]:
        """
        验证WinPE工作空间的完整性

        Args:
            workspace_path: 工作空间路径

        Returns:
            Tuple[bool, str]: (成功状态, 验证消息)
        """
        try:
            if not workspace_path.exists():
                return False, f"工作空间目录不存在: {workspace_path}"

            # 检查必要文件和目录
            required_files = [
                workspace_path / "media" / "sources" / "boot.wim",
                workspace_path / "media" / "boot" / "etfsboot.com"
            ]

            required_dirs = [
                workspace_path / "media",
                workspace_path / "media" / "sources",
                workspace_path / "media" / "boot",
                workspace_path / "media" / "efi"
            ]

            missing_files = []
            missing_dirs = []

            for file_path in required_files:
                if not file_path.exists():
                    missing_files.append(str(file_path))

            for dir_path in required_dirs:
                if not dir_path.exists():
                    missing_dirs.append(str(dir_path))

            if not missing_files and not missing_dirs:
                success_msg = "WinPE工作空间验证通过"
                print(f"{success_msg} [验证]")
                return True, success_msg
            else:
                error_msg = "WinPE工作空间验证失败:\n"
                if missing_files:
                    error_msg += f"  缺少文件: {', '.join(missing_files)}\n"
                if missing_dirs:
                    error_msg += f"  缺少目录: {', '.join(missing_dirs)}"
                print(f"{error_msg} [验证]")
                return False, error_msg

        except Exception as e:
            error_msg = f"验证WinPE工作空间时发生错误: {str(e)}"
            print(f"{error_msg} [异常]")
            return False, error_msg