#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinPE启动配置模块
负责WinPE启动过程中的窗口管理和配置优化
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger("WinPEManager")


class BootConfig:
    """WinPE启动配置管理器"""
    
    def __init__(self, config_manager, adk_manager, parent_callback=None):
        self.config = config_manager
        self.adk = adk_manager
        self.parent_callback = parent_callback
    
    def configure_winpe_startup(self, current_build_path: Path, desktop_type: str) -> Tuple[bool, str]:
        """配置WinPE启动设置，隐藏cmd.exe窗口
        
        Args:
            current_build_path: 当前构建路径
            desktop_type: 桌面环境类型
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not current_build_path:
                return False, "工作空间未初始化"

            mount_dir = current_build_path / "mount"
            if not mount_dir.exists() or not list(mount_dir.iterdir()):
                logger.warning("WinPE镜像未挂载，跳过启动配置")
                return True, "镜像未挂载，跳过启动配置"

            logger.info(f"🚀 配置WinPE启动设置，桌面类型: {desktop_type}")

            # 根据桌面类型配置不同的启动方案
            if desktop_type == "disabled":
                return self._configure_no_desktop_startup(mount_dir)
            elif desktop_type == "cairo":
                return self._configure_cairo_startup(mount_dir)
            elif desktop_type == "winxshell":
                return self._configure_winxshell_startup(mount_dir)
            else:
                return False, f"不支持的桌面类型: {desktop_type}"

        except Exception as e:
            error_msg = f"配置WinPE启动设置失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def _configure_no_desktop_startup(self, mount_dir: Path) -> Tuple[bool, str]:
        """配置无桌面环境的启动（隐藏cmd.exe窗口）"""
        try:
            logger.info("配置无桌面环境的启动设置...")
            
            # 方案1：使用start命令最小化启动cmd.exe
            startup_script = mount_dir / "Windows" / "System32" / "winpeshl.ini"
            startup_script_content = """[LaunchApps]
%SystemRoot%\\System32\\wpeinit.exe
%SystemRoot%\\System32\\cmd_minimized.exe
"""
            startup_script.write_text(startup_script_content)
            
            # 创建最小化启动cmd的包装脚本
            cmd_minimized = mount_dir / "Windows" / "System32" / "cmd_minimized.bat"
            cmd_minimized_content = """@echo off
title WinPE Command Prompt
rem 最小化当前窗口
powershell -Command "& {$wshell = New-Object -ComObject wscript.shell; $wshell.AppActivate('WinPE Command Prompt'); sleep 1; $wshell.SendKeys('% n')}"
rem 启动命令提示符
cmd.exe
"""
            cmd_minimized.write_text(cmd_minimized_content)
            
            # 方案2：创建隐藏启动的VBS脚本
            hidden_cmd_vbs = mount_dir / "Windows" / "System32" / "hidden_cmd.vbs"
            hidden_cmd_content = '''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "cmd.exe" & chr(34), 0, False
'''
            hidden_cmd_vbs.write_text(hidden_cmd_content)
            
            # 方案3：创建静默启动脚本
            silent_startup = mount_dir / "Windows" / "System32" / "silent_startup.bat"
            silent_content = """@echo off
rem 静默启动WinPE命令提示符
rem 检查是否有桌面环境在运行
tasklist | findstr /i "explorer.exe" >nul
if %ERRORLEVEL% EQU 0 (
    echo 桌面环境正在运行，隐藏命令提示符
    exit
)

rem 检查是否有其他桌面环境
tasklist | findstr /i "cairodesktop.exe" >nul
if %ERRORLEVEL% EQU 0 (
    echo Cairo Desktop正在运行，隐藏命令提示符
    exit
)

tasklist | findstr /i "winxshell.exe" >nul
if %ERRORLEVEL% EQU 0 (
    echo WinXShell正在运行，隐藏命令提示符
    exit
)

rem 如果没有桌面环境，最小化启动命令提示符
start /MIN cmd.exe
"""
            silent_startup.write_text(silent_content)
            
            # 更新winpeshl.ini使用静默启动
            startup_script.write_text("""[LaunchApps]
%SystemRoot%\\System32\\wpeinit.exe
%SystemRoot%\\System32\\silent_startup.bat
""")
            
            logger.info("✅ 无桌面环境启动配置完成")
            return True, "无桌面环境启动配置完成"

        except Exception as e:
            error_msg = f"配置无桌面环境启动失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _configure_cairo_startup(self, mount_dir: Path) -> Tuple[bool, str]:
        """配置Cairo Desktop启动（隐藏cmd.exe窗口）"""
        try:
            logger.info("配置Cairo Desktop启动设置...")
            
            # 创建优化的Cairo启动脚本
            cairo_startup = mount_dir / "Windows" / "System32" / "CairoShell.bat"
            cairo_content = """@echo off
title Cairo Desktop Startup
echo 正在启动Cairo Desktop...

rem 设置环境变量
set USERPROFILE=X:\\Users\\Default
set APPDATA=X:\\Users\\Default\\AppData\\Roaming
set LOCALAPPDATA=X:\\Users\\Default\\AppData\\Local

rem 设置工作目录
cd /d "X:\\Cairo Shell"

rem 检查Cairo Desktop是否存在
if exist "CairoDesktop.exe" (
    echo 启动Cairo Desktop...
    start "Cairo Desktop" /MIN "CairoDesktop.exe" /noshell=true
    
    rem 等待Cairo Desktop启动
    timeout /t 5 /nobreak >nul
    
    rem 检查Cairo Desktop是否正在运行
    tasklist | findstr /i "cairodesktop.exe" >nul
    if %ERRORLEVEL% EQU 0 (
        echo Cairo Desktop启动成功，隐藏命令提示符
        exit
    ) else (
        echo Cairo Desktop启动失败，显示命令提示符
        goto :show_cmd
    )
) else (
    echo Cairo Desktop未找到
    goto :show_cmd
)

:show_cmd
rem 如果Cairo Desktop启动失败，显示命令提示符
echo 启动命令提示符...
start /MIN cmd.exe
exit
"""
            cairo_startup.write_text(cairo_content)
            
            # 创建Cairo专用的winpeshl.ini
            winpeshl_ini = mount_dir / "Windows" / "System32" / "winpeshl.ini"
            winpeshl_content = """[LaunchApps]
%SystemRoot%\\System32\\wpeinit.exe
%SystemRoot%\\System32\\CairoShell.bat
"""
            winpeshl_ini.write_text(winpeshl_content)
            
            # 创建Cairo Desktop配置文件
            cairo_config_dir = mount_dir / "Cairo Shell" / "Config"
            cairo_config_dir.mkdir(parents=True, exist_ok=True)
            
            cairo_settings = cairo_config_dir / "settings.xml"
            settings_content = """<?xml version="1.0" encoding="utf-8"?>
<Settings>
    <Shell>
        <EnableShell>true</EnableShell>
        <StartupMode>Desktop</StartupMode>
        <AutoStart>true</AutoStart>
        <HideCommandLine>true</HideCommandLine>
    </Shell>
    <Desktop>
        <ShowDesktop>true</ShowDesktop>
        <WallpaperMode>Stretch</WallpaperMode>
        <HideTaskbar>false</HideTaskbar>
    </Desktop>
    <Performance>
        <EnableAnimations>false</EnableAnimations>
        <EnableTransparency>false</EnableTransparency>
        <StartupDelay>2000</StartupDelay>
    </Performance>
</Settings>"""
            cairo_settings.write_text(settings_content)
            
            logger.info("✅ Cairo Desktop启动配置完成")
            return True, "Cairo Desktop启动配置完成"

        except Exception as e:
            error_msg = f"配置Cairo Desktop启动失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _configure_winxshell_startup(self, mount_dir: Path) -> Tuple[bool, str]:
        """配置WinXShell启动（隐藏cmd.exe窗口）"""
        try:
            logger.info("配置WinXShell启动设置...")
            
            # 获取语言配置
            language_code = self.config.get("winpe.language", "zh-CN")
            language_name = self._get_language_name(language_code)
            
            # 创建优化的WinXShell启动脚本（完全去掉cmd.exe）
            winxshell_startup = mount_dir / "Windows" / "System32" / "WinXShell.bat"
            winxshell_content = f"""@echo off
title WinXShell Startup
echo 正在启动WinXShell ({language_name})...

rem 设置环境变量
set USERPROFILE=X:\\Users\\Default
set APPDATA=X:\\Users\\Default\\AppData\\Roaming
set LOCALAPPDATA=X:\\Users\\Default\\AppData\\Local
set TEMP=X:\\Temp
set TMP=X:\\Temp

rem 设置语言环境
set LANG={language_code}
set LANGUAGE={language_code}
set LC_ALL={language_code}

rem 创建临时目录
if not exist "X:\\Temp" mkdir "X:\\Temp"

rem 设置工作目录
cd /d "X:\\WinXShell"

rem 检查WinXShell是否存在
if exist "WinXShell_x64.exe" (
    echo 启动WinXShell ({language_name})...
    echo 使用配置: X:\\WinXShell\\WinXShell.ini
    echo 语言设置: {language_code}
    
    rem 启动WinXShell（WinPE模式 + 桌面 + 静默 + 无控制台）
    start "" /MIN "WinXShell_x64.exe" -winpe -desktop -silent -log="X:\\WinXShell\\debug.log" -jcfg="X:\\WinXShell\\WinXShell.ini"
    
    rem 等待WinXShell启动
    timeout /t 3 /nobreak >nul
    
    rem 检查WinXShell是否正在运行
    tasklist | findstr /i "winxshell.exe" >nul
    if %ERRORLEVEL% EQU 0 (
        echo WinXShell启动成功
        echo 语言环境: {language_name}
        exit
    ) else (
        echo WinXShell启动失败，检查日志...
        if exist "X:\\WinXShell\\debug.log" (
            echo 调试日志内容:
            type "X:\\WinXShell\\debug.log"
        )
        rem 不显示cmd.exe，直接退出
        exit
    )
) else (
    echo WinXShell未找到
    echo 预期位置: X:\\WinXShell\\WinXShell_x64.exe
    rem 不显示cmd.exe，直接退出
    exit
)

rem 完全退出，不显示任何命令提示符
exit
"""
            winxshell_startup.write_text(winxshell_content)
            
            # 创建WinXShell专用的winpeshl.ini
            winpeshl_ini = mount_dir / "Windows" / "System32" / "winpeshl.ini"
            winpeshl_content = """[LaunchApps]
%SystemRoot%\\System32\\wpeinit.exe
%SystemRoot%\\System32\\WinXShell.bat
"""
            winpeshl_ini.write_text(winpeshl_content)
            
            # 创建WinXShell配置文件（针对WinPE优化）
            winxshell_config_dir = mount_dir / "WinXShell"
            winxshell_config_dir.mkdir(exist_ok=True)
            
            winxshell_config = winxshell_config_dir / "WinXShell.ini"
            config_content = f"""[WinXShell]
# WinPE专用配置
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
# 桌面设置（WinPE优化）
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
MaxCacheSize=32
PluginLoadDelay=1000

[Startup]
# 启动配置
LoadDesktop=true
LoadTaskbar=true
LoadStartMenu=true
LoadPlugins=true
HideCommandLine=true
SilentMode=true

[Debug]
# 调试配置
LogLevel=2
LogFile=X:\\WinXShell\\debug.log
VerboseLogging=true
"""
            winxshell_config.write_text(config_content)
            
            logger.info("✅ WinXShell启动配置完成")
            return True, "WinXShell启动配置完成"

        except Exception as e:
            error_msg = f"配置WinXShell启动失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def create_advanced_startup_scripts(self, mount_dir: Path) -> Tuple[bool, str]:
        """创建高级启动脚本，提供多种隐藏cmd.exe的方案"""
        try:
            logger.info("创建高级启动脚本...")
            
            scripts_dir = mount_dir / "Windows" / "System32" / "StartupScripts"
            scripts_dir.mkdir(exist_ok=True)
            
            # 方案1：使用PowerShell隐藏窗口
            ps_hidden = scripts_dir / "hide_cmd_powershell.ps1"
            ps_content = '''# PowerShell脚本：隐藏命令提示符窗口
Add-Type -Name User32 -Namespace Win32Api -PassThru -MemberDefinition @"
[DllImport("user32.dll")]
[return: MarshalAs(UnmanagedType.Bool)]
public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
"@

$process = Start-Process -FilePath "cmd.exe" -WindowStyle Hidden -PassThru
[Win32Api.User32]::ShowWindow($process.MainWindowHandle, 0)
'''
            ps_hidden.write_text(ps_content)
            
            # 方案2：使用VBScript隐藏窗口
            vbs_hidden = scripts_dir / "hide_cmd_vbs.vbs"
            vbs_content = '''' VBScript：隐藏命令提示符窗口
Set objShell = CreateObject("WScript.Shell")
objShell.Run "cmd.exe", 0, False
'''
            vbs_hidden.write_text(vbs_content)
            
            # 方案3：使用批处理 + PowerShell组合
            hybrid_hidden = scripts_dir / "hide_cmd_hybrid.bat"
            hybrid_content = """@echo off
rem 混合方案：使用批处理 + PowerShell隐藏窗口
powershell -WindowStyle Hidden -Command "& {Start-Process cmd.exe -WindowStyle Hidden}"
"""
            hybrid_hidden.write_text(hybrid_content)
            
            # 方案4：使用Windows API隐藏窗口
            api_hidden = scripts_dir / "hide_cmd_api.bat"
            api_content = """@echo off
rem 使用Windows API隐藏窗口
powershell -Command "& {$sig = '[DllImport(\\"user32.dll\\")]public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);'; $type = Add-Type -MemberDefinition $sig -Name 'Win32' -Namespace API -PassThru; $proc = Start-Process cmd.exe -PassThru; [API.Win32]::ShowWindow($proc.MainWindowHandle, 0);}"
"""
            api_hidden.write_text(api_content)
            
            # 方案5：创建系统服务隐藏启动
            service_hidden = scripts_dir / "hide_cmd_service.bat"
            service_content = """@echo off
rem 使用系统服务方式隐藏启动
sc create WinPECmd binPath= "cmd.exe" type= own start= auto
sc start WinPECmd
sc delete WinPECmd
"""
            service_hidden.write_text(service_content)
            
            # 创建启动脚本选择器
            script_selector = scripts_dir / "startup_selector.bat"
            selector_content = """@echo off
rem 启动脚本选择器
rem 根据系统环境选择最佳的隐藏方案

rem 检查PowerShell是否可用
powershell -Command "Exit" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo 使用PowerShell隐藏方案
    call "%~dp0hide_cmd_powershell.ps1"
    goto :end
)

rem 检查VBScript是否可用
cscript //Nologo //E:vbscript "%~dp0hide_cmd_vbs.vbs" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo 使用VBScript隐藏方案
    cscript //Nologo "%~dp0hide_cmd_vbs.vbs"
    goto :end
)

rem 使用混合方案
echo 使用混合隐藏方案
call "%~dp0hide_cmd_hybrid.bat"

:end
echo 启动脚本执行完成
"""
            script_selector.write_text(selector_content)
            
            logger.info("✅ 高级启动脚本创建完成")
            return True, "高级启动脚本创建完成"

        except Exception as e:
            error_msg = f"创建高级启动脚本失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def configure_registry_settings(self, mount_dir: Path) -> Tuple[bool, str]:
        """配置注册表设置以隐藏cmd.exe窗口"""
        try:
            logger.info("配置注册表设置...")
            
            # 创建注册表配置文件
            registry_dir = mount_dir / "Windows" / "System32" / "config"
            if not registry_dir.exists():
                registry_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建软件注册表配置
            software_reg = registry_dir / "SOFTWARE_hidecmd.reg"
            reg_content = """Windows Registry Editor Version 5.00

[HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon]
"Shell"="explorer.exe"

[HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System]
"HideFastUserSwitching"=dword:00000001
"DisableTaskMgr"=dword:00000000

[HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced]
"HideFileExt"=dword:00000000
"ShowSuperHidden"=dword:00000001

[HKEY_CURRENT_USER\\Console]
"WindowPosition"=dword:00040004
"WindowSize"=dword:00190050
"ScreenBufferSize"=dword:012c0050
"WindowAlpha"=dword:00000000
"""
            software_reg.write_text(reg_content)
            
            # 创建系统注册表配置
            system_reg = registry_dir / "SYSTEM_hidecmd.reg"
            system_content = """Windows Registry Editor Version 5.00

[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Windows]
"NoPopupsOnBoot"=dword:00000001
"ErrorMode"=dword:00000002

[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment]
"ComSpec"="%SystemRoot%\\System32\\cmd.exe"

[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\EventLog\\Application]
"MaxSize"=dword:00080000
"""
            system_reg.write_text(system_content)
            
            logger.info("✅ 注册表配置完成")
            return True, "注册表配置完成"

        except Exception as e:
            error_msg = f"配置注册表设置失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _get_language_name(self, language_code: str) -> str:
        """获取语言名称"""
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
                "ru-RU": "Русский"
            }
            
            return language_mapping.get(language_code, language_code)
            
        except Exception as e:
            logger.error(f"获取语言名称失败: {str(e)}")
            return language_code
    
    def create_startup_configuration_file(self, mount_dir: Path, desktop_type: str) -> Tuple[bool, str]:
        """创建启动配置文件"""
        try:
            logger.info("创建启动配置文件...")
            
            config_dir = mount_dir / "Windows" / "System32" / "config"
            config_dir.mkdir(exist_ok=True)
            
            startup_config = {
                "desktop_type": desktop_type,
                "hide_cmd_window": True,
                "startup_delay": 3,
                "fallback_to_cmd": True,
                "debug_mode": False,
                "language": self.config.get("winpe.language", "zh-CN"),
                "created_at": "2025-10-26",
                "version": "1.0"
            }
            
            config_file = config_dir / "startup_config.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(startup_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ 启动配置文件创建完成: {config_file}")
            return True, f"启动配置文件创建完成: {desktop_type}"

        except Exception as e:
            error_msg = f"创建启动配置文件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
