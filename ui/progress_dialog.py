#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进度对话框模块
提供进度显示和取消功能的对话框
"""

from typing import Optional, Callable

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QTextEdit, QGroupBox, QApplication
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont
from ui.button_styler import apply_3d_button_style


class ProgressDialog(QDialog):
    """进度对话框"""

    # 自定义信号
    cancelled = pyqtSignal()

    def __init__(self, title: str = "进度", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(500, 350)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)

        self.is_cancelled = False
        self.auto_close = True

        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 状态标签
        self.status_label = QLabel("准备中...")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # 详细信息组
        details_group = QGroupBox("详细信息")
        details_layout = QVBoxLayout(details_group)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(150)
        self.details_text.setFont(QFont("Consolas", 9))
        details_layout.addWidget(self.details_text)

        layout.addWidget(details_group)

        # 按钮组
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel)
        apply_3d_button_style(self.cancel_btn)  # 应用立体样式
        button_layout.addWidget(self.cancel_btn)

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        apply_3d_button_style(self.close_btn)  # 应用立体样式
        self.close_btn.setVisible(False)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def update_progress(self, value: int, status: str = "", details: str = ""):
        """更新进度

        Args:
            value: 进度值 (0-100)
            status: 状态文本
            details: 详细信息文本
        """
        # 更新进度条
        self.progress_bar.setValue(value)

        # 更新状态标签
        if status:
            self.status_label.setText(status)

        # 更新详细信息
        if details:
            self.details_text.append(details)
            self.details_text.ensureCursorVisible()

        # 如果进度完成且启用自动关闭
        if value >= 100 and self.auto_close:
            self.on_finished()

    def set_status(self, status: str):
        """设置状态文本"""
        self.status_label.setText(status)

    def add_details(self, details: str):
        """添加详细信息"""
        self.details_text.append(details)
        self.details_text.ensureCursorVisible()

    def clear_details(self):
        """清空详细信息"""
        self.details_text.clear()

    def cancel(self):
        """取消操作"""
        self.is_cancelled = True
        self.cancelled.emit()
        self.cancel_btn.setEnabled(False)
        self.set_status("正在取消...")

    def on_finished(self):
        """操作完成"""
        self.cancel_btn.setVisible(False)
        self.close_btn.setVisible(True)
        self.progress_bar.setValue(100)

    def reset(self):
        """重置对话框状态"""
        self.is_cancelled = False
        self.progress_bar.setValue(0)
        self.status_label.setText("准备中...")
        self.details_text.clear()
        self.cancel_btn.setVisible(True)
        self.cancel_btn.setEnabled(True)
        self.close_btn.setVisible(False)

    def set_auto_close(self, enabled: bool):
        """设置是否自动关闭"""
        self.auto_close = enabled

    def get_cancelled(self) -> bool:
        """获取是否已取消"""
        return self.is_cancelled


class TaskProgressDialog(ProgressDialog):
    """任务进度对话框"""

    def __init__(self, task_function: Callable, title: str = "任务进度", parent=None):
        super().__init__(title, parent)
        self.task_function = task_function
        self.task_thread = None

    def start_task(self, *args, **kwargs):
        """开始执行任务"""
        self.reset()
        self.cancel_btn.setEnabled(True)

        # 创建工作线程
        self.task_thread = TaskThread(self.task_function, *args, **kwargs)
        self.task_thread.progress_signal.connect(self.update_progress)
        self.task_thread.finished_signal.connect(self.on_task_finished)
        self.task_thread.error_signal.connect(self.on_task_error)

        # 连接取消信号
        self.cancelled.connect(self.task_thread.stop)

        # 启动任务
        self.task_thread.start()

    def on_task_finished(self, result=None):
        """任务完成"""
        self.update_progress(100, "任务完成", f"任务执行完成。返回结果: {result}")
        self.on_finished()

    def on_task_error(self, error_message: str):
        """任务出错"""
        self.update_progress(0, "任务失败", f"任务执行失败: {error_message}")
        self.on_finished()

    def cancel(self):
        """取消任务"""
        super().cancel()
        if self.task_thread and self.task_thread.isRunning():
            self.task_thread.stop()

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止任务线程
        if self.task_thread and self.task_thread.isRunning():
            self.task_thread.stop()
            self.task_thread.wait(3000)  # 等待3秒

        super().closeEvent(event)


class TaskThread(QThread):
    """任务执行线程"""

    # 信号定义
    progress_signal = pyqtSignal(int, str, str)  # 进度、状态、详细信息
    finished_signal = pyqtSignal(object)  # 完成信号，带结果
    error_signal = pyqtSignal(str)  # 错误信号

    def __init__(self, task_function: Callable, *args, **kwargs):
        super().__init__()
        self.task_function = task_function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.is_cancelled = False

    def run(self):
        """执行任务"""
        self.is_running = True
        try:
            # 执行任务函数，传递进度回调
            result = self.task_function(
                self.progress_callback,
                *self.args,
                **self.kwargs
            )

            if not self.is_cancelled:
                self.finished_signal.emit(result)

        except Exception as e:
            if not self.is_cancelled:
                self.error_signal.emit(str(e))

        finally:
            self.is_running = False

    def stop(self):
        """停止任务"""
        self.is_cancelled = True
        self.is_running = False

    def progress_callback(self, value: int, status: str = "", details: str = ""):
        """进度回调函数"""
        if not self.is_cancelled:
            self.progress_signal.emit(value, status, details)


# 使用示例
def example_task_with_progress(progress_callback, *args, **kwargs):
    """示例任务函数，展示如何使用进度回调"""
    import time

    # 模拟任务执行
    steps = [
        (10, "Initializing...", "开始执行任务初始化"),
        (30, "Processing data...", "正在处理输入数据"),
        (60, "Executing core operations...", "执行主要业务逻辑"),
        (90, "Cleaning up resources...", "清理临时资源和缓存"),
        (100, "Complete", "任务执行完成")
    ]

    for value, status, details in steps:
        if progress_callback:
            progress_callback(value, status, details)

        # 模拟工作
        time.sleep(1)

    return "任务执行成功"


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 创建任务进度对话框
    dialog = TaskProgressDialog(example_task_with_progress, "示例任务")

    # 开始任务
    dialog.start_task()

    # 显示对话框
    dialog.show()

    sys.exit(app.exec_())