#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进度对话框模块
用于显示长时间操作的进度
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QProgressBar, QTextEdit, QWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon
import sys
from pathlib import Path


class ProgressDialog(QDialog):
    """进度对话框类"""

    # 定义信号
    cancelled = pyqtSignal()

    def __init__(self, parent=None, title="操作进度", show_log=True, can_cancel=True):
        """
        初始化进度对话框

        Args:
            parent: 父窗口
            title: 对话框标题
            show_log: 是否显示日志区域
            can_cancel: 是否可以取消操作
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(500, 350 if show_log else 200)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)

        # 状态变量
        self.is_cancelled = False
        self.show_log = show_log
        self.can_cancel = can_cancel

        self._init_ui()
        self._setup_style()

    def _init_ui(self):
        """初始化UI组件"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题标签
        self.title_label = QLabel("正在执行操作...")
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.title_label.setFont(font)
        layout.addWidget(self.title_label)

        # 当前操作标签
        self.current_op_label = QLabel("准备开始...")
        self.current_op_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.current_op_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

        # 详细信息标签
        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)

        # 日志区域（可选）
        if self.show_log:
            log_label = QLabel("操作日志:")
            log_label.setFont(font)
            layout.addWidget(log_label)

            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            self.log_text.setMaximumHeight(120)
            self.log_text.setFont(QFont("Consolas", 9))
            layout.addWidget(self.log_text)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        if self.can_cancel:
            self.cancel_button = QPushButton("取消")
            self.cancel_button.clicked.connect(self._on_cancel_clicked)
            self.cancel_button.setFixedWidth(80)
            button_layout.addWidget(self.cancel_button)

        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.close)
        self.close_button.setFixedWidth(80)
        self.close_button.setEnabled(False)  # 初始时禁用关闭按钮
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _setup_style(self):
        """设置样式"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
            }
            QLabel {
                color: #333333;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
                color: #333333;
            }
        """)

    def _on_cancel_clicked(self):
        """取消按钮点击事件"""
        self.is_cancelled = True
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("正在取消...")
        self.cancelled.emit()
        self.add_log("用户请求取消操作 [进度对话框]")

    def set_title(self, title):
        """设置标题"""
        self.setWindowTitle(title)
        self.title_label.setText(title)

    def set_current_operation(self, operation):
        """设置当前操作描述"""
        self.current_op_label.setText(operation)

    def set_progress(self, value, message=""):
        """设置进度值和消息"""
        self.progress_bar.setValue(value)
        if message:
            self.detail_label.setText(message)

    def add_log(self, message):
        """添加日志消息"""
        if self.show_log:
            self.log_text.append(message)
            # 自动滚动到底部
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )

    def set_completed(self, success=True, message=""):
        """设置操作完成状态"""
        if success:
            self.progress_bar.setValue(100)
            self.detail_label.setText(message or "操作完成")
            self.add_log(f"操作成功完成: {message} [进度对话框]")
        else:
            self.detail_label.setText(message or "操作失败")
            self.add_log(f"操作失败: {message} [进度对话框]")

        # 禁用取消按钮，启用关闭按钮
        if self.can_cancel:
            self.cancel_button.setEnabled(False)
            self.cancel_button.setVisible(False)
        self.close_button.setEnabled(True)

        # 更改进度条颜色
        if not success:
            self.progress_bar.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #f44336;
                }
            """)

    def reset(self):
        """重置对话框状态"""
        self.progress_bar.setValue(0)
        self.current_op_label.setText("准备开始...")
        self.detail_label.setText("")
        if self.show_log:
            self.log_text.clear()
        self.is_cancelled = False

        if self.can_cancel:
            self.cancel_button.setEnabled(True)
            self.cancel_button.setText("取消")
            self.cancel_button.setVisible(True)
        self.close_button.setEnabled(False)

        # 重置进度条样式
        self.progress_bar.setStyleSheet("")


class WIMOperationThread(QThread):
    """WIM操作线程"""

    # 定义信号
    progress = pyqtSignal(int, str)  # 进度信号 (百分比, 消息)
    log = pyqtSignal(str)  # 日志信号
    finished = pyqtSignal(bool, str)  # 完成信号 (成功状态, 消息)

    def __init__(self, operation_type, wim_manager, *args, **kwargs):
        """
        初始化WIM操作线程

        Args:
            operation_type: 操作类型 ('mount' 或 'unmount')
            wim_manager: WIM管理器实例
            *args, **kwargs: 传递给WIM管理器方法的参数
        """
        super().__init__()
        self.operation_type = operation_type
        self.wim_manager = wim_manager
        self.args = args
        self.kwargs = kwargs
        self.is_cancelled = False

    def run(self):
        """执行WIM操作"""
        try:
            if self.operation_type == 'mount':
                self._run_mount_operation()
            elif self.operation_type == 'unmount':
                self._run_unmount_operation()
            else:
                raise ValueError(f"不支持的操作类型: {self.operation_type}")

        except Exception as e:
            error_msg = f"操作失败: {str(e)}"
            self.log.emit(f"{error_msg} [WIM线程]")
            self.finished.emit(False, error_msg)

    def _run_mount_operation(self):
        """执行挂载操作"""
        self.log.emit("开始WIM挂载操作 [WIM线程]")
        self.progress.emit(5, "初始化挂载环境")

        if self.is_cancelled:
            return

        # 创建进度回调函数
        def progress_callback(percent, message):
            if not self.is_cancelled:
                self.progress.emit(min(percent, 95), message)  # 最多到95%，留给完成处理
                self.log.emit(f"{message} [WIM线程]")

        # 添加进度回调到kwargs
        self.kwargs['progress_callback'] = progress_callback

        self.progress.emit(10, "执行挂载操作")

        # 调用WIM管理器的挂载方法
        success, message = self.wim_manager.mount_wim(*self.args, **self.kwargs)

        if self.is_cancelled:
            self.log.emit("操作已被取消 [WIM线程]")
            return

        if success:
            self.progress.emit(100, "挂载操作完成")
            self.log.emit(f"WIM挂载成功: {message} [WIM线程]")
            self.finished.emit(True, message)
        else:
            self.log.emit(f"WIM挂载失败: {message} [WIM线程]")
            self.finished.emit(False, message)

    def _run_unmount_operation(self):
        """执行卸载操作"""
        self.log.emit("开始WIM卸载操作 [WIM线程]")
        self.progress.emit(5, "初始化卸载环境")

        if self.is_cancelled:
            return

        # 创建进度回调函数
        def progress_callback(percent, message):
            if not self.is_cancelled:
                self.progress.emit(min(percent, 95), message)
                self.log.emit(f"{message} [WIM线程]")

        # 添加进度回调到kwargs
        self.kwargs['progress_callback'] = progress_callback

        self.progress.emit(10, "执行卸载操作")

        # 调用WIM管理器的卸载方法
        success, message = self.wim_manager.unmount_wim(*self.args, **self.kwargs)

        if self.is_cancelled:
            self.log.emit("操作已被取消 [WIM线程]")
            return

        if success:
            self.progress.emit(100, "卸载操作完成")
            self.log.emit(f"WIM卸载成功: {message} [WIM线程]")
            self.finished.emit(True, message)
        else:
            self.log.emit(f"WIM卸载失败: {message} [WIM线程]")
            self.finished.emit(False, message)

    def cancel(self):
        """取消操作"""
        self.is_cancelled = True


def show_wim_mount_progress(parent, wim_manager, build_dir, wim_file_path=None):
    """
    显示WIM挂载进度对话框

    Args:
        parent: 父窗口
        wim_manager: WIM管理器实例
        build_dir: 构建目录
        wim_file_path: WIM文件路径（可选）

    Returns:
        QDialog: 进度对话框实例
    """
    dialog = ProgressDialog(parent, "WIM挂载进度", show_log=True, can_cancel=True)
    dialog.set_title("正在挂载WIM文件")
    dialog.set_current_operation("准备挂载WIM文件...")

    # 创建操作线程
    thread = WIMOperationThread('mount', wim_manager, build_dir, wim_file_path)

    # 连接信号
    thread.progress.connect(dialog.set_progress)
    thread.log.connect(dialog.add_log)
    thread.finished.connect(dialog.set_completed)
    dialog.cancelled.connect(thread.cancel)

    # 线程完成后删除
    thread.finished.connect(thread.deleteLater)

    # 启动线程
    thread.start()

    return dialog


def show_wim_unmount_progress(parent, wim_manager, build_dir, commit_changes=True):
    """
    显示WIM卸载进度对话框

    Args:
        parent: 父窗口
        wim_manager: WIM管理器实例
        build_dir: 构建目录
        commit_changes: 是否提交更改

    Returns:
        QDialog: 进度对话框实例
    """
    dialog = ProgressDialog(parent, "WIM卸载进度", show_log=True, can_cancel=True)
    dialog.set_title("正在卸载WIM文件")
    dialog.set_current_operation("准备卸载WIM文件...")

    # 创建操作线程
    thread = WIMOperationThread('unmount', wim_manager, build_dir, commit_changes)

    # 连接信号
    thread.progress.connect(dialog.set_progress)
    thread.log.connect(dialog.add_log)
    thread.finished.connect(dialog.set_completed)
    dialog.cancelled.connect(thread.cancel)

    # 线程完成后删除
    thread.finished.connect(thread.deleteLater)

    # 启动线程
    thread.start()

    return dialog


if __name__ == "__main__":
    # 测试代码
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 模拟WIM管理器
    class MockWIMManager:
        def mount_wim(self, build_dir, wim_file_path=None, progress_callback=None):
            import time
            for i in range(0, 101, 10):
                if progress_callback:
                    progress_callback(i, f"挂载进度 {i}%")
                time.sleep(0.1)
            return True, "挂载成功"

        def unmount_wim(self, build_dir, commit_changes=True, progress_callback=None):
            import time
            for i in range(0, 101, 10):
                if progress_callback:
                    progress_callback(i, f"卸载进度 {i}%")
                time.sleep(0.1)
            return True, "卸载成功"

    # 测试挂载进度对话框
    wim_manager = MockWIMManager()
    dialog = show_wim_mount_progress(None, wim_manager, Path("test_build"), Path("test.wim"))
    dialog.show()

    sys.exit(app.exec_())