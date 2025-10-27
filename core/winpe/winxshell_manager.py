#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinXShell管理器
提供WinXShell的调用、配置和管理功能
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger("WinPEManager")


class WinXShellManager:
    """WinXShell管理器类"""

    def __init__(self, config_manager, adk_manager):
        """初始化WinXShell管理器

        Args:
            config_manager: 配置管理器
            adk_manager: ADK管理器
        """
        self.config = config_manager
        self.adk = adk_manager

    def get_winxshell_path(self, build_path: Path) -> Optional[Path]:
        """获取WinXShell程序路径

        Args:
            build_path: 构建路径

        Returns:
            Path: WinXShell程序路径，如果不存在则返回None
        """
        try:
            # 查找WinXShell程序
            program_files = build_path / "media" / "Program Files" / "WinXShell"

            # 按优先级查找可执行文件
            exe_files = [
                "WinXShell_x64.exe",
                "WinXShell_x86.exe",
                "WinXShellC_x64.exe",
                "WinXShellC_x86.exe"
            ]

            for exe_file in exe_files:
                exe_path = program_files / exe_file
                if exe_path.exists():
                    return exe_path

            logger.warning(f"未找到WinXShell可执行文件: {program_files}")
            return None

        except Exception as e:
            logger.error(f"获取WinXShell路径失败: {str(e)}")
            return None

    def check_winxshell_status(self, build_path: Path) -> Tuple[bool, str]:
        """检查WinXShell运行状态

        Args:
            build_path: 构建路径

        Returns:
            Tuple[bool, str]: (是否运行, 状态信息)
        """
        try:
            winxshell_path = self.get_winxshell_path(build_path)
            if not winxshell_path:
                return False, "WinXShell程序不存在"

            # 检查WinXShell进程是否运行
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq WinXShell.exe'],
                                   capture_output=True, text=True, timeout=10)

            if 'WinXShell.exe' in result.stdout:
                return True, "WinXShell正在运行"
            else:
                return False, "WinXShell未运行"

        except Exception as e:
            logger.error(f"检查WinXShell状态失败: {str(e)}")
            return False, f"检查失败: {str(e)}"

    def launch_winxshell(self, build_path: Path, mode: str = "desktop") -> Tuple[bool, str]:
        """启动WinXShell

        Args:
            build_path: 构建路径
            mode: 启动模式 (desktop/winpe/daemon)

        Returns:
            Tuple[bool, str]: (启动成功, 消息)
        """
        try:
            winxshell_path = self.get_winxshell_path(build_path)
            if not winxshell_path:
                return False, "WinXShell程序不存在"

            # 构建启动命令
            cmd_args = [str(winxshell_path)]

            if mode == "desktop":
                cmd_args.extend(["-winpe", "-desktop", "-silent"])
            elif mode == "daemon":
                cmd_args.extend(["-regist", "-daemon"])
            elif mode == "winpe":
                cmd_args.extend(["-winpe", "-silent"])

            # 添加配置文件参数
            jcfg_path = build_path / "media" / "Program Files" / "WinXShell" / "WinXShell.jcfg"
            if jcfg_path.exists():
                cmd_args.extend(["-jcfg", f'"{jcfg_path}"'])

            logger.info(f"启动WinXShell: {' '.join(cmd_args)}")

            # 启动进程
            process = subprocess.Popen(cmd_args,
                                  cwd=build_path,
                                  shell=False)

            # 等待一下检查是否启动成功
            time.sleep(2)

            if process.poll() is None:
                success, status = self.check_winxshell_status(build_path)
                if success:
                    return True, f"WinXShell已启动，模式: {mode}"
                else:
                    return False, f"WinXShell启动失败: {status}"
            else:
                return False, f"WinXShell进程立即退出"

        except Exception as e:
            logger.error(f"启动WinXShell失败: {str(e)}")
            return False, f"启动失败: {str(e)}"

    def exit_winxshell(self, build_path: Path, method: str = "quit") -> Tuple[bool, str]:
        """退出或隐藏WinXShell

        Args:
            build_path: 构建路径
            method: 退出方法 (quit/exit/restart/minimize)

        Returns:
            Tuple[bool, str]: (操作成功, 消息)
        """
        try:
            winxshell_path = self.get_winxshell_path(build_path)
            if not winxshell_path:
                return False, "WinXShell程序不存在"

            # 构建退出命令
            cmd_args = [str(winxshell_path)]

            if method == "quit":
                cmd_args.append("-quit")
                action = "退出WinXShell"
            elif method == "exit":
                cmd_args.append("-exit")
                action = "退出WinXShell并重启"
            elif method == "minimize":
                cmd_args.append("-minimize")
                action = "最小化WinXShell"
            elif method == "restart":
                cmd_args.append("-restart")
                action = "重启WinXShell"
            else:
                return False, f"不支持的退出方法: {method}"

            logger.info(f"执行WinXShell操作: {' '.join(cmd_args)}")

            # 执行命令
            result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return True, f"{action}成功"
            else:
                return False, f"{action}失败: {result.stderr}"

        except Exception as e:
            logger.error(f"WinXShell操作失败: {str(e)}")
            return False, f"操作失败: {str(e)}"

    def hide_cmd_window(self, build_path: Path) -> Tuple[bool, str]:
        """隐藏cmd窗口

        Args:
            build_path: 构建路径

        Returns:
            Tuple[bool, str]: (操作成功, 消息)
        """
        try:
            # 方法1: 通过WinXShell隐藏
            success, message = self.exit_winxshell(build_path, "hide_cmd")
            if success:
                return True, message

            # 方法2: 使用PowerShell隐藏
            ps_script = '''
            $processes = Get-Process | Where-Object {$_.ProcessName -like "cmd*"}
            foreach ($process in $processes) {
                $process.MainWindowHandle = [System.Runtime.InteropServices.Marshal]::GetDelegateForFieldPointer($process, "MainWindowHandle", $false, $false, $false)
                if ($process.MainWindowHandle) {
                    $null = [System.Runtime.InteropServices.Marshal]::GetDelegateForFieldPointer($process, "MainWindowHandle", $false, $false, $false)
                    [System.Runtime.InteropServices.Marshal]::GetInt32Value($null, [System.IntPtr]::Zero) | Out-Null
                }
            }
            '''

            try:
                result = subprocess.run(['powershell', '-Command', ps_script],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return True, "CMD窗口已隐藏"
            except:
                pass

            # 方法3: 修改窗口属性
            self._modify_cmd_properties(build_path)
            return True, "CMD属性已修改"

        except Exception as e:
            logger.error(f"隐藏cmd窗口失败: {str(e)}")
            return False, f"隐藏失败: {str(e)}"

    def _modify_cmd_properties(self, build_path: Path):
        """修改cmd窗口属性"""
        try:
            # 创建隐藏cmd的批处理文件
            peconfig_path = build_path / "media" / "Windows" / "System32" / "PEConfig"
            peconfig_path.mkdir(parents=True, exist_ok=True)

            # 创建隐藏CMD的配置
            hide_cmd_bat = peconfig_path / "HideCMD.bat"
            hide_cmd_content = '''@echo off
title WinPE Console
mode con: cols=80 lines=25
color 0a
echo CMD窗口已优化
echo 如需退出，请点击窗口关闭按钮
timeout /t 300 >nul
'''

            hide_cmd_bat.write_text(hide_cmd_content, encoding='utf-8')
            logger.info("已创建隐藏CMD配置文件")

        except Exception as e:
            logger.error(f"修改cmd属性失败: {str(e)}")

    def create_enhanced_startup_config(self, build_path: Path) -> Tuple[bool, str]:
        """创建增强的启动配置，包含退出和隐藏功能

        Args:
            build_path: 构建路径

        Returns:
            Tuple[bool, str]: (创建成功, 消息)
        """
        try:
            peconfig_path = build_path / "media" / "Windows" / "System32" / "PEConfig"
            peconfig_path.mkdir(parents=True, exist_ok=True)

            winxshell_path = self.get_winxshell_path(build_path)
            if not winxshell_path:
                return False, "WinXShell程序不存在"

            # 创建增强的启动配置
            enhanced_config = peconfig_path / "EnhancedStartup.ini"
            config_content = f'''[Settings]
WinXShellPath={winxshell_path}
AutoHideCMD=true
AutoExitOnDesktop=true
ExitMethod=quit
ShowDesktopButton=true
EnableExitHotkey=true
ExitHotkey=Ctrl+Alt+Q
MinimizeOnStartup=false

[Commands]
HideCMD="{winxshell_path}" -hide_cmd
ExitWinXShell="{winxshell_path}" -quit
RestartWinXShell="{winxshell_path}" -restart
ShowDesktop="{winxshell_path}" -show_desktop

[Hotkeys]
Ctrl+Alt+H=hide_cmd
Ctrl+Alt+Q=quit
Ctrl+Alt+R=restart
Ctrl+Alt+M=minimize
F11=toggle_desktop
'''

            enhanced_config.write_text(config_content, encoding='utf-8')

            logger.info("增强启动配置已创建")
            return True, "增强启动配置创建成功"

        except Exception as e:
            logger.error(f"创建增强启动配置失败: {str(e)}")
            return False, f"创建失败: {str(e)}"

    def get_winxshell_info(self, build_path: Path) -> dict:
        """获取WinXShell信息

        Args:
            build_path: 构建路径

        Returns:
            dict: WinXShell信息
        """
        try:
            winxshell_path = self.get_winxshell_path(build_path)
            is_running, status = self.check_winxshell_status(build_path)
            jcfg_path = build_path / "media" / "Program Files" / "WinXShell" / "WinXShell.jcfg"

            info = {
                "winxshell_path": str(winxshell_path) if winxshell_path else None,
                "is_running": is_running,
                "status": status,
                "jcfg_exists": jcfg_path.exists(),
                "jcfg_path": str(jcfg_path),
                "program_files": str(build_path / "media" / "Program Files" / "WinXShell"),
                "mount_path": str(build_path / "mount")
            }

            return info

        except Exception as e:
            logger.error(f"获取WinXShell信息失败: {str(e)}")
            return {"error": str(e)}