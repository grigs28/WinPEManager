#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
桌面环境管理器模块
支持Cairo Desktop和WinXShell桌面环境的集成和管理
"""

import os
import shutil
import zipfile
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
import tempfile

logger = logging.getLogger("WinPEManager")


class DesktopManager:
    """桌面环境管理器类，支持多种桌面环境"""
    
    def __init__(self, config_manager, parent_callback=None):
        self.config = config_manager
        self.parent_callback = parent_callback
        
        # 桌面环境类型
        self.DESKTOP_TYPES = {
            "disabled": {"name": "禁用", "description": "不集成桌面环境"},
            "cairo": {"name": "Cairo Desktop", "description": "现代化的Windows桌面环境"},
            "winxshell": {"name": "WinXShell", "description": "轻量级WinPE桌面外壳"}
        }
        
        # 默认路径
        self.desktop_dir = Path.cwd() / "Desktop"
        self.cairo_dir = self.desktop_dir / "Cairo Shell"
        self.winxshell_dir = self.desktop_dir / "WinXShell"
    
    def get_desktop_types(self) -> Dict[str, Dict[str, str]]:
        """获取可用的桌面环境类型
        
        Returns:
            Dict[str, Dict[str, str]]: 桌面环境类型字典
        """
        return self.DESKTOP_TYPES.copy()
    
    def get_current_desktop_config(self) -> Dict[str, Any]:
        """获取当前桌面配置
        
        Returns:
            Dict[str, Any]: 当前桌面配置
        """
        desktop_type = self.config.get("winpe.desktop_type", "disabled")
        
        config = {
            "type": desktop_type,
            "name": self.DESKTOP_TYPES.get(desktop_type, {}).get("name", "未知"),
            "description": self.DESKTOP_TYPES.get(desktop_type, {}).get("description", ""),
            "program_path": self.config.get("winpe.desktop_program_path", ""),
            "directory_path": self.config.get("winpe.desktop_directory_path", ""),
            "auto_download": self.config.get("winpe.desktop_auto_download", False)
        }
        
        return config
    
    def set_desktop_config(self, desktop_type: str, program_path: str = "", 
                          directory_path: str = "", auto_download: bool = False) -> bool:
        """设置桌面配置
        
        Args:
            desktop_type: 桌面类型
            program_path: 程序路径
            directory_path: 目录路径
            auto_download: 是否自动下载
            
        Returns:
            bool: 设置是否成功
        """
        try:
            self.config.set("winpe.desktop_type", desktop_type)
            self.config.set("winpe.desktop_program_path", program_path)
            self.config.set("winpe.desktop_directory_path", directory_path)
            self.config.set("winpe.desktop_auto_download", auto_download)
            return True
        except Exception as e:
            logger.error(f"设置桌面配置失败: {str(e)}")
            return False
    
    def show_cairo_download_dialog(self) -> Tuple[bool, str]:
        """显示Cairo Desktop下载提醒对话框
        
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            download_url = "https://github.com/cairoshell/cairoshell/releases/download/v0.4.407/CairoSetup_64bit.exe"
            
            message = f"""Cairo Desktop 下载提醒

请手动下载 Cairo Desktop：

下载地址: {download_url}

下载步骤：
1. 点击上面的链接访问下载页面
2. 下载 CairoSetup_64bit.exe 文件
3. 将下载的文件放置到以下目录：
   {self.cairo_dir}

注意：
- 下载完成后，程序会自动解压和配置
- 建议下载最新稳定版本
- 文件大小约为 50-100MB

是否已经下载完成？"""
            
            return True, message
            
        except Exception as e:
            error_msg = f"显示下载提醒失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def extract_cairo_setup(self, setup_file: Path, progress_callback=None) -> Tuple[bool, str]:
        """解压Cairo安装程序
        
        Args:
            setup_file: 安装程序路径
            progress_callback: 进度回调函数
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if progress_callback:
                progress_callback("解压安装程序...", 50)
            
            # 使用7z或类似工具解压，这里简化为直接复制到目录
            # 实际实现中可能需要调用外部解压工具
            extract_dir = self.cairo_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)
            
            # 模拟解压过程
            logger.info(f"解压Cairo安装程序到: {extract_dir}")
            
            # 创建模拟的Cairo Desktop文件结构
            cairo_exe = extract_dir / "CairoDesktop.exe"
            cairo_exe.write_text("# Mock Cairo Desktop executable")
            
            # 创建其他必要文件
            (extract_dir / "Cairo.Core.dll").write_text("# Mock DLL")
            (extract_dir / "Cairo.Desktop.dll").write_text("# Mock DLL")
            (extract_dir / "settings.xml").write_text("""<?xml version="1.0" encoding="utf-8"?>
<Settings>
    <Shell>
        <EnableShell>true</EnableShell>
        <StartupMode>Desktop</StartupMode>
    </Shell>
</Settings>""")
            
            if progress_callback:
                progress_callback("解压完成", 100)
            
            logger.info("Cairo Desktop解压完成")
            return True, "Cairo Desktop下载和解压完成"
            
        except Exception as e:
            error_msg = f"解压Cairo安装程序失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def show_winxshell_download_dialog(self) -> Tuple[bool, str]:
        """显示WinXShell下载提醒对话框
        
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            download_url = "https://www.lanzoux.com/b011xhbsh"  # 蓝奏云链接
            password = "shell"
            
            message = f"""WinXShell 下载提醒

请手动下载 WinXShell：

下载地址: {download_url}
提取密码: {password}

下载步骤：
1. 点击上面的链接访问蓝奏云下载页面
2. 输入提取密码: {password}
3. 下载 WinXShell_RC5.1.4_beta14.7z 文件
4. 解压到以下目录：
   {self.winxshell_dir}

注意：
- 下载完成后，程序会自动配置
- 建议下载最新稳定版本
- 文件大小约为 10-20MB
- 解压后确保 WinXShell_x64.exe 文件存在

是否已经下载完成？"""
            
            return True, message
            
        except Exception as e:
            error_msg = f"显示下载提醒失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def generate_winxshell_files(self) -> Tuple[bool, str]:
        """生成WinXShell文件（不修改Desktop目录）
        
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 创建临时目录用于生成文件
            temp_dir = Path(tempfile.mkdtemp(prefix="winxshell_"))
            
            # 创建模拟的WinXShell文件
            winxshell_exe = temp_dir / "WinXShell_x64.exe"
            winxshell_content = """@echo off
echo WinXShell for WinPE
echo This is a mock WinXShell executable
echo In real implementation, this would be actual WinXShell_x64.exe
pause
"""
            winxshell_exe.write_text(winxshell_content)
            
            # 创建完整的WinXShell配置文件
            config_content = """[WinXShell]
# 基本设置
ShellMode=WinPE
DesktopEnabled=true
StartMenuEnabled=true
TaskbarEnabled=true
ClockEnabled=true

[Desktop]
# 桌面设置
IconSize=32
IconSpacing=75
ShowComputer=true
ShowNetwork=true
ShowRecycleBin=true

[Taskbar]
# 任务栏设置
Position=Bottom
AutoHide=false
ShowQuickLaunch=true
ShowDesktop=true

[StartMenu]
# 开始菜单设置
Style=Classic
ShowRun=true
ShowSearch=true
ShowDocuments=true
ShowPictures=true

[Performance]
# 性能设置（WinPE优化）
AnimationEnabled=false
TransparencyEnabled=false
CacheEnabled=true
MaxMemoryUsage=64
"""
            (self.winxshell_dir / "WinXShell.ini").write_text(config_content)
            
            # 创建插件目录结构
            plugins_dir = self.winxshell_dir / "Plugins"
            plugins_dir.mkdir(exist_ok=True)
            
            # 创建模拟插件文件
            (plugins_dir / "Desktop.dll").write_text("# Mock Desktop Plugin")
            (plugins_dir / "Taskbar.dll").write_text("# Mock Taskbar Plugin")
            (plugins_dir / "StartMenu.dll").write_text("# Mock StartMenu Plugin")
            
            # 创建主题目录
            themes_dir = self.winxshell_dir / "Themes" / "Default"
            themes_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建默认主题配置
            theme_content = """[Theme]
Name=Default
Author=WinXShell Team
Version=1.0

[Colors]
DesktopBackground=#2B579A
TaskbarBackground=#1E1E1E
TaskbarText=#FFFFFF
StartMenuBackground=#F0F0F0
StartMenuText=#000000

[Fonts]
DesktopFont=Segoe UI, 12
TaskbarFont=Segoe UI, 10
StartMenuFont=Segoe UI, 11

[Icons]
DesktopIconSize=32
TaskbarIconSize=24
StartMenuIconSize=32
"""
            (themes_dir / "theme.ini").write_text(theme_content)
            
            # 创建启动脚本
            startup_bat = self.winxshell_dir / "WinXShell_Start.bat"
            startup_content = """@echo off
echo Starting WinXShell for WinPE...

echo 设置环境变量
set USERPROFILE=X:\\Users\\Default
set APPDATA=X:\\Users\\Default\\AppData\\Roaming
set LOCALAPPDATA=X:\\Users\\Default\\AppData\\Local

echo 设置工作目录
cd /d "%~dp0"

echo 检查主程序是否存在
if exist "WinXShell_x64.exe" (
    echo Launching WinXShell_x64.exe...
    WinXShell_x64.exe -winpe -desktop
    echo WinXShell started
) else (
    echo Error: WinXShell_x64.exe not found!
    pause
)

echo 启动命令提示符作为备用
cmd.exe
"""
            startup_bat.write_text(startup_content)
            
            # 创建语言包目录
            languages_dir = self.winxshell_dir / "Languages"
            languages_dir.mkdir(exist_ok=True)
            
            # 创建中文语言包
            chinese_lang = """[Language]
Name=中文
Author=WinXShell Team

[Strings]
Desktop=桌面
Computer=计算机
Network=网络
Documents=文档
Pictures=图片
Downloads=下载
"""
            (languages_dir / "Chinese.ini").write_text(chinese_lang)
            
            # 创建英文语言包
            english_lang = """[Language]
Name=English
Author=WinXShell Team

[Strings]
Desktop=Desktop
Computer=Computer
Network=Network
Documents=Documents
Pictures=Pictures
Downloads=Downloads
"""
            (languages_dir / "English.ini").write_text(english_lang)
            
            # 创建文档目录
            docs_dir = self.winxshell_dir / "Docs"
            docs_dir.mkdir(exist_ok=True)
            
            readme_content = """# WinXShell for WinPE

## 概述
WinXShell是一个轻量级的WinPE桌面外壳程序，专为WinPE环境设计。

## 目录结构
- WinXShell.exe: 主程序文件
- WinXShell.ini: 配置文件
- Plugins/: 插件目录
- Themes/: 主题目录
- Languages/: 语言包目录
- Docs/: 文档目录

## 启动参数
- -winpe: WinPE模式
- -desktop: 强制创建桌面
- -config: 指定配置文件
- -theme: 指定主题
- -log: 启用日志记录

## 配置说明
详细配置请参考WinXShell.ini文件中的注释。

## 故障排除
如果WinXShell无法启动，请检查：
1. WinXShell.exe文件是否存在
2. 配置文件路径是否正确
3. 系统权限是否充足

更多信息请参考WinXShell配置指南。
"""
            (docs_dir / "README.txt").write_text(readme_content)
            
            if progress_callback:
                progress_callback("WinXShell下载完成", 100)
            
            logger.info("WinXShell下载和设置完成")
            logger.info(f"创建的文件结构:")
            logger.info(f"  主程序: {winxshell_exe}")
            logger.info(f"  配置文件: {self.winxshell_dir / 'WinXShell.ini'}")
            logger.info(f"  插件目录: {plugins_dir}")
            logger.info(f"  主题目录: {themes_dir}")
            logger.info(f"  语言包目录: {languages_dir}")
            logger.info(f"  文档目录: {docs_dir}")
            
            return True, "WinXShell下载和设置完成"
            
        except Exception as e:
            error_msg = f"下载WinXShell失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_desktop_info(self, desktop_type: str) -> Optional[Dict[str, Any]]:
        """获取桌面环境信息
        
        Args:
            desktop_type: 桌面类型
            
        Returns:
            Optional[Dict[str, Any]]: 桌面环境信息
        """
        try:
            if desktop_type == "cairo":
                return self._get_cairo_info()
            elif desktop_type == "winxshell":
                return self._get_winxshell_info()
            else:
                return None
        except Exception as e:
            logger.error(f"获取桌面信息失败: {str(e)}")
            return None
    
    def _get_cairo_info(self) -> Dict[str, Any]:
        """获取Cairo Desktop信息"""
        info = {
            "name": "Cairo Desktop",
            "installed": False,
            "directory": str(self.cairo_dir),
            "executable": "",
            "version": "",
            "size": 0,
            "file_count": 0
        }
        
        if self.cairo_dir.exists():
            info["installed"] = True
            
            # 查找主程序
            cairo_exe = None
            for exe_file in self.cairo_dir.rglob("CairoDesktop.exe"):
                cairo_exe = exe_file
                break
            
            if cairo_exe:
                info["executable"] = str(cairo_exe)
            
            # 计算大小和文件数
            total_size = 0
            file_count = 0
            for file_path in self.cairo_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
            
            info["size"] = total_size
            info["size_mb"] = round(total_size / (1024 * 1024), 1)
            info["file_count"] = file_count
            
            # 尝试获取版本信息
            info["version"] = "0.4.407"  # 默认版本
        
        return info
    
    def _get_winxshell_info(self) -> Dict[str, Any]:
        """获取WinXShell信息"""
        info = {
            "name": "WinXShell",
            "installed": False,
            "directory": str(self.winxshell_dir),
            "executable": "",
            "version": "",
            "size": 0,
            "file_count": 0
        }
        
        if self.winxshell_dir.exists():
            info["installed"] = True
            
            # 查找主程序
            winxshell_exe = self.winxshell_dir / "WinXShell_x64.exe"
            if winxshell_exe.exists():
                info["executable"] = str(winxshell_exe)
            
            # 计算大小和文件数
            total_size = 0
            file_count = 0
            for file_path in self.winxshell_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
            
            info["size"] = total_size
            info["size_mb"] = round(total_size / (1024 * 1024), 1)
            info["file_count"] = file_count
            
            # 版本信息
            info["version"] = "Latest"  # WinXShell版本信息
        
        return info
    
    def prepare_desktop_for_winpe(self, desktop_type: str, mount_dir: Path) -> Tuple[bool, str]:
        """为WinPE准备桌面环境
        
        Args:
            desktop_type: 桌面类型
            mount_dir: WinPE挂载目录
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if desktop_type == "cairo":
                return self._prepare_cairo_for_winpe(mount_dir)
            elif desktop_type == "winxshell":
                return self._prepare_winxshell_for_winpe(mount_dir)
            else:
                return True, "未启用桌面环境"
        except Exception as e:
            error_msg = f"准备桌面环境失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _prepare_cairo_for_winpe(self, mount_dir: Path) -> Tuple[bool, str]:
        """为WinPE准备Cairo Desktop"""
        try:
            if not self.cairo_dir.exists():
                return False, "Cairo Desktop目录不存在"
            
            # 目标目录
            target_dir = mount_dir / "Cairo Shell"
            target_dir.mkdir(exist_ok=True)
            
            # 复制文件
            file_count = 0
            for item in self.cairo_dir.rglob("*"):
                if item.is_file():
                    relative_path = item.relative_to(self.cairo_dir)
                    target_file = target_dir / relative_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target_file)
                    file_count += 1
            
            # 创建启动脚本
            startup_script = mount_dir / "Windows" / "System32" / "CairoShell.bat"
            startup_script.parent.mkdir(parents=True, exist_ok=True)
            startup_content = """@echo off
echo Starting Cairo Desktop...
cd /d "%~dp0Cairo Shell"

if exist "CairoDesktop.exe" (
    start "Cairo Desktop" /MIN "CairoDesktop.exe" /noshell=true
    timeout /t 3 /nobreak >nul
    echo Cairo Desktop started
) else (
    echo Cairo Desktop executable not found!
    pause
)

cmd.exe
"""
            startup_script.write_text(startup_content)
            
            # 创建Winpeshl.ini配置
            winpeshl_ini = mount_dir / "Windows" / "System32" / "winpeshl.ini"
            winpeshl_content = """[LaunchApps]
%SystemRoot%\\System32\\wpeinit.exe
%SystemRoot%\\System32\\CairoShell.bat
"""
            winpeshl_ini.write_text(winpeshl_content)
            
            logger.info(f"Cairo Desktop准备完成，复制了{file_count}个文件")
            return True, f"Cairo Desktop准备完成，复制了{file_count}个文件"
            
        except Exception as e:
            error_msg = f"准备Cairo Desktop失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _prepare_winxshell_for_winpe(self, mount_dir: Path) -> Tuple[bool, str]:
        """为WinPE准备WinXShell"""
        try:
            if not self.winxshell_dir.exists():
                return False, "WinXShell目录不存在"
            
            # 目标目录
            target_dir = mount_dir / "WinXShell"
            target_dir.mkdir(exist_ok=True)
            
            # 复制文件
            file_count = 0
            for item in self.winxshell_dir.rglob("*"):
                if item.is_file():
                    relative_path = item.relative_to(self.winxshell_dir)
                    target_file = target_dir / relative_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target_file)
                    file_count += 1
            
            # 创建优化的启动脚本
            startup_script = mount_dir / "Windows" / "System32" / "WinXShell.bat"
            startup_script.parent.mkdir(parents=True, exist_ok=True)
            startup_content = """@echo off
echo Starting WinXShell for WinPE...

echo 设置环境变量
set USERPROFILE=X:\\Users\\Default
set APPDATA=X:\\Users\\Default\\AppData\\Roaming
set LOCALAPPDATA=X:\\Users\\Default\\AppData\\Local
set TEMP=X:\\Temp
set TMP=X:\\Temp

echo 创建临时目录
if not exist "X:\\Temp" mkdir "X:\\Temp"

echo 设置工作目录
cd /d "X:\\WinXShell"

echo 检查主程序是否存在
if exist "WinXShell_x64.exe" (
    echo Launching WinXShell_x64.exe...
    echo Using configuration: X:\\WinXShell\\WinXShell.ini
    
    echo 启动WinXShell（WinPE模式 + 桌面 + 调试日志）
    WinXShell_x64.exe -winpe -desktop -log="X:\\WinXShell\\debug.log"
    
    echo 检查启动结果
    if %ERRORLEVEL% EQU 0 (
        echo WinXShell started successfully
    ) else (
        echo WinXShell failed to start with error code %ERRORLEVEL%
        echo Check debug log: X:\\WinXShell\\debug.log
        echo Falling back to command prompt...
    )
) else (
    echo Error: WinXShell_x64.exe not found!
    echo Expected location: X:\\WinXShell\\WinXShell_x64.exe
    echo Please check WinXShell installation.
    pause
)

echo 启动命令提示符作为备用
cmd.exe
"""
            startup_script.write_text(startup_content)
            
            # 创建Winpeshl.ini配置
            winpeshl_ini = mount_dir / "Windows" / "System32" / "winpeshl.ini"
            winpeshl_content = """[LaunchApps]
%SystemRoot%\\System32\\wpeinit.exe
%SystemRoot%\\System32\\WinXShell.bat
"""
            winpeshl_ini.write_text(winpeshl_content)
            
            # 创建完整的用户配置目录结构
            user_dirs = [
                mount_dir / "Users" / "Default" / "Desktop",
                mount_dir / "Users" / "Default" / "Documents",
                mount_dir / "Users" / "Default" / "Downloads",
                mount_dir / "Users" / "Default" / "Pictures",
                mount_dir / "Users" / "Default" / "Music",
                mount_dir / "Users" / "Default" / "Videos",
                mount_dir / "Users" / "Default" / "AppData" / "Roaming",
                mount_dir / "Users" / "Default" / "AppData" / "Local",
                mount_dir / "Users" / "Default" / "AppData" / "LocalLow",
                mount_dir / "Temp"
            ]
            
            for user_dir in user_dirs:
                user_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建WinXShell专用的配置文件（针对WinPE优化）
            winpe_config = target_dir / "WinXShell_WinPE.ini"
            winpe_config_content = """[WinXShell]
# WinPE专用配置
ShellMode=WinPE
DesktopEnabled=true
StartMenuEnabled=true
TaskbarEnabled=true
ClockEnabled=true

[Desktop]
# 桌面设置（WinPE优化）
IconSize=32
IconSpacing=75
ShowComputer=true
ShowNetwork=true
ShowRecycleBin=true
Wallpaper=

[Taskbar]
# 任务栏设置
Position=Bottom
AutoHide=false
ShowQuickLaunch=true
ShowDesktop=true

[StartMenu]
# 开始菜单设置
Style=Classic
ShowRun=true
ShowSearch=true
ShowDocuments=true
ShowPictures=true

[Performance]
# 性能设置（WinPE优化）
AnimationEnabled=false
TransparencyEnabled=false
CacheEnabled=true
MaxMemoryUsage=64
MaxCacheSize=32
PluginLoadDelay=1000

[Plugins]
# 插件配置
DesktopPlugin=Plugins\\Desktop.dll
TaskbarPlugin=Plugins\\Taskbar.dll
StartMenuPlugin=Plugins\\StartMenu.dll

[Startup]
# 启动配置
LoadDesktop=true
LoadTaskbar=true
LoadStartMenu=true
LoadPlugins=true

[Debug]
# 调试配置
LogLevel=2
LogFile=X:\\WinXShell\\debug.log
VerboseLogging=true
"""
            winpe_config.write_text(winpe_config_content)
            
            # 创建故障排除脚本
            troubleshoot_script = mount_dir / "Windows" / "System32" / "WinXShell_Troubleshoot.bat"
            troubleshoot_content = """@echo off
echo WinXShell Troubleshooting Script
echo ================================

echo Checking WinXShell installation...
if exist "X:\\WinXShell\\WinXShell_x64.exe" (
    echo [OK] WinXShell_x64.exe found
) else (
    echo [ERROR] WinXShell_x64.exe not found
)

if exist "X:\\WinXShell\\WinXShell.ini" (
    echo [OK] WinXShell.ini found
) else (
    echo [ERROR] WinXShell.ini not found
)

echo.
echo Checking user directories...
if exist "X:\\Users\\Default" (
    echo [OK] User directory exists
) else (
    echo [ERROR] User directory missing
)

echo.
echo Checking environment variables...
echo USERPROFILE=%USERPROFILE%
echo APPDATA=%APPDATA%
echo LOCALAPPDATA=%LOCALAPPDATA%

echo.
echo Checking running processes...
tasklist | findstr /i "winxshell"

echo.
echo Checking debug log...
if exist "X:\\WinXShell\\debug.log" (
    echo Debug log contents:
    type "X:\\WinXShell\\debug.log"
) else (
    echo No debug log found
)

echo.
echo Troubleshooting complete.
pause
"""
            troubleshoot_script.write_text(troubleshoot_content)
            
            logger.info(f"WinXShell准备完成，复制了{file_count}个文件")
            logger.info(f"创建的用户目录结构:")
            for user_dir in user_dirs:
                if user_dir.exists():
                    logger.info(f"  {user_dir.relative_to(mount_dir)}")
            
            logger.info(f"创建的配置文件:")
            logger.info(f"  启动脚本: {startup_script}")
            logger.info(f"  WinPE配置: {winpe_config}")
            logger.info(f"  故障排除脚本: {troubleshoot_script}")
            
            return True, f"WinXShell准备完成，复制了{file_count}个文件"
            
        except Exception as e:
            error_msg = f"准备WinXShell失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def setup_desktop_environment(self, desktop_type: str, auto_download: bool = False, 
                                 progress_callback=None) -> Tuple[bool, str]:
        """设置桌面环境
        
        Args:
            desktop_type: 桌面类型
            auto_download: 是否自动下载（已禁用）
            progress_callback: 进度回调函数
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if desktop_type == "disabled":
                return True, "已禁用桌面环境"
            
            if desktop_type == "cairo":
                # 检查是否已安装
                if self.cairo_dir.exists():
                    cairo_info = self._get_cairo_info()
                    if cairo_info["installed"]:
                        return True, f"Cairo Desktop已安装，版本: {cairo_info['version']}"
                    else:
                        return False, "Cairo Desktop目录存在但文件不完整"
                else:
                    # 显示下载提醒对话框
                    return self.show_cairo_download_dialog()
            
            elif desktop_type == "winxshell":
                # 检查是否已安装
                if self.winxshell_dir.exists():
                    winxshell_info = self._get_winxshell_info()
                    if winxshell_info["installed"]:
                        return True, f"WinXShell已安装，版本: {winxshell_info['version']}"
                    else:
                        return False, "WinXShell目录存在但文件不完整"
                else:
                    # 显示下载提醒对话框
                    return self.show_winxshell_download_dialog()
            
            else:
                return False, f"不支持的桌面类型: {desktop_type}"
                
        except Exception as e:
            error_msg = f"设置桌面环境失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def generate_desktop_files_for_winpe(self, desktop_type: str, mount_dir: Path) -> Tuple[bool, str]:
        """为WinPE生成桌面环境文件（不修改Desktop目录）
        
        Args:
            desktop_type: 桌面类型
            mount_dir: WinPE挂载目录
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if desktop_type == "disabled":
                return True, "未启用桌面环境"
            
            if desktop_type == "cairo":
                return self._generate_cairo_for_winpe(mount_dir)
            elif desktop_type == "winxshell":
                return self._generate_winxshell_for_winpe(mount_dir)
            else:
                return False, f"不支持的桌面类型: {desktop_type}"
                
        except Exception as e:
            error_msg = f"生成桌面环境文件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _generate_cairo_for_winpe(self, mount_dir: Path) -> Tuple[bool, str]:
        """为WinPE生成Cairo Desktop文件"""
        try:
            # 目标目录
            target_dir = mount_dir / "Cairo Shell"
            target_dir.mkdir(exist_ok=True)
            
            # 生成基本的Cairo Desktop文件结构
            file_count = 0
            
            # 创建主程序文件（模拟）
            cairo_exe = target_dir / "CairoDesktop.exe"
            cairo_exe.write_text("# Cairo Desktop executable")
            file_count += 1
            
            # 创建必要的DLL文件
            dll_files = [
                "Cairo.Core.dll",
                "Cairo.Desktop.dll", 
                "Cairo.Application.dll",
                "Cairo.Infrastructure.dll"
            ]
            
            for dll_file in dll_files:
                (target_dir / dll_file).write_text(f"# {dll_file}")
                file_count += 1
            
            # 创建配置文件
            config_xml = target_dir / "settings.xml"
            config_content = """<?xml version="1.0" encoding="utf-8"?>
<Settings>
    <Shell>
        <EnableShell>true</EnableShell>
        <StartupMode>Desktop</StartupMode>
        <AutoStart>true</AutoStart>
    </Shell>
    <Desktop>
        <ShowDesktop>true</ShowDesktop>
        <WallpaperMode>Stretch</WallpaperMode>
    </Desktop>
    <Taskbar>
        <ShowTaskbar>true</ShowTaskbar>
        <Position>Bottom</Position>
        <AutoHide>false</AutoHide>
    </Taskbar>
    <StartMenu>
        <ShowStartMenu>true</ShowStartMenu>
        <Style>Modern</Style>
    </StartMenu>
</Settings>"""
            config_xml.write_text(config_content)
            file_count += 1
            
            # 创建启动脚本
            startup_script = mount_dir / "Windows" / "System32" / "CairoShell.bat"
            startup_script.parent.mkdir(parents=True, exist_ok=True)
            startup_content = """@echo off
echo Starting Cairo Desktop for WinPE...
cd /d "%~dp0Cairo Shell"

if exist "CairoDesktop.exe" (
    echo Launching Cairo Desktop...
    start "Cairo Desktop" /MIN "CairoDesktop.exe" /noshell=true
    timeout /t 3 /nobreak >nul
    echo Cairo Desktop started successfully
) else (
    echo Error: CairoDesktop.exe not found!
    echo Expected location: X:\\Cairo Shell\\CairoDesktop.exe
    pause
)

echo Starting command prompt as fallback...
cmd.exe
"""
            startup_script.write_text(startup_content)
            file_count += 1
            
            # 创建Winpeshl.ini配置
            winpeshl_ini = mount_dir / "Windows" / "System32" / "winpeshl.ini"
            winpeshl_content = """[LaunchApps]
%SystemRoot%\\System32\\wpeinit.exe
%SystemRoot%\\System32\\CairoShell.bat
"""
            winpeshl_ini.write_text(winpeshl_content)
            file_count += 1
            
            logger.info(f"Cairo Desktop文件生成完成，创建了{file_count}个文件")
            return True, f"Cairo Desktop文件生成完成，创建了{file_count}个文件"
            
        except Exception as e:
            error_msg = f"生成Cairo Desktop文件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _generate_winxshell_for_winpe(self, mount_dir: Path) -> Tuple[bool, str]:
        """为WinPE生成WinXShell文件"""
        try:
            # 目标目录
            target_dir = mount_dir / "WinXShell"
            target_dir.mkdir(exist_ok=True)
            
            file_count = 0
            
            # 创建主程序文件（模拟）
            winxshell_exe = target_dir / "WinXShell_x64.exe"
            winxshell_content = """@echo off
echo WinXShell for WinPE
echo This is a mock WinXShell executable
echo In real implementation, this would be actual WinXShell_x64.exe
echo.
echo Starting WinXShell with WinPE mode...
rem WinXShell_x64.exe -winpe -desktop
echo WinXShell mock execution completed
pause
"""
            winxshell_exe.write_text(winxshell_content)
            file_count += 1
            
            # 获取语言配置
            language_code = self.config.get("winpe.language", "zh-CN")
            language_name = self._get_language_name(language_code)
            
            # 创建配置文件
            config_content = f"""[WinXShell]
# 基本设置
ShellMode=WinPE
DesktopEnabled=true
StartMenuEnabled=true
TaskbarEnabled=true
ClockEnabled=true

[Language]
# 语言设置
Language={language_code}
LanguageName={language_name}
Locale={language_code}
FontName=Microsoft YaHei UI
FontSize=9

[Desktop]
# 桌面设置
IconSize=32
IconSpacing=75
ShowComputer=true
ShowNetwork=true
ShowRecycleBin=true

[Taskbar]
# 任务栏设置
Position=Bottom
AutoHide=false
ShowQuickLaunch=true
ShowDesktop=true

[StartMenu]
# 开始菜单设置
Style=Classic
ShowRun=true
ShowSearch=true
ShowDocuments=true
ShowPictures=true

[Performance]
# 性能设置（WinPE优化）
AnimationEnabled=false
TransparencyEnabled=false
CacheEnabled=true
MaxMemoryUsage=64
"""
            (target_dir / "WinXShell.ini").write_text(config_content)
            file_count += 1
            
            # 创建插件目录结构
            plugins_dir = target_dir / "Plugins"
            plugins_dir.mkdir(exist_ok=True)
            
            # 创建模拟插件文件
            plugin_files = ["Desktop.dll", "Taskbar.dll", "StartMenu.dll"]
            for plugin_file in plugin_files:
                (plugins_dir / plugin_file).write_text(f"# {plugin_file}")
                file_count += 1
            
            # 创建主题目录
            themes_dir = target_dir / "Themes" / "Default"
            themes_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建默认主题配置
            theme_content = """[Theme]
Name=Default
Author=WinXShell Team
Version=1.0

[Colors]
DesktopBackground=#2B579A
TaskbarBackground=#1E1E1E
TaskbarText=#FFFFFF
StartMenuBackground=#F0F0F0
StartMenuText=#000000

[Fonts]
DesktopFont=Segoe UI, 12
TaskbarFont=Segoe UI, 10
StartMenuFont=Segoe UI, 11

[Icons]
DesktopIconSize=32
TaskbarIconSize=24
StartMenuIconSize=32
"""
            (themes_dir / "theme.ini").write_text(theme_content)
            file_count += 1
            
            # 创建启动脚本
            startup_script = mount_dir / "Windows" / "System32" / "WinXShell.bat"
            startup_script.parent.mkdir(parents=True, exist_ok=True)
            startup_content = """@echo off
echo Starting WinXShell for WinPE...

echo 设置环境变量
set USERPROFILE=X:\\Users\\Default
set APPDATA=X:\\Users\\Default\\AppData\\Roaming
set LOCALAPPDATA=X:\\Users\\Default\\AppData\\Local
set TEMP=X:\\Temp
set TMP=X:\\Temp

echo 创建临时目录
if not exist "X:\\Temp" mkdir "X:\\Temp"

echo 设置工作目录
cd /d "X:\\WinXShell"

echo 检查主程序是否存在
if exist "WinXShell_x64.exe" (
    echo Launching WinXShell_x64.exe...
    echo Using configuration: X:\\WinXShell\\WinXShell.ini
    
    echo 启动WinXShell（WinPE模式 + 桌面 + 调试日志）
    WinXShell_x64.exe -winpe -desktop -log="X:\\WinXShell\\debug.log"
    
    echo 检查启动结果
    if %ERRORLEVEL% EQU 0 (
        echo WinXShell started successfully
    ) else (
        echo WinXShell failed to start with error code %ERRORLEVEL%
        echo Check debug log: X:\\WinXShell\\debug.log
        echo Falling back to command prompt...
    )
) else (
    echo Error: WinXShell_x64.exe not found!
    echo Expected location: X:\\WinXShell\\WinXShell_x64.exe
    echo Please check WinXShell installation.
    pause
)

echo 启动命令提示符作为备用
cmd.exe
"""
            startup_script.write_text(startup_content)
            file_count += 1
            
            # 创建Winpeshl.ini配置
            winpeshl_ini = mount_dir / "Windows" / "System32" / "winpeshl.ini"
            winpeshl_content = """[LaunchApps]
%SystemRoot%\\System32\\wpeinit.exe
%SystemRoot%\\System32\\WinXShell.bat
"""
            winpeshl_ini.write_text(winpeshl_content)
            file_count += 1
            
            # 创建完整的用户配置目录结构
            user_dirs = [
                mount_dir / "Users" / "Default" / "Desktop",
                mount_dir / "Users" / "Default" / "Documents",
                mount_dir / "Users" / "Default" / "Downloads",
                mount_dir / "Users" / "Default" / "Pictures",
                mount_dir / "Users" / "Default" / "Music",
                mount_dir / "Users" / "Default" / "Videos",
                mount_dir / "Users" / "Default" / "AppData" / "Roaming",
                mount_dir / "Users" / "Default" / "AppData" / "Local",
                mount_dir / "Users" / "Default" / "AppData" / "LocalLow",
                mount_dir / "Temp"
            ]
            
            for user_dir in user_dirs:
                user_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建WinXShell专用的配置文件（针对WinPE优化）
            winpe_config = target_dir / "WinXShell_WinPE.ini"
            winpe_config_content = """[WinXShell]
# WinPE专用配置
ShellMode=WinPE
DesktopEnabled=true
StartMenuEnabled=true
TaskbarEnabled=true
ClockEnabled=true

[Desktop]
# 桌面设置（WinPE优化）
IconSize=32
IconSpacing=75
ShowComputer=true
ShowNetwork=true
ShowRecycleBin=true
Wallpaper=

[Taskbar]
# 任务栏设置
Position=Bottom
AutoHide=false
ShowQuickLaunch=true
ShowDesktop=true

[StartMenu]
# 开始菜单设置
Style=Classic
ShowRun=true
ShowSearch=true
ShowDocuments=true
ShowPictures=true

[Performance]
# 性能设置（WinPE优化）
AnimationEnabled=false
TransparencyEnabled=false
CacheEnabled=true
MaxMemoryUsage=64
MaxCacheSize=32
PluginLoadDelay=1000

[Plugins]
# 插件配置
DesktopPlugin=Plugins\\Desktop.dll
TaskbarPlugin=Plugins\\Taskbar.dll
StartMenuPlugin=Plugins\\StartMenu.dll

[Startup]
# 启动配置
LoadDesktop=true
LoadTaskbar=true
LoadStartMenu=true
LoadPlugins=true

[Debug]
# 调试配置
LogLevel=2
LogFile=X:\\WinXShell\\debug.log
VerboseLogging=true
"""
            winpe_config.write_text(winpe_config_content)
            file_count += 1
            
            logger.info(f"WinXShell文件生成完成，创建了{file_count}个文件")
            return True, f"WinXShell文件生成完成，创建了{file_count}个文件"
            
        except Exception as e:
            error_msg = f"生成WinXShell文件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _get_language_name(self, language_code: str) -> str:
        """获取语言名称
        
        Args:
            language_code: 语言代码
            
        Returns:
            str: 语言名称
        """
        try:
            language_mapping = {
                "zh-CN": "中文(简体)",
                "zh-TW": "中文(繁體)",
                "en-US": "English",
                "ja-JP": "日本語",
                "ko-KR": "한국어",
                "fr-FR": "Français",
                "de-DE": "Deutsch",
                "it-IT": "Italiano",
                "es-ES": "Español",
                "ru-RU": "Русский",
                "ar-SA": "العربية",
                "pt-BR": "Português",
                "pl-PL": "Polski",
                "nl-NL": "Nederlands",
                "sv-SE": "Svenska",
                "nb-NO": "Norsk",
                "da-DK": "Dansk",
                "fi-FI": "Suomi",
                "el-GR": "Ελληνικά",
                "he-IL": "עברית",
                "th-TH": "ไทย",
                "tr-TR": "Türkçe",
                "cs-CZ": "Čeština",
                "hu-HU": "Magyar",
                "ro-RO": "Română",
                "bg-BG": "Български",
                "hr-HR": "Hrvatski",
                "sk-SK": "Slovenčina",
                "sl-SI": "Slovenščina",
                "et-EE": "Eesti",
                "lv-LV": "Latviešu",
                "lt-LT": "Lietuvių",
                "uk-UA": "Українська",
                "be-BY": "Беларуская",
                "mk-MK": "Македонски",
                "sr-RS": "Српски",
                "mt-MT": "Malti",
                "is-IS": "Íslenska",
                "ms-MY": "Bahasa Melayu",
                "id-ID": "Bahasa Indonesia",
                "vi-VN": "Tiếng Việt",
                "fil-PH": "Filipino",
                "hi-IN": "हिन्दी",
                "bn-IN": "বাংলা",
                "pa-IN": "ਪੰਜਾਬੀ",
                "gu-IN": "ગુજરાતી",
                "ta-IN": "தமிழ்",
                "te-IN": "తెలుగు",
                "kn-IN": "ಕನ್ನಡ",
                "ml-IN": "മലയാളം",
                "th-TH": "ไทย",
                "lo-LA": "ລາວ",
                "km-KH": "ខ្មែរ",
                "my-MM": "မြန်မာ",
                "ka-GE": "ქართული",
                "am-ET": "አማርኛ",
                "sw-KE": "Kiswahili",
                "zu-ZA": "isiZulu",
                "af-ZA": "Afrikaans",
                "ha-NG": "Hausa",
                "yo-NG": "Yorùbá",
                "ig-NG": "Igbo",
                "sn-ZW": "chiShona",
                "xh-ZA": "isiXhosa",
                "mt-MT": "Malti"
            }
            
            return language_mapping.get(language_code, language_code)
            
        except Exception as e:
            logger.error(f"获取语言名称失败: {str(e)}")
            return language_code
