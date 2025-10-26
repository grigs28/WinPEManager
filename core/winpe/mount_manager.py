#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
镜像挂载管理模块
负责WinPE镜像的挂载和卸载操作
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger("WinPEManager")


class MountManager:
    """WinPE镜像挂载管理器"""

    def __init__(self, config_manager, adk_manager, parent_callback=None):
        self.config = config_manager
        self.adk = adk_manager
        self.parent_callback = parent_callback

    def check_and_request_admin_privileges(self) -> bool:
        """检查并请求管理员权限"""
        import ctypes
        from PyQt5.QtWidgets import QMessageBox, QApplication
        import sys

        if ctypes.windll.shell32.IsUserAnAdmin():
            return True

        # 由于我们在MountManager类中，需要通过其他方式显示消息框
        # 这里先返回False，让上层处理权限请求
        logger.error("DISM操作需要管理员权限，但当前程序没有管理员权限")
        return False

    def mount_winpe_image(self, current_build_path: Path, wim_file_path: Optional[Path] = None) -> Tuple[bool, str]:
        """挂载WinPE镜像

        Args:
            current_build_path: 当前构建路径
            wim_file_path: 指定的WIM文件路径（可选）

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not current_build_path:
                return False, "工作空间未初始化"

            # 确定要挂载的WIM文件
            if wim_file_path and wim_file_path.exists():
                wim_file = wim_file_path
                logger.info(f"使用指定的WIM文件: {wim_file}")
            else:
                # 默认挂载boot.wim（既是工作镜像也是启动镜像）
                wim_file = current_build_path / "media" / "sources" / "boot.wim"
                logger.info(f"使用默认的boot.wim文件: {wim_file}")

            mount_dir = current_build_path / "mount"

            logger.info(f"准备挂载WIM镜像")
            logger.info(f"镜像文件: {wim_file}")
            logger.info(f"挂载目录: {mount_dir}")

            # 检查WIM文件
            if not wim_file.exists():
                logger.error(f"WIM文件不存在: {wim_file}")
                return False, f"WIM文件不存在: {wim_file}"

            # 检查WIM文件大小
            wim_size = wim_file.stat().st_size
            logger.info(f"WIM文件大小: {wim_size:,} 字节 ({wim_size/1024/1024:.1f} MB)")
            # 对于不同类型的WIM文件，使用不同的大小阈值
            if wim_file.name.lower() == "boot.wim":
                if wim_size < 100 * 1024 * 1024:  # 小于100MB可能有问题
                    logger.warning(f"boot.wim文件大小异常小: {wim_size/1024/1024:.1f} MB，可能复制不完整")
            elif wim_file.name.lower() == "winpe.wim":
                if wim_size < 200 * 1024 * 1024:  # 小于200MB可能有问题
                    logger.warning(f"winpe.wim文件大小异常小: {wim_size/1024/1024:.1f} MB，可能复制不完整")
            else:
                if wim_size < 50 * 1024 * 1024:  # 小于50MB可能有问题
                    logger.warning(f"WIM文件大小异常小: {wim_size/1024/1024:.1f} MB，可能复制不完整")

            # 清理并创建挂载目录
            if mount_dir.exists():
                existing_files = list(mount_dir.iterdir())
                if existing_files:
                    logger.warning(f"检测到挂载目录不为空，包含 {len(existing_files)} 个文件/目录")
                    logger.info("尝试清理挂载目录...")
                    cleanup_success, cleanup_msg = self.unmount_winpe_image(current_build_path, discard=True)
                    if cleanup_success:
                        logger.info("挂载目录清理成功")
                    else:
                        logger.warning(f"挂载目录清理失败: {cleanup_msg}")

                    # 强制删除挂载目录内容
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

    def unmount_winpe_image(self, current_build_path: Path, discard: bool = False) -> Tuple[bool, str]:
        """卸载WinPE镜像

        Args:
            current_build_path: 当前构建路径
            discard: 是否放弃更改

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not current_build_path:
                return False, "工作空间未初始化"

            # 现在挂载的是boot.wim文件
            mount_dir = current_build_path / "mount"

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

    def is_mounted(self, current_build_path: Path) -> bool:
        """检查镜像是否已挂载

        Args:
            current_build_path: 当前构建路径

        Returns:
            bool: 是否已挂载
        """
        try:
            mount_dir = current_build_path / "mount"
            if not mount_dir.exists():
                return False

            # 检查挂载目录是否为空
            return bool(list(mount_dir.iterdir()))
        except Exception as e:
            logger.error(f"检查挂载状态时发生错误: {str(e)}")
            return False

    def ensure_unmounted(self, current_build_path: Path) -> Tuple[bool, str]:
        """确保镜像已卸载，如果已挂载则先卸载

        Args:
            current_build_path: 当前构建路径

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if self.is_mounted(current_build_path):
                logger.info("检测到镜像已挂载，正在卸载...")
                return self.unmount_winpe_image(current_build_path, discard=False)
            else:
                logger.info("镜像未挂载，可直接进行后续操作")
                return True, "镜像未挂载"
        except Exception as e:
            error_msg = f"确保镜像卸载时发生错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def cleanup_mount_directory(self, current_build_path: Path) -> bool:
        """清理挂载目录

        Args:
            current_build_path: 当前构建路径

        Returns:
            bool: 是否成功清理
        """
        try:
            mount_dir = current_build_path / "mount"
            
            if not mount_dir.exists():
                return True

            # 如果目录不为空，先尝试卸载
            if list(mount_dir.iterdir()):
                success, _ = self.unmount_winpe_image(current_build_path, discard=True)
                if not success:
                    logger.warning("卸载失败，尝试强制删除挂载目录")

            # 强制删除目录
            if mount_dir.exists():
                shutil.rmtree(mount_dir, ignore_errors=True)
                logger.info("挂载目录已清理")

            return True
        except Exception as e:
            logger.error(f"清理挂载目录时发生错误: {str(e)}")
            return False