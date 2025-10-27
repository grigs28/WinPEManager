#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WIM操作线程模块
处理所有后台WIM操作
"""

from pathlib import Path
from typing import Tuple

from PyQt5.QtCore import QThread, pyqtSignal

from core.unified_manager import UnifiedWIMManager
from utils.logger import get_logger


class WIMOperationThread(QThread):
    """WIM操作线程 - 统一处理所有WIM操作"""

    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    error_signal = pyqtSignal(str)

    def __init__(self, config_manager, adk_manager, parent, operation: str, build_dir: Path, **kwargs):
        super().__init__()
        self.config_manager = config_manager
        self.adk_manager = adk_manager
        self.parent = parent
        self.operation = operation
        self.build_dir = build_dir
        self.kwargs = kwargs
        self._is_running = True

    def run(self):
        """执行WIM操作"""
        try:
            from core.unified_manager import UnifiedWIMManager
            from utils.logger import get_logger

            logger = get_logger("WIMOperationThread")
            logger.info(f"开始执行WIM操作: {self.operation}")

            # 创建统一WIM管理器
            self.progress_signal.emit(10)
            wim_manager = UnifiedWIMManager(self.config_manager, self.adk_manager, self.parent)
            self.progress_signal.emit(20)

            # 根据操作类型执行相应的方法
            if self.operation == "mount":
                success, message = self._mount_operation(wim_manager, logger)
            elif self.operation in ["unmount", "unmount_commit", "unmount_discard"]:
                success, message = self._unmount_operation(wim_manager, logger)
            elif self.operation == "create_iso":
                success, message = self._create_iso_operation(wim_manager, logger)
            elif self.operation == "create_usb":
                success, message = self._create_usb_operation(wim_manager, logger)
            elif self.operation == "smart_cleanup":
                success, message = self._smart_cleanup_operation(wim_manager, logger)
            else:
                success, message = False, f"不支持的操作类型: {self.operation}"

            self.progress_signal.emit(100)
            self.finished_signal.emit(success, message)

        except Exception as e:
            logger = get_logger("WIMOperationThread")
            logger.error(f"WIM操作异常: {str(e)}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            self.error_signal.emit(f"WIM操作过程中发生错误: {str(e)}")

    def _mount_operation(self, wim_manager, logger) -> Tuple[bool, str]:
        """挂载操作"""
        self.progress_signal.emit(30)
        self.log_signal.emit("检查挂载前条件...")

        # 执行挂载前检查
        wim_file_path = self.kwargs.get("wim_file_path")
        if not wim_file_path:
            # 获取主要WIM文件
            wim_file_path = wim_manager.get_primary_wim(self.build_dir)
            if not wim_file_path:
                return False, "未找到WIM文件"

        self.progress_signal.emit(40)
        self.log_signal.emit(f"开始挂载WIM文件: {wim_file_path.name}")

        # 执行挂载
        self.progress_signal.emit(60)
        success, message = wim_manager.mount_wim(self.build_dir, wim_file_path)

        self.progress_signal.emit(80)
        self.log_signal.emit("验证挂载结果...")

        return success, message

    def _unmount_operation(self, wim_manager, logger) -> Tuple[bool, str]:
        """卸载操作"""
        self.progress_signal.emit(30)
        self.log_signal.emit("检查卸载前条件...")

        # 执行卸载前检查
        success, message = wim_manager.pre_unmount_checks(self.build_dir)
        if not success:
            return False, message

        self.progress_signal.emit(40)
        commit = self.kwargs.get("commit", True)
        action_text = "保存更改并" if commit else "放弃更改并"
        self.log_signal.emit(f"开始{action_text}卸载...")

        # 执行卸载
        self.progress_signal.emit(60)
        self.log_signal.emit(f"正在{action_text}卸载WIM镜像...")
        success, message = wim_manager.unmount_wim(self.build_dir, commit=commit)

        self.progress_signal.emit(80)
        self.log_signal.emit("验证卸载结果...")

        # 完成清理工作
        self.progress_signal.emit(90)
        if success:
            self.log_signal.emit("清理挂载信息文件...")
            action_result = "保存更改" if commit else "放弃更改"
            self.log_signal.emit(f"WIM镜像{action_result}并卸载完成")
        else:
            self.log_signal.emit("卸载操作完成，但可能存在错误")

        self.progress_signal.emit(100)
        self.log_signal.emit("卸载操作已全部完成")

        return success, message

    def _create_iso_operation(self, wim_manager, logger) -> Tuple[bool, str]:
        """ISO创建操作"""
        self.progress_signal.emit(30)
        self.log_signal.emit("检查ISO创建前条件...")

        # 执行ISO创建前检查
        success, message = wim_manager.pre_iso_checks(self.build_dir)
        if not success:
            return False, message

        self.progress_signal.emit(40)
        iso_path = self.kwargs.get("iso_path")
        if not iso_path:
            return False, "未指定ISO输出路径"

        self.log_signal.emit(f"开始创建ISO文件: {Path(iso_path).name}")

        # 自动卸载已挂载的镜像
        self.progress_signal.emit(50)
        self.log_signal.emit("检查并自动卸载已挂载的镜像...")
        auto_success, auto_message = wim_manager.auto_unmount_before_iso(self.build_dir)
        if not auto_success:
            self.log_signal.emit(f"自动卸载警告: {auto_message}")

        # 创建ISO
        self.progress_signal.emit(70)
        success, message = wim_manager.create_iso(self.build_dir, Path(iso_path))

        self.progress_signal.emit(80)
        self.log_signal.emit("验证ISO创建结果...")

        return success, message

    def _create_usb_operation(self, wim_manager, logger) -> Tuple[bool, str]:
        """USB创建操作"""
        self.progress_signal.emit(30)
        self.log_signal.emit("检查USB创建前条件...")

        usb_path = self.kwargs.get("usb_path")
        if not usb_path:
            return False, "未指定USB设备路径"

        # 执行USB创建前检查
        success, message = wim_manager.pre_usb_checks(self.build_dir, Path(usb_path))
        if not success:
            return False, message

        self.progress_signal.emit(40)
        self.log_signal.emit(f"开始制作USB启动盘: {Path(usb_path).name}")

        # 创建USB
        self.progress_signal.emit(70)
        success, message = wim_manager.create_usb(self.build_dir, Path(usb_path))

        self.progress_signal.emit(80)
        self.log_signal.emit("验证USB创建结果...")

        return success, message

    def _smart_cleanup_operation(self, wim_manager, logger) -> Tuple[bool, str]:
        """智能清理操作"""
        self.progress_signal.emit(30)
        self.log_signal.emit("开始智能清理...")

        # 执行智能清理
        self.progress_signal.emit(60)
        cleanup_result = wim_manager.smart_cleanup(self.build_dir)

        self.progress_signal.emit(80)
        self.log_signal.emit("验证清理结果...")

        if cleanup_result.get("success", False):
            actions = cleanup_result.get("actions_taken", [])
            message = f"智能清理完成，执行了 {len(actions)} 个操作"
            if cleanup_result.get("warnings"):
                message += f"，有 {len(cleanup_result['warnings'])} 个警告"
            return True, message
        else:
            return False, "智能清理失败"

    def stop(self):
        """停止操作"""
        self._is_running = False