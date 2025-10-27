#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
copype模式WinXShell集成模块
为copype构建模式提供WinXShell集成功能
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

try:
    from utils.logger import log_build_step, log_system_event, log_command
    ENHANCED_LOGGING_AVAILABLE = True
except ImportError:
    ENHANCED_LOGGING_AVAILABLE = False

logger = logging.getLogger("WinPEManager")


class CopypeWinXShellIntegrator:
    """copype模式WinXShell集成器"""

    def __init__(self, config_manager, adk_manager):
        self.config = config_manager
        self.adk = adk_manager

    def integrate_winxshell_to_copype_after_makewinpe(self, current_build_path: Path) -> Tuple[bool, str]:
        """在MakeWinPEMedia执行后集成WinXShell到WIM镜像

        Args:
            current_build_path: 当前构建路径

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not current_build_path or not current_build_path.exists():
                return False, "构建路径不存在"

            # 检查是否需要集成WinXShell
            desktop_type = self.config.get("winpe.desktop_type", "disabled")
            if desktop_type != "winxshell":
                logger.info("桌面类型不是WinXShell，跳过集成")
                return True, "跳过WinXShell集成"

            logger.info("🔧 开始为copype模式集成WinXShell到WIM镜像...")

            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("WinXShell集成", "开始copype模式WIM镜像集成")
                log_system_event("WinXShell集成", "开始WIM镜像集成", "info")

            # 1. 检查源文件
            success, message = self._check_winxshell_source()
            if not success:
                return False, message

            # 2. 挂载boot.wim并集成WinXShell
            success, message = self._integrate_to_boot_wim(current_build_path)
            if not success:
                return False, message

            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("WinXShell集成", "copype模式WIM镜像集成完成")
                log_system_event("WinXShell集成", "WIM镜像集成完成", "info")

            logger.info("✅ copype模式WinXShell WIM镜像集成完成")
            return True, "copype模式WinXShell WIM镜像集成完成"

        except Exception as e:
            error_msg = f"copype模式WinXShell WIM镜像集成失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("WinXShell集成", f"集成失败: {error_msg}", "error")
            return False, error_msg

    def _check_winxshell_source(self) -> Tuple[bool, str]:
        """检查WinXShell源文件"""
        try:
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("检查源文件", "验证WinXShell源文件")

            winxshell_source = Path("D:/APP/WinPEManager/Desktop/WinXShell")
            if not winxshell_source.exists():
                error_msg = "WinXShell源目录不存在"
                logger.warning(f"⚠️ {error_msg}: {winxshell_source}")
                return False, error_msg

            # 检查关键文件
            required_files = [
                "WinXShell_x64.exe",
                "WinXShell.jcfg",
                "wxsStub.dll"
            ]

            missing_files = []
            for file_name in required_files:
                file_path = winxshell_source / file_name
                if not file_path.exists():
                    missing_files.append(file_name)

            if missing_files:
                error_msg = f"缺少关键文件: {', '.join(missing_files)}"
                logger.error(f"❌ {error_msg}")
                return False, error_msg

            logger.info("✅ WinXShell源文件检查通过")
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("检查源文件", "WinXShell源文件验证通过")

            return True, "WinXShell源文件检查通过"

        except Exception as e:
            error_msg = f"检查WinXShell源文件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _integrate_to_media_directory(self, current_build_path: Path) -> Tuple[bool, str]:
        """集成WinXShell到media目录"""
        try:
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("集成到media", "复制WinXShell文件到media目录")

            media_path = current_build_path / "media"
            if not media_path.exists():
                return False, "media目录不存在"

            # 创建WinXShell目录结构
            winxshell_target = media_path / "Program Files" / "WinXShell"
            winxshell_target.mkdir(parents=True, exist_ok=True)

            winxshell_source = Path("D:/APP/WinPEManager/Desktop/WinXShell")
            copied_files = []

            # 复制可执行文件
            exe_files = [
                "WinXShell_x64.exe",
                "WinXShell_x86.exe",
                "WinXShellC_x64.exe",
                "WinXShellC_x86.exe"
            ]

            for exe_file in exe_files:
                source_file = winxshell_source / exe_file
                if source_file.exists():
                    target_file = winxshell_target / exe_file
                    shutil.copy2(source_file, target_file)
                    copied_files.append(exe_file)
                    logger.info(f"📦 复制可执行文件: {exe_file}")

            # 复制DLL文件
            dll_files = [
                "wxsStub.dll",
                "wxsStub32.dll"
            ]

            for dll_file in dll_files:
                source_file = winxshell_source / dll_file
                if source_file.exists():
                    target_file = winxshell_target / dll_file
                    shutil.copy2(source_file, target_file)
                    copied_files.append(dll_file)
                    logger.info(f"📦 复制DLL文件: {dll_file}")

            # 复制配置文件
            config_files = [
                "WinXShell.jcfg",
                "WinXShell.lua",
                "WinXShell.zh-CN.jcfg"
            ]

            for config_file in config_files:
                source_file = winxshell_source / config_file
                if source_file.exists():
                    target_file = winxshell_target / config_file
                    shutil.copy2(source_file, target_file)
                    copied_files.append(config_file)
                    logger.info(f"📦 复制配置文件: {config_file}")

            # 复制其他重要文件
            other_files = [
                "History.md",
                "wallpaper.jpg"
            ]

            for other_file in other_files:
                source_file = winxshell_source / other_file
                if source_file.exists():
                    target_file = winxshell_target / other_file
                    shutil.copy2(source_file, target_file)
                    logger.info(f"📦 复制其他文件: {other_file}")

            # 复制Libs目录（如果存在）
            libs_source = winxshell_source / "Libs"
            if libs_source.exists():
                libs_target = winxshell_target / "Libs"
                shutil.copytree(libs_source, libs_target, dirs_exist_ok=True)
                logger.info("📦 复制Libs目录")

            # 复制wxsUI目录（如果存在）
            ui_source = winxshell_source / "wxsUI"
            if ui_source.exists():
                ui_target = winxshell_target / "wxsUI"
                shutil.copytree(ui_source, ui_target, dirs_exist_ok=True)
                logger.info("📦 复制wxsUI目录")

            logger.info(f"✅ WinXShell文件集成完成，共复制 {len(copied_files)} 个文件")
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("文件复制", f"WinXShell文件复制完成，共复制 {len(copied_files)} 个文件")

            return True, f"WinXShell文件集成完成，复制 {len(copied_files)} 个文件"

        except Exception as e:
            error_msg = f"集成WinXShell到media目录失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _create_startup_config(self, current_build_path: Path) -> Tuple[bool, str]:
        """创建启动配置"""
        try:
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("创建启动配置", "生成WinXShell启动配置")

            media_path = current_build_path / "media"
            system32_path = media_path / "Windows" / "System32"

            # 确保目录存在
            system32_path.mkdir(parents=True, exist_ok=True)

            # 获取语言配置
            language_code = self.config.get("winpe.language", "zh-CN")
            language_name = self._get_language_name(language_code)

            # 1. 创建winpeshl.ini
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("winpeshl.ini", "创建WinPE启动配置文件")

            winpeshl_ini = system32_path / "winpeshl.ini"
            winpeshl_content = f"""[LaunchApps]
%SystemRoot%\\System32\\wpeinit.exe
%SystemRoot%\\System32\\cmd.exe /c "%SystemRoot%\\System32\\PEConfig\\Run.cmd Run"
"""
            winpeshl_ini.write_text(winpeshl_content, encoding='utf-8')
            logger.info("📝 winpeshl.ini 已创建")

            # 2. 创建PEConfig目录结构
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("PEConfig目录", "创建PEConfig/Run目录结构")

            peconfig_path = system32_path / "PEConfig"
            peconfig_path.mkdir(exist_ok=True)

            run_path = peconfig_path / "Run"
            run_path.mkdir(exist_ok=True)

            # 3. 创建Run.cmd
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("Run.cmd", "创建PEConfig主启动脚本")

            run_cmd = peconfig_path / "Run.cmd"
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
            run_cmd.write_text(run_cmd_content, encoding='utf-8')
            logger.info("📝 Run.cmd 已创建")

            # 4. 创建InitWinXShell.ini
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("InitWinXShell.ini", "创建WinXShell启动配置文件")

            init_winxshell_ini = run_path / "InitWinXShell.ini"
            init_content = f"""EXEC !"%ProgramFiles%\\WinXShell\\WinXShell_x64.exe" -regist -daemon
EXEC !"%ProgramFiles%\\WinXShell\\WinXShell_x64.exe" -winpe -desktop -silent -jcfg="%ProgramFiles%\\WinXShell\\WinXShell.jcfg"
"""
            init_winxshell_ini.write_text(init_content, encoding='utf-8')
            logger.info("📝 InitWinXShell.ini 已创建")

            # 4. 创建退出和隐藏CMD的增强配置
            # 使用WinXShell管理器统一处理
            try:
                from .winxshell_manager import WinXShellManager
                winxshell_manager = WinXShellManager(self.config, self.adk)

                success, message = winxshell_manager.create_enhanced_startup_config(mount_dir)
                if ENHANCED_LOGGING_AVAILABLE:
                    if success:
                        log_build_step("退出配置", "WinXShell增强配置创建完成")
                    else:
                        log_build_step("退出配置", f"WinXShell增强配置创建失败: {message}")

            except ImportError:
                # 如果导入失败，跳过增强功能
                logger.warning("WinXShell管理器不可用，跳过增强配置")
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("退出配置", "跳过WinXShell增强配置")

            # 5. 优化WinXShell.jcfg配置文件
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("WinXShell.jcfg", "生成优化的WinXShell配置文件")

            winxshell_config = media_path / "Program Files" / "WinXShell" / "WinXShell.jcfg"
            config_content = f"""{{
  "JS_README": {{
    "can_be_omitted_section": true,
    "description": [
      "WinPE专用WinXShell配置文件",
      "copype模式集成",
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
            winxshell_config.write_text(config_content, encoding='utf-8')
            logger.info("📝 WinXShell.jcfg 配置已优化")

            logger.info("✅ WinXShell启动配置创建完成")
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("配置完成", "WinXShell启动配置创建完成")
                log_system_event("WinXShell配置", f"桌面环境: WinXShell, 语言: {language_name}", "info")

            # 4. 创建退出和隐藏CMD的增强配置
            # 使用WinXShell管理器处理退出和隐藏功能
            try:
                from .winxshell_manager import WinXShellManager
                winxshell_manager = WinXShellManager(self.config, self.adk)

                success, message = winxshell_manager.create_enhanced_startup_config(mount_dir)
                if ENHANCED_LOGGING_AVAILABLE:
                    if success:
                        log_build_step("退出配置", "WinXShell增强配置创建完成")
                    else:
                        log_build_step("退出配置", f"WinXShell增强配置创建失败: {message}")

            except ImportError:
                # 如果导入失败，跳过增强功能
                logger.warning("WinXShell管理器不可用，跳过增强配置")
                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("退出配置", "跳过WinXShell增强配置")

        except Exception as e:
            error_msg = f"创建WinXShell启动配置失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _integrate_to_boot_wim(self, current_build_path: Path) -> Tuple[bool, str]:
        """集成WinXShell到boot.wim镜像中"""
        try:
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("挂载WIM", "开始挂载boot.wim镜像")

            # 导入挂载管理器
            from core.unified_manager import UnifiedWIMManager
            mount_manager = UnifiedWIMManager(self.config, self.adk)

            boot_wim_path = current_build_path / "media" / "sources" / "boot.wim"
            mount_dir = current_build_path / "temp_wim_mount"

            # 挂载boot.wim
            logger.info("📂 挂载boot.wim镜像...")
            success, message = mount_manager.mount_wim(boot_wim_path)
            if not success:
                return False, f"挂载boot.wim失败: {message}"

            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("挂载WIM", "boot.wim镜像挂载成功")

            try:
                # 在WIM镜像中集成WinXShell
                success, message = self._integrate_winxshell_to_mounted_wim(mount_dir)
                if not success:
                    return False, message

                # 提交更改并卸载
                logger.info("💾 提交WIM镜像更改...")
                success, message = mount_manager.unmount_wim(boot_wim_path, commit=True)
                if not success:
                    return False, f"卸载boot.wim失败: {message}"

                if ENHANCED_LOGGING_AVAILABLE:
                    log_build_step("提交WIM", "boot.wim镜像更改已提交")

                logger.info("✅ WinXShell已成功集成到boot.wim镜像中")
                return True, "WinXShell已成功集成到boot.wim镜像中"

            finally:
                # 确保清理挂载目录
                if mount_dir.exists():
                    import shutil
                    try:
                        shutil.rmtree(mount_dir, ignore_errors=True)
                    except:
                        pass

        except Exception as e:
            error_msg = f"集成WinXShell到boot.wim失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _integrate_winxshell_to_mounted_wim(self, mount_dir: Path) -> Tuple[bool, str]:
        """将WinXShell集成到已挂载的WIM镜像中"""
        try:
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("集成到WIM", "开始复制WinXShell文件到WIM镜像")

            # 创建WIM镜像中的WinXShell目录
            winxshell_target = mount_dir / "Windows" / "System32" / "PEConfig" / "Run"
            winxshell_program_target = mount_dir / "Program Files" / "WinXShell"

            winxshell_target.mkdir(parents=True, exist_ok=True)
            winxshell_program_target.mkdir(parents=True, exist_ok=True)

            # 复制WinXShell程序文件
            winxshell_source = Path("D:/APP/WinPEManager/Desktop/WinXShell")
            copied_files = []

            # 复制可执行文件到Program Files
            exe_files = [
                "WinXShell_x64.exe",
                "WinXShell_x86.exe"
            ]

            for exe_file in exe_files:
                source_file = winxshell_source / exe_file
                if source_file.exists():
                    target_file = winxshell_program_target / exe_file
                    shutil.copy2(source_file, target_file)
                    copied_files.append(exe_file)
                    logger.info(f"📦 复制到WIM: {exe_file}")

            # 复制DLL文件
            dll_files = ["wxsStub.dll", "wxsStub32.dll"]
            for dll_file in dll_files:
                source_file = winxshell_source / dll_file
                if source_file.exists():
                    target_file = winxshell_program_target / dll_file
                    shutil.copy2(source_file, target_file)
                    copied_files.append(dll_file)
                    logger.info(f"📦 复制到WIM: {dll_file}")

            # 复制配置文件
            config_files = ["WinXShell.jcfg", "WinXShell.lua"]
            for config_file in config_files:
                source_file = winxshell_source / config_file
                if source_file.exists():
                    target_file = winxshell_program_target / config_file
                    shutil.copy2(source_file, target_file)
                    copied_files.append(config_file)
                    logger.info(f"📦 复制到WIM: {config_file}")

            # 创建启动配置文件
            success, message = self._create_wim_startup_config(mount_dir)
            if not success:
                return False, message

            logger.info(f"✅ WinXShell文件已复制到WIM镜像，共复制 {len(copied_files)} 个文件")
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("文件复制到WIM", f"WinXShell文件复制完成，共复制 {len(copied_files)} 个文件")

            return True, f"WinXShell文件已复制到WIM镜像，复制 {len(copied_files)} 个文件"

        except Exception as e:
            error_msg = f"复制WinXShell文件到WIM镜像失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _create_wim_startup_config(self, mount_dir: Path) -> Tuple[bool, str]:
        """在WIM镜像中创建启动配置"""
        try:
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("WIM启动配置", "创建WIM镜像中的启动配置")

            system32_path = mount_dir / "Windows" / "System32"

            # 1. 创建winpeshl.ini
            winpeshl_ini = system32_path / "winpeshl.ini"
            winpeshl_content = """[LaunchApps]
%SystemRoot%\\System32\\wpeinit.exe
%SystemRoot%\\System32\\cmd.exe /c "%SystemRoot%\\System32\\PEConfig\\Run.cmd Run"
"""
            winpeshl_ini.write_text(winpeshl_content, encoding='utf-8')
            logger.info("📝 WIM中创建: winpeshl.ini")

            # 2. 创建PEConfig/Run目录结构
            peconfig_path = system32_path / "PEConfig"
            run_path = peconfig_path / "Run"
            run_path.mkdir(parents=True, exist_ok=True)

            # 3. 创建Run.cmd
            run_cmd = peconfig_path / "Run.cmd"
            run_cmd_content = """@echo off

if exist "%~dp0%1\\*.ini" (
  for /f %%i in ('dir /b "%~dp0%1\\*.ini"') do (
    echo LOAD "%1\\%%i"
    start X:\\Windows\\System32\\pecmd.exe LOAD "%~dp0%1\\%%i"
  )
)
"""
            run_cmd.write_text(run_cmd_content, encoding='utf-8')
            logger.info("📝 WIM中创建: Run.cmd")

            # 4. 创建InitWinXShell.ini
            init_winxshell_ini = run_path / "InitWinXShell.ini"
            init_content = """EXEC !"%ProgramFiles%\\WinXShell\\WinXShell_x64.exe" -regist -daemon
EXEC !"%ProgramFiles%\\WinXShell\\WinXShell_x64.exe" -winpe -desktop -silent -jcfg="%ProgramFiles%\\WinXShell\\WinXShell.jcfg"
"""
            init_winxshell_ini.write_text(init_content, encoding='utf-8')
            logger.info("📝 WIM中创建: InitWinXShell.ini")

            logger.info("✅ WIM镜像启动配置创建完成")
            if ENHANCED_LOGGING_AVAILABLE:
                log_build_step("WIM配置完成", "WIM镜像启动配置创建完成")

            return True, "WIM镜像启动配置创建完成"

        except Exception as e:
            error_msg = f"创建WIM启动配置失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _get_language_name(self, language_code: str) -> str:
        """获取语言名称"""
        language_map = {
            "zh-CN": "中文",
            "en-US": "English",
            "ja-JP": "日本語",
            "ko-KR": "한국어",
            "fr-FR": "Français",
            "de-DE": "Deutsch",
            "es-ES": "Español",
            "ru-RU": "Русский"
        }
        return language_map.get(language_code, language_code)

    