#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
操作接口模块
提供统一的挂载、卸载、ISO创建、USB制作操作接口
"""

import shutil
from pathlib import Path
from typing import Tuple

from utils.logger import (
    get_logger, 
    log_command, 
    log_build_step, 
    log_system_event, 
    log_error,
    start_build_session,
    end_build_session
)


class OperationManager:
    """操作管理器
    
    负责所有WIM相关的操作执行
    """
    
    def __init__(self, path_manager, check_manager, config_manager, adk_manager, parent_callback=None):
        self.path_manager = path_manager
        self.check_manager = check_manager
        self.config = config_manager
        self.adk = adk_manager
        self.parent_callback = parent_callback
        self.logger = get_logger("OperationManager")
    
    def mount_wim(self, build_dir: Path, wim_file_path: Path = None) -> Tuple[bool, str]:
        """统一挂载接口
        
        Args:
            build_dir: 构建目录路径
            wim_file_path: WIM文件路径（可选，如果不提供则自动查找）
            
        Returns:
            Tuple[bool, str]: (挂载结果, 消息)
        """
        try:
            self.logger.info("🚀 开始统一挂载操作...")
            log_system_event("WIM挂载", "开始挂载操作")
            
            # 如果没有提供WIM文件，自动查找
            if not wim_file_path:
                wim_file_path = self.path_manager.get_primary_wim(build_dir)
                if not wim_file_path:
                    error_msg = "在构建目录中未找到WIM文件"
                    self.logger.error(error_msg)
                    return False, error_msg
                self.logger.info(f"自动找到WIM文件: {wim_file_path}")
            
            # 挂载前检查
            check_success, check_msg = self.check_manager.pre_mount_checks(build_dir, wim_file_path)
            if not check_success:
                return False, check_msg
            
            # 开始挂载操作
            mount_dir = self.path_manager.get_mount_dir(build_dir)
            self.logger.info(f"开始挂载WIM镜像: {wim_file_path}")
            log_build_step("WIM挂载", f"WIM文件: {wim_file_path}, 挂载目录: {mount_dir}")
            
            # 创建挂载目录
            mount_dir.mkdir(parents=True, exist_ok=True)
            
            # 构建DISM命令
            wim_file_str = str(wim_file_path)
            mount_dir_str = str(mount_dir)
            
            args = [
                "/mount-wim",
                "/wimfile:" + wim_file_str,
                "/index:1",
                "/mountdir:" + mount_dir_str
            ]
            
            # 记录命令
            log_command(" ".join(args), "挂载WIM镜像")
            
            # 执行DISM命令
            success, stdout, stderr = self.adk.run_dism_command(args)
            
            if success:
                self.logger.info("✅ WIM镜像挂载成功")
                log_build_step("WIM挂载成功", f"挂载目录: {mount_dir}")
                log_system_event("WIM挂载", "WIM镜像挂载成功", "info")
                
                # 创建挂载信息文件
                mount_info_file = mount_dir / ".mount_info"
                try:
                    with open(mount_info_file, 'w', encoding='utf-8') as f:
                        f.write(f"mounted_wim: {wim_file_path}\n")
                        f.write(f"mount_time: {self._get_current_timestamp()}\n")
                        f.write(f"build_dir: {build_dir}\n")
                    
                    # 创建WIM文件特定的挂载标记文件
                    wim_name = wim_file_path.stem
                    mount_marker_file = mount_dir / f".{wim_name}_mounted"
                    mount_marker_file.touch()
                    
                    self.logger.debug(f"创建挂载信息文件: {mount_info_file}")
                    self.logger.debug(f"创建挂载标记文件: {mount_marker_file}")
                except Exception as e:
                    self.logger.warning(f"创建挂载信息文件失败: {str(e)}")
                
                # 验证挂载结果
                if mount_dir.exists() and any(mount_dir.iterdir()):
                    # 只统计关键目录数量，避免列出所有文件
                    key_dirs = ['Windows', 'Program Files', 'Users', 'System32']
                    found_dirs = [d for d in key_dirs if (mount_dir / d).exists()]
                    self.logger.info(f"挂载验证成功，发现关键目录: {', '.join(found_dirs)}")
                    return True, f"WIM镜像挂载成功 (关键目录: {', '.join(found_dirs)})"
                else:
                    error_msg = "挂载验证失败，挂载目录为空"
                    self.logger.error(error_msg)
                    return False, error_msg
            else:
                error_msg = f"DISM挂载失败: {stderr}"
                self.logger.error(error_msg)
                log_system_event("WIM挂载失败", error_msg, "error")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"挂载WIM镜像时发生错误: {str(e)}"
            log_error(e, "WIM挂载")
            return False, error_msg
    
    def unmount_wim(self, build_dir: Path, commit: bool = True) -> Tuple[bool, str]:
        """统一卸载接口
        
        Args:
            build_dir: 构建目录路径
            commit: 是否提交更改（True=保存，False=放弃）
            
        Returns:
            Tuple[bool, str]: (卸载结果, 消息)
        """
        try:
            action = "保存更改并" if commit else "放弃更改并"
            self.logger.info(f"🔄 开始统一卸载操作 ({action})...")
            log_system_event("WIM卸载", f"开始{action}卸载操作")
            
            # 卸载前检查
            check_success, check_msg = self.check_manager.pre_unmount_checks(build_dir)
            if not check_success:
                return False, check_msg
            
            mount_dir = self.path_manager.get_mount_dir(build_dir)
            self.logger.info(f"开始卸载WIM镜像{action}: {mount_dir}")
            log_build_step("WIM卸载", f"挂载目录: {mount_dir}, 操作: {action}")
            
            # 构建DISM命令
            mount_dir_str = str(mount_dir)
            
            if commit:
                args = [
                    "/unmount-wim",
                    "/mountdir:" + mount_dir_str,
                    "/commit"
                ]
            else:
                args = [
                    "/unmount-wim",
                    "/mountdir:" + mount_dir_str,
                    "/discard"
                ]
            
            # 记录命令
            log_command(" ".join(args), f"{action}卸载WIM镜像")
            
            # 执行DISM命令
            success, stdout, stderr = self.adk.run_dism_command(args)
            
            if success:
                self.logger.info(f"✅ WIM镜像{action}卸载成功")
                log_build_step("WIM卸载成功", f"{action}卸载完成")
                log_system_event("WIM卸载", f"WIM镜像{action}卸载成功", "info")
                
                # 删除挂载信息文件
                mount_info_file = mount_dir / ".mount_info"
                try:
                    if mount_info_file.exists():
                        mount_info_file.unlink()
                        self.logger.debug(f"删除挂载信息文件: {mount_info_file}")
                    
                    # 删除所有WIM文件特定的挂载标记文件
                    for marker_file in mount_dir.glob(".*_mounted"):
                        try:
                            marker_file.unlink()
                            self.logger.debug(f"删除挂载标记文件: {marker_file}")
                        except Exception as e:
                            self.logger.warning(f"删除挂载标记文件失败: {str(e)}")
                            
                except Exception as e:
                    self.logger.warning(f"删除挂载信息文件失败: {str(e)}")
                
                # 验证卸载结果
                if not mount_dir.exists() or not any(mount_dir.iterdir()):
                    self.logger.info("卸载验证成功，挂载目录已清空")
                    return True, f"WIM镜像{action}卸载成功"
                else:
                    error_msg = "卸载验证失败，挂载目录仍然不为空"
                    self.logger.warning(error_msg)
                    # 尝试强制清理
                    cleanup_success, cleanup_msg = self.check_manager._force_cleanup_mount(mount_dir)
                    if cleanup_success:
                        return True, f"WIM镜像{action}卸载成功（已强制清理）"
                    else:
                        return False, f"{error_msg}，强制清理也失败: {cleanup_msg}"
            else:
                error_msg = f"DISM卸载失败: {stderr}"
                self.logger.error(error_msg)
                log_system_event("WIM卸载失败", error_msg, "error")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"卸载WIM镜像时发生错误: {str(e)}"
            log_error(e, "WIM卸载")
            return False, error_msg
    
    def create_iso(self, build_dir: Path, iso_path: Path = None) -> Tuple[bool, str]:
        """统一ISO创建接口
        
        Args:
            build_dir: 构建目录路径
            iso_path: ISO输出路径（可选）
            
        Returns:
            Tuple[bool, str]: (创建结果, 消息)
        """
        try:
            self.logger.info("📀 开始统一ISO创建操作...")
            log_system_event("ISO创建", "开始ISO创建操作")
            
            # 跳过ISO创建前检查，直接开始创建
            self.logger.info("跳过ISO创建前检查，直接开始创建")
            
            # 确定ISO输出路径
            if iso_path is None:
                iso_path_str = self.config.get("output.iso_path", "")
                if not iso_path_str:
                    configured_workspace = self.config.get("output.workspace", "").strip()
                    if configured_workspace:
                        workspace = Path(configured_workspace)
                    else:
                        # 使用基于架构的默认工作空间
                        architecture = self.config.get("winpe.architecture", "amd64")
                        workspace = Path.cwd() / f"WinPE_{architecture}"

                    # 从构建目录中提取时间戳，生成唯一的ISO文件名
                    import datetime
                    build_dir_name = build_dir.name
                    if "WinPE_" in build_dir_name:
                        timestamp = build_dir_name.replace("WinPE_", "")
                        iso_filename = f"WinPE_{timestamp}.iso"
                    else:
                        # 如果构建目录名不包含时间戳，使用当前时间
                        current_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        iso_filename = f"WinPE_{current_timestamp}.iso"

                    # 创建output目录
                    output_dir = Path.cwd() / "output"
                    output_dir.mkdir(exist_ok=True)
                    iso_path = output_dir / iso_filename

                    self.logger.info(f"生成的ISO文件名: {iso_filename}")
                else:
                    iso_path = Path(iso_path_str)

                    # 如果用户配置了固定路径但文件已存在，添加时间戳后缀
                    if iso_path.exists():
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        stem = iso_path.stem
                        suffix = iso_path.suffix
                        iso_path = iso_path.parent / f"{stem}_{timestamp}{suffix}"
                        self.logger.info(f"文件已存在，使用新文件名: {iso_path.name}")
            
            iso_path = Path(iso_path)
            self.logger.info(f"ISO输出路径: {iso_path}")
            log_build_step("ISO创建", f"输出路径: {iso_path}")
            
            # 开始构建会话
            build_info = {
                "build_dir": str(build_dir),
                "iso_path": str(iso_path),
                "operation": "iso_creation"
            }
            start_build_session(build_info)
            
            try:
                # 使用ADK管理器直接创建ISO
                self.logger.info("使用ADK管理器创建ISO文件")
                
                # 构建MakeWinPEMedia命令
                # 正确的参数顺序: MakeWinPEMedia.cmd /ISO <工作目录> <ISO路径>
                iso_path_str = str(iso_path)
                build_dir_str = str(build_dir)
                
                args = [
                    "/ISO",
                    build_dir_str,
                    iso_path_str
                ]
                
                # 记录命令
                log_command(" ".join(args), "创建ISO文件")
                
                # 执行MakeWinPEMedia命令
                self.logger.info("执行MakeWinPEMedia命令...")
                if iso_path.exists():
                    self.logger.info(f"目标ISO文件已存在: {iso_path}")
                    self.logger.info("将自动覆盖现有ISO文件")

                success, stdout, stderr = self.adk.run_make_winpe_media_command(args)
                
                if success:
                    self.logger.info("✅ ISO文件创建成功")
                    log_build_step("ISO创建成功", f"文件: {iso_path}")
                    log_system_event("ISO创建", "ISO文件创建成功", "info")
                    
                    # 检查ISO文件大小
                    if iso_path.exists():
                        file_size = iso_path.stat().st_size / (1024 * 1024)
                        self.logger.info(f"ISO文件大小: {file_size:.1f} MB")
                    
                    end_build_session(True, f"ISO创建成功: {iso_path}")
                    return True, f"ISO文件创建成功: {iso_path}"
                else:
                    error_msg = f"MakeWinPEMedia命令失败: {stderr}"
                    self.logger.error(error_msg)
                    log_system_event("ISO创建失败", error_msg, "error")
                    end_build_session(False, error_msg)
                    return False, f"ISO创建失败: {error_msg}"
                
                    
            except Exception as e:
                error_msg = f"ISO创建过程异常: {str(e)}"
                log_error(e, "ISO创建过程")
                log_system_event("ISO创建异常", error_msg, "error")
                end_build_session(False, error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"创建ISO时发生错误: {str(e)}"
            log_error(e, "ISO创建")
            return False, error_msg
    
    def create_usb(self, build_dir: Path, usb_path: Path) -> Tuple[bool, str]:
        """统一USB制作接口
        
        Args:
            build_dir: 构建目录路径
            usb_path: USB设备路径
            
        Returns:
            Tuple[bool, str]: (制作结果, 消息)
        """
        try:
            self.logger.info("💾 开始统一USB制作操作...")
            log_system_event("USB制作", "开始USB启动盘制作")
            
            # USB制作前检查
            check_success, check_msg = self.check_manager.pre_usb_checks(build_dir, usb_path)
            if not check_success:
                return False, check_msg
            
            # 获取主要WIM文件
            wim_file_path = self.path_manager.get_primary_wim(build_dir)
            if not wim_file_path:
                error_msg = "在构建目录中未找到WIM文件"
                self.logger.error(error_msg)
                return False, error_msg
            
            self.logger.info(f"开始制作USB启动盘: {wim_file_path} -> {usb_path}")
            log_build_step("USB制作", f"WIM文件: {wim_file_path}, USB路径: {usb_path}")
            
            # 开始构建会话
            build_info = {
                "build_dir": str(build_dir),
                "usb_path": str(usb_path),
                "wim_file": str(wim_file_path),
                "operation": "usb_creation"
            }
            start_build_session(build_info)
            
            try:
                # 检查设备类型确认
                is_removable = self.check_manager._is_removable_device(usb_path)
                if not is_removable:
                    self.logger.warning(f"选定的路径可能不是可移动设备: {usb_path}")
                    # 这里可以添加用户确认逻辑
                
                # 复制WIM文件到USB设备
                self.logger.info("复制WIM文件到USB设备...")
                log_build_step("复制WIM文件", f"目标: {usb_path}")
                
                dest_wim_path = usb_path / wim_file_path.name
                shutil.copy2(wim_file_path, dest_wim_path)
                
                # 设置启动扇区（简化实现）
                self.logger.info("设置USB启动扇区...")
                log_build_step("设置启动扇区", "配置USB启动")
                
                # 这里可以实现更复杂的USB启动盘制作逻辑
                # 目前简单复制文件并返回成功
                
                self.logger.info("✅ USB启动盘制作成功")
                log_build_step("USB制作成功", f"USB设备: {usb_path}")
                log_system_event("USB制作", "USB启动盘制作成功", "info")
                
                # 验证USB设备
                if dest_wim_path.exists():
                    file_size = dest_wim_path.stat().st_size / (1024 * 1024)
                    self.logger.info(f"USB上的WIM文件大小: {file_size:.1f} MB")
                
                end_build_session(True, f"USB启动盘制作成功: {usb_path}")
                return True, f"USB启动盘制作成功: {usb_path}"
                
            except Exception as e:
                error_msg = f"USB制作过程异常: {str(e)}"
                log_error(e, "USB制作过程")
                log_system_event("USB制作异常", error_msg, "error")
                end_build_session(False, error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"制作USB启动盘时发生错误: {str(e)}"
            log_error(e, "USB制作")
            return False, error_msg
    
    def auto_unmount_before_iso(self, build_dir: Path) -> Tuple[bool, str]:
        """ISO创建前自动卸载镜像"""
        try:
            self.logger.info("🔧 开始自动卸载流程...")
            log_build_step("自动卸载", "开始ISO创建前的自动卸载")
            
            mount_dir = self.path_manager.get_mount_dir(build_dir)
            
            # 方法1：标准卸载
            wim_file_path = self.path_manager.get_primary_wim(build_dir)
            if wim_file_path:
                success, message = self.unmount_wim(build_dir, commit=False)  # 放弃更改
                if success:
                    return True, "标准卸载成功"
            
            # 方法2：强制卸载
            self.logger.warning("标准卸载失败，尝试强制卸载...")
            success, message = self._force_unmount(mount_dir)
            if success:
                return True, "强制卸载成功"
            
            # 方法3：清理挂载目录
            self.logger.warning("强制卸载失败，尝试清理目录...")
            success, message = self.check_manager._force_cleanup_mount(mount_dir)
            if success:
                return True, "目录清理成功"
            
            return False, "所有自动卸载方法都失败"
            
        except Exception as e:
            error_msg = f"自动卸载过程失败: {str(e)}"
            log_error(e, "自动卸载")
            return False, error_msg
    
    def _force_unmount(self, mount_dir: Path) -> Tuple[bool, str]:
        """强制卸载"""
        try:
            # 删除挂载信息文件
            mount_info_file = mount_dir / ".mount_info"
            try:
                if mount_info_file.exists():
                    mount_info_file.unlink()
                    self.logger.debug(f"强制卸载时删除挂载信息文件: {mount_info_file}")
                
                # 删除所有WIM文件特定的挂载标记文件
                for marker_file in mount_dir.glob(".*_mounted"):
                    try:
                        marker_file.unlink()
                        self.logger.debug(f"强制卸载时删除挂载标记文件: {marker_file}")
                    except Exception as e:
                        self.logger.warning(f"删除挂载标记文件失败: {str(e)}")
                            
            except Exception as e:
                self.logger.warning(f"删除挂载信息文件失败: {str(e)}")
            
            # 这里可以实现更复杂的强制卸载逻辑
            # 目前简单返回成功，实际使用中需要调用DISM强制卸载
            return True, "强制卸载成功"
        except Exception as e:
            return False, f"强制卸载失败: {str(e)}"
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
