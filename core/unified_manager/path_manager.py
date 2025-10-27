#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径管理模块
提供统一的路径管理和WIM文件查找功能
"""

from pathlib import Path
from typing import List, Dict, Optional

from utils.logger import get_logger, log_build_step


class PathManager:
    """路径管理器
    
    负责统一管理所有路径相关操作
    """
    
    def __init__(self):
        self.logger = get_logger("PathManager")
    
    def get_mount_dir(self, build_dir: Path) -> Path:
        """获取统一的挂载目录
        
        Args:
            build_dir: 构建目录路径
            
        Returns:
            Path: 挂载目录路径 (build_dir/mount)
        """
        mount_dir = build_dir / "mount"
        self.logger.debug(f"获取挂载目录: {mount_dir}")
        return mount_dir
    
    def find_wim_files(self, build_dir: Path) -> List[Dict]:
        """在构建目录中查找所有WIM文件
        
        Args:
            build_dir: 构建目录路径
            
        Returns:
            List[Dict]: WIM文件信息列表
        """
        self.logger.info(f"在构建目录中查找WIM文件: {build_dir}")
        log_build_step("WIM文件搜索", f"搜索目录: {build_dir}")
        
        wim_files = []
        
        try:
            # 检查构建目录是否存在
            if not build_dir.exists():
                self.logger.warning(f"构建目录不存在: {build_dir}")
                return wim_files
            
            # 按优先级搜索WIM文件
            search_patterns = [
                ("copype", build_dir / "media" / "sources" / "boot.wim"),
                ("dism", build_dir / "winpe.wim"),
            ]
            
            # 搜索特定模式的WIM文件
            for wim_type, wim_path in search_patterns:
                if wim_path.exists():
                    wim_info = self._create_wim_info(wim_path, wim_type, build_dir)
                    wim_files.append(wim_info)
                    self.logger.info(f"找到{wim_type}模式WIM文件: {wim_path}")
            
            # 递归搜索其他WIM文件
            for wim_path in build_dir.rglob("*.wim"):
                # 跳过已经处理过的文件
                already_processed = any(wf["path"] == wim_path for wf in wim_files)
                if not already_processed:
                    wim_type = self._determine_wim_type(wim_path)
                    wim_info = self._create_wim_info(wim_path, wim_type, build_dir)
                    wim_files.append(wim_info)
                    self.logger.info(f"找到其他WIM文件: {wim_path}")
            
            # 按大小排序
            wim_files.sort(key=lambda x: x["size"], reverse=True)
            
            self.logger.info(f"共找到 {len(wim_files)} 个WIM文件")
            log_build_step("WIM文件搜索完成", f"找到 {len(wim_files)} 个WIM文件")
            
            return wim_files
            
        except Exception as e:
            self.logger.error(f"搜索WIM文件失败: {str(e)}")
            return wim_files
    
    def get_primary_wim(self, build_dir: Path) -> Optional[Path]:
        """获取主要的WIM文件（优先级：boot.wim > winpe.wim > 其他）
        
        Args:
            build_dir: 构建目录路径
            
        Returns:
            Optional[Path]: 主要WIM文件路径
        """
        self.logger.info(f"获取主要WIM文件: {build_dir}")
        
        # 按优先级检查
        priority_paths = [
            build_dir / "media" / "sources" / "boot.wim",  # copype模式优先
            build_dir / "winpe.wim",                       # DISM模式
        ]
        
        for wim_path in priority_paths:
            if wim_path.exists():
                self.logger.info(f"找到主要WIM文件: {wim_path}")
                return wim_path
        
        # 如果优先级文件都不存在，查找第一个可用的WIM文件
        wim_files = list(build_dir.rglob("*.wim"))
        if wim_files:
            wim_path = wim_files[0]
            self.logger.info(f"使用第一个找到的WIM文件: {wim_path}")
            return wim_path
        
        self.logger.warning("未找到任何WIM文件")
        return None
    
    def _create_wim_info(self, wim_path: Path, wim_type: str, build_dir: Path) -> Dict:
        """创建WIM文件信息字典"""
        try:
            return {
                "path": wim_path,
                "name": wim_path.name,
                "type": wim_type,
                "size": wim_path.stat().st_size,
                "mount_status": self._check_mount_status_for_wim(wim_path, build_dir),
                "build_dir": build_dir
            }
        except Exception as e:
            self.logger.error(f"创建WIM信息失败: {str(e)}")
            return {
                "path": wim_path,
                "name": wim_path.name,
                "type": "unknown",
                "size": 0,
                "mount_status": False,
                "build_dir": build_dir
            }
    
    def _determine_wim_type(self, wim_path: Path) -> str:
        """确定WIM文件类型"""
        try:
            # 根据文件名和路径判断类型
            if wim_path.name.lower() == "boot.wim":
                return "copype"
            elif wim_path.name.lower() == "winpe.wim":
                return "dism"
            elif "sources" in str(wim_path).lower():
                return "copype"
            else:
                return "unknown"
        except Exception:
            return "unknown"
    
    def _check_mount_status_for_wim(self, wim_path: Path, build_dir: Path) -> bool:
        """检查特定WIM文件的挂载状态"""
        try:
            mount_dir = self.get_mount_dir(build_dir)
            if not mount_dir.exists():
                return False
            
            # 检查挂载目录是否为空
            if not list(mount_dir.iterdir()):
                return False
            
            # 检查是否有挂载信息文件或标记
            mount_info_file = mount_dir / ".mount_info"
            if mount_info_file.exists():
                try:
                    with open(mount_info_file, 'r', encoding='utf-8') as f:
                        mount_info = f.read().strip()
                        # 检查是否是当前WIM文件的挂载信息
                        if str(wim_path) in mount_info:
                            return True
                except Exception:
                    pass
            
            # 检查WIM文件特定的挂载标记文件
            wim_name = wim_path.stem
            mount_marker_file = mount_dir / f".{wim_name}_mounted"
            if mount_marker_file.exists():
                self.logger.debug(f"找到WIM文件 {wim_name} 的挂载标记文件")
                return True
            
            # 如果没有挂载信息文件，检查是否只有一个WIM文件被挂载
            # 这种情况下，假设挂载目录中的内容属于当前WIM文件
            wim_files_in_build = list(build_dir.rglob("*.wim"))
            if len(wim_files_in_build) == 1:
                # 检查唯一的WIM文件是否是当前文件
                only_wim = wim_files_in_build[0]
                if only_wim == wim_path:
                    return True
                else:
                    return False
            
            # 如果有多个WIM文件，需要更精确的检查
            # 检查挂载目录中是否有当前WIM文件对应的标记
            wim_name = wim_path.stem
            for item in mount_dir.iterdir():
                if item.is_file() and item.name.startswith(f".{wim_name}_mounted"):
                    return True
            
            # 如果没有找到特定标记，使用简单的目录存在性检查
            # 但这种情况下不能确定是哪个WIM文件挂载的
            return False
            
        except Exception:
            return False
