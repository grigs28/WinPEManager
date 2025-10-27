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
            logger.info("🔧 开始配置WinXShell启动设置...")
            from utils.logger import log_build_step, log_system_event

            # 获取语言配置
            language_code = self.config.get("winpe.language", "zh-CN")
            language_name = self._get_language_name(language_code)
            log_build_step("WinXShell配置", f"语言设置: {language_name} ({language_code})")
            
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
    
    rem 启动WinXShell（基于研究的最优参数组合）
    echo 使用参数: -winpe -desktop -silent -jcfg
    echo 这将完全隐藏cmd.exe窗口并启动桌面环境

    rem 优先使用标准WinXShell.exe
    if exist "WinXShell.exe" (
        start "" /B "WinXShell.exe" -winpe -desktop -silent -jcfg="X:\\WinXShell\\WinXShell.jcfg"
    ) else if exist "WinXShell_x64.exe" (
        start "" /B "WinXShell_x64.exe" -winpe -desktop -silent -jcfg="X:\\WinXShell\\WinXShell.jcfg"
    ) else (
        echo 错误: 未找到WinXShell可执行文件
        exit
    )
    
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

            # 创建WinXShell专用的InitWinXShell.ini（基于现有WIM工作配置）
            log_build_step("PEConfig目录", "创建PEConfig/Run目录结构")
            peconfig_run_dir = mount_dir / "Windows" / "System32" / "PEConfig" / "Run"
            peconfig_run_dir.mkdir(parents=True, exist_ok=True)

            log_build_step("InitWinXShell.ini", "创建WinXShell启动配置文件")
            init_winxshell_ini = peconfig_run_dir / "InitWinXShell.ini"
            init_content = f"""EXEC !"%ProgramFiles%\\WinXShell\\WinXShell.exe" -regist -daemon
EXEC !"%ProgramFiles%\\WinXShell\\WinXShell.exe" -winpe -desktop -silent -jcfg="%ProgramFiles%\\WinXShell\\WinXShell.jcfg"
"""
            init_winxshell_ini.write_text(init_content)
            logger.info("📝 InitWinXShell.ini 配置已写入")

            # 创建RunShell.cmd - 模拟现有WinPE的启动脚本
            runshell_cmd = peconfig_run_dir / "RunShell.cmd"
            runshell_content = """@echo off
rem WinXShell启动脚本
rem 基于现有WinPE的工作模式

title WinXShell Startup
echo Starting WinXShell...

rem 设置环境变量
set USERPROFILE=X:\\Users\\Default
set APPDATA=X:\\Users\\Default\\AppData\\Roaming
set LOCALAPPDATA=X:\\Users\\Default\\AppData\\Local

rem 尝试启动WinXShell
if exist "%ProgramFiles%\\WinXShell\\WinXShell.exe" (
    echo Found WinXShell at Program Files path
    "%ProgramFiles%\\WinXShell\\WinXShell.exe" -regist -daemon
    timeout /t 2 /nobreak >nul
    "%ProgramFiles%\\WinXShell\\WinXShell.exe" -winpe -desktop -silent -jcfg="%ProgramFiles%\\WinXShell\\WinXShell.jcfg"
)

rem 检查是否启动成功
timeout /t 3 /nobreak >nul
tasklist | findstr /i "winxshell.exe" >nul
if %ERRORLEVEL% EQU 0 (
    echo WinXShell started successfully
) else (
    echo WinXShell failed to start
)

rem 退出命令提示符
exit
"""
            runshell_cmd.write_text(runshell_content)

            # 创建简化版的Start.cmd - 直接调用RunShell.cmd
            start_cmd = peconfig_run_dir / "Start.cmd"
            start_content = """@echo off
call "%~dp0\\RunShell.cmd"
exit
"""
            start_cmd.write_text(start_content)

            # 创建WinXShell专用启动脚本（使用VBS隐藏窗口）
            hidden_winxshell_vbs = mount_dir / "Windows" / "System32" / "hidden_winxshell.vbs"
            vbs_content = f'''Option Explicit
Dim objShell, objFSO, strWinXShellPath

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 检查WinXShell路径
strWinXShellPath = "%ProgramFiles%\\WinXShell\\WinXShell.exe"
If Not objFSO.FileExists(objShell.ExpandEnvironmentStrings(strWinXShellPath)) Then
    strWinXShellPath = "X:\\\\WinXShell\\\\WinXShell.exe"
    If Not objFSO.FileExists(strWinXShellPath) Then
        WScript.Quit
    End If
End If

' 使用最优参数启动WinXShell（完全隐藏cmd）
objShell.Run chr(34) & objShell.ExpandEnvironmentStrings(strWinXShellPath) & chr(34) & " -winpe -desktop -silent -jcfg", 0, False

' 等待启动
WScript.Sleep 2000

WScript.Quit
'''
            hidden_winxshell_vbs.write_text(vbs_content)
            
            # 创建完整的PEConfig调用链（基于现有WinPE工作模式）
            peconfig_dir = mount_dir / "Windows" / "System32" / "PEConfig"
            peconfig_dir.mkdir(parents=True, exist_ok=True)

            # 创建基于真实发现的Run.cmd脚本
            log_build_step("Run.cmd", "创建PEConfig主启动脚本")
            run_cmd = peconfig_dir / "Run.cmd"
            run_cmd_content = """@echo off

if exist "%~dp0%1\\*.ini" (
  for /f %%i in ('dir /b "%~dp0%1\\*.ini"') do (
    echo LOAD "%1\\%%i"
    start X:\\Windows\\System32\\pecmd.exe LOAD "%~dp0%1\\%%i"
  )
)

if exist "%~dp0%1\\*.exe" (
  for /f %%i in ('dir /b "%~dp0%1\\*.exe"') do (
    echo run "%1\\%%i"
    start X:\\Windows\\System32\\pecmd.exe EXEC !"%~dp0%1\\%%i"
  )
)

if exist "%~dp0%1\\*.cmd" (
  for /f %%i in ('dir /b "%~dp0%1\\*.cmd"') do (
    echo run "%1\\%%i"
    start X:\\Windows\\System32\\pecmd.exe EXEC !cmd /c "%~dp0%1\\%%i"
  )
)

if exist "%~dp0%1\\*.bat" (
  for /f %%i in ('dir /b "%~dp0%1\\*.bat"') do (
    echo run "%1\\%%i"
    start X:\\Windows\\System32\\pecmd.exe EXEC !cmd /c "%~dp0%1\\%%i"
  )
)
"""
            run_cmd.write_text(run_cmd_content)
            logger.info("📝 Run.cmd 启动脚本已写入")

            # 不再需要复杂的中间脚本，直接使用pecmd.exe处理

            # 创建WinXShell专用的winpeshl.ini（基于真实发现的工作模式）
            log_build_step("winpeshl.ini", "创建WinPE启动配置文件")
            winpeshl_ini = mount_dir / "Windows" / "System32" / "winpeshl.ini"
            winpeshl_content = """[LaunchApps]
%SystemRoot%\\System32\\wpeinit.exe
%SystemRoot%\\System32\\cmd.exe /c "%SystemRoot%\\System32\\PEConfig\\Run.cmd Run"
"""
            winpeshl_ini.write_text(winpeshl_content)
            logger.info("📝 winpeshl.ini 启动配置已写入")
            
            # 创建WinXShell配置文件（基于研究的jcfg格式）
            winxshell_config_dir = mount_dir / "Program Files" / "WinXShell"
            winxshell_config_dir.mkdir(parents=True, exist_ok=True)

            # 复制WinXShell程序文件（如果存在）
            log_build_step("WinXShell程序", "复制WinXShell程序文件")
            winxshell_source = Path("D:/APP/WinPEManager/Desktop/WinXShell")
            if winxshell_source.exists():
                import shutil
                copied_files = []
                for exe_file in winxshell_source.glob("*.exe"):
                    shutil.copy2(exe_file, winxshell_config_dir / exe_file.name)
                    copied_files.append(exe_file.name)
                    logger.info(f"📦 复制程序文件: {exe_file.name}")

                # 复制配置文件
                jcfg_source = winxshell_source / "WinXShell.jcfg"
                if jcfg_source.exists():
                    shutil.copy2(jcfg_source, winxshell_config_dir / "WinXShell.jcfg")
                    logger.info("📦 复制配置文件: WinXShell.jcfg")

                # 复制所有支持文件
                for other_file in winxshell_source.glob("*"):
                    if other_file.is_file() and other_file.suffix.lower() in ['.lua', '.dll', '.ini']:
                        shutil.copy2(other_file, winxshell_config_dir / other_file.name)
                        logger.info(f"📦 复制支持文件: {other_file.name}")

                log_build_step("文件复制", f"共复制 {len(copied_files)} 个程序文件")
            else:
                log_build_step("WinXShell程序", "⚠️ 未找到本地WinXShell文件，将使用默认配置", "warning")
                logger.warning("⚠️ 未找到本地WinXShell文件目录")

            # 创建优化的WinXShell.jcfg配置文件
            winxshell_config = winxshell_config_dir / "WinXShell.jcfg"
            config_content = f"""{{
  "JS_README": {{
    "can_be_omitted_section": true,
    "description": [
      "WinPE专用WinXShell配置文件",
      "基于WinXShell 5.0文档研究优化",
      "语言设置: {language_name} ({language_code})"
    ]
  }},
  "JS_DAEMON": {{
    "screen_brightness": 100,
    "handle_CAPS_double": false,
    "disable_showdesktop": false
  }},
  "JS_DESKTOP": {{
    "bkcolor": [199, 237, 204],
    "::WP_MODE": 0,
    "::WP": "",
    "iconsize": 32,
    "3rd_open_arguments": "\\"%s\\"",
    "cascademenu": {{
      "#WinXNew": "Directory\\\\Background\\\\shell\\\\WinXNew"
    }}
  }},
  "JS_THEMES": {{
    "dark": {{
      "taskbar": {{
        "bkcolor": [38, 38, 38],
        "bkmode": "transparent",
        "transparency": 64,
        "task_line_color": [238, 238, 238],
        "textcolor": "0xffffff"
      }}
    }}
  }},
  "JS_TASKBAR": {{
    "visible": true,
    "smallicon": false,
    "thumbnail": true,
    "task_close_button": true,
    "no_task_title": false,
    "userebar": false,
    "theme": "dark",
    "height": 40
  }},
  "::STARTMENU": {{
    "start_pushed_bkcolor": [0, 100, 180],
    "start_icon": "theme",
    "notopitems": false,
    "noprograms": false,
    "nosettings": false,
    "nobrowse": false,
    "noconnections": false,
    "nofind": false,
    "norun": false,
    "nologoff": false,
    "norestart": false,
    "noshutdown": false,
    "noterm": false,
    "commands": {{
      "reboot": {{
        "command": "Wpeutil.exe",
        "parameters": "Reboot"
      }},
      "shutdown": {{
        "command": "Wpeutil.exe",
        "parameters": "Shutdown"
      }}
    }}
  }},
  "::QL": {{
    "maxiconsinrow": 20,
    "hide_showdesktop": false,
    "hide_fileexplorer": false,
    "hide_fixedsep": false,
    "hide_usericons": false,
    "folder": "Microsoft\\\\Internet Explorer\\\\Quick Launch\\\\User Pinned\\\\TaskBar"
  }},
  "JS_NOTIFYAREA": {{
    "hide_toggle_button": false,
    "hide_showdesktop_button": false
  }},
  "JS_NOTIFYCLOCK": {{
    "visible": true
  }},
  "JS_JENV": {{
    "LANG": "{language_code}",
    "LANGUAGE": "{language_code}",
    "LC_ALL": "{language_code}",
    "USERPROFILE": "X:\\\\Users\\\\Default",
    "APPDATA": "X:\\\\Users\\\\Default\\\\AppData\\\\Roaming",
    "LOCALAPPDATA": "X:\\\\Users\\\\Default\\\\AppData\\\\Local"
  }}
}}
"""
            winxshell_config.write_text(config_content)
            logger.info("📝 WinXShell.jcfg 配置文件已生成")

            # 配置完成总结
            log_build_step("配置完成", "WinXShell启动配置已全部完成")
            log_system_event("WinXShell配置", f"桌面环境: WinXShell, 语言: {language_name}", "info")
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
