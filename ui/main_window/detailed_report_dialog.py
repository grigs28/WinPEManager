#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细报告对话框
支持双击放大、可拖拽调整大小的报告显示窗口
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QFrame, QSplitter, QMessageBox, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QIcon


class DetailedReportDialog(QDialog):
    """详细报告对话框，支持调整大小和双击放大"""

    def __init__(self, parent=None, title="详细报告", report_text=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(800, 600)

        # 初始状态标志
        self.is_maximized = False
        self.normal_geometry = None

        # 报告文本
        self.report_text = report_text

        # 初始化UI
        self.init_ui()
        self.setup_connections()

        # 设置窗口标志
        self.setWindowFlags(
            Qt.Dialog |
            Qt.WindowCloseButtonHint |
            Qt.WindowMinMaxButtonsHint
        )

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 标题栏
        title_frame = QFrame()
        title_frame.setFrameStyle(QFrame.StyledPanel)
        title_layout = QHBoxLayout(title_frame)

        title_label = QLabel("📋 详细报告")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2C3E50;
                padding: 5px;
            }
        """)
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # 状态标签
        self.status_label = QLabel("双击标题栏或内容区域可最大化/还原")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #7F8C8D;
                font-style: italic;
            }
        """)
        title_layout.addWidget(self.status_label)

        layout.addWidget(title_frame)

        # 创建分割器
        splitter = QSplitter(Qt.Vertical)

        # 报告内容区域
        self.report_text_edit = QTextEdit()
        self.report_text_edit.setPlainText(self.report_text)
        self.report_text_edit.setReadOnly(True)
        self.report_text_edit.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                background-color: #F8F9FA;
                border: 1px solid #BDC3C7;
                border-radius: 5px;
                padding: 10px;
                line-height: 1.4;
            }
        """)

        # 设置等宽字体
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.TypeWriter)
        self.report_text_edit.setFont(font)

        splitter.addWidget(self.report_text_edit)

        # 控制面板
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.StyledPanel)
        control_layout = QHBoxLayout(control_frame)

        # 功能按钮
        self.wrap_checkbox = QCheckBox("自动换行")
        self.wrap_checkbox.setChecked(True)
        self.wrap_checkbox.stateChanged.connect(self.toggle_word_wrap)
        control_layout.addWidget(self.wrap_checkbox)

        self.copy_btn = QPushButton("📋 复制报告")
        self.copy_btn.clicked.connect(self.copy_report)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        """)
        control_layout.addWidget(self.copy_btn)

        self.save_btn = QPushButton("💾 保存报告")
        self.save_btn.clicked.connect(self.save_report)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        control_layout.addWidget(self.save_btn)

        control_layout.addStretch()

        # 关闭按钮
        self.close_btn = QPushButton("❌ 关闭")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)
        control_layout.addWidget(self.close_btn)

        splitter.addWidget(control_frame)

        # 设置分割器比例
        splitter.setSizes([500, 80])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        layout.addWidget(splitter)

    def setup_connections(self):
        """设置信号连接"""
        # 双击标题栏最大化/还原
        title_frame = self.findChild(QFrame)
        if title_frame:
            title_frame.mouseDoubleClickEvent = self.toggle_maximize

        # 双击文本区域最大化/还原
        self.report_text_edit.mouseDoubleClickEvent = self.toggle_maximize

    def toggle_maximize(self, event=None):
        """切换最大化/还原状态"""
        if self.is_maximized:
            # 还原窗口
            if self.normal_geometry:
                self.setGeometry(self.normal_geometry)
            self.showNormal()
            self.is_maximized = False
            self.status_label.setText("双击标题栏或内容区域可最大化/还原")
        else:
            # 最大化窗口
            self.normal_geometry = self.geometry()
            self.showMaximized()
            self.is_maximized = True
            self.status_label.setText("双击标题栏或内容区域可还原窗口大小")

    def toggle_word_wrap(self, state):
        """切换自动换行"""
        if state == 2:  # Qt.Checked
            self.report_text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        else:  # Qt.Unchecked
            self.report_text_edit.setLineWrapMode(QTextEdit.NoWrap)

    def copy_report(self):
        """复制报告到剪贴板"""
        try:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self.report_text_edit.toPlainText())

            # 显示复制成功提示
            self.status_label.setText("✅ 报告已复制到剪贴板")
            QTimer.singleShot(2000, lambda: self.status_label.setText(
                "双击标题栏或内容区域可最大化/还原" if not self.is_maximized
                else "双击标题栏或内容区域可还原窗口大小"
            ))
        except Exception as e:
            self.status_label.setText(f"❌ 复制失败: {str(e)}")

    def save_report(self):
        """保存报告到文件"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            from datetime import datetime

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存详细报告",
                f"version_replacement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "文本文件 (*.txt);;JSON文件 (*.json);;所有文件 (*)"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.report_text_edit.toPlainText())

                # 显示保存成功提示
                self.status_label.setText(f"✅ 报告已保存到: {file_path}")
                QTimer.singleShot(3000, lambda: self.status_label.setText(
                    "双击标题栏或内容区域可最大化/还原" if not self.is_maximized
                    else "双击标题栏或内容区域可还原窗口大小"
                ))
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存报告时发生错误:\n{str(e)}")

    def keyPressEvent(self, event):
        """处理键盘事件"""
        # Ctrl+W 关闭窗口
        if event.key() == Qt.Key_W and event.modifiers() == Qt.ControlModifier:
            self.accept()
        # Escape 关闭窗口
        elif event.key() == Qt.Key_Escape:
            self.accept()
        # F11 切换最大化
        elif event.key() == Qt.Key_F11:
            self.toggle_maximize()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        # 更新状态标签
        if self.is_maximized:
            self.status_label.setText("双击标题栏或内容区域可还原窗口大小")
        else:
            self.status_label.setText("双击标题栏或内容区域可最大化/还原")

    def show_report(self, title=None, report_text=None):
        """显示报告"""
        if title:
            self.setWindowTitle(title)
        if report_text:
            self.report_text = report_text
            self.report_text_edit.setPlainText(report_text)

        # 移动到父窗口中心
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)

        self.exec_()


class EnhancedDetailedReportDialog(DetailedReportDialog):
    """增强版详细报告对话框，支持更多功能"""

    def __init__(self, parent=None, result_data=None):
        title = "增强版版本替换详细报告"
        report_text = self._format_enhanced_report(result_data) if result_data else ""

        super().__init__(parent, title, report_text)

        self.result_data = result_data
        self.init_enhanced_features()

    def init_enhanced_features(self):
        """初始化增强功能"""
        # 添加JSON格式化按钮
        control_frame = self.findChild(QFrame)
        if control_frame:
            control_layout = control_frame.layout()

            # 在复制按钮前插入JSON格式化按钮
            self.format_json_btn = QPushButton("🎨 格式化JSON")
            self.format_json_btn.clicked.connect(self.format_json_report)
            self.format_json_btn.setStyleSheet("""
                QPushButton {
                    background-color: #9B59B6;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #8E44AD;
                }
            """)

            control_layout.insertWidget(2, self.format_json_btn)

    def _format_enhanced_report(self, result_data):
        """格式化增强版报告"""
        if not result_data:
            return "无报告数据"

        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("增强版WinPE版本替换详细报告")
        report_lines.append("=" * 60)
        report_lines.append("")

        # 基本信息
        report_lines.append("📊 基本信息")
        report_lines.append("-" * 30)
        report_lines.append(f"操作时间: {result_data.get('timestamp', 'N/A')}")
        report_lines.append(f"操作状态: {'✅ 成功' if result_data.get('success', False) else '❌ 失败'}")
        report_lines.append("")

        # 路径信息
        report_lines.append("📁 路径信息")
        report_lines.append("-" * 30)
        source_wim = result_data.get('source_wim', 'N/A')
        target_wim = result_data.get('target_wim', 'N/A')
        output_wim = result_data.get('output_wim', 'N/A')

        report_lines.append(f"源WIM: {source_wim}")
        report_lines.append(f"目标WIM: {target_wim}")
        report_lines.append(f"输出WIM: {output_wim}")
        report_lines.append("")

        # 操作统计
        report_lines.append("📈 操作统计")
        report_lines.append("-" * 30)
        external_programs = result_data.get('external_programs_copied', 0)
        report_lines.append(f"外部程序复制数量: {external_programs}")
        report_lines.append("")

        # WIM分析结果
        wim_differences = result_data.get('wim_differences', {})
        if wim_differences:
            report_lines.append("🔍 WIM差异分析")
            report_lines.append("-" * 30)
            missing_items = wim_differences.get('missing_in_target', [])
            if missing_items:
                report_lines.append("发现的差异:")
                for item in missing_items:
                    report_lines.append(f"  - {item}")
            else:
                report_lines.append("未发现显著差异")
            report_lines.append("")

        # 挂载目录分析结果
        mount_differences = result_data.get('mount_differences', {})
        if mount_differences:
            report_lines.append("📂 挂载目录分析")
            report_lines.append("-" * 30)

            external_programs = mount_differences.get('external_programs', [])
            startup_configs = mount_differences.get('startup_configs', [])

            report_lines.append(f"外部程序: {len(external_programs)} 个")
            report_lines.append(f"启动配置: {len(startup_configs)} 个")
            report_lines.append("")

        report_lines.append("=" * 60)
        report_lines.append("报告生成完成")
        report_lines.append("=" * 60)

        return "\n".join(report_lines)

    def format_json_report(self):
        """格式化JSON报告"""
        if self.result_data:
            try:
                import json
                formatted_json = json.dumps(self.result_data, ensure_ascii=False, indent=2)

                # 创建JSON格式化对话框
                json_dialog = DetailedReportDialog(self, "JSON格式报告", formatted_json)
                json_dialog.exec_()
            except Exception as e:
                QMessageBox.critical(self, "格式化失败", f"JSON格式化失败:\n{str(e)}")


def show_detailed_report(parent, title="详细报告", result_data=None, report_text=None):
    """显示详细报告的便捷函数"""
    if result_data and not report_text:
        # 使用增强版报告对话框
        dialog = EnhancedDetailedReportDialog(parent, result_data)
    else:
        # 使用基础报告对话框
        dialog = DetailedReportDialog(parent, title, report_text or "")

    dialog.show_report()