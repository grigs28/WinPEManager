#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WIM映像管理模块
提供WIM映像的挂载、卸载、USB启动盘制作功能
"""

import os
import shutil
import subprocess
import platform
import ctypes
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from PyQt5.QtWidgets import (
    QMessageBox, QProgressDialog, QFileDialog, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QComboBox, QDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor

from ui.button_styler import apply_3d_button_style, apply_3d_button_style_alternate, apply_3d_button_style_red
from utils.logger import log_error


class MountThread(QThread):
    """WIM挂载线程"""

    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)
    error_signal = pyqtSignal(str)

    def __init__(self, config_manager, adk_manager, parent, build_dir, wim_file_path=None):
        super().__init__()
        self.config_manager = config_manager
        self.adk_manager = adk_manager
        self.parent = parent
        self.build_dir = build_dir
        self.wim_file_path = wim_file_path
        self._is_running = True
    
    def run(self):
        """执行挂载操作"""
        try:
            # 阶段1: 初始化和准备 (5%)
            self.progress_signal.emit(5)
            
            # 阶段2: 创建统一WIM管理器 (15%)
            from core.unified_manager import UnifiedWIMManager
            from utils.logger import get_logger
            wim_manager = UnifiedWIMManager(self.config_manager, self.adk_manager, self.parent)
            logger = get_logger("WIMManager")
            self.progress_signal.emit(15)
            
            # 阶段3: 检查挂载状态 (25%)
            logger.info(f"开始挂载操作，WIM文件: {self.wim_file_path}")

            # 使用统一的挂载目录逻辑：使用UnifiedWIMManager提供的路径管理
            from core.unified_manager import UnifiedWIMManager
            wim_manager = UnifiedWIMManager(self.config_manager, self.adk_manager, self.parent)
            mount_dir = wim_manager.get_mount_dir(self.build_dir)
            logger.info(f"使用统一挂载目录: {mount_dir}")

            # 检查是否已经挂载
            if mount_dir.exists() and list(mount_dir.iterdir()):
                logger.warning("WIM文件已经挂载，无需重复挂载")
                self.progress_signal.emit(100)
                self.finished_signal.emit(False, "WIM文件已经挂载，无需重复挂载")
                return

            self.progress_signal.emit(25)

            # 阶段4: 准备挂载环境 (35%)
            logger.info("准备挂载环境")
            if not mount_dir.exists():
                mount_dir.mkdir(parents=True, exist_ok=True)
            self.progress_signal.emit(35)
            
            # 阶段5: 执行挂载操作 (35%-85%)
            logger.info("开始执行DISM挂载命令")
            self.progress_signal.emit(45)

            # 添加超时机制和更详细的日志
            import threading
            import time
            import queue
            
            # 使用队列安全的方式执行挂载操作
            result_queue = queue.Queue()
            
            def mount_operation():
                try:
                    logger.info("开始调用wim_manager.mount_wim()")
                    success, message = wim_manager.mount_wim(self.build_dir, Path(self.wim_file_path))
                    logger.info(f"wim_manager.mount_wim() 返回: success={success}, message='{message}'")
                    result_queue.put((success, message))
                except Exception as e:
                    error_msg = f"挂载操作异常: {str(e)}"
                    logger.error(error_msg)
                    import traceback
                    logger.error(f"异常堆栈: {traceback.format_exc()}")
                    result_queue.put((False, error_msg))
            
            # 启动挂载操作线程
            mount_thread = threading.Thread(target=mount_operation)
            mount_thread.daemon = True
            mount_thread.start()
            
            # 等待最多30秒
            try:
                success, message = result_queue.get(timeout=30)
                logger.info(f"从线程获得结果: success={success}, message='{message}'")
            except queue.Empty:
                logger.error("挂载操作超时，强制终止")
                self.progress_signal.emit(100)
                self.error_signal.emit("挂载操作超时，请检查系统资源或WIM文件完整性")
                return
            
            # 阶段6: 验证挂载结果 (85%)
            self.progress_signal.emit(85)
            logger.info("验证挂载结果")
            
            if success:
                # 验证挂载是否成功
                if mount_dir.exists() and list(mount_dir.iterdir()):
                    logger.info("挂载验证成功")
                    self.progress_signal.emit(95)
                else:
                    logger.warning("挂载验证失败，目录为空")
                    success = False
                    message = "挂载验证失败，挂载目录为空"
            else:
                logger.error(f"挂载操作失败: {message}")
            
            # 阶段7: 完成 (95%-100%)
            self.progress_signal.emit(95)
            
            # 短暂延迟确保用户能看到完成进度
            import time
            time.sleep(0.3)
            
            self.progress_signal.emit(100)
            logger.info("挂载操作完成")
            self.finished_signal.emit(success, message)
            
        except Exception as e:
            logger = get_logger("WIMManager")
            logger.error(f"挂载过程中发生异常: {str(e)}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            self.error_signal.emit(f"挂载过程中发生错误: {str(e)}")
    
    def stop(self):
        """停止挂载操作"""
        self._is_running = False


class UnmountThread(QThread):
    """WIM卸载线程"""

    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)
    error_signal = pyqtSignal(str)

    def __init__(self, config_manager, adk_manager, parent, build_dir, wim_file_path, commit=True):
        super().__init__()
        self.config_manager = config_manager
        self.adk_manager = adk_manager
        self.parent = parent
        self.build_dir = build_dir
        self.wim_file_path = wim_file_path
        self.commit = commit
        self._is_running = True
    
    def run(self):
        """执行卸载操作"""
        try:
            # 添加日志输出
            from utils.logger import get_logger
            logger = get_logger("WIMManager")
            logger.info(f"开始卸载操作，构建目录: {self.build_dir}")
            logger.info(f"卸载模式: {'保存更改' if self.commit else '放弃更改'}")
            
            # 阶段1: 初始化和准备 (5%)
            self.progress_signal.emit(5)
            
            # 阶段2: 创建统一WIM管理器 (15%)
            from core.unified_manager import UnifiedWIMManager
            wim_manager = UnifiedWIMManager(self.config_manager, self.adk_manager, self.parent)
            logger.info("UnifiedWIMManager 创建完成")
            self.progress_signal.emit(15)
            
            # 阶段3: 检查挂载状态 (25%)
            logger.info("检查挂载状态")
            # 使用统一的挂载目录逻辑：使用UnifiedWIMManager提供的路径管理
            from core.unified_manager import UnifiedWIMManager
            wim_manager = UnifiedWIMManager(self.config_manager, self.adk_manager, self.parent)
            mount_dir = wim_manager.get_mount_dir(self.build_dir)
            logger.info(f"使用统一挂载目录: {mount_dir}")

            if not mount_dir.exists():
                logger.warning("挂载目录不存在，无需卸载")
                self.progress_signal.emit(100)
                self.finished_signal.emit(False, "挂载目录不存在，无需卸载")
                return

            if not list(mount_dir.iterdir()):
                logger.warning("挂载目录为空，可能已经卸载")
                self.progress_signal.emit(100)
                self.finished_signal.emit(False, "挂载目录为空，可能已经卸载")
                return
            
            self.progress_signal.emit(25)
            
            # 阶段4: 准备卸载环境 (35%)
            logger.info("准备卸载环境")
            action_text = "保存更改并卸载" if self.commit else "放弃更改并卸载"
            logger.info(f"卸载模式: {action_text}")
            self.progress_signal.emit(35)
            
            # 阶段5: 执行卸载操作 (35%-85%)
            logger.info("开始执行DISM卸载命令")
            self.progress_signal.emit(45)
            
            success, message = wim_manager.unmount_wim(self.build_dir, commit=self.commit)
            logger.info(f"unmount_winpe_image 返回结果: success={success}, message={message}")
            
            # 阶段6: 验证卸载结果 (85%)
            self.progress_signal.emit(85)
            logger.info("验证卸载结果")
            
            if success:
                # 验证卸载是否成功
                if mount_dir.exists() and not list(mount_dir.iterdir()):
                    logger.info("卸载验证成功，目录已清空")
                    self.progress_signal.emit(95)
                elif not mount_dir.exists():
                    logger.info("卸载验证成功，挂载目录已删除")
                    self.progress_signal.emit(95)
                else:
                    logger.warning("卸载验证失败，目录仍然不为空")
                    success = False
                    message = "卸载验证失败，目录仍然不为空"
            else:
                logger.error(f"卸载操作失败: {message}")
            
            # 阶段7: 完成 (95%-100%)
            self.progress_signal.emit(95)
            
            # 短暂延迟确保用户能看到完成进度
            import time
            time.sleep(0.3)
            
            self.progress_signal.emit(100)
            logger.info("卸载操作完成")
            self.finished_signal.emit(success, message)
            
        except Exception as e:
            from utils.logger import get_logger
            logger = get_logger("WIMManager")
            logger.error(f"卸载过程中发生异常: {str(e)}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            self.error_signal.emit(f"卸载过程中发生错误: {str(e)}")
    
    def stop(self):
        """停止卸载操作"""
        self._is_running = False


class WIMManager:
    """WIM映像管理器"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.config_manager = main_window.config_manager
        self.adk_manager = main_window.adk_manager
        
    def show_wim_manager_dialog(self):
        """显示WIM映像管理对话框"""
        try:
            # 创建WIM管理对话框
            dialog = WIMManagerDialog(self.main_window, self.config_manager, self.adk_manager)
            
            # 显示对话框
            if dialog.exec_() == QDialog.Accepted:
                # 刷新构建目录列表
                if hasattr(self.main_window, 'refresh_builds_list'):
                    self.main_window.refresh_builds_list()
                    
        except Exception as e:
            log_error(e, "显示WIM管理对话框")
            QMessageBox.critical(self.main_window, "错误", f"显示WIM管理对话框时发生错误: {str(e)}")


class WIMManagerDialog(QDialog):
    """WIM映像管理对话框"""
    
    def __init__(self, parent, config_manager, adk_manager):
        super().__init__(parent)
        self.parent = parent
        self.config_manager = config_manager
        self.adk_manager = adk_manager
        
        self.setWindowTitle("WIM映像管理")
        self.setModal(True)
        self.resize(800, 600)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        
        # 创建WIM操作区域
        wim_group = QGroupBox("WIM映像操作")
        wim_layout = QVBoxLayout()
        
        # 挂载WIM映像
        mount_layout = QHBoxLayout()
        mount_btn = QPushButton("挂载WIM映像")
        mount_btn.setMinimumHeight(40)
        apply_3d_button_style(mount_btn)
        mount_btn.clicked.connect(self.mount_wim_image)
        
        mount_info = QLabel("挂载选中的WIM映像到挂载目录进行修改")
        mount_info.setWordWrap(True)
        mount_info.setStyleSheet("color: #666; font-size: 12px; margin: 5px;")
        
        mount_layout.addWidget(mount_btn)
        mount_layout.addWidget(mount_info)
        mount_layout.addStretch()
        
        # 卸载保存
        unmount_commit_layout = QHBoxLayout()
        unmount_commit_btn = QPushButton("卸载并保存")
        unmount_commit_btn.setMinimumHeight(40)
        apply_3d_button_style_alternate(unmount_commit_btn)
        unmount_commit_btn.clicked.connect(self.unmount_wim_commit)
        
        unmount_commit_info = QLabel("卸载WIM映像并保存所有更改")
        unmount_commit_info.setWordWrap(True)
        unmount_commit_info.setStyleSheet("color: #666; font-size: 12px; margin: 5px;")
        
        unmount_commit_layout.addWidget(unmount_commit_btn)
        unmount_commit_layout.addWidget(unmount_commit_info)
        unmount_commit_layout.addStretch()
        
        # 卸载不保存
        unmount_discard_layout = QHBoxLayout()
        unmount_discard_btn = QPushButton("卸载不保存")
        unmount_discard_btn.setMinimumHeight(40)
        apply_3d_button_style_red(unmount_discard_btn)
        unmount_discard_btn.clicked.connect(self.unmount_wim_discard)
        
        unmount_discard_info = QLabel("卸载WIM映像并放弃所有更改")
        unmount_discard_info.setWordWrap(True)
        unmount_discard_info.setStyleSheet("color: #666; font-size: 12px; margin: 5px;")
        
        unmount_discard_layout.addWidget(unmount_discard_btn)
        unmount_discard_layout.addWidget(unmount_discard_info)
        unmount_discard_layout.addStretch()
        
        # USB启动盘制作
        usb_layout = QHBoxLayout()
        usb_btn = QPushButton("制作USB启动盘")
        usb_btn.setMinimumHeight(40)
        apply_3d_button_style(usb_btn)
        usb_btn.clicked.connect(self.create_usb_bootable)
        
        usb_info = QLabel("制作可启动的USB驱动器")
        usb_info.setWordWrap(True)
        usb_info.setStyleSheet("color: #666; font-size: 12px; margin: 5px;")
        
        usb_layout.addWidget(usb_btn)
        usb_layout.addWidget(usb_info)
        usb_layout.addStretch()
        
        # 添加到WIM布局
        wim_layout.addLayout(mount_layout)
        wim_layout.addLayout(unmount_commit_layout)
        wim_layout.addLayout(unmount_discard_layout)
        wim_layout.addLayout(usb_layout)
        
        wim_group.setLayout(wim_layout)
        
        # 创建状态显示区域
        status_group = QGroupBox("当前状态")
        status_layout = QVBoxLayout()
        
        # WIM映像列表
        self.wim_list = QListWidget()
        self.wim_list.setMinimumHeight(200)
        self.wim_list.setStyleSheet("""
            QListWidget {
                font-family: 'Microsoft YaHei UI', 'SimHei';
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
                alternate-background-color: #f9f9f9;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
                border-radius: 3px;
                margin: 1px;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: white;
                font-weight: bold;
                border: 1px solid #005a9e;
            }
            QListWidget::item:hover {
                background-color: #f0f8ff;
                border: 1px solid #b3d9ff;
            }
        """)
        self.wim_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        status_layout.addWidget(QLabel("所有WinPE工作目录中的WIM映像文件:"))
        status_layout.addWidget(self.wim_list)
        
        status_group.setLayout(status_layout)
        
        # 添加到主布局
        main_layout.addWidget(wim_group)
        main_layout.addWidget(status_group)
        
        # 添加按钮区域
        button_layout = QHBoxLayout()
        
        close_btn = QPushButton("关闭")
        close_btn.setMinimumHeight(40)
        close_btn.clicked.connect(self.reject)
        
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.setMinimumHeight(40)
        refresh_btn.clicked.connect(self.refresh_directories)
        
        button_layout.addStretch()
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        
        # 初始化数据
        self.refresh_directories()
    
    def refresh_directories(self):
        """递归扫描WinPE工作目录中的所有目录，列出所有WIM文件"""
        try:
            self.wim_list.clear()
            
            # 获取工作空间路径
            workspace = Path(self.config_manager.get("output.workspace", ""))
            if not workspace.exists():
                workspace = Path.cwd() / "workspace" / "WinPE_Build"
            
            # 递归扫描所有目录中的WIM文件
            all_wim_files = []
            if workspace.exists():
                all_wim_files = self.scan_wim_files_recursive(workspace)
            
            # 按大小排序
            all_wim_files.sort(key=lambda x: x["size"], reverse=True)
            
            # 添加到列表
            for wim_file in all_wim_files:
                size_mb = wim_file["size"] / (1024 * 1024)
                size_str = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{size_mb*1024:.0f} KB"
                
                status_text = "已挂载" if wim_file["mount_status"] else "未挂载"
                
                # 获取挂载位置 - 统一使用构建目录下的mount目录
                if wim_file["mount_status"]:
                    mount_dir = wim_file["build_dir"] / "mount"
                    mount_path = str(mount_dir)
                else:
                    mount_path = "未挂载"

                # 构建目录信息和相对路径
                build_dir_name = wim_file["build_dir"].name
                wim_relative_path = str(wim_file["path"]).replace(str(wim_file["build_dir"]), "").lstrip("\\/")

                import datetime
                ctime = wim_file["build_dir"].stat().st_ctime
                time_str = datetime.datetime.fromtimestamp(ctime).strftime('%Y-%m-%d %H:%M')

                # 为已挂载项添加图标
                display_name = wim_file['name']
                if wim_file["mount_status"] and not display_name.startswith("📂 "):
                    display_name = f"📂 {display_name}"

                item_text = f"{display_name} - {size_str} - {wim_file['type'].upper()} - {status_text} - {build_dir_name} ({time_str}) - {wim_relative_path}"

                list_item = QListWidgetItem(item_text)
                list_item.setData(Qt.UserRole, wim_file)
                list_item.setToolTip(
                    f"WIM文件: {wim_file['name']}\n"
                    f"完整路径: {wim_file['path']}\n"
                    f"相对路径: {wim_relative_path}\n"
                    f"大小: {size_str}\n"
                    f"类型: {wim_file['type'].upper()}\n"
                    f"状态: {status_text}\n"
                    f"构建目录: {build_dir_name} ({time_str})\n"
                    f"挂载位置: {mount_path}"
                )
                
                # 设置状态颜色和样式
                if wim_file["mount_status"]:
                    # 已挂载项使用更明显的绿色背景和深色文字
                    list_item.setBackground(QColor("#E8F5E8"))
                    list_item.setForeground(QColor("#2E7D32"))  # 深绿色文字

                    # 设置自定义样式用于已挂载项
                    custom_style = """
                        QListWidget::item {
                            background-color: #E8F5E8;
                            border: 1px solid #4CAF50;
                            font-weight: 500;
                            padding: 8px;
                            border-radius: 3px;
                            margin: 1px;
                        }
                        QListWidget::item:selected {
                            background-color: #2E7D32;
                            color: white;
                            border: 1px solid #1B5E20;
                            font-weight: bold;
                        }
                    """
                    list_item.setData(Qt.UserRole + 1, "mounted")
                else:
                    # 未挂载项使用默认样式
                    list_item.setForeground(QColor("#333333"))  # 深灰色文字
                    custom_style = """
                        QListWidget::item {
                            background-color: white;
                            border: 1px solid #eee;
                            font-weight: normal;
                            padding: 8px;
                            border-radius: 3px;
                            margin: 1px;
                        }
                        QListWidget::item:selected {
                            background-color: #0078d4;
                            color: white;
                            border: 1px solid #005a9e;
                            font-weight: bold;
                        }
                    """
                    list_item.setData(Qt.UserRole + 1, "unmounted")

                self.wim_list.addItem(list_item)

                # 应用自定义样式
                if wim_file["mount_status"]:
                    # 为已挂载项应用特殊样式
                    row = self.wim_list.count() - 1
                    item = self.wim_list.item(row)
                    if item:
                        item.setBackground(QColor("#E8F5E8"))
                        item.setForeground(QColor("#2E7D32"))
            
            if not all_wim_files:
                self.wim_list.addItem("暂无WIM映像文件")
                
        except Exception as e:
            log_error(e, "刷新WIM文件列表")
            QMessageBox.critical(self, "错误", f"刷新WIM文件列表时发生错误: {str(e)}")
    
    def scan_wim_files_recursive(self, root_dir: Path) -> List[Dict]:
        """递归扫描目录中的所有WIM文件"""
        wim_files = []

        try:
            # 首先获取所有构建目录（以WinPE_开头的目录）
            build_dirs = []
            for item in root_dir.iterdir():
                if item.is_dir() and item.name.startswith("WinPE_"):
                    build_dirs.append(item)

            # 为每个构建目录扫描WIM文件
            for build_dir in build_dirs:
                wim_files.extend(self.scan_wim_files_in_build_dir(build_dir))

            # 也扫描其他位置的WIM文件（比如旧的构建格式）
            for item in root_dir.rglob("*"):
                if item.is_file() and item.suffix.lower() == '.wim':
                    # 检查是否已经在构建目录中处理过
                    already_processed = False
                    for wim_file in wim_files:
                        if str(item) == str(wim_file["path"]):
                            already_processed = True
                            break

                    if not already_processed:
                        # 确定WIM文件类型
                        wim_type = self.determine_wim_type(item)

                        # 获取构建目录（WIM文件所在的上级目录）
                        build_dir = self.find_build_dir_for_wim(item)

                        if build_dir:
                            wim_files.append({
                                "path": item,
                                "name": item.name,
                                "type": wim_type,
                                "size": item.stat().st_size,
                                "mount_status": self.check_mount_status({"path": str(item)}),
                                "build_dir": build_dir
                            })
                        else:
                            # 如果找不到构建目录，使用文件所在目录
                            wim_files.append({
                                "path": item,
                                "name": item.name,
                                "type": wim_type,
                                "size": item.stat().st_size,
                                "mount_status": False,  # 默认未挂载
                                "build_dir": item.parent
                            })

        except Exception as e:
            log_error(e, f"递归扫描WIM文件: {root_dir}")

        return wim_files

    def scan_wim_files_in_build_dir(self, build_dir: Path) -> List[Dict]:
        """扫描特定构建目录中的WIM文件"""
        wim_files = []

        try:
            # 检查构建目录是否存在
            if not build_dir.exists():
                return wim_files

            # 扫描boot.wim（在media/sources目录下）
            boot_wim_path = build_dir / "media" / "sources" / "boot.wim"
            if boot_wim_path.exists():
                wim_files.append({
                    "path": boot_wim_path,
                    "name": boot_wim_path.name,
                    "type": "copype",
                    "size": boot_wim_path.stat().st_size,
                    "mount_status": self.check_mount_status({"path": str(boot_wim_path)}),
                    "build_dir": build_dir
                })

            # 扫描winpe.wim（在构建目录根目录下）
            winpe_wim_path = build_dir / "winpe.wim"
            if winpe_wim_path.exists():
                wim_files.append({
                    "path": winpe_wim_path,
                    "name": winpe_wim_path.name,
                    "type": "dism",
                    "size": winpe_wim_path.stat().st_size,
                    "mount_status": self.check_mount_status({"path": str(winpe_wim_path)}),
                    "build_dir": build_dir
                })

            # 扫描其他WIM文件（递归搜索）
            for item in build_dir.rglob("*.wim"):
                # 跳过已经处理过的文件
                if item.name.lower() in ["boot.wim", "winpe.wim"]:
                    continue

                # 确定WIM文件类型
                wim_type = self.determine_wim_type(item)

                wim_files.append({
                    "path": item,
                    "name": item.name,
                    "type": wim_type,
                    "size": item.stat().st_size,
                    "mount_status": self.check_mount_status({"path": str(item)}),
                    "build_dir": build_dir
                })

        except Exception as e:
            log_error(e, f"扫描构建目录WIM文件: {build_dir}")

        return wim_files
    
    def determine_wim_type(self, wim_path: Path) -> str:
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
    
    def find_build_dir_for_wim(self, wim_path: Path) -> Optional[Path]:
        """为WIM文件找到对应的构建目录"""
        try:
            # 如果是boot.wim，构建目录是上上级目录
            if wim_path.name.lower() == "boot.wim":
                # 路径应该是: build_dir/media/sources/boot.wim
                if "sources" in str(wim_path) and "media" in str(wim_path):
                    return wim_path.parent.parent.parent
                else:
                    # 如果路径格式不标准，尝试找到WinPE_开头的目录
                    current = wim_path.parent
                    while current != current.parent:
                        if current.name.startswith("WinPE_"):
                            return current
                        current = current.parent

            # 如果是winpe.wim，构建目录是上级目录
            elif wim_path.name.lower() == "winpe.wim":
                return wim_path.parent

            # 对于其他WIM文件，尝试找到包含WinPE_的上级目录
            current = wim_path.parent
            while current != current.parent:  # 避免无限循环
                if current.name.startswith("WinPE_"):
                    return current
                current = current.parent

            # 如果没找到WinPE_目录，尝试其他常见的构建目录结构
            # 检查是否有media目录
            media_dir = wim_path.parent / "media"
            if media_dir.exists():
                return wim_path.parent

            # 检查是否有mount目录
            mount_dir = wim_path.parent / "mount"
            if mount_dir.exists():
                return wim_path.parent

            # 如果没找到，返回文件所在目录
            return wim_path.parent

        except Exception:
            return wim_path.parent
    
    
    def check_mount_status(self, wim_file: Dict) -> bool:
        """检查WIM文件的挂载状态"""
        try:
            if not wim_file or not wim_file.get("path"):
                return False

            wim_file_path = Path(wim_file["path"])
            mount_dir = wim_file_path.parent / "mount"
            if not mount_dir.exists():
                return False
            return bool(list(mount_dir.iterdir()))
        except Exception:
            return False
    
    def get_selected_wim(self) -> Optional[Dict]:
        """获取选中的WIM文件"""
        current_item = self.wim_list.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None
    
    def mount_wim_image(self):
        """挂载WIM映像"""
        try:
            wim_file = self.get_selected_wim()
            if not wim_file:
                QMessageBox.warning(self, "提示", "请先选择要挂载的WIM映像文件")
                return
            
            # 检查是否已经挂载
            if wim_file["mount_status"]:
                QMessageBox.information(self, "提示", f"WIM映像 {wim_file['name']} 已经挂载，无需重复挂载。")
                return
            
            # 检查管理员权限
            if not ctypes.windll.shell32.IsUserAnAdmin():
                reply = QMessageBox.question(
                    self, "需要管理员权限",
                    "WIM挂载操作需要管理员权限。\n\n是否以管理员身份重新启动程序？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.restart_as_admin()
                return
            
            # 执行挂载操作
            self.parent.log_message(f"开始挂载WIM映像: {wim_file['name']}")
            
            # 创建进度对话框
            progress = QProgressDialog("正在挂载WIM映像...", "取消", 0, 100, self)
            progress.setWindowTitle("挂载WIM映像")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            # 使用列表框中的构建目录和WIM文件路径
            build_dir = wim_file["build_dir"]
            wim_file_path = wim_file["path"]

            # 创建挂载线程
            self.mount_thread = MountThread(self.config_manager, self.adk_manager, self.parent, build_dir, wim_file_path)
            self.mount_thread.progress_signal.connect(progress.setValue)
            self.mount_thread.finished_signal.connect(self.on_mount_finished)
            self.mount_thread.error_signal.connect(self.on_mount_error)
            
            # 保存进度对话框和WIM文件信息用于回调
            self.current_progress = progress
            self.current_wim_file = wim_file
            self.current_build_dir = build_dir
            
            # 启动线程
            self.mount_thread.start()
                
        except Exception as e:
            log_error(e, "挂载WIM映像")
            QMessageBox.critical(self, "错误", f"挂载WIM映像时发生错误: {str(e)}")
    
    def unmount_wim_commit(self):
        """卸载WIM映像并保存"""
        self.unmount_wim_image(commit=True)
    
    def unmount_wim_discard(self):
        """卸载WIM映像不保存"""
        self.unmount_wim_image(commit=False)
    
    def unmount_wim_image(self, commit: bool = True):
        """卸载WIM映像"""
        try:
            wim_file = self.get_selected_wim()
            if not wim_file:
                QMessageBox.warning(self, "提示", "请先选择要卸载的WIM映像文件")
                return
            
            # 检查是否已挂载
            if not wim_file["mount_status"]:
                QMessageBox.warning(self, "提示", "选中的WIM映像未挂载")
                return
            
            # 检查管理员权限
            if not ctypes.windll.shell32.IsUserAnAdmin():
                reply = QMessageBox.question(
                    self, "需要管理员权限",
                    "WIM卸载操作需要管理员权限。\n\n是否以管理员身份重新启动程序？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.restart_as_admin()
                return
            
            action = "保存" if commit else "放弃"
            self.parent.log_message(f"开始卸载WIM映像并{action}: {wim_file['name']}")
            
            # 创建进度对话框
            progress = QProgressDialog(f"正在卸载WIM映像并{action}...", "取消", 0, 100, self)
            progress.setWindowTitle(f"卸载WIM映像并{action}")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            # 使用列表框中的构建目录
            build_dir = wim_file["build_dir"]
            wim_file_path = wim_file["path"]

            # 创建卸载线程
            self.unmount_thread = UnmountThread(self.config_manager, self.adk_manager, self.parent, build_dir, wim_file_path, commit)
            self.unmount_thread.progress_signal.connect(progress.setValue)
            self.unmount_thread.finished_signal.connect(self.on_unmount_finished)
            self.unmount_thread.error_signal.connect(self.on_unmount_error)
            
            # 保存进度对话框和WIM文件信息用于回调
            self.current_progress = progress
            self.current_wim_file = wim_file
            self.current_build_dir = build_dir
            self.current_action = action
            
            # 启动线程
            self.unmount_thread.start()
                
        except Exception as e:
            log_error(e, f"卸载WIM映像并{action}")
            QMessageBox.critical(self, "错误", f"卸载WIM映像时发生错误: {str(e)}")
    
    def create_usb_bootable(self):
        """制作USB启动盘"""
        try:
            wim_file = self.get_selected_wim()
            if not wim_file:
                QMessageBox.warning(self, "提示", "请先选择要制作USB启动盘的WIM映像文件")
                return
            
            # 选择USB驱动器
            usb_path = QFileDialog.getExistingDirectory(
                self,
                "选择USB驱动器",
                "",
                QFileDialog.ShowDirsOnly
            )
            
            if not usb_path:
                return
            
            usb_path = Path(usb_path)
            
            # 确认制作USB启动盘
            reply = QMessageBox.question(
                self,
                "确认制作USB启动盘",
                f"即将制作USB启动盘:\n\n"
                f"WIM文件: {wim_file['name']}\n"
                f"USB驱动器: {usb_path}\n\n"
                f"⚠️ 警告: 此操作将格式化USB驱动器并删除所有数据！\n\n"
                f"确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # 检查管理员权限
            if not ctypes.windll.shell32.IsUserAnAdmin():
                reply = QMessageBox.question(
                    self,
                    "需要管理员权限",
                    "USB启动盘制作需要管理员权限。\n\n是否以管理员身份重新启动程序？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.restart_as_admin()
                return
            else:
                return
            
            self.parent.log_message(f"开始制作USB启动盘: {wim_file['name']} -> {usb_path}")
            
            # 创建进度对话框
            progress = QProgressDialog("正在制作USB启动盘...", "取消", 0, 100, self)
            progress.setWindowTitle("制作USB启动盘")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            try:
                # 执行USB启动盘制作
                success, message = self._create_usb_bootable_device(wim_file, usb_path, progress)
                
                progress.setValue(100)
                progress.close()
                
                if success:
                    QMessageBox.information(self, "制作成功", f"USB启动盘制作成功:\n{usb_path}")
                    self.parent.log_message(f"USB启动盘制作成功: {usb_path}")
                else:
                    QMessageBox.critical(self, "制作失败", f"USB启动盘制作失败:\n{message}")
                    self.parent.log_message(f"USB启动盘制作失败: {message}")
                    
            except Exception as e:
                progress.close()
                log_error(e, "制作USB启动盘")
                QMessageBox.critical(self, "错误", f"制作USB启动盘时发生错误: {str(e)}")
                
        except Exception as e:
            log_error(e, "制作USB启动盘")
            QMessageBox.critical(self, "错误", f"制作USB启动盘时发生错误: {str(e)}")
    
    def _create_usb_bootable_device(self, wim_file: Dict, usb_path: Path, progress: QProgressDialog) -> Tuple[bool, str]:
        """制作USB启动盘设备"""
        try:
            progress.setValue(10)
            progress.setLabelText("准备USB设备...")
            
            # 检查USB路径是否存在
            if not usb_path.exists():
                return False, f"USB驱动器路径不存在: {usb_path}"
            
            # 检查是否为可移动设备
            if not self.is_removable_device(usb_path):
                reply = QMessageBox.question(
                    self,
                    "设备类型确认",
                    f"选定的路径可能不是可移动设备:\n{usb_path}\n\n"
                    "继续制作可能导致数据丢失。\n\n"
                    "确定要继续吗？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply != QMessageBox.Yes:
                    return False, "用户取消操作"
            
            progress.setValue(20)
            progress.setLabelText("格式化USB设备...")
            
            # 格式化USB设备
            format_success, format_message = self.format_usb_device(usb_path)
            if not format_success:
                return False, f"USB设备格式化失败: {format_message}"
            
            progress.setValue(40)
            progress.setLabelText("复制WIM文件...")
            
            # 复制WIM文件到USB设备
            copy_success, copy_message = self.copy_wim_to_usb(wim_file, usb_path)
            if not copy_success:
                return False, f"WIM文件复制失败: {copy_message}"
            
            progress.setValue(60)
            progress.setLabelText("设置启动扇区...")
            
            # 设置启动扇区
            boot_success, boot_message = self.setup_usb_boot_sector(usb_path)
            if not boot_success:
                return False, f"启动扇区设置失败: {boot_message}"
            
            progress.setValue(80)
            progress.setLabelText("验证USB启动盘...")
            
            # 验证USB启动盘
            verify_success, verify_message = self.verify_usb_bootable(usb_path)
            if not verify_success:
                return False, f"USB启动盘验证失败: {verify_message}"
            
            progress.setValue(100)
            return True, f"USB启动盘制作成功: {usb_path}"
            
        except Exception as e:
            return False, f"制作USB启动盘时发生错误: {str(e)}"
    
    def is_removable_device(self, path: Path) -> bool:
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
    
    def format_usb_device(self, usb_path: Path) -> Tuple[bool, str]:
        """格式化USB设备"""
        try:
            # 使用Windows格式化命令
            drive = str(usb_path)[:2]
            
            # 格式化为FAT32文件系统
            cmd = f'format {drive}: /FS:FAT32 /Q /X'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, "USB设备格式化成功"
            else:
                return False, f"格式化命令失败: {result.stderr}"
                
        except Exception as e:
            return False, f"格式化USB设备时发生错误: {str(e)}"
    
    def copy_wim_to_usb(self, wim_file: Dict, usb_path: Path) -> Tuple[bool, str]:
        """复制WIM文件到USB设备"""
        try:
            # 复制WIM文件
            import shutil
            
            source_path = wim_file["path"]
            dest_path = usb_path / wim_file["path"].name
            
            shutil.copy2(source_path, dest_path)
            
            return True, "WIM文件复制成功"
            
        except Exception as e:
            return False, f"复制WIM文件时发生错误: {str(e)}"
    
    def setup_usb_boot_sector(self, usb_path: Path) -> Tuple[bool, str]:
        """设置USB启动扇区"""
        try:
            # 使用diskpart设置活动分区
            drive = str(usb_path)[:2]
            
            script = f"""
select volume {drive}=1
active
exit
"""
            
            # 创建临时脚本文件
            script_file = usb_path / "setup_boot.txt"
            with open(script_file, 'w') as f:
                f.write(script)
            
            # 执行diskpart命令
            cmd = f'diskpart /s {script_file}'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            # 清理临时文件
            try:
                script_file.unlink()
            except:
                pass
            
            if result.returncode == 0:
                return True, "USB启动扇区设置成功"
            else:
                return False, f"启动扇区设置失败: {result.stderr}"
                
        except Exception as e:
            return False, f"设置USB启动扇区时发生错误: {str(e)}"
    
    def verify_usb_bootable(self, usb_path: Path) -> Tuple[bool, str]:
        """验证USB启动盘"""
        try:
            # 检查关键文件是否存在
            wim_files = list(usb_path.glob("*.wim"))
            
            if not wim_files:
                return False, "USB设备上未找到WIM文件"
            
            # 检查启动扇区
            drive = str(usb_path)[:2]
            cmd = f'diskpart /s "list volume"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                # 检查是否有活动分区
                if "Active" in result.stdout:
                    return True, "USB启动盘验证成功"
                else:
                    return False, "USB设备未设置活动分区"
            else:
                return False, f"无法验证启动扇区: {result.stderr}"
                
        except Exception as e:
            return False, f"验证USB启动盘时发生错误: {str(e)}"
    
    def on_mount_finished(self, success: bool, message: str):
        """挂载完成回调"""
        try:
            # 关闭进度对话框
            if hasattr(self, 'current_progress'):
                self.current_progress.close()
            
            if success:
                QMessageBox.information(self, "挂载成功", f"WIM映像挂载成功:\n{self.current_wim_file['name']}")
                self.parent.log_message(f"WIM映像挂载成功: {self.current_wim_file['name']}")
                self.refresh_directories()
            else:
                QMessageBox.critical(self, "挂载失败", f"WIM映像挂载失败:\n{message}")
                self.parent.log_message(f"WIM映像挂载失败: {message}")
                
        except Exception as e:
            log_error(e, "挂载完成回调")
            QMessageBox.critical(self, "错误", f"处理挂载结果时发生错误: {str(e)}")
    
    def on_mount_error(self, error_message: str):
        """挂载错误回调"""
        try:
            # 关闭进度对话框
            if hasattr(self, 'current_progress'):
                self.current_progress.close()
            
            QMessageBox.critical(self, "挂载错误", f"挂载过程中发生错误:\n{error_message}")
            self.parent.log_message(f"挂载过程中发生错误: {error_message}")
                
        except Exception as e:
            log_error(e, "挂载错误回调")
            QMessageBox.critical(self, "错误", f"处理挂载错误时发生错误: {str(e)}")
    
    def on_unmount_finished(self, success: bool, message: str):
        """卸载完成回调"""
        try:
            # 关闭进度对话框
            if hasattr(self, 'current_progress'):
                self.current_progress.close()
            
            if success:
                QMessageBox.information(self, "卸载成功", f"WIM映像卸载成功并{self.current_action}:\n{self.current_wim_file['name']}")
                self.parent.log_message(f"WIM映像卸载成功并{self.current_action}: {self.current_wim_file['name']}")
                self.refresh_directories()
            else:
                QMessageBox.critical(self, "卸载失败", f"WIM映像卸载失败:\n{message}")
                self.parent.log_message(f"WIM映像卸载失败: {message}")
                
        except Exception as e:
            log_error(e, "卸载完成回调")
            QMessageBox.critical(self, "错误", f"处理卸载结果时发生错误: {str(e)}")
    
    def on_unmount_error(self, error_message: str):
        """卸载错误回调"""
        try:
            # 关闭进度对话框
            if hasattr(self, 'current_progress'):
                self.current_progress.close()
            
            QMessageBox.critical(self, "卸载错误", f"卸载过程中发生错误:\n{error_message}")
            self.parent.log_message(f"卸载过程中发生错误: {error_message}")
                
        except Exception as e:
            log_error(e, "卸载错误回调")
            QMessageBox.critical(self, "错误", f"处理卸载错误时发生错误: {str(e)}")
    
    def on_item_double_clicked(self, item):
        """双击列表项事件"""
        try:
            wim_file = item.data(Qt.UserRole)
            if not wim_file:
                return
            
            # 如果已挂载，打开挂载目录
            if wim_file["mount_status"]:
                # 使用WIM文件所在目录的mount子目录
                wim_file_path = Path(wim_file["path"])
                mount_dir = wim_file_path.parent / "mount"
                
                if mount_dir.exists():
                    # 打开文件管理器
                    import subprocess
                    import platform
                    
                    if platform.system() == "Windows":
                        subprocess.run(['explorer', str(mount_dir)])
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(['open', str(mount_dir)])
                    else:  # Linux
                        subprocess.run(['xdg-open', str(mount_dir)])
                    
                    self.parent.log_message(f"已打开挂载目录: {mount_dir}")
                else:
                    QMessageBox.warning(self, "提示", f"挂载目录不存在: {mount_dir}")
            else:
                # 如果未挂载，提示用户
                reply = QMessageBox.question(
                    self, "提示", 
                    f"WIM映像 {wim_file['name']} 未挂载。\n\n是否要挂载此映像？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.mount_wim_image()
                    
        except Exception as e:
            log_error(e, "双击列表项")
            QMessageBox.critical(self, "错误", f"双击操作时发生错误: {str(e)}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 停止所有线程
            if hasattr(self, 'mount_thread') and self.mount_thread.isRunning():
                self.mount_thread.stop()
                self.mount_thread.wait(3000)
            
            if hasattr(self, 'unmount_thread') and self.unmount_thread.isRunning():
                self.unmount_thread.stop()
                self.unmount_thread.wait(3000)
            
            event.accept()
            
        except Exception as e:
            log_error(e, "WIM管理对话框关闭")
            event.accept()
    
    def restart_as_admin(self):
        """以管理员身份重新启动程序"""
        try:
            import sys
            
            # 获取当前程序路径
            if hasattr(sys, 'frozen'):
                current_exe = sys.executable
            else:
                current_exe = str(Path(__file__).parent.parent.parent / "main.py")
            
            # 请求管理员权限重新启动
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                current_exe,
                " ".join(sys.argv[1:]),
                None,
                1
            )
            
            # 退出当前程序
            from PyQt5.QtWidgets import QApplication
            QApplication.quit()
            sys.exit(0)
            
        except Exception as e:
            QMessageBox.critical(self, "重新启动失败", f"无法以管理员身份重新启动程序: {str(e)}")
