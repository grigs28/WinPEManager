#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
桌面环境配置对话框模块
提供桌面环境的详细配置界面
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QCheckBox, QGroupBox, 
    QFormLayout, QMessageBox, QTextEdit, QTabWidget,
    QWidget, QSpinBox, QSlider, QGridLayout
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QDesktopServices
from ui.button_styler import apply_3d_button_style, apply_3d_button_style_alternate, apply_3d_button_style_red
from utils.logger import log_error


class DesktopConfigDialog(QDialog):
    """桌面环境配置对话框"""
    
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.parent_window = parent
        
        self.setWindowTitle("桌面环境配置")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 基本配置标签页
        self.create_basic_config_tab()
        
        # 高级配置标签页
        self.create_advanced_config_tab()
        
        # 下载和帮助标签页
        self.create_download_help_tab()
        
        # 按钮行
        button_layout = QHBoxLayout()
        
        # 测试配置按钮
        test_btn = QPushButton("测试配置")
        test_btn.clicked.connect(self.test_config)
        apply_3d_button_style(test_btn)
        button_layout.addWidget(test_btn)
        
        # 重置按钮
        reset_btn = QPushButton("重置默认")
        reset_btn.clicked.connect(self.reset_config)
        apply_3d_button_style_red(reset_btn)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        # 保存按钮
        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self.save_config)
        apply_3d_button_style_alternate(save_btn)
        button_layout.addWidget(save_btn)
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        apply_3d_button_style_red(cancel_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def create_basic_config_tab(self):
        """创建基本配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 桌面类型选择
        type_group = QGroupBox("桌面环境类型")
        type_layout = QFormLayout(type_group)
        
        self.desktop_type_combo = QComboBox()
        from core.desktop_manager import DesktopManager
        desktop_manager = DesktopManager(self.config_manager)
        desktop_types = desktop_manager.get_desktop_types()
        
        for desktop_id, desktop_info in desktop_types.items():
            display_text = f"{desktop_info['name']} - {desktop_info['description']}"
            self.desktop_type_combo.addItem(display_text, desktop_id)
        
        type_layout.addRow("桌面类型:", self.desktop_type_combo)
        layout.addWidget(type_group)
        
        # 路径配置
        path_group = QGroupBox("路径配置")
        path_layout = QFormLayout(path_group)
        
        # 程序路径
        self.program_path_edit = QLineEdit()
        self.program_path_edit.setPlaceholderText("桌面环境主程序路径")
        program_browse_btn = QPushButton("浏览...")
        program_browse_btn.clicked.connect(self.browse_program_path)
        program_browse_btn.setMaximumWidth(80)
        apply_3d_button_style(program_browse_btn)
        
        program_layout = QHBoxLayout()
        program_layout.addWidget(self.program_path_edit)
        program_layout.addWidget(program_browse_btn)
        path_layout.addRow("程序路径:", program_layout)
        
        # 目录路径
        self.directory_path_edit = QLineEdit()
        self.directory_path_edit.setPlaceholderText("桌面环境安装目录")
        directory_browse_btn = QPushButton("浏览...")
        directory_browse_btn.clicked.connect(self.browse_directory_path)
        directory_browse_btn.setMaximumWidth(80)
        apply_3d_button_style(directory_browse_btn)
        
        directory_layout = QHBoxLayout()
        directory_layout.addWidget(self.directory_path_edit)
        directory_layout.addWidget(directory_browse_btn)
        path_layout.addRow("目录路径:", directory_layout)
        
        layout.addWidget(path_group)
        
        # 启动选项
        startup_group = QGroupBox("启动选项")
        startup_layout = QFormLayout(startup_group)
        
        self.auto_start_check = QCheckBox("开机自动启动")
        startup_layout.addRow("自动启动:", self.auto_start_check)
        
        self.safe_mode_check = QCheckBox("安全模式启动")
        startup_layout.addRow("安全模式:", self.safe_mode_check)
        
        self.debug_mode_check = QCheckBox("调试模式")
        startup_layout.addRow("调试模式:", self.debug_mode_check)
        
        layout.addWidget(startup_group)
        
        self.tab_widget.addTab(widget, "基本配置")
    
    def create_advanced_config_tab(self):
        """创建高级配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 性能配置
        performance_group = QGroupBox("性能配置")
        performance_layout = QGridLayout(performance_group)
        
        # 内存限制
        performance_layout.addWidget(QLabel("内存限制 (MB):"), 0, 0)
        self.memory_limit_spin = QSpinBox()
        self.memory_limit_spin.setRange(32, 512)
        self.memory_limit_spin.setValue(64)
        self.memory_limit_spin.setSuffix(" MB")
        performance_layout.addWidget(self.memory_limit_spin, 0, 1)
        
        # 缓存大小
        performance_layout.addWidget(QLabel("缓存大小 (MB):"), 1, 0)
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(8, 128)
        self.cache_size_spin.setValue(32)
        self.cache_size_spin.setSuffix(" MB")
        performance_layout.addWidget(self.cache_size_spin, 1, 1)
        
        # 插件加载延迟
        performance_layout.addWidget(QLabel("插件延迟 (ms):"), 2, 0)
        self.plugin_delay_spin = QSpinBox()
        self.plugin_delay_spin.setRange(0, 5000)
        self.plugin_delay_spin.setValue(1000)
        self.plugin_delay_spin.setSuffix(" ms")
        performance_layout.addWidget(self.plugin_delay_spin, 2, 1)
        
        layout.addWidget(performance_group)
        
        # 外观配置
        appearance_group = QGroupBox("外观配置")
        appearance_layout = QFormLayout(appearance_group)
        
        # 主题选择
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["默认", "深色", "浅色", "自定义"])
        appearance_layout.addRow("主题:", self.theme_combo)
        
        # 图标大小
        self.icon_size_combo = QComboBox()
        self.icon_size_combo.addItems(["小 (16x16)", "中 (32x32)", "大 (48x48)", "超大 (64x64)"])
        appearance_layout.addRow("图标大小:", self.icon_size_combo)
        
        # 动画效果
        self.animation_check = QCheckBox("启用动画效果")
        appearance_layout.addRow("动画效果:", self.animation_check)
        
        # 透明效果
        self.transparency_check = QCheckBox("启用透明效果")
        appearance_layout.addRow("透明效果:", self.transparency_check)
        
        layout.addWidget(appearance_group)
        
        # 自定义参数
        custom_group = QGroupBox("自定义参数")
        custom_layout = QVBoxLayout(custom_group)
        
        self.custom_params_edit = QTextEdit()
        self.custom_params_edit.setMaximumHeight(100)
        self.custom_params_edit.setPlaceholderText("输入自定义启动参数，每行一个...")
        custom_layout.addWidget(self.custom_params_edit)
        
        layout.addWidget(custom_group)
        
        self.tab_widget.addTab(widget, "高级配置")
    
    def create_download_help_tab(self):
        """创建下载和帮助标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 下载信息
        download_group = QGroupBox("下载信息")
        download_layout = QVBoxLayout(download_group)
        
        self.download_info_edit = QTextEdit()
        self.download_info_edit.setReadOnly(True)
        self.download_info_edit.setFont(QFont("Consolas", 9))
        download_layout.addWidget(self.download_info_edit)
        
        layout.addWidget(download_group)
        
        # 快速链接
        links_group = QGroupBox("快速链接")
        links_layout = QGridLayout(links_group)
        
        # Cairo Desktop链接
        cairo_link_btn = QPushButton("Cairo Desktop 下载")
        cairo_link_btn.clicked.connect(lambda: self.open_url("https://github.com/cairoshell/cairoshell/releases/download/v0.4.407/CairoSetup_64bit.exe"))
        apply_3d_button_style(cairo_link_btn)
        links_layout.addWidget(cairo_link_btn, 0, 0)
        
        # WinXShell链接
        winxshell_link_btn = QPushButton("WinXShell 下载")
        winxshell_link_btn.clicked.connect(lambda: self.open_url("https://www.lanzoux.com/b011xhbsh"))
        apply_3d_button_style(winxshell_link_btn)
        links_layout.addWidget(winxshell_link_btn, 0, 1)
        
        # 文档链接
        docs_link_btn = QPushButton("配置文档")
        docs_link_btn.clicked.connect(self.show_documentation)
        apply_3d_button_style(docs_link_btn)
        links_layout.addWidget(docs_link_btn, 1, 0)
        
        # 社区链接
        community_link_btn = QPushButton("社区支持")
        community_link_btn.clicked.connect(lambda: self.open_url("https://github.com/grigs28/WinPEManager"))
        apply_3d_button_style(community_link_btn)
        links_layout.addWidget(community_link_btn, 1, 1)
        
        layout.addWidget(links_group)
        
        # 状态信息
        status_group = QGroupBox("状态信息")
        status_layout = QVBoxLayout(status_group)
        
        self.status_info_edit = QTextEdit()
        self.status_info_edit.setReadOnly(True)
        self.status_info_edit.setMaximumHeight(100)
        status_layout.addWidget(self.status_info_edit)
        
        layout.addWidget(status_group)
        
        self.tab_widget.addTab(widget, "下载和帮助")
    
    def load_config(self):
        """加载配置"""
        try:
            # 桌面类型
            current_desktop_type = self.config_manager.get("winpe.desktop_type", "disabled")
            for i in range(self.desktop_type_combo.count()):
                if self.desktop_type_combo.itemData(i) == current_desktop_type:
                    self.desktop_type_combo.setCurrentIndex(i)
                    break
            
            # 路径配置
            self.program_path_edit.setText(self.config_manager.get("winpe.desktop_program_path", ""))
            self.directory_path_edit.setText(self.config_manager.get("winpe.desktop_directory_path", ""))
            
            # 启动选项
            self.auto_start_check.setChecked(self.config_manager.get("winpe.desktop_auto_start", False))
            self.safe_mode_check.setChecked(self.config_manager.get("winpe.desktop_safe_mode", False))
            self.debug_mode_check.setChecked(self.config_manager.get("winpe.desktop_debug_mode", False))
            
            # 性能配置
            self.memory_limit_spin.setValue(self.config_manager.get("winpe.desktop_memory_limit", 64))
            self.cache_size_spin.setValue(self.config_manager.get("winpe.desktop_cache_size", 32))
            self.plugin_delay_spin.setValue(self.config_manager.get("winpe.desktop_plugin_delay", 1000))
            
            # 外观配置
            theme_index = self.theme_combo.findText(self.config_manager.get("winpe.desktop_theme", "默认"))
            if theme_index >= 0:
                self.theme_combo.setCurrentIndex(theme_index)
            
            icon_size_text = self.config_manager.get("winpe.desktop_icon_size", "中 (32x32)")
            icon_size_index = self.icon_size_combo.findText(icon_size_text)
            if icon_size_index >= 0:
                self.icon_size_combo.setCurrentIndex(icon_size_index)
            
            self.animation_check.setChecked(self.config_manager.get("winpe.desktop_animation", True))
            self.transparency_check.setChecked(self.config_manager.get("winpe.desktop_transparency", True))
            
            # 自定义参数
            custom_params = self.config_manager.get("winpe.desktop_custom_params", "")
            if isinstance(custom_params, list):
                custom_params = "\n".join(custom_params)
            self.custom_params_edit.setPlainText(custom_params)
            
            # 更新下载信息和状态
            self.update_download_info()
            self.update_status_info()
            
        except Exception as e:
            log_error(e, "加载桌面配置")
    
    def save_config(self):
        """保存配置"""
        try:
            # 桌面类型
            desktop_type = self.desktop_type_combo.currentData()
            self.config_manager.set("winpe.desktop_type", desktop_type)
            
            # 路径配置
            self.config_manager.set("winpe.desktop_program_path", self.program_path_edit.text())
            self.config_manager.set("winpe.desktop_directory_path", self.directory_path_edit.text())
            
            # 启动选项
            self.config_manager.set("winpe.desktop_auto_start", self.auto_start_check.isChecked())
            self.config_manager.set("winpe.desktop_safe_mode", self.safe_mode_check.isChecked())
            self.config_manager.set("winpe.desktop_debug_mode", self.debug_mode_check.isChecked())
            
            # 性能配置
            self.config_manager.set("winpe.desktop_memory_limit", self.memory_limit_spin.value())
            self.config_manager.set("winpe.desktop_cache_size", self.cache_size_spin.value())
            self.config_manager.set("winpe.desktop_plugin_delay", self.plugin_delay_spin.value())
            
            # 外观配置
            self.config_manager.set("winpe.desktop_theme", self.theme_combo.currentText())
            self.config_manager.set("winpe.desktop_icon_size", self.icon_size_combo.currentText())
            self.config_manager.set("winpe.desktop_animation", self.animation_check.isChecked())
            self.config_manager.set("winpe.desktop_transparency", self.transparency_check.isChecked())
            
            # 自定义参数
            custom_params_text = self.custom_params_edit.toPlainText().strip()
            if custom_params_text:
                custom_params = [line.strip() for line in custom_params_text.split('\n') if line.strip()]
            else:
                custom_params = []
            self.config_manager.set("winpe.desktop_custom_params", custom_params)
            
            # 保存配置
            self.config_manager.save_config()
            
            QMessageBox.information(self, "成功", "桌面环境配置已保存！")
            self.accept()
            
        except Exception as e:
            log_error(e, "保存桌面配置")
            QMessageBox.warning(self, "错误", f"保存配置失败: {str(e)}")
    
    def reset_config(self):
        """重置为默认配置"""
        try:
            reply = QMessageBox.question(
                self, "确认重置",
                "确定要重置所有配置为默认值吗？\n\n此操作无法撤销。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 重置为默认值
                self.desktop_type_combo.setCurrentIndex(0)  # 第一个选项通常是"disabled"
                self.program_path_edit.clear()
                self.directory_path_edit.clear()
                self.auto_start_check.setChecked(False)
                self.safe_mode_check.setChecked(False)
                self.debug_mode_check.setChecked(False)
                self.memory_limit_spin.setValue(64)
                self.cache_size_spin.setValue(32)
                self.plugin_delay_spin.setValue(1000)
                self.theme_combo.setCurrentIndex(0)
                self.icon_size_combo.setCurrentIndex(1)  # 中等大小
                self.animation_check.setChecked(True)
                self.transparency_check.setChecked(True)
                self.custom_params_edit.clear()
                
                QMessageBox.information(self, "成功", "配置已重置为默认值！")
                
        except Exception as e:
            log_error(e, "重置桌面配置")
            QMessageBox.warning(self, "错误", f"重置配置失败: {str(e)}")
    
    def test_config(self):
        """测试配置"""
        try:
            desktop_type = self.desktop_type_combo.currentData()
            program_path = self.program_path_edit.text()
            directory_path = self.directory_path_edit.text()
            
            # 验证配置
            errors = []
            
            if desktop_type != "disabled":
                if not program_path:
                    errors.append("程序路径不能为空")
                elif not Path(program_path).exists():
                    errors.append(f"程序文件不存在: {program_path}")
                
                if not directory_path:
                    errors.append("目录路径不能为空")
                elif not Path(directory_path).exists():
                    errors.append(f"目录不存在: {directory_path}")
            
            if errors:
                error_msg = "配置验证失败:\n\n" + "\n".join(f"• {error}" for error in errors)
                QMessageBox.warning(self, "配置错误", error_msg)
            else:
                success_msg = "配置验证通过！\n\n"
                if desktop_type != "disabled":
                    success_msg += f"桌面类型: {desktop_type}\n"
                    success_msg += f"程序路径: {program_path}\n"
                    success_msg += f"目录路径: {directory_path}\n"
                else:
                    success_msg += "桌面环境已禁用\n"
                
                success_msg += f"内存限制: {self.memory_limit_spin.value()} MB\n"
                success_msg += f"缓存大小: {self.cache_size_spin.value()} MB"
                
                QMessageBox.information(self, "验证成功", success_msg)
                
        except Exception as e:
            log_error(e, "测试桌面配置")
            QMessageBox.warning(self, "错误", f"测试配置失败: {str(e)}")
    
    def browse_program_path(self):
        """浏览程序路径"""
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择桌面环境主程序",
            self.program_path_edit.text(),
            "可执行文件 (*.exe);;所有文件 (*.*)"
        )
        if file_path:
            self.program_path_edit.setText(file_path)
    
    def browse_directory_path(self):
        """浏览目录路径"""
        from PyQt5.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(
            self, "选择桌面环境目录",
            self.directory_path_edit.text()
        )
        if directory:
            self.directory_path_edit.setText(directory)
    
    def open_url(self, url: str):
        """打开URL"""
        try:
            QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            log_error(e, "打开URL")
            QMessageBox.warning(self, "错误", f"无法打开链接: {str(e)}")
    
    def show_documentation(self):
        """显示文档"""
        try:
            from core.desktop_manager import DesktopManager
            desktop_manager = DesktopManager(self.config_manager)
            desktop_type = self.desktop_type_combo.currentData()
            
            if desktop_type == "cairo":
                doc_content = """Cairo Desktop 配置文档

基本配置:
1. 程序文件: CairoDesktop.exe
2. 配置文件: settings.xml
3. 主题目录: Themes/
4. 插件目录: Plugins/

启动参数:
- /noshell=true: 不替换系统外壳
- /startup=Desktop: 启动桌面模式
- /config=path: 指定配置文件路径

故障排除:
1. 检查 .NET Framework 版本
2. 验证配置文件语法
3. 查看日志文件
4. 禁用插件逐个测试"""
                
            elif desktop_type == "winxshell":
                doc_content = """WinXShell 配置文档

基本配置:
1. 程序文件: WinXShell_x64.exe
2. 配置文件: WinXShell.ini
3. 插件目录: Plugins/
4. 主题目录: Themes/

启动参数:
- -winpe: WinPE模式
- -desktop: 强制创建桌面
- -config=path: 指定配置文件
- -log=file: 启用日志记录

性能优化:
1. 禁用动画效果
2. 限制内存使用
3. 启用缓存机制
4. 优化插件加载

故障排除:
1. 检查 debug.log 文件
2. 使用 WinXShell_Troubleshoot.bat
3. 验证环境变量设置
4. 测试最小配置启动"""
                
            else:
                doc_content = """桌面环境配置文档

当前未选择桌面环境。

可选桌面环境:
1. Cairo Desktop
   - 现代化的Windows桌面环境
   - 支持主题和插件扩展
   - 需要 .NET Framework 4.7.2+

2. WinXShell
   - 轻量级WinPE桌面外壳
   - 专为WinPE环境优化
   - 支持Lua脚本扩展

选择桌面环境后，这里将显示详细的配置文档。"""
            
            # 显示文档对话框
            doc_dialog = QDialog(self)
            doc_dialog.setWindowTitle("配置文档")
            doc_dialog.setMinimumSize(600, 400)
            doc_dialog.setModal(True)
            
            doc_layout = QVBoxLayout(doc_dialog)
            
            doc_text = QTextEdit()
            doc_text.setReadOnly(True)
            doc_text.setPlainText(doc_content)
            doc_text.setFont(QFont("Consolas", 9))
            doc_layout.addWidget(doc_text)
            
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(doc_dialog.accept)
            apply_3d_button_style_red(close_btn)
            doc_layout.addWidget(close_btn)
            
            doc_dialog.exec_()
            
        except Exception as e:
            log_error(e, "显示文档")
            QMessageBox.warning(self, "错误", f"显示文档失败: {str(e)}")
    
    def update_download_info(self):
        """更新下载信息"""
        try:
            desktop_type = self.desktop_type_combo.currentData()
            
            if desktop_type == "cairo":
                info = """Cairo Desktop 下载信息

最新版本: v0.4.407
下载地址: https://github.com/cairoshell/cairoshell/releases/download/v0.4.407/CairoSetup_64bit.exe
文件大小: 约 50-100 MB
系统要求: Windows 10/11, .NET Framework 4.7.2+

安装步骤:
1. 下载 CairoSetup_64bit.exe
2. 右键选择"以管理员身份运行"
3. 选择安装目录（建议: Desktop/Cairo Shell）
4. 等待安装完成

注意事项:
- 安装过程中可能需要网络连接
- 建议关闭杀毒软件避免误报
- 安装完成后重启计算机"""
                
            elif desktop_type == "winxshell":
                info = """WinXShell 下载信息

最新版本: RC5.1.4_beta14
下载地址: https://www.lanzoux.com/b011xhbsh
提取密码: shell
文件大小: 约 10-20 MB
系统要求: Windows PE/10/11

安装步骤:
1. 访问蓝奏云下载页面
2. 输入提取密码: shell
3. 下载 WinXShell_RC5.1.4_beta14.7z
4. 解压到目标目录（建议: Desktop/WinXShell）
5. 确保包含 WinXShell_x64.exe 文件

注意事项:
- 解压时保持目录结构
- 建议使用7-Zip解压
- 解压后检查文件完整性"""
                
            else:
                info = """桌面环境下载信息

当前未选择桌面环境。

可选桌面环境:
1. Cairo Desktop
   - 现代化的Windows桌面环境
   - 支持主题和插件扩展
   - 下载地址: https://github.com/cairoshell/cairoshell

2. WinXShell
   - 轻量级WinPE桌面外壳
   - 专为WinPE环境优化
   - 下载地址: https://www.lanzoux.com/b011xhbsh (密码: shell)

选择桌面环境后，这里将显示详细的下载信息。"""
            
            self.download_info_edit.setPlainText(info)
            
        except Exception as e:
            log_error(e, "更新下载信息")
    
    def update_status_info(self):
        """更新状态信息"""
        try:
            from core.desktop_manager import DesktopManager
            desktop_manager = DesktopManager(self.config_manager)
            desktop_type = self.desktop_type_combo.currentData()
            
            if desktop_type == "disabled":
                status = "桌面环境状态: 已禁用\n\n未选择任何桌面环境。"
                
            else:
                desktop_info = desktop_manager.get_desktop_info(desktop_type)
                if desktop_info and desktop_info.get("installed", False):
                    status = f"""桌面环境状态: 已安装

桌面环境: {desktop_info['name']}
版本信息: {desktop_info.get('version', 'Unknown')}
安装目录: {desktop_info.get('directory', 'Unknown')}
程序文件: {desktop_info.get('executable', 'Unknown')}
文件数量: {desktop_info.get('file_count', 0)} 个
占用空间: {desktop_info.get('size_mb', 0)} MB

状态: 正常运行"""
                else:
                    status = f"""桌面环境状态: 未安装

桌面环境: {desktop_manager.get_desktop_types().get(desktop_type, {}).get('name', 'Unknown')}
安装目录: {self.directory_path_edit.text() or '未设置'}
程序文件: {self.program_path_edit.text() or '未设置'}

状态: 需要下载和安装"""
            
            self.status_info_edit.setPlainText(status)
            
        except Exception as e:
            log_error(e, "更新状态信息")
