#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态管理模块
提供挂载状态和构建信息的查询功能
"""

from pathlib import Path
from typing import Dict

from utils.logger import get_logger, log_error


class StatusManager:
    """状态管理器
    
    负责管理所有状态查询功能
    """
    
    def __init__(self, path_manager):
        self.path_manager = path_manager
        self.logger = get_logger("StatusManager")
    
    def get_mount_status(self, build_dir: Path) -> Dict:
        """获取挂载状态信息
        
        Args:
            build_dir: 构建目录路径
            
        Returns:
            Dict: 挂载状态信息
        """
        try:
            mount_dir = self.path_manager.get_mount_dir(build_dir)
            wim_files = self.path_manager.find_wim_files(build_dir)
            
            status = {
                "build_dir": str(build_dir),
                "mount_dir": str(mount_dir),
                "mount_dir_exists": mount_dir.exists(),
                "is_mounted": False,
                "mounted_files": [],
                "wim_files": wim_files,
                "total_wim_count": len(wim_files)
            }
            
            if mount_dir.exists() and any(mount_dir.iterdir()):
                status["is_mounted"] = True
                # 只统计关键文件，避免列出所有文件路径
                key_files = ['Windows', 'Program Files', 'Users', 'System32']
                found_files = [f for f in key_files if (mount_dir / f).exists()]
                status["mounted_files"] = found_files  # 只显示关键目录，不显示完整路径
                status["mounted_dirs"] = found_files  # 使用found_files替代mounted_files
            
            return status
            
        except Exception as e:
            log_error(e, "获取挂载状态")
            return {"error": str(e)}
    
    def get_build_info(self, build_dir: Path) -> Dict:
        """获取构建目录完整信息
        
        Args:
            build_dir: 构建目录路径
            
        Returns:
            Dict: 构建信息
        """
        try:
            wim_files = self.path_manager.find_wim_files(build_dir)
            mount_status = self.get_mount_status(build_dir)
            
            info = {
                "build_dir": str(build_dir),
                "build_dir_exists": build_dir.exists(),
                "build_dir_size": sum(f.stat().st_size for f in build_dir.rglob("*") if f.is_file()) if build_dir.exists() else 0,
                "wim_files": wim_files,
                "mount_status": mount_status,
                "has_boot_wim": any(wf["name"].lower() == "boot.wim" for wf in wim_files),
                "has_winpe_wim": any(wf["name"].lower() == "winpe.wim" for wf in wim_files),
                "total_wim_size": sum(wf["size"] for wf in wim_files),
                "created_time": build_dir.stat().st_ctime if build_dir.exists() else None
            }
            
            return info
            
        except Exception as e:
            log_error(e, "获取构建信息")
            return {"error": str(e)}
    
    def get_wim_summary(self, build_dir: Path) -> Dict:
        """获取WIM文件摘要信息
        
        Args:
            build_dir: 构建目录路径
            
        Returns:
            Dict: WIM摘要信息
        """
        try:
            wim_files = self.path_manager.find_wim_files(build_dir)
            
            summary = {
                "total_count": len(wim_files),
                "total_size": sum(wf["size"] for wf in wim_files),
                "by_type": {},
                "by_name": {},
                "mounted_count": 0,
                "unmounted_count": 0
            }
            
            # 按类型统计
            for wim_file in wim_files:
                wim_type = wim_file["type"]
                if wim_type not in summary["by_type"]:
                    summary["by_type"][wim_type] = {"count": 0, "size": 0}
                summary["by_type"][wim_type]["count"] += 1
                summary["by_type"][wim_type]["size"] += wim_file["size"]
                
                # 按名称统计
                wim_name = wim_file["name"]
                if wim_name not in summary["by_name"]:
                    summary["by_name"][wim_name] = wim_file
                
                # 挂载状态统计
                if wim_file["mount_status"]:
                    summary["mounted_count"] += 1
                else:
                    summary["unmounted_count"] += 1
            
            return summary
            
        except Exception as e:
            log_error(e, "获取WIM摘要")
            return {"error": str(e)}
    
    def get_system_status(self) -> Dict:
        """获取系统状态信息
        
        Returns:
            Dict: 系统状态信息
        """
        try:
            import platform
            import shutil
            
            status = {
                "platform": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor()
                },
                "disk_usage": {},
                "python_version": platform.python_version(),
                "timestamp": self._get_current_timestamp()
            }
            
            # 获取主要磁盘使用情况
            try:
                import psutil
                partitions = psutil.disk_partitions()
                for partition in partitions:
                    if partition.device:
                        usage = psutil.disk_usage(partition.mountpoint)
                        status["disk_usage"][partition.device] = {
                            "total": usage.total,
                            "used": usage.used,
                            "free": usage.free,
                            "percent": (usage.used / usage.total) * 100
                        }
            except ImportError:
                # 如果psutil不可用，使用shutil获取当前目录磁盘信息
                current_disk = shutil.disk_usage(".")
                status["disk_usage"]["current"] = {
                    "total": current_disk.total,
                    "used": current_disk.used,
                    "free": current_disk.free,
                    "percent": (current_disk.used / current_disk.total) * 100
                }
            
            return status
            
        except Exception as e:
            log_error(e, "获取系统状态")
            return {"error": str(e)}
    
    def validate_build_structure(self, build_dir: Path) -> Dict:
        """验证构建目录结构
        
        Args:
            build_dir: 构建目录路径
            
        Returns:
            Dict: 验证结果
        """
        try:
            validation = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "structure": {
                    "has_media": False,
                    "has_sources": False,
                    "has_boot_wim": False,
                    "has_mount_dir": False,
                    "media_complete": False
                }
            }
            
            if not build_dir.exists():
                validation["is_valid"] = False
                validation["errors"].append(f"构建目录不存在: {build_dir}")
                return validation
            
            # 检查基本结构
            media_path = build_dir / "media"
            sources_path = media_path / "sources"
            boot_wim_path = sources_path / "boot.wim"
            mount_dir = self.path_manager.get_mount_dir(build_dir)
            
            validation["structure"]["has_media"] = media_path.exists()
            validation["structure"]["has_sources"] = sources_path.exists()
            validation["structure"]["has_boot_wim"] = boot_wim_path.exists()
            validation["structure"]["has_mount_dir"] = mount_dir.exists()
            
            # 检查Media目录完整性
            if media_path.exists():
                required_files = [
                    "bootmgr",
                    "bootmgr.efi",
                    "BCD",
                    "sources/boot.wim"
                ]
                
                missing_files = []
                for required_file in required_files:
                    file_path = media_path / required_file
                    if not file_path.exists():
                        missing_files.append(required_file)
                
                if not missing_files:
                    validation["structure"]["media_complete"] = True
                else:
                    validation["warnings"].append(f"Media目录缺少文件: {', '.join(missing_files)}")
            
            # 检查WIM文件
            wim_files = self.path_manager.find_wim_files(build_dir)
            if not wim_files:
                validation["is_valid"] = False
                validation["errors"].append("未找到任何WIM文件")
            
            # 检查挂载状态
            if mount_dir.exists() and any(mount_dir.iterdir()):
                validation["warnings"].append("检测到挂载目录不为空，可能存在未完成的挂载")
            
            return validation
            
        except Exception as e:
            log_error(e, "验证构建结构")
            return {"is_valid": False, "error": str(e)}
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
