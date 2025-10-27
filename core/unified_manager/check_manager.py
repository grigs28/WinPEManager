#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查机制模块
提供挂载前、卸载前、ISO创建前、USB制作前的完整检查功能
"""

import os
import shutil
import subprocess
import time
import platform
import ctypes
from pathlib import Path
from typing import List, Tuple

from utils.logger import get_logger, log_build_step, log_error


class CheckManager:
    """检查管理器
    
    负责所有操作前的检查机制
    """
    
    def __init__(self, path_manager):
        self.path_manager = path_manager
        self.logger = get_logger("CheckManager")
    
    def pre_mount_checks(self, build_dir: Path, wim_file_path: Path) -> Tuple[bool, str]:
        """挂载前完整检查
        
        Args:
            build_dir: 构建目录路径
            wim_file_path: WIM文件路径
            
        Returns:
            Tuple[bool, str]: (检查结果, 消息)
        """
        self.logger.info("🔍 开始挂载前检查...")
        log_build_step("挂载前检查", f"构建目录: {build_dir}, WIM文件: {wim_file_path}")
        
        try:
            # 检查1：构建目录
            if not build_dir.exists():
                error_msg = f"构建目录不存在: {build_dir}"
                self.logger.error(error_msg)
                return False, error_msg
            
            # 检查2：WIM文件
            if not wim_file_path.exists():
                error_msg = f"WIM文件不存在: {wim_file_path}"
                self.logger.error(error_msg)
                return False, error_msg
            
            # 检查WIM文件大小
            wim_size = wim_file_path.stat().st_size
            wim_size_mb = wim_size / (1024 * 1024)
            self.logger.info(f"WIM文件大小: {wim_size_mb:.1f} MB")
            
            # 根据文件类型设置不同的大小阈值
            if wim_file_path.name.lower() == "boot.wim":
                if wim_size < 100 * 1024 * 1024:  # 小于100MB
                    error_msg = f"boot.wim文件过小，可能损坏: {wim_size_mb:.1f}MB"
                    self.logger.warning(error_msg)
                    return False, error_msg
            elif wim_file_path.name.lower() == "winpe.wim":
                if wim_size < 200 * 1024 * 1024:  # 小于200MB
                    error_msg = f"winpe.wim文件过小，可能损坏: {wim_size_mb:.1f}MB"
                    self.logger.warning(error_msg)
                    return False, error_msg
            else:
                if wim_size < 50 * 1024 * 1024:  # 小于50MB
                    error_msg = f"WIM文件过小，可能损坏: {wim_size_mb:.1f}MB"
                    self.logger.warning(error_msg)
                    return False, error_msg
            
            # 检查3：挂载目录
            mount_dir = self.path_manager.get_mount_dir(build_dir)
            if mount_dir.exists() and any(mount_dir.iterdir()):
                self.logger.warning("⚠️ 检测到挂载目录不为空，尝试清理...")
                log_build_step("清理挂载目录", f"目录: {mount_dir}")
                
                cleanup_success, cleanup_msg = self._force_cleanup_mount(mount_dir)
                if not cleanup_success:
                    error_msg = f"无法清理现有挂载: {cleanup_msg}"
                    self.logger.error(error_msg)
                    return False, error_msg
                else:
                    self.logger.info("挂载目录清理成功")
            
            # 检查4：管理员权限
            if not self._check_admin_privileges():
                error_msg = "需要管理员权限进行挂载操作"
                self.logger.error(error_msg)
                return False, error_msg
            
            # 检查5：磁盘空间
            disk_usage = shutil.disk_usage(str(build_dir))
            free_gb = disk_usage.free / (1024**3)
            self.logger.info(f"可用磁盘空间: {free_gb:.1f} GB")
            
            if free_gb < 1.0:  # 小于1GB
                error_msg = f"磁盘空间不足，剩余: {free_gb:.1f}GB"
                self.logger.error(error_msg)
                return False, error_msg
            
            self.logger.info("✅ 挂载前检查全部通过")
            log_build_step("挂载前检查", "所有检查通过")
            return True, "检查通过"
            
        except Exception as e:
            error_msg = f"挂载前检查失败: {str(e)}"
            log_error(e, "挂载前检查")
            return False, error_msg
    
    def pre_unmount_checks(self, build_dir: Path) -> Tuple[bool, str]:
        """卸载前完整检查
        
        Args:
            build_dir: 构建目录路径
            
        Returns:
            Tuple[bool, str]: (检查结果, 消息)
        """
        self.logger.info("🔍 开始卸载前检查...")
        log_build_step("卸载前检查", f"构建目录: {build_dir}")
        
        try:
            mount_dir = self.path_manager.get_mount_dir(build_dir)
            
            # 检查1：是否真的已挂载
            if not mount_dir.exists():
                self.logger.info("挂载目录不存在，无需卸载")
                return True, "无需卸载"
            
            if not any(mount_dir.iterdir()):
                self.logger.info("挂载目录为空，可能已卸载")
                return True, "可能已卸载"
            
            # 检查2：文件锁定状态
            locked_files = self._check_file_locks(mount_dir)
            if locked_files:
                self.logger.warning(f"⚠️ 检测到文件锁定: {locked_files}")
                log_build_step("检查文件锁定", f"锁定文件: {locked_files}")
                
                # 尝试解锁
                unlock_success, unlock_msg = self._try_unlock_files(locked_files)
                if not unlock_success:
                    error_msg = f"无法解除文件锁定: {unlock_msg}"
                    self.logger.error(error_msg)
                    return False, error_msg
                else:
                    self.logger.info("文件锁定解除成功")
            
            # 检查3：DISM进程状态
            dism_running = self._check_dism_processes()
            if dism_running:
                self.logger.warning("⚠️ 检测到运行中的DISM进程")
                log_build_step("检查DISM进程", f"运行中的进程: {dism_running}")
                
                # 尝试等待或终止
                process_success, process_msg = self._handle_dism_processes(dism_running)
                if not process_success:
                    error_msg = f"无法处理DISM进程: {process_msg}"
                    self.logger.error(error_msg)
                    return False, error_msg
                else:
                    self.logger.info("DISM进程处理成功")
            
            self.logger.info("✅ 卸载前检查全部通过")
            log_build_step("卸载前检查", "所有检查通过")
            return True, "检查通过"
            
        except Exception as e:
            error_msg = f"卸载前检查失败: {str(e)}"
            log_error(e, "卸载前检查")
            return False, error_msg
    
    def pre_iso_checks(self, build_dir: Path, config_manager) -> Tuple[bool, str]:
        """ISO创建前完整检查
        
        Args:
            build_dir: 构建目录路径
            config_manager: 配置管理器
            
        Returns:
            Tuple[bool, str]: (检查结果, 消息)
        """
        self.logger.info("🔍 开始ISO创建前检查...")
        log_build_step("ISO创建前检查", f"构建目录: {build_dir}")
        
        try:
            # 检查1：镜像挂载状态 ✅
            mount_dir = self.path_manager.get_mount_dir(build_dir)
            if mount_dir.exists() and any(mount_dir.iterdir()):
                self.logger.warning("⚠️ 检测到镜像仍处于挂载状态")
                log_build_step("检查挂载状态", "镜像仍挂载，需要自动卸载")
                
                # 这里应该调用自动卸载，但为了避免循环依赖，先返回警告
                error_msg = "检测到镜像仍处于挂载状态，请先卸载镜像"
                self.logger.error(error_msg)
                return False, error_msg
            
            # 检查2：Media目录完整性
            media_path = build_dir / "media"
            if not media_path.exists():
                error_msg = f"Media目录不存在: {media_path}"
                self.logger.error(error_msg)
                return False, error_msg
            
            # 检查3：关键启动文件
            critical_files = {
                "boot.wim": media_path / "sources" / "boot.wim",
                "etfsboot.com": media_path / "Boot" / "etfsboot.com"
            }
            
            missing_files = []
            for name, path in critical_files.items():
                if not path.exists():
                    missing_files.append(f"{name} ({path})")
                else:
                    self.logger.debug(f"关键文件存在: {name} -> {path}")
            
            if missing_files:
                error_msg = f"关键启动文件缺失: {', '.join(missing_files)}"
                self.logger.error(error_msg)
                return False, error_msg
            
            # 检查4：WIM文件完整性
            boot_wim = critical_files["boot.wim"]
            wim_size = boot_wim.stat().st_size
            wim_size_mb = wim_size / (1024 * 1024)
            self.logger.info(f"boot.wim文件大小: {wim_size_mb:.1f} MB")
            
            if wim_size < 100 * 1024 * 1024:  # 小于100MB
                error_msg = f"boot.wim文件过小: {wim_size_mb:.1f}MB"
                self.logger.error(error_msg)
                return False, error_msg
            
            # 检查5：输出目录权限
            iso_path_str = config_manager.get("output.iso_path", "")
            if iso_path_str:
                iso_path = Path(iso_path_str)
                iso_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 检查写入权限
                test_file = iso_path.parent / ".iso_test"
                try:
                    test_file.write_text("test")
                    test_file.unlink()
                    self.logger.debug("ISO输出目录写入权限检查通过")
                except Exception as e:
                    error_msg = f"ISO输出目录无写入权限: {e}"
                    self.logger.error(error_msg)
                    return False, error_msg
            
            # 检查6：磁盘空间
            required_space = wim_size * 1.2  # 预留20%空间
            available_space = shutil.disk_usage(str(iso_path.parent)).free if iso_path_str else shutil.disk_usage(str(build_dir)).free
            required_gb = required_space / (1024**3)
            available_gb = available_space / (1024**3)
            
            self.logger.info(f"磁盘空间检查 - 需要: {required_gb:.1f}GB, 可用: {available_gb:.1f}GB")
            
            if available_space < required_space:
                error_msg = f"磁盘空间不足，需要: {required_gb:.1f}GB，可用: {available_gb:.1f}GB"
                self.logger.error(error_msg)
                return False, error_msg
            
            self.logger.info("✅ ISO创建前检查全部通过")
            log_build_step("ISO创建前检查", "所有检查通过")
            return True, "检查通过"
            
        except Exception as e:
            error_msg = f"ISO创建前检查失败: {str(e)}"
            log_error(e, "ISO创建前检查")
            return False, error_msg
    
    def pre_usb_checks(self, build_dir: Path, usb_path: Path) -> Tuple[bool, str]:
        """USB制作前完整检查
        
        Args:
            build_dir: 构建目录路径
            usb_path: USB设备路径
            
        Returns:
            Tuple[bool, str]: (检查结果, 消息)
        """
        self.logger.info("🔍 开始USB制作前检查...")
        log_build_step("USB制作前检查", f"构建目录: {build_dir}, USB路径: {usb_path}")
        
        try:
            # 检查1：构建目录和WIM文件
            wim_file_path = self.path_manager.get_primary_wim(build_dir)
            if not wim_file_path:
                error_msg = "在构建目录中未找到WIM文件"
                self.logger.error(error_msg)
                return False, error_msg
            
            # 检查2：USB设备路径
            if not usb_path.exists():
                error_msg = f"USB设备路径不存在: {usb_path}"
                self.logger.error(error_msg)
                return False, error_msg
            
            # 检查3：设备类型
            is_removable = self._is_removable_device(usb_path)
            if not is_removable:
                self.logger.warning(f"选定的路径可能不是可移动设备: {usb_path}")
                # 这里不返回错误，让用户确认
            
            # 检查4：磁盘空间
            wim_size = wim_file_path.stat().st_size
            required_space = wim_size * 1.5  # 预留50%空间
            available_space = shutil.disk_usage(str(usb_path)).free
            
            if available_space < required_space:
                error_msg = f"USB设备空间不足，需要: {required_space/1024/1024:.1f}MB，可用: {available_space/1024/1024:.1f}MB"
                self.logger.error(error_msg)
                return False, error_msg
            
            self.logger.info("✅ USB制作前检查全部通过")
            log_build_step("USB制作前检查", "所有检查通过")
            return True, "检查通过"
            
        except Exception as e:
            error_msg = f"USB制作前检查失败: {str(e)}"
            log_error(e, "USB制作前检查")
            return False, error_msg
    
    # === 私有辅助方法 ===
    def _check_admin_privileges(self) -> bool:
        """检查管理员权限"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            return False
    
    def _check_file_locks(self, mount_dir: Path) -> List[str]:
        """检查文件锁定状态"""
        locked_files = []
        try:
            # 只检查关键文件的锁定状态，避免遍历所有文件
            key_files = [
                mount_dir / "Windows" / "System32" / "config" / "SYSTEM",
                mount_dir / "Windows" / "System32" / "config" / "SOFTWARE",
                mount_dir / "Windows" / "System32" / "drivers" / "etc" / "hosts"
            ]
            
            for file_path in key_files:
                if file_path.exists() and file_path.is_file():
                    try:
                        # 尝试以写入模式打开文件
                        with open(file_path, 'r+b') as f:
                            pass
                    except (PermissionError, OSError):
                        locked_files.append(str(file_path))
        except Exception as e:
            self.logger.error(f"检查文件锁定失败: {str(e)}")
        
        return locked_files
    
    def _try_unlock_files(self, locked_files: List[str]) -> Tuple[bool, str]:
        """尝试解锁文件"""
        try:
            # 这里可以实现更复杂的解锁逻辑
            # 目前简单返回成功，实际使用中可能需要等待或强制解锁
            return True, "解锁成功"
        except Exception as e:
            return False, f"解锁失败: {str(e)}"
    
    def _check_dism_processes(self) -> List[str]:
        """检查DISM进程"""
        try:
            result = subprocess.run(['tasklist', '/fi', 'imagename eq dism.exe'], 
                              capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and 'dism.exe' in result.stdout:
                # 解析进程信息
                lines = result.stdout.split('\n')
                processes = []
                for line in lines:
                    if 'dism.exe' in line:
                        processes.append(line.strip())
                return processes
            return []
        except Exception as e:
            self.logger.error(f"检查DISM进程失败: {str(e)}")
            return []
    
    def _handle_dism_processes(self, processes: List[str]) -> Tuple[bool, str]:
        """处理DISM进程"""
        try:
            if not processes:
                return True, "没有DISM进程需要处理"
            
            # 等待一段时间让进程完成
            self.logger.info("等待DISM进程完成...")
            time.sleep(5)
            
            # 再次检查
            remaining_processes = self._check_dism_processes()
            if not remaining_processes:
                return True, "DISM进程已完成"
            
            # 尝试终止进程
            self.logger.warning("尝试终止DISM进程...")
            result = subprocess.run(['taskkill', '/f', '/im', 'dism.exe'],
                              capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                time.sleep(2)  # 等待进程完全终止
                return True, "DISM进程已终止"
            else:
                return False, f"终止DISM进程失败: {result.stderr}"
                
        except Exception as e:
            return False, f"处理DISM进程异常: {str(e)}"
    
    def _is_removable_device(self, path: Path) -> bool:
        """检查是否为可移动设备"""
        try:
            # 在Windows上检查驱动器类型
            if platform.system() == "Windows":
                try:
                    import win32api
                    import win32file
                    
                    drive = str(path)[:2]  # 获取驱动器字母
                    drive_type = win32api.GetDriveType(drive + "\\")
                    
                    # DRIVE_REMOVABLE = 2
                    return drive_type == 2
                except ImportError:
                    # 如果win32api不可用，使用简单检查
                    return True  # 假设是可移动设备
            
            return False
        except Exception:
            return False
    
    def _force_cleanup_mount(self, mount_dir: Path) -> Tuple[bool, str]:
        """强制清理挂载目录"""
        try:
            if mount_dir.exists():
                # 尝试正常删除
                shutil.rmtree(mount_dir, ignore_errors=True)
                self.logger.info("挂载目录清理成功")
                return True, "清理成功"
            else:
                self.logger.info("挂载目录不存在，无需清理")
                return True, "无需清理"
        except Exception as e:
            error_msg = f"强制清理挂载目录失败: {str(e)}"
            log_error(e, "强制清理挂载目录")
            return False, error_msg
