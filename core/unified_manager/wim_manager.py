#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一WIM管理器主类
整合所有子模块，提供统一的WIM管理接口
"""

from pathlib import Path
from typing import Tuple, Dict, Optional

from utils.logger import get_logger, update_log_context

from .path_manager import PathManager
from .check_manager import CheckManager
from .operation_manager import OperationManager
from .status_manager import StatusManager


class UnifiedWIMManager:
    """统一的WIM管理器主类
    
    整合所有子模块功能，提供完整的WIM管理解决方案
    """
    
    def __init__(self, config_manager, adk_manager, parent_callback=None):
        """初始化统一WIM管理器
        
        Args:
            config_manager: 配置管理器
            adk_manager: ADK管理器
            parent_callback: 父级回调对象
        """
        self.config = config_manager
        self.adk = adk_manager
        self.parent_callback = parent_callback
        self.logger = get_logger("UnifiedWIMManager")
        
        # 初始化上下文
        self.operation_context = {}
        update_log_context(
            module="UnifiedWIMManager",
            operation="initialization"
        )
        
        # 初始化子模块
        self.path_manager = PathManager()
        self.check_manager = CheckManager(self.path_manager)
        self.operation_manager = OperationManager(
            self.path_manager, 
            self.check_manager, 
            self.config, 
            self.adk, 
            self.parent_callback
        )
        self.status_manager = StatusManager(self.path_manager)
        
        self.logger.info("统一WIM管理器初始化完成")
        self.logger.info("子模块初始化完成: PathManager, CheckManager, OperationManager, StatusManager")
    
    # === 路径管理接口 ===
    def get_mount_dir(self, build_dir: Path) -> Path:
        """获取统一的挂载目录"""
        return self.path_manager.get_mount_dir(build_dir)
    
    def find_wim_files(self, build_dir: Path) -> list:
        """在构建目录中查找所有WIM文件"""
        return self.path_manager.find_wim_files(build_dir)
    
    def get_primary_wim(self, build_dir: Path) -> Optional[Path]:
        """获取主要的WIM文件"""
        return self.path_manager.get_primary_wim(build_dir)
    
    # === 检查机制接口 ===
    def pre_mount_checks(self, build_dir: Path, wim_file_path: Path) -> Tuple[bool, str]:
        """挂载前完整检查"""
        return self.check_manager.pre_mount_checks(build_dir, wim_file_path)
    
    def pre_unmount_checks(self, build_dir: Path) -> Tuple[bool, str]:
        """卸载前完整检查"""
        return self.check_manager.pre_unmount_checks(build_dir)
    
    def pre_iso_checks(self, build_dir: Path) -> Tuple[bool, str]:
        """ISO创建前完整检查"""
        return self.check_manager.pre_iso_checks(build_dir, self.config)
    
    def pre_usb_checks(self, build_dir: Path, usb_path: Path) -> Tuple[bool, str]:
        """USB制作前完整检查"""
        return self.check_manager.pre_usb_checks(build_dir, usb_path)
    
    # === 操作接口 ===
    def mount_wim(self, build_dir: Path, wim_file_path: Path = None) -> Tuple[bool, str]:
        """统一挂载接口"""
        return self.operation_manager.mount_wim(build_dir, wim_file_path)
    
    def unmount_wim(self, build_dir: Path, commit: bool = True) -> Tuple[bool, str]:
        """统一卸载接口"""
        return self.operation_manager.unmount_wim(build_dir, commit)
    
    def create_iso(self, build_dir: Path, iso_path: Path = None) -> Tuple[bool, str]:
        """统一ISO创建接口"""
        return self.operation_manager.create_iso(build_dir, iso_path)
    
    def create_usb(self, build_dir: Path, usb_path: Path) -> Tuple[bool, str]:
        """统一USB制作接口"""
        return self.operation_manager.create_usb(build_dir, usb_path)
    
    def auto_unmount_before_iso(self, build_dir: Path) -> Tuple[bool, str]:
        """ISO创建前自动卸载镜像"""
        return self.operation_manager.auto_unmount_before_iso(build_dir)
    
    # === 状态管理接口 ===
    def get_mount_status(self, build_dir: Path) -> Dict:
        """获取挂载状态信息"""
        return self.status_manager.get_mount_status(build_dir)
    
    def get_build_info(self, build_dir: Path) -> Dict:
        """获取构建目录完整信息"""
        return self.status_manager.get_build_info(build_dir)
    
    def get_wim_summary(self, build_dir: Path) -> Dict:
        """获取WIM文件摘要信息"""
        return self.status_manager.get_wim_summary(build_dir)
    
    def get_system_status(self) -> Dict:
        """获取系统状态信息"""
        return self.status_manager.get_system_status()
    
    def validate_build_structure(self, build_dir: Path) -> Dict:
        """验证构建目录结构"""
        return self.status_manager.validate_build_structure(build_dir)
    
    # === 高级功能接口 ===
    def quick_mount_check(self, build_dir: Path) -> Dict:
        """快速挂载检查
        
        Args:
            build_dir: 构建目录路径
            
        Returns:
            Dict: 快速检查结果
        """
        try:
            self.logger.info("🔍 执行快速挂载检查...")
            
            # 获取主要WIM文件
            primary_wim = self.get_primary_wim(build_dir)
            
            # 获取挂载状态
            mount_status = self.get_mount_status(build_dir)
            
            # 执行基本检查
            if primary_wim:
                mount_check, mount_msg = self.pre_mount_checks(build_dir, primary_wim)
            else:
                mount_check, mount_msg = False, "未找到主要WIM文件"
            
            result = {
                "build_dir": str(build_dir),
                "primary_wim": str(primary_wim) if primary_wim else None,
                "mount_status": mount_status,
                "mount_check_passed": mount_check,
                "mount_check_message": mount_msg,
                "recommendations": []
            }
            
            # 生成建议
            if not primary_wim:
                result["recommendations"].append("建议先创建或复制WIM文件到构建目录")
            
            if mount_status["is_mounted"]:
                result["recommendations"].append("检测到已挂载的镜像，建议先卸载再进行其他操作")
            
            if not mount_check:
                result["recommendations"].append(f"挂载检查失败: {mount_msg}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"快速挂载检查失败: {str(e)}")
            return {"error": str(e)}
    
    def smart_cleanup(self, build_dir: Path) -> Dict:
        """智能清理构建目录
        
        Args:
            build_dir: 构建目录路径
            
        Returns:
            Dict: 清理结果
        """
        try:
            self.logger.info("🧹 执行智能清理...")
            
            cleanup_result = {
                "build_dir": str(build_dir),
                "actions_taken": [],
                "warnings": [],
                "success": True
            }
            
            # 检查挂载状态
            mount_status = self.get_mount_status(build_dir)
            
            if mount_status["is_mounted"]:
                # 尝试卸载
                success, message = self.unmount_wim(build_dir, commit=False)
                if success:
                    cleanup_result["actions_taken"].append("成功卸载WIM镜像")
                else:
                    cleanup_result["warnings"].append(f"卸载失败: {message}")
                    cleanup_result["success"] = False
            
            # 清理临时文件
            mount_dir = self.get_mount_dir(build_dir)
            if mount_dir.exists():
                try:
                    import shutil
                    shutil.rmtree(mount_dir, ignore_errors=True)
                    cleanup_result["actions_taken"].append("清理挂载目录")
                except Exception as e:
                    cleanup_result["warnings"].append(f"清理挂载目录失败: {str(e)}")
            
            # 验证清理结果
            validation = self.validate_build_structure(build_dir)
            if not validation["is_valid"]:
                cleanup_result["warnings"].extend(validation["errors"])
            
            return cleanup_result
            
        except Exception as e:
            self.logger.error(f"智能清理失败: {str(e)}")
            return {"error": str(e), "success": False}
    
    def get_operation_history(self, build_dir: Path) -> Dict:
        """获取操作历史（简化实现）
        
        Args:
            build_dir: 构建目录路径
            
        Returns:
            Dict: 操作历史信息
        """
        try:
            # 这里可以实现更复杂的操作历史记录
            # 目前返回基本的状态信息
            build_info = self.get_build_info(build_dir)
            mount_status = self.get_mount_status(build_dir)
            
            return {
                "build_dir": str(build_dir),
                "current_status": {
                    "mounted": mount_status["is_mounted"],
                    "wim_count": len(build_info.get("wim_files", [])),
                    "last_modified": build_info.get("created_time")
                },
                "available_operations": self._get_available_operations(build_dir),
                "recommendations": self._get_operation_recommendations(build_dir)
            }
            
        except Exception as e:
            self.logger.error(f"获取操作历史失败: {str(e)}")
            return {"error": str(e)}
    
    def _get_available_operations(self, build_dir: Path) -> list:
        """获取可用操作列表"""
        operations = []
        
        try:
            mount_status = self.get_mount_status(build_dir)
            wim_files = self.find_wim_files(build_dir)
            
            if wim_files and not mount_status["is_mounted"]:
                operations.append("mount")
            
            if mount_status["is_mounted"]:
                operations.append("unmount")
                operations.append("modify")
            
            if not mount_status["is_mounted"] and wim_files:
                operations.append("create_iso")
                operations.append("create_usb")
            
            operations.append("cleanup")
            operations.append("validate")
            
        except Exception as e:
            self.logger.error(f"获取可用操作失败: {str(e)}")
        
        return operations
    
    def _get_operation_recommendations(self, build_dir: Path) -> list:
        """获取操作建议"""
        recommendations = []
        
        try:
            mount_status = self.get_mount_status(build_dir)
            wim_files = self.find_wim_files(build_dir)
            validation = self.validate_build_structure(build_dir)
            
            if not wim_files:
                recommendations.append("建议先创建或复制WIM文件")
            
            if mount_status["is_mounted"]:
                recommendations.append("建议完成修改后及时卸载镜像")
            
            if validation.get("warnings"):
                recommendations.extend(validation["warnings"])
            
            if not recommendations:
                recommendations.append("构建目录状态良好，可以进行正常操作")
            
        except Exception as e:
            self.logger.error(f"获取操作建议失败: {str(e)}")
        
        return recommendations
    
    # === 调试和诊断接口 ===
    def get_diagnostics(self, build_dir: Path) -> Dict:
        """获取诊断信息
        
        Args:
            build_dir: 构建目录路径
            
        Returns:
            Dict: 诊断信息
        """
        try:
            self.logger.info("🔧 收集诊断信息...")
            
            diagnostics = {
                "timestamp": self._get_current_timestamp(),
                "build_directory": str(build_dir),
                "system_info": self.get_system_status(),
                "build_info": self.get_build_info(build_dir),
                "mount_status": self.get_mount_status(build_dir),
                "validation": self.validate_build_structure(build_dir),
                "wim_summary": self.get_wim_summary(build_dir),
                "module_status": {
                    "path_manager": "ok",
                    "check_manager": "ok",
                    "operation_manager": "ok",
                    "status_manager": "ok"
                }
            }
            
            return diagnostics
            
        except Exception as e:
            self.logger.error(f"收集诊断信息失败: {str(e)}")
            return {"error": str(e)}
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
