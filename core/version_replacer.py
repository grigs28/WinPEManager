#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinPE版本替换模块
实现WinPE版本的完整替换功能，包括组件检测、迁移和版本更新
"""

import os
import shutil
import subprocess
import stat
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

from utils.logger import get_logger, log_command, log_build_step, log_system_event


class WIMVersionDetector:
    """WIM版本检测器"""

    def __init__(self, adk_manager):
        self.adk_manager = adk_manager
        self.logger = get_logger("WIMVersionDetector")

    def detect_wim_version(self, wim_file: Path) -> Dict[str, Any]:
        """
        检测WIM文件版本信息

        Args:
            wim_file: WIM文件路径

        Returns:
            版本信息字典
        """
        version_info = {
            "file_path": str(wim_file),
            "file_name": wim_file.name,
            "file_size": wim_file.stat().st_size if wim_file.exists() else 0,
            "version": "Unknown",
            "architecture": "Unknown",
            "os_family": "Unknown",
            "build_number": "Unknown",
            "creation_time": "",
            "dism_info": {}
        }

        if not wim_file.exists():
            return version_info

        # 获取文件创建时间
        creation_time = datetime.fromtimestamp(wim_file.stat().st_ctime)
        version_info["creation_time"] = creation_time.strftime("%Y-%m-%d %H:%M:%S")

        # 方法1：使用DISM获取详细信息
        try:
            dism_info = self._get_dism_image_info(wim_file)
            version_info["dism_info"] = dism_info

            # 解析版本信息
            if "Version" in str(dism_info):
                version_info["version"] = self._extract_version_from_dism(dism_info)
            if "Architecture" in str(dism_info):
                version_info["architecture"] = self._extract_arch_from_dism(dism_info)

        except Exception as e:
            self.logger.warning(f"DISM版本检测失败: {str(e)}")

        # 方法2：基于文件命名模式识别
        file_name_upper = wim_file.name.upper()
        if "WIN11" in file_name_upper:
            version_info["os_family"] = "Windows 11"
        elif "WIN10" in file_name_upper:
            version_info["os_family"] = "Windows 10"
        elif "WIN8" in file_name_upper or "WIN2012" in file_name_upper:
            version_info["os_family"] = "Windows 8/2012"
        elif "WIN7" in file_name_upper or "WIN2008" in file_name_upper:
            version_info["os_family"] = "Windows 7/2008"

        # 方法3：基于路径推断
        path_parts = str(wim_file).upper().split(os.sep)
        for part in path_parts:
            if "WIN11" in part:
                version_info["os_family"] = "Windows 11"
                break
            elif "WIN10" in part:
                version_info["os_family"] = "Windows 10"
                break

        return version_info

    def _get_dism_image_info(self, wim_file: Path) -> Dict:
        """使用DISM获取镜像信息"""
        args = [
            "/Get-ImageInfo",
            f"/ImageFile:{wim_file}"
        ]

        success, stdout, stderr = self.adk_manager.run_dism_command(args)

        if success:
            return {"stdout": stdout, "stderr": stderr, "success": True}
        else:
            return {"stdout": stdout, "stderr": stderr, "success": False}

    def _extract_version_from_dism(self, dism_info: Dict) -> str:
        """从DISM输出中提取版本信息"""
        stdout = dism_info.get("stdout", "")
        for line in stdout.split('\n'):
            if 'Version' in line and ':' in line:
                return line.split(':')[1].strip()
        return "Unknown"

    def _extract_arch_from_dism(self, dism_info: Dict) -> str:
        """从DISM输出中提取架构信息"""
        stdout = dism_info.get("stdout", "")
        for line in stdout.split('\n'):
            if 'Architecture' in line and ':' in line:
                arch = line.split(':')[1].strip()
                if "x64" in arch or "amd64" in arch:
                    return "x64"
                elif "x86" in arch:
                    return "x86"
                elif "arm64" in arch:
                    return "ARM64"
        return "Unknown"


class ComponentAnalyzer:
    """组件分析器"""

    def __init__(self, adk_manager=None):
        self.logger = get_logger("ComponentAnalyzer")
        self.adk_manager = adk_manager

    def analyze_wim_components(self, mount_path: Path) -> Dict[str, Any]:
        """
        分析WIM组件结构

        Args:
            mount_path: 挂载路径

        Returns:
            组件分析结果
        """
        analysis = {
            "mount_path": str(mount_path),
            "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "basic_info": self._analyze_basic_info(mount_path),
            "core_files": self._analyze_core_files(mount_path),
            "custom_components": self._analyze_custom_components(mount_path),
            "startup_scripts": self._analyze_startup_scripts(mount_path),
            "drivers": self._analyze_drivers(mount_path),
            "desktop_environment": self._analyze_desktop_environment(mount_path),
            "networking": self._analyze_networking(mount_path),
            "packages": self._analyze_packages(mount_path),
            "external_programs": self._analyze_external_programs(mount_path),
            "dism_packages": self._analyze_dism_packages(mount_path) if self.adk_manager else {},
            "integrity_check": self._check_integrity(mount_path)
        }

        return analysis

    def _analyze_basic_info(self, mount_path: Path) -> Dict:
        """分析基本信息"""
        basic_info = {
            "windows_dir_exists": (mount_path / "Windows").exists(),
            "system32_dir_exists": (mount_path / "Windows" / "System32").exists(),
            "total_size": self._calculate_directory_size(mount_path),
        }

        # 计算文件和目录统计
        try:
            all_items = list(mount_path.rglob("*"))
            basic_info["file_count"] = len([item for item in all_items if item.is_file()])
            basic_info["directory_count"] = len([item for item in all_items if item.is_dir()])
        except Exception as e:
            self.logger.warning(f"计算文件统计失败: {str(e)}")
            basic_info["file_count"] = 0
            basic_info["directory_count"] = 0

        return basic_info

    def _analyze_core_files(self, mount_path: Path) -> Dict:
        """分析核心文件"""
        system32 = mount_path / "Windows" / "System32"
        core_files = {
            "winpe.wim": {"exists": False, "size": 0, "path": ""},
            "winpeshl.exe": {"exists": False, "size": 0, "path": ""},
            "wpeinit.exe": {"exists": False, "size": 0, "path": ""},
            "wpeutil.exe": {"exists": False, "size": 0, "path": ""},
            "winload.exe": {"exists": False, "size": 0, "path": ""},
            "bootmgr": {"exists": False, "size": 0, "path": ""},
            "setup.exe": {"exists": False, "size": 0, "path": ""}
        }

        for file_name in core_files:
            file_path = system32 / file_name
            if not file_path.exists():
                # 尝试在根目录查找
                file_path = mount_path / file_name

            if file_path.exists():
                core_files[file_name] = {
                    "exists": True,
                    "size": file_path.stat().st_size,
                    "path": str(file_path),
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                }

        return core_files

    def _analyze_custom_components(self, mount_path: Path) -> Dict:
        """分析自定义组件"""
        custom_components = {
            "peconfig": {"exists": False, "files": []},
            "scripts": {"exists": False, "files": []},
            "programs": {"exists": False, "files": []},
            "tools": {"exists": False, "files": []},
            "wallpapers": {"exists": False, "files": []}
        }

        system32 = mount_path / "Windows" / "System32"

        # 检查PEConfig
        peconfig_dir = system32 / "PEConfig"
        if peconfig_dir.exists():
            custom_components["peconfig"]["exists"] = True
            custom_components["peconfig"]["files"] = [str(f.relative_to(mount_path)) for f in peconfig_dir.rglob("*") if f.is_file()]

        # 检查Scripts目录
        scripts_dir = mount_path / "Scripts"
        if scripts_dir.exists():
            custom_components["scripts"]["exists"] = True
            custom_components["scripts"]["files"] = [str(f.relative_to(mount_path)) for f in scripts_dir.rglob("*") if f.is_file()]

        # 检查Programs目录
        programs_dir = system32 / "Programs"
        if programs_dir.exists():
            custom_components["programs"]["exists"] = True
            custom_components["programs"]["files"] = [str(f.relative_to(mount_path)) for f in programs_dir.rglob("*") if f.is_file()]

        # 检查Tools目录
        tools_dir = mount_path / "Tools"
        if tools_dir.exists():
            custom_components["tools"]["exists"] = True
            custom_components["tools"]["files"] = [str(f.relative_to(mount_path)) for f in tools_dir.rglob("*") if f.is_file()]

        # 检查自定义壁纸
        wallpaper_dir = mount_path / "Windows" / "Web" / "Wallpaper" / "Custom"
        if wallpaper_dir.exists():
            custom_components["wallpapers"]["exists"] = True
            custom_components["wallpapers"]["files"] = [str(f.relative_to(mount_path)) for f in wallpaper_dir.rglob("*") if f.is_file()]

        return custom_components

    def _analyze_startup_scripts(self, mount_path: Path) -> Dict:
        """分析启动脚本"""
        system32 = mount_path / "Windows" / "System32"

        startup_scripts = {
            "winpeshl_ini": {"exists": False, "content": "", "commands": []},
            "startnet_cmd": {"exists": False, "content": "", "commands": []},
            "custom_startup": {"exists": False, "files": []}
        }

        # 检查winpeshl.ini
        winpeshl_ini = system32 / "winpeshl.ini"
        if winpeshl_ini.exists():
            try:
                content = winpeshl_ini.read_text(encoding='utf-8', errors='ignore')
                startup_scripts["winpeshl_ini"] = {
                    "exists": True,
                    "content": content,
                    "commands": self._parse_winpeshl_commands(content)
                }
            except Exception as e:
                self.logger.warning(f"读取winpeshl.ini失败: {str(e)}")

        # 检查startnet.cmd
        startnet_cmd = system32 / "startnet.cmd"
        if startnet_cmd.exists():
            try:
                content = startnet_cmd.read_text(encoding='utf-8', errors='ignore')
                startup_scripts["startnet_cmd"] = {
                    "exists": True,
                    "content": content,
                    "commands": self._parse_batch_commands(content)
                }
            except Exception as e:
                self.logger.warning(f"读取startnet.cmd失败: {str(e)}")

        # 检查自定义启动脚本
        cmd_files = list(system32.glob("*.cmd"))
        bat_files = list(system32.glob("*.bat"))
        for script_file in cmd_files + bat_files:
            if script_file.name not in ["startnet.cmd"]:
                if not startup_scripts["custom_startup"]["exists"]:
                    startup_scripts["custom_startup"]["exists"] = True

                startup_scripts["custom_startup"]["files"].append({
                    "name": script_file.name,
                    "path": str(script_file.relative_to(mount_path)),
                    "size": script_file.stat().st_size
                })

        return startup_scripts

    def _analyze_drivers(self, mount_path: Path) -> Dict:
        """分析驱动程序"""
        drivers_info = {
            "drivers_dir_exists": False,
            "total_drivers": 0,
            "inf_files": [],
            "driver_categories": {},
            "storage_drivers": [],
            "network_drivers": [],
            "display_drivers": []
        }

        drivers_dir = mount_path / "Drivers"
        if not drivers_dir.exists():
            return drivers_info

        drivers_info["drivers_dir_exists"] = True

        # 统计INF文件
        inf_files = list(drivers_dir.rglob("*.inf"))
        drivers_info["total_drivers"] = len(inf_files)
        drivers_info["inf_files"] = [str(f.relative_to(mount_path)) for f in inf_files]

        # 分类驱动程序
        for inf_file in inf_files:
            try:
                category = self._classify_driver(inf_file)
                rel_path = str(inf_file.relative_to(mount_path))

                if category not in drivers_info["driver_categories"]:
                    drivers_info["driver_categories"][category] = []

                drivers_info["driver_categories"][category].append(rel_path)

                # 具体分类
                if "storage" in category.lower() or "scsi" in category.lower():
                    drivers_info["storage_drivers"].append(rel_path)
                elif "network" in category.lower() or "net" in category.lower():
                    drivers_info["network_drivers"].append(rel_path)
                elif "display" in category.lower() or "video" in category.lower():
                    drivers_info["display_drivers"].append(rel_path)

            except Exception as e:
                self.logger.warning(f"分类驱动失败 {inf_file}: {str(e)}")

        return drivers_info

    def _analyze_desktop_environment(self, mount_path: Path) -> Dict:
        """分析桌面环境"""
        desktop_env = {
            "shell_type": "Unknown",
            "shell_files": [],
            "custom_shell": {"exists": False, "name": "", "path": ""},
            "explorer": {"exists": False, "path": ""},
            "winxshell": {"exists": False, "path": ""},
            "cairo_shell": {"exists": False, "path": ""},
            "custom_desktop": {"exists": False, "files": []}
        }

        system32 = mount_path / "Windows" / "System32"
        programs_dir = system32 / "Programs"

        # 检查explorer.exe
        explorer_path = system32 / "explorer.exe"
        if explorer_path.exists():
            desktop_env["explorer"] = {"exists": True, "path": str(explorer_path.relative_to(mount_path))}

        # 检查WinXShell
        winxshell_files = list(system32.glob("WinXShell*")) + list(programs_dir.glob("WinXShell*"))
        if winxshell_files:
            desktop_env["winxshell"] = {
                "exists": True,
                "path": str(winxshell_files[0].relative_to(mount_path))
            }
            desktop_env["shell_type"] = "WinXShell"

        # 检查Cairo Shell
        cairo_files = list(system32.glob("Cairo*")) + list(programs_dir.glob("Cairo*"))
        if cairo_files:
            desktop_env["cairo_shell"] = {
                "exists": True,
                "path": str(cairo_files[0].relative_to(mount_path))
            }
            desktop_env["shell_type"] = "Cairo Shell"

        # 检查自定义桌面程序
        if programs_dir.exists():
            custom_files = []
            for file_path in programs_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.exe', '.dll']:
                    custom_files.append({
                        "name": file_path.name,
                        "path": str(file_path.relative_to(mount_path)),
                        "size": file_path.stat().st_size
                    })

            if custom_files:
                desktop_env["custom_desktop"]["exists"] = True
                desktop_env["custom_desktop"]["files"] = custom_files

        # 确定Shell类型
        if desktop_env["explorer"]["exists"] and not desktop_env["winxshell"]["exists"]:
            desktop_env["shell_type"] = "Explorer"
        elif desktop_env["winxshell"]["exists"]:
            desktop_env["shell_type"] = "WinXShell"
        elif desktop_env["cairo_shell"]["exists"]:
            desktop_env["shell_type"] = "Cairo Shell"

        return desktop_env

    def _analyze_networking(self, mount_path: Path) -> Dict:
        """分析网络组件"""
        networking = {
            "network_components": {},
            "protocols": [],
            "services": [],
            "tools": []
        }

        system32 = mount_path / "Windows" / "System32"

        # 检查网络组件
        network_files = [
            "netcfg.exe", "netsh.exe", "net.exe", "ipconfig.exe",
            "ping.exe", "tracert.exe", "nslookup.exe", "ftp.exe",
            "telnet.exe", "ssh.exe", "wlan.exe"
        ]

        for net_file in network_files:
            file_path = system32 / net_file
            networking["network_components"][net_file] = {
                "exists": file_path.exists(),
                "path": str(file_path.relative_to(mount_path)) if file_path.exists() else ""
            }

        # 检查网络服务
        network_services = ["dot3svc", "netlogon", "lanmanserver", "lanmanworkstation"]
        for service in network_services:
            service_path = system32 / f"{service}.dll"
            if service_path.exists():
                networking["services"].append(service)

        return networking

    def _analyze_packages(self, mount_path: Path) -> Dict:
        """分析已安装的包"""
        packages = {
            "total_packages": 0,
            "language_packs": [],
            "feature_packs": [],
            "driver_packs": [],
            "optional_packages": []
        }

        # 这里可以通过DISM命令获取已安装的包信息
        # 由于需要ADK支持，这里提供基础框架

        return packages

    def _check_integrity(self, mount_path: Path) -> Dict:
        """检查完整性"""
        integrity = {
            "windows_directory": (mount_path / "Windows").exists(),
            "system32_directory": (mount_path / "Windows" / "System32").exists(),
            "boot_files": self._check_boot_files(mount_path),
            "registry_files": self._check_registry_files(mount_path),
            "critical_dlls": self._check_critical_dlls(mount_path),
            "overall_status": "Unknown"
        }

        # 计算整体状态
        checks = [
            integrity["windows_directory"],
            integrity["system32_directory"],
            integrity["boot_files"]["all_present"],
            integrity["registry_files"]["all_present"],
            integrity["critical_dlls"]["all_present"]
        ]

        if all(checks):
            integrity["overall_status"] = "Good"
        elif any(checks):
            integrity["overall_status"] = "Warning"
        else:
            integrity["overall_status"] = "Critical"

        return integrity

    def _check_boot_files(self, mount_path: Path) -> Dict:
        """检查启动文件"""
        boot_files = {
            "bootmgr": (mount_path / "bootmgr").exists(),
            "boot_dir": (mount_path / "boot").exists(),
            "efi_dir": (mount_path / "EFI").exists(),
            "sources_dir": (mount_path / "sources").exists(),
            "all_present": False
        }

        required_files = [
            boot_files["bootmgr"],
            boot_files["boot_dir"],
            boot_files["sources_dir"]
        ]

        boot_files["all_present"] = all(required_files)

        return boot_files

    def _check_registry_files(self, mount_path: Path) -> Dict:
        """检查注册表文件"""
        config_dir = mount_path / "Windows" / "System32" / "config"

        registry_files = {
            "sam": (config_dir / "sam").exists(),
            "system": (config_dir / "system").exists(),
            "software": (config_dir / "software").exists(),
            "default": (config_dir / "default").exists(),
            "security": (config_dir / "security").exists(),
            "all_present": False
        }

        required_files = [
            registry_files["sam"],
            registry_files["system"],
            registry_files["software"],
            registry_files["default"],
            registry_files["security"]
        ]

        registry_files["all_present"] = all(required_files)

        return registry_files

    def _check_critical_dlls(self, mount_path: Path) -> Dict:
        """检查关键DLL"""
        system32 = mount_path / "Windows" / "System32"

        critical_dlls = {
            "kernel32.dll": (system32 / "kernel32.dll").exists(),
            "user32.dll": (system32 / "user32.dll").exists(),
            "gdi32.dll": (system32 / "gdi32.dll").exists(),
            "ntdll.dll": (system32 / "ntdll.dll").exists(),
            "advapi32.dll": (system32 / "advapi32.dll").exists(),
            "shell32.dll": (system32 / "shell32.dll").exists(),
            "all_present": False
        }

        required_dlls = list(critical_dlls.values())[:-1]  # 排除all_present
        critical_dlls["all_present"] = all(required_dlls)

        return critical_dlls

    def _calculate_directory_size(self, path: Path) -> int:
        """计算目录大小"""
        total_size = 0
        try:
            for item in path.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
        except Exception as e:
            self.logger.warning(f"计算目录大小失败: {str(e)}")

        return total_size

    def _analyze_external_programs(self, mount_path: Path) -> Dict[str, Any]:
        """分析外部程序和启动机制"""
        external_programs = {
            "winxshell": self._analyze_winxshell(mount_path),
            "cairo_shell": self._analyze_cairo_shell(mount_path),
            "shell_f5": self._analyze_shell_f5(mount_path),
            "third_party_tools": self._analyze_third_party_tools(mount_path),
            "startup_mechanisms": self._analyze_startup_mechanisms(mount_path),
            "configuration_files": self._analyze_configuration_files(mount_path)
        }

        return external_programs

    def _analyze_winxshell(self, mount_path: Path) -> Dict:
        """分析WinXShell"""
        winxshell_info = {
            "installed": False,
            "version": "Unknown",
            "executable_path": "",
            "config_files": [],
            "ui_themes": [],
            "lua_scripts": [],
            "vb_scripts": [],
            "startup_config": {},
            "features": {
                "taskbar": False,
                "start_menu": False,
                "desktop": False,
                "quick_launch": False,
                "notification_area": False,
                "clock_area": False
            },
            "configuration_details": {}
        }

        # 检查WinXShell安装
        program_files = mount_path / "Program Files"
        winxshell_dir = program_files / "WinXShell"
        system32 = mount_path / "Windows" / "System32"

        if winxshell_dir.exists():
            winxshell_info["installed"] = True

            # 查找可执行文件
            winxshell_exe = winxshell_dir / "WinXShell.exe"
            if winxshell_exe.exists():
                winxshell_info["executable_path"] = str(winxshell_exe.relative_to(mount_path))
                winxshell_info["version"] = self._get_file_version(winxshell_exe)

            # 分析配置文件
            jcfg_file = winxshell_dir / "WinXShell.jcfg"
            if jcfg_file.exists():
                winxshell_info["config_files"].append(str(jcfg_file.relative_to(mount_path)))
                winxshell_info["configuration_details"] = self._parse_winxshell_config(jcfg_file)

            # 分析Lua脚本
            lua_file = winxshell_dir / "WinXShell.lua"
            if lua_file.exists():
                winxshell_info["lua_scripts"].append(str(lua_file.relative_to(mount_path)))

            # 分析VB脚本
            for vb_file in winxshell_dir.glob("*.vbs"):
                winxshell_info["vb_scripts"].append({
                    "name": vb_file.name,
                    "path": str(vb_file.relative_to(mount_path)),
                    "size": vb_file.stat().st_size
                })

            # 分析UI主题
            wxs_ui_dir = winxshell_dir / "wxsUI"
            if wxs_ui_dir.exists():
                for theme_dir in wxs_ui_dir.iterdir():
                    if theme_dir.is_dir():
                        winxshell_info["ui_themes"].append({
                            "name": theme_dir.name,
                            "path": str(theme_dir.relative_to(mount_path)),
                            "files": len([f for f in theme_dir.rglob("*") if f.is_file()])
                        })

            # 分析功能特性
            config = winxshell_info["configuration_details"]
            if "::任务栏" in config:
                winxshell_info["features"]["taskbar"] = True
            if "::开始菜单" in config:
                winxshell_info["features"]["start_menu"] = True
            if "::桌面" in config:
                winxshell_info["features"]["desktop"] = True
            if "::快速启动栏" in config:
                winxshell_info["features"]["quick_launch"] = True
            if "::托盘区域" in config:
                winxshell_info["features"]["notification_area"] = True
            if "::时钟栏" in config:
                winxshell_info["features"]["clock_area"] = True

        return winxshell_info

    def _analyze_cairo_shell(self, mount_path: Path) -> Dict:
        """分析Cairo Shell"""
        cairo_info = {
            "installed": False,
            "version": "Unknown",
            "executable_path": "",
            "config_files": [],
            "themes": [],
            "plugins": []
        }

        # 检查Cairo Shell安装
        desktop_dir = mount_path / "Desktop"
        program_files = mount_path / "Program Files"
        system32 = mount_path / "Windows" / "System32"
        cairo_dir = None

        # 在常见位置查找Cairo Shell
        possible_locations = [
            desktop_dir / "Cairo Shell",
            program_files / "Cairo Shell",
            program_files / "CairoDesktop",
            system32 / "CairoShell"
        ]

        for location in possible_locations:
            if location.exists():
                cairo_dir = location
                break

        if cairo_dir:
            cairo_info["installed"] = True

            # 查找可执行文件
            cairo_exe = cairo_dir / "CairoDesktop.exe"
            if not cairo_exe.exists():
                cairo_exe = cairo_dir / "CairoShell.exe"

            if cairo_exe.exists():
                cairo_info["executable_path"] = str(cairo_exe.relative_to(mount_path))
                cairo_info["version"] = self._get_file_version(cairo_exe)

            # 分析配置和主题
            for config_file in cairo_dir.glob("*.cfg") + cairo_dir.glob("*.xml") + cairo_dir.glob("*.conf"):
                cairo_info["config_files"].append({
                    "name": config_file.name,
                    "path": str(config_file.relative_to(mount_path)),
                    "size": config_file.stat().st_size
                })

            # 查找插件
            plugins_dir = cairo_dir / "Plugins"
            if plugins_dir.exists():
                for plugin_file in plugins_dir.rglob("*.dll"):
                    cairo_info["plugins"].append({
                        "name": plugin_file.name,
                        "path": str(plugin_file.relative_to(mount_path)),
                        "size": plugin_file.stat().st_size
                    })

        return cairo_info

    def _analyze_shell_f5(self, mount_path: Path) -> Dict:
        """分析ShellF5"""
        shellf5_info = {
            "installed": False,
            "executable_files": [],
            "config_files": []
        }

        # 查找ShellF5文件
        program_files = mount_path / "Program Files"
        shellf5_dir = program_files / "ShellF5"

        if shellf5_dir.exists():
            shellf5_info["installed"] = True

            # 查找可执行文件
            for exe_file in shellf5_dir.glob("*.exe"):
                shellf5_info["executable_files"].append({
                    "name": exe_file.name,
                    "path": str(exe_file.relative_to(mount_path)),
                    "size": exe_file.stat().st_size
                })

            # 查找配置文件
            ini_files = list(shellf5_dir.glob("*.ini"))
            cfg_files = list(shellf5_dir.glob("*.cfg"))
            for config_file in ini_files + cfg_files:
                shellf5_info["config_files"].append({
                    "name": config_file.name,
                    "path": str(config_file.relative_to(mount_path)),
                    "size": config_file.stat().st_size
                })

        return shellf5_info

    def _analyze_third_party_tools(self, mount_path: Path) -> Dict:
        """分析第三方工具"""
        tools_info = {
            "file_managers": [],
            "browsers": [],
            "system_tools": [],
            "security_tools": [],
            "media_tools": [],
            "development_tools": []
        }

        program_files = mount_path / "Program Files"
        system32 = mount_path / "Windows" / "System32"

        # 分析文件管理器
        file_managers = ["explorer++.exe", "TotalCommander.exe", "DirectoryOpus.exe", "DoubleCommander.exe"]
        for fm in file_managers:
            fm_path = system32 / fm
            if not fm_path.exists():
                fm_path = program_files / fm
            if fm_path.exists():
                tools_info["file_managers"].append({
                    "name": fm,
                    "path": str(fm_path.relative_to(mount_path)),
                    "size": fm_path.stat().st_size
                })

        # 分析系统工具
        system_tools = ["procexp.exe", "autoruns.exe", "ProcessHacker.exe", "TaskManager.exe"]
        for st in system_tools:
            st_path = system32 / st
            if not st_path.exists():
                st_path = program_files / "SysinternalsSuite" / st
            if st_path.exists():
                tools_info["system_tools"].append({
                    "name": st,
                    "path": str(st_path.relative_to(mount_path)),
                    "size": st_path.stat().st_size
                })

        # 分析其他工具
        other_tools = ["7z.exe", "WinRAR.exe", "Notepad++.exe", "VLC.exe"]
        for ot in other_tools:
            ot_path = program_files / ot
            if ot_path.exists():
                # 根据文件名分类
                if "7z" in ot.lower() or "winrar" in ot.lower():
                    tools_info["system_tools"].append({
                        "name": ot,
                        "path": str(ot_path.relative_to(mount_path)),
                        "size": ot_path.stat().st_size
                    })
                elif "notepad" in ot.lower():
                    tools_info["development_tools"].append({
                        "name": ot,
                        "path": str(ot_path.relative_to(mount_path)),
                        "size": ot_path.stat().st_size
                    })

        return tools_info

    def _analyze_startup_mechanisms(self, mount_path: Path) -> Dict:
        """分析启动机制"""
        startup_info = {
            "winpeshl_config": {"exists": False, "commands": []},
            "startnet_config": {"exists": False, "commands": []},
            "peconfig_system": {"exists": False, "init_files": []},
            "registry_startup": {"exists": False, "entries": []},
            "autorun_locations": {},
            "service_configurations": {}
        }

        system32 = mount_path / "Windows" / "System32"

        # 分析winpeshl.ini
        winpeshl_ini = system32 / "winpeshl.ini"
        if winpeshl_ini.exists():
            try:
                content = winpeshl_ini.read_text(encoding='utf-8', errors='ignore')
                startup_info["winpeshl_config"]["exists"] = True
                startup_info["winpeshl_config"]["commands"] = self._parse_winpeshl_commands(content)
            except Exception as e:
                self.logger.warning(f"读取winpeshl.ini失败: {str(e)}")

        # 分析startnet.cmd
        startnet_cmd = system32 / "startnet.cmd"
        if startnet_cmd.exists():
            try:
                content = startnet_cmd.read_text(encoding='utf-8', errors='ignore')
                startup_info["startnet_config"]["exists"] = True
                startup_info["startnet_config"]["commands"] = self._parse_batch_commands(content)
            except Exception as e:
                self.logger.warning(f"读取startnet.cmd失败: {str(e)}")

        # 分析PEConfig启动系统
        peconfig_dir = system32 / "PEConfig"
        if peconfig_dir.exists():
            startup_info["peconfig_system"]["exists"] = True

            run_dir = peconfig_dir / "Run"
            if run_dir.exists():
                for init_file in run_dir.glob("*.ini"):
                    try:
                        content = init_file.read_text(encoding='utf-8', errors='ignore')
                        startup_info["peconfig_system"]["init_files"].append({
                            "name": init_file.name,
                            "path": str(init_file.relative_to(mount_path)),
                            "content": content,
                            "commands": self._parse_peconfig_commands(content)
                        })
                    except Exception as e:
                        self.logger.warning(f"读取PEConfig文件失败 {init_file}: {str(e)}")

        return startup_info

    def _analyze_configuration_files(self, mount_path: Path) -> Dict:
        """分析配置文件"""
        config_info = {
            "ini_files": [],
            "json_files": [],
            "xml_files": [],
            "registry_files": [],
            "lua_scripts": [],
            "batch_scripts": []
        }

        # 搜索常见配置文件
        config_patterns = [
            "*.ini", "*.json", "*.xml", "*.cfg", "*.conf",
            "*.lua", "*.reg", "*.cmd", "*.bat"
        ]

        for pattern in config_patterns:
            for config_file in mount_path.rglob(pattern):
                if config_file.is_file():
                    file_info = {
                        "name": config_file.name,
                        "path": str(config_file.relative_to(mount_path)),
                        "size": config_file.stat().st_size,
                        "modified": datetime.fromtimestamp(config_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    }

                    if config_file.suffix.lower() == '.ini':
                        config_info["ini_files"].append(file_info)
                    elif config_file.suffix.lower() == '.json':
                        config_info["json_files"].append(file_info)
                    elif config_file.suffix.lower() == '.xml':
                        config_info["xml_files"].append(file_info)
                    elif config_file.suffix.lower() == '.lua':
                        config_info["lua_scripts"].append(file_info)
                    elif config_file.suffix.lower() == '.reg':
                        config_info["registry_files"].append(file_info)
                    elif config_file.suffix.lower() in ['.cmd', '.bat']:
                        config_info["batch_scripts"].append(file_info)

        return config_info

    def _get_file_version(self, file_path: Path) -> str:
        """获取文件版本信息"""
        try:
            # 这里可以实现更复杂的版本检测逻辑
            # 简单实现：基于文件修改时间
            mtime = file_path.stat().st_mtime
            mod_time = datetime.fromtimestamp(mtime)
            return f"Unknown (修改于: {mod_time.strftime('%Y-%m-%d')})"
        except Exception:
            return "Unknown"

    def _parse_winxshell_config(self, jcfg_file: Path) -> Dict:
        """解析WinXShell配置文件"""
        try:
            content = jcfg_file.read_text(encoding='utf-8', errors='ignore')
            # 简单的JSON解析，实际应该使用更健壮的解析器
            config = {}

            # 检查关键配置项
            if "\"::主题段\"" in content:
                config["has_themes"] = True
            if "\"::任务栏\"" in content:
                config["has_taskbar"] = True
            if "\"::开始菜单\"" in content:
                config["has_start_menu"] = True
            if "\"::桌面\"" in content:
                config["has_desktop"] = True
            if "\"::第3方文件管理器\"" in content:
                config["has_file_manager"] = True

            return config
        except Exception as e:
            self.logger.warning(f"解析WinXShell配置失败: {str(e)}")
            return {}

    def _parse_peconfig_commands(self, content: str) -> List[str]:
        """解析PEConfig命令"""
        commands = []
        try:
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('EXEC') or line.startswith('CALL') or line.startswith('FIND') or line.startswith('TEAM'):
                    commands.append(line)
        except Exception as e:
            self.logger.warning(f"解析PEConfig命令失败: {str(e)}")

        return commands

    def _parse_winpeshl_commands(self, content: str) -> List[str]:
        """解析winpeshl.ini命令"""
        commands = []
        try:
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('Command') and '=' in line:
                    command = line.split('=', 1)[1].strip()
                    commands.append(command)
        except Exception as e:
            self.logger.warning(f"解析winpeshl.ini命令失败: {str(e)}")

        return commands

    def _parse_batch_commands(self, content: str) -> List[str]:
        """解析批处理命令"""
        commands = []
        try:
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('rem') and not line.startswith('@'):
                    commands.append(line)
        except Exception as e:
            self.logger.warning(f"解析批处理命令失败: {str(e)}")

        return commands

    def _analyze_dism_packages(self, mount_path: Path) -> Dict:
        """使用DISM分析已安装的包和功能"""
        if not self.adk_manager:
            return {"error": "ADK管理器未初始化"}

        dism_analysis = {
            "packages": {"installed": [], "available": []},
            "features": {"enabled": [], "disabled": [], "available": []},
            "appx_packages": [],
            "capabilities": [],
            "winpe_optional_components": {}
        }

        try:
            # 分析已安装的包
            dism_analysis["packages"] = self._get_installed_packages(mount_path)

            # 分析功能状态
            dism_analysis["features"] = self._get_feature_status(mount_path)

            # 分析WinPE可选组件
            dism_analysis["winpe_optional_components"] = self._get_winpe_optional_components(mount_path)

            # 分析Appx包（如果有）
            dism_analysis["appx_packages"] = self._get_appx_packages(mount_path)

            # 分析系统功能
            dism_analysis["capabilities"] = self._get_system_capabilities(mount_path)

        except Exception as e:
            self.logger.error(f"DISM包分析失败: {str(e)}")
            dism_analysis["error"] = str(e)

        return dism_analysis

    def _get_installed_packages(self, mount_path: Path) -> Dict:
        """获取已安装的包列表 - 基于文件系统分析"""
        packages_info = {
            "installed": [],
            "count": 0,
            "error": None
        }

        try:
            # 验证挂载路径是否存在
            if not mount_path.exists():
                error_msg = f"挂载路径不存在: {mount_path}"
                self.logger.error(error_msg)
                packages_info["error"] = error_msg
                return packages_info

            # 检查是否是有效的WinPE挂载点
            windows_dir = mount_path / "Windows"
            if not windows_dir.exists():
                error_msg = f"不是有效的WinPE挂载点，缺少Windows目录: {mount_path}"
                self.logger.error(error_msg)
                packages_info["error"] = error_msg
                return packages_info

            # 不使用DISM，直接分析文件系统
            self.logger.info(f"分析挂载目录的包信息: {mount_path}")

            # 分析WinSxS目录中的包信息
            winsxs_path = mount_path / "Windows" / "WinSxS"
            if winsxs_path.exists():
                try:
                    manifests = list(winsxs_path.glob("*.manifest"))
                    if manifests:
                        packages_info["installed"] = [
                            {
                                "identity": f"WinSxS Package {i+1}",
                                "name": manifest.stem,
                                "type": "manifest",
                                "path": str(manifest.relative_to(mount_path))
                            }
                            for i, manifest in enumerate(manifests[:100])  # 限制为前100个
                        ]
                        self.logger.info(f"通过WinSxS分析发现 {len(manifests)} 个manifest文件")
                except Exception as e:
                    self.logger.warning(f"分析WinSxS目录时出错: {str(e)}")

            # 分析 servicing 目录中的包信息
            servicing_path = mount_path / "Windows" / "servicing" / "Packages"
            if servicing_path.exists():
                try:
                    package_files = list(servicing_path.glob("*.mum"))
                    if package_files:
                        servicing_packages = [
                            {
                                "identity": f"Servicing Package {i+1}",
                                "name": mum_file.stem,
                                "type": "servicing",
                                "path": str(mum_file.relative_to(mount_path))
                            }
                            for i, mum_file in enumerate(package_files[:50])  # 限制为前50个
                        ]
                        packages_info["installed"].extend(servicing_packages)
                        self.logger.info(f"通过servicing目录发现额外的 {len(package_files)} 个包")
                except Exception as e:
                    self.logger.warning(f"分析servicing目录时出错: {str(e)}")

            packages_info["count"] = len(packages_info["installed"])
            self.logger.info(f"总共分析了 {packages_info['count']} 个包")

        except Exception as e:
            error_msg = f"获取已安装包时出错: {str(e)}"
            self.logger.error(error_msg)
            packages_info["error"] = error_msg

        return packages_info

    def _get_feature_status(self, mount_path: Path) -> Dict:
        """获取功能状态 - 基于文件系统分析"""
        features_info = {
            "enabled": [],
            "disabled": [],
            "total_count": 0,
            "error": None
        }

        try:
            # 验证挂载路径
            if not mount_path.exists():
                error_msg = f"挂载路径不存在: {mount_path}"
                self.logger.error(error_msg)
                features_info["error"] = error_msg
                return features_info

            windows_dir = mount_path / "Windows"
            if not windows_dir.exists():
                error_msg = f"不是有效的WinPE挂载点: {mount_path}"
                self.logger.error(error_msg)
                features_info["error"] = error_msg
                return features_info

            # 不使用DISM，基于文件系统分析功能状态
            self.logger.info(f"分析挂载目录的功能状态: {mount_path}")

            # 分析可选功能目录
            optional_features_path = mount_path / "Windows" / "System32" / "Optional"
            if optional_features_path.exists():
                try:
                    feature_dirs = [d for d in optional_features_path.iterdir() if d.is_dir()]
                    if feature_dirs:
                        features_info["enabled"] = [
                            {
                                "name": feature_dir.name,
                                "type": "optional_feature",
                                "path": str(feature_dir.relative_to(mount_path))
                            }
                            for feature_dir in feature_dirs
                        ]
                        self.logger.info(f"发现 {len(feature_dirs)} 个可选功能")
                except Exception as e:
                    self.logger.warning(f"分析可选功能目录时出错: {str(e)}")

            # 分析注册表功能
            registry_software_path = mount_path / "Windows" / "System32" / "config" / "SOFTWARE"
            if registry_software_path.exists():
                features_info["enabled"].append({
                    "name": "Registry System",
                    "type": "registry",
                    "path": "Windows/System32/config/SOFTWARE"
                })
                self.logger.info("发现注册表系统配置")

            # 分析PowerShell功能
            powershell_path = mount_path / "Windows" / "System32" / "WindowsPowerShell"
            if powershell_path.exists():
                features_info["enabled"].append({
                    "name": "PowerShell",
                    "type": "shell_feature",
                    "path": "Windows/System32/WindowsPowerShell"
                })
                self.logger.info("发现PowerShell功能")

            features_info["total_count"] = len(features_info["enabled"])
            self.logger.info(f"总共分析了 {features_info['total_count']} 个功能")

        except Exception as e:
            error_msg = f"获取功能状态时出错: {str(e)}"
            self.logger.error(error_msg)
            features_info["error"] = error_msg

        return features_info

    def _get_winpe_optional_components(self, mount_path: Path) -> Dict:
        """获取WinPE可选组件信息"""
        winpe_components = {
            "wmi": False,
            "powershell": False,
            "netfx": False,
            "secure_startup": False,
            "storage": False,
            "networking": False,
            "recovery": False,
            "scripting": False,
            "driver_support": False,
            "custom_components": []
        }

        # WinPE可选组件包名映射
        component_mapping = {
            "WinPE-WMI": "wmi",
            "WinPE-PowerShell": "powershell",
            "WinPE-NetFx": "netfx",
            "WinPE-SecureStartup": "secure_startup",
            "WinPE-Storage": "storage",
            "WinPE-WinReCfg": "recovery",
            "WinPE-Scripting": "scripting",
            "WinPE-Dot3Svc": "networking",
            "WinPE-HTA": "scripting",
            "WinPE-MDAC": "storage"
        }

        try:
            # 使用统一的DISM命令获取包信息
            result = self._execute_dism_command("get-packages", mount_path)

            if result["success"] and result["data"]:
                packages = result["data"]
                for package in packages:
                    package_name = package.get("identity", "") or package.get("name", "")
                    for pkg_name, component_key in component_mapping.items():
                        if pkg_name in package_name:
                            winpe_components[component_key] = True
                            break

                self.logger.info(f"WinPE组件分析完成，使用方法: {result['method_used']}")
            else:
                self.logger.warning(f"获取包信息失败: {result.get('error', 'Unknown error')}")

            # 检查自定义组件
            custom_packages = self._find_custom_packages(mount_path)
            winpe_components["custom_components"] = custom_packages

        except Exception as e:
            self.logger.error(f"获取WinPE可选组件时出错: {str(e)}")

        return winpe_components

    def _get_appx_packages(self, mount_path: Path) -> List[Dict]:
        """获取Appx包信息"""
        try:
            # 使用统一的DISM命令获取Appx包信息
            result = self._execute_dism_command("get-provisionedappxpackages", mount_path)

            if result["success"]:
                appx_packages = result["data"] if isinstance(result["data"], list) else []
                self.logger.info(f"Appx包分析完成，使用方法: {result['method_used']}")
                return appx_packages
            else:
                self.logger.warning(f"获取Appx包信息失败: {result.get('error', 'Unknown error')}")
                return []

        except Exception as e:
            self.logger.error(f"获取Appx包时出错: {str(e)}")
            return []

    def _execute_dism_command(self, command_type: str, mount_path: Path, **kwargs) -> Dict[str, Any]:
        """
        统一的DISM命令执行函数

        Args:
            command_type: DISM命令类型 (get-packages, get-features, get-capabilities, etc.)
            mount_path: 挂载路径
            **kwargs: 额外参数

        Returns:
            Dict: {"success": bool, "data": Any, "error": str, "method_used": str}
        """
        result = {
            "success": False,
            "data": None,
            "error": None,
            "method_used": "filesystem_analysis"  # 默认使用文件系统分析
        }

        try:
            # 验证挂载路径
            if not mount_path.exists():
                result["error"] = f"挂载路径不存在: {mount_path}"
                result["method_used"] = "validation_failed"
                return result

            windows_dir = mount_path / "Windows"
            if not windows_dir.exists():
                result["error"] = f"不是有效的WinPE挂载点: {mount_path}"
                result["method_used"] = "validation_failed"
                return result

            # DISM命令配置和预检查
            dism_commands = {
                "get-packages": {
                    "args": ["/Image:{}".format(str(mount_path)), "/Get-Packages"],
                    "parser": self._parse_package_list,
                    "fallback": self._get_packages_from_filesystem,
                    "precheck": self._precheck_packages_files
                },
                "get-features": {
                    "args": ["/Image:{}".format(str(mount_path)), "/Get-Features"],
                    "parser": self._parse_feature_list,
                    "fallback": self._get_features_from_filesystem,
                    "precheck": self._precheck_features_files
                },
                "get-capabilities": {
                    "args": ["/Image:{}".format(str(mount_path)), "/Get-Capabilities"],
                    "parser": self._parse_capabilities,
                    "fallback": self._get_capabilities_from_filesystem,
                    "precheck": self._precheck_capabilities_files
                },
                "get-winpe-options": {
                    "args": ["/Image:{}".format(str(mount_path)), "/Get-WinPEOptions"],
                    "parser": self._parse_winpe_options,
                    "fallback": self._get_winpe_options_from_filesystem,
                    "precheck": self._precheck_winpe_files
                },
                "get-provisionedappxpackages": {
                    "args": ["/Image:{}".format(str(mount_path)), "/Get-ProvisionedAppxPackages"],
                    "parser": self._parse_appx_packages,
                    "fallback": self._get_appx_packages_from_filesystem,
                    "precheck": self._precheck_appx_files
                }
            }

            if command_type not in dism_commands:
                result["error"] = f"不支持的DISM命令类型: {command_type}"
                result["method_used"] = "invalid_command"
                return result

            command_config = dism_commands[command_type]
            precheck_method = command_config["precheck"]
            fallback_method = command_config["fallback"]

            # 执行预检查，如果相关文件不存在则直接使用文件系统分析
            should_use_dism = precheck_method(mount_path)
            if not should_use_dism:
                self.logger.info(f"预检查发现相关文件不存在，直接使用文件系统分析: {command_type}")
                fallback_data = fallback_method(mount_path)
                result["success"] = True
                result["data"] = fallback_data
                result["method_used"] = "filesystem_analysis_precheck"
                return result

            # 尝试使用DISM命令
            args = command_config["args"]
            parser = command_config["parser"]

            self.logger.info(f"预检查通过，执行DISM命令 {command_type}: {' '.join(args)}")

            # 执行DISM命令
            success, stdout, stderr = self.adk_manager.run_dism_command(args)

            if success and stdout:
                # 解析DISM输出
                parsed_data = parser(stdout)
                result["success"] = True
                result["data"] = parsed_data
                result["method_used"] = "dism"
                self.logger.info(f"DISM命令 {command_type} 执行成功，获得 {len(parsed_data) if isinstance(parsed_data, list) else 1} 个结果")
            else:
                # DISM失败，使用文件系统分析方法
                self.logger.warning(f"DISM命令 {command_type} 失败: {stderr}")
                self.logger.info(f"切换到文件系统分析方法: {command_type}")

                fallback_data = fallback_method(mount_path)
                result["success"] = True
                result["data"] = fallback_data
                result["method_used"] = "filesystem_analysis_fallback"
                result["error"] = f"DISM失败但文件系统分析成功: {stderr}"

        except Exception as e:
            error_msg = f"执行DISM命令 {command_type} 时出错: {str(e)}"
            self.logger.error(error_msg)
            result["error"] = error_msg
            result["method_used"] = "exception"

        return result

    def _precheck_packages_files(self, mount_path: Path) -> bool:
        """检查包相关文件是否存在"""
        # 检查包相关目录
        package_paths = [
            mount_path / "Windows" / "WinSxS",
            mount_path / "Windows" / "servicing" / "Packages",
            mount_path / "Windows" / "servicing",
            mount_path / "Windows" / "inf",
            mount_path / "Windows" / "system32" / "driverstore"  # 驱动包
        ]

        # 检查是否有manifest或mum文件
        for path in package_paths:
            if path.exists():
                # 检查是否有包相关文件
                if any(path.glob("*.manifest")) or any(path.glob("*.mum")) or any(path.glob("*.inf")):
                    return True
        return False

    def _precheck_features_files(self, mount_path: Path) -> bool:
        """检查功能相关文件是否存在"""
        # 检查功能相关目录
        feature_paths = [
            mount_path / "Windows" / "System32" / "Optional",
            mount_path / "Windows" / "Microsoft.NET",  # .NET功能
            mount_path / "Windows" / "SysWOW64" / "Optional",  # 32位可选功能
            mount_path / "Windows" / "System32" / "drivers"  # 驱动功能
        ]

        for path in feature_paths:
            if path.exists() and any(path.iterdir()):
                return True

        # 检查特定功能文件
        feature_files = [
            mount_path / "Windows" / "System32" / "dot3svc.dll",      # WiFi服务
            mount_path / "Windows" / "System32" / "bitsperf.dll",     # 后台智能传输
            mount_path / "Windows" / "System32" / "dism.exe",        # DISM工具本身
            mount_path / "Windows" / "System32" / "powershell.exe"   # PowerShell
        ]

        return any(file.exists() for file in feature_files)

    def _precheck_capabilities_files(self, mount_path: Path) -> bool:
        """检查能力相关文件是否存在"""
        # 检查能力相关目录
        capability_paths = [
            mount_path / "Windows" / "System32" / "WindowsPowerShell",
            mount_path / "Windows" / "System32" / "wbem",
            mount_path / "Windows" / "Microsoft.NET",
            mount_path / "Windows" / "System32" / "slmgr.vbs",       # 许可证管理
            mount_path / "Windows" / "System32" / "cmd.exe",         # 命令行
            mount_path / "Windows" / "System32" / "regedit.exe"      # 注册表编辑器
        ]

        # 检查能力相关文件
        capability_files = [
            mount_path / "Windows" / "System32" / "dxgi.dll",        # DirectX
            mount_path / "Windows" / "System32" / "cscript.exe",     # Windows脚本
            mount_path / "Windows" / "System32" / "wscript.exe",     # Windows脚本
            mount_path / "Windows" / "System32" / "net.exe",         # 网络工具
            mount_path / "Windows" / "System32" / "ipconfig.exe"     # 网络配置
        ]

        return any(path.exists() for path in capability_paths) or any(file.exists() for file in capability_files)

    def _precheck_winpe_files(self, mount_path: Path) -> bool:
        """检查WinPE相关文件是否存在"""
        # 检查WinPE核心文件
        winpe_files = [
            mount_path / "Windows" / "System32" / "winpeshl.exe",
            mount_path / "Windows" / "System32" / "wpeinit.exe",
            mount_path / "Windows" / "System32" / "wpeutil.exe",
            mount_path / "Windows" / "System32" / "winload.exe",
            mount_path / "Windows" / "System32" / "bootmgr.exe"
        ]

        # 检查WinPE配置文件
        winpe_configs = [
            mount_path / "Windows" / "System32" / "winpeshl.ini",
            mount_path / "Windows" / "System32" / "startnet.cmd",
            mount_path / "Windows" / "System32" / "setup.exe"
        ]

        # 检查WinPE相关目录
        winpe_dirs = [
            mount_path / "Windows" / "Panther",           # Windows安装配置
            mount_path / "Windows" / "Setup",             # 安装文件
            mount_path / "sources"                        # 安装源文件
        ]

        return (any(file.exists() for file in winpe_files) or
                any(config.exists() for config in winpe_configs) or
                any(dir.exists() for dir in winpe_dirs))

    def _precheck_appx_files(self, mount_path: Path) -> bool:
        """检查Appx相关文件是否存在"""
        # 检查Appx相关目录
        appx_paths = [
            mount_path / "Windows" / "SystemApps",
            mount_path / "Program Files" / "WindowsApps",
            mount_path / "Program Files (x86)" / "WindowsApps",
            mount_path / "Windows" / "System32" / "config" / "SOFTWARE",  # 注册表中的应用信息
        ]

        # 检查传统程序目录
        traditional_program_paths = [
            mount_path / "Program Files",
            mount_path / "Program Files (x86)",
            mount_path / "Windows" / "System32" / "com" / "dllcache",  # DLL缓存
            mount_path / "Windows" / "downloaded" / "program files"     # 下载的程序
        ]

        all_program_paths = appx_paths + traditional_program_paths

        for path in all_program_paths:
            if path.exists():
                # 检查是否有可执行文件
                exe_files = list(path.glob("*.exe"))
                if exe_files:
                    return True

        # 检查特定的应用程序文件
        app_files = [
            mount_path / "Windows" / "System32" / "notepad.exe",    # 记事本
            mount_path / "Windows" / "System32" / "calc.exe",       # 计算器
            mount_path / "Windows" / "System32" / "mspaint.exe",    # 画图
            mount_path / "Windows" / "System32" / "taskmgr.exe"     # 任务管理器
        ]

        return any(file.exists() for file in app_files)

    def _get_packages_from_filesystem(self, mount_path: Path) -> List[Dict]:
        """从文件系统获取包信息"""
        packages = []

        # 分析WinSxS目录
        winsxs_path = mount_path / "Windows" / "WinSxS"
        if winsxs_path.exists():
            manifests = list(winsxs_path.glob("*.manifest"))
            packages.extend([
                {
                    "identity": f"WinSxS Package {i+1}",
                    "name": manifest.stem,
                    "type": "manifest",
                    "path": str(manifest.relative_to(mount_path))
                }
                for i, manifest in enumerate(manifests[:50])
            ])

        # 分析servicing目录
        servicing_path = mount_path / "Windows" / "servicing" / "Packages"
        if servicing_path.exists():
            package_files = list(servicing_path.glob("*.mum"))
            packages.extend([
                {
                    "identity": f"Servicing Package {i+1}",
                    "name": mum_file.stem,
                    "type": "servicing",
                    "path": str(mum_file.relative_to(mount_path))
                }
                for i, mum_file in enumerate(package_files[:25])
            ])

        return packages

    def _get_features_from_filesystem(self, mount_path: Path) -> Dict[str, List]:
        """从文件系统获取功能信息"""
        features = {"enabled": [], "disabled": []}

        # 分析可选功能目录
        optional_path = mount_path / "Windows" / "System32" / "Optional"
        if optional_path.exists():
            feature_dirs = [d for d in optional_path.iterdir() if d.is_dir()]
            features["enabled"] = [
                {
                    "name": feature_dir.name,
                    "type": "optional_feature",
                    "path": str(feature_dir.relative_to(mount_path))
                }
                for feature_dir in feature_dirs
            ]

        return features

    def _get_capabilities_from_filesystem(self, mount_path: Path) -> List[str]:
        """从文件系统获取能力信息"""
        capabilities = []

        # 检查常见的能力指示文件
        capability_indicators = {
            "PowerShell": mount_path / "Windows" / "System32" / "WindowsPowerShell",
            "WMI": mount_path / "Windows" / "System32" / "wbem",
            "NET Framework": mount_path / "Windows" / "Microsoft.NET",
            "DirectX": mount_path / "Windows" / "System32" / "dxgi.dll",
            "Windows Scripting": mount_path / "Windows" / "System32" / "cscript.exe"
        }

        for capability, path in capability_indicators.items():
            if path.exists():
                capabilities.append(capability)

        return capabilities

    def _get_winpe_options_from_filesystem(self, mount_path: Path) -> List[Dict]:
        """从文件系统获取WinPE选项信息"""
        options = []

        # 检查WinPE相关文件和目录
        winpe_files = [
            mount_path / "Windows" / "System32" / "winpeshl.exe",
            mount_path / "Windows" / "System32" / "wpeinit.exe",
            mount_path / "Windows" / "System32" / "wpeutil.exe"
        ]

        for file_path in winpe_files:
            if file_path.exists():
                options.append({
                    "name": file_path.stem,
                    "type": "winpe_component",
                    "path": str(file_path.relative_to(mount_path))
                })

        return options

    def _get_appx_packages_from_filesystem(self, mount_path: Path) -> List[Dict]:
        """从文件系统获取Appx包信息"""
        appx_packages = []

        # 分析SystemApps
        systemapps_path = mount_path / "Windows" / "SystemApps"
        if systemapps_path.exists():
            appx_dirs = [d for d in systemapps_path.iterdir() if d.is_dir() and "Microsoft.Windows" in d.name]
            for appx_dir in appx_dirs:
                appx_packages.append({
                    "name": appx_dir.name,
                    "type": "system_app",
                    "path": str(appx_dir.relative_to(mount_path))
                })

        # 分析程序文件
        for program_dir in ["Program Files", "Program Files (x86)"]:
            prog_path = mount_path / program_dir
            if prog_path.exists():
                exe_files = list(prog_path.glob("*/**/*.exe"))
                for exe_file in exe_files[:10]:
                    appx_packages.append({
                        "name": exe_file.parent.name,
                        "type": "traditional_program",
                        "path": str(exe_file.relative_to(mount_path))
                    })

        return appx_packages

    def _get_system_capabilities(self, mount_path: Path) -> List[str]:
        """获取系统能力"""
        result = self._execute_dism_command("get-capabilities", mount_path)
        if result["success"]:
            return result["data"] if isinstance(result["data"], list) else []
        return []

    def _parse_package_list(self, stdout: str) -> List[Dict]:
        """解析包列表"""
        packages = []
        lines = stdout.split('\n')

        current_package = {}
        for line in lines:
            line = line.strip()

            if line.startswith("Package Identity :"):
                if current_package:
                    packages.append(current_package)
                current_package = {"identity": line.split(":", 1)[1].strip()}
            elif " : " in line and current_package:
                key, value = line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()
                current_package[key] = value

        if current_package:
            packages.append(current_package)

        return packages

    def _parse_feature_list(self, stdout: str) -> tuple:
        """解析功能列表，返回(已启用, 已禁用)"""
        enabled = []
        disabled = []
        lines = stdout.split('\n')

        for line in lines:
            line = line.strip()
            if " : " in line:
                feature_name, status = line.split(":", 1)
                feature_name = feature_name.strip()
                status = status.strip().lower()

                if "enabled" in status:
                    enabled.append(feature_name)
                elif "disabled" in status:
                    disabled.append(feature_name)

        return enabled, disabled

    def _parse_appx_packages(self, stdout: str) -> List[Dict]:
        """解析Appx包"""
        appx_packages = []
        lines = stdout.split('\n')

        current_package = {}
        for line in lines:
            line = line.strip()

            if line.startswith("DisplayName :"):
                if current_package:
                    appx_packages.append(current_package)
                current_package = {"display_name": line.split(":", 1)[1].strip()}
            elif " : " in line and current_package:
                key, value = line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()
                current_package[key] = value

        if current_package:
            appx_packages.append(current_package)

        return appx_packages

    def _parse_capabilities(self, stdout: str) -> List[str]:
        """解析系统能力"""
        capabilities = []
        lines = stdout.split('\n')

        for line in lines:
            line = line.strip()
            if " : " in line:
                capability_name = line.split(":", 1)[0].strip()
                capabilities.append(capability_name)

        return capabilities

    def _parse_winpe_options(self, stdout: str) -> List[Dict]:
        """解析WinPE选项"""
        winpe_options = []
        lines = stdout.split('\n')

        current_option = {}
        for line in lines:
            line = line.strip()

            if line.startswith("选项 :") or line.startswith("Option :"):
                if current_option:
                    winpe_options.append(current_option)
                current_option = {"name": line.split(":", 1)[1].strip()}
            elif " : " in line and current_option:
                key, value = line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()
                current_option[key] = value

        if current_option:
            winpe_options.append(current_option)

        return winpe_options

    def _find_custom_packages(self, mount_path: Path) -> List[Dict]:
        """查找自定义包"""
        custom_packages = []

        # 在常见位置查找自定义包
        search_paths = [
            mount_path / "Packages",
            mount_path / "Windows" / "Servicing" / "Packages",
            mount_path / "Program Files" / "Custom Packages"
        ]

        for search_path in search_paths:
            if search_path.exists():
                for package_file in search_path.glob("*.cab"):
                    package_info = {
                        "name": package_file.name,
                        "path": str(package_file.relative_to(mount_path)),
                        "size": package_file.stat().st_size if package_file.exists() else 0
                    }
                    custom_packages.append(package_info)

        return custom_packages

    def analyze_mount_differences(self, source_mount: Path, target_mount: Path) -> Dict[str, Any]:
        """
        深度分析两个WIM挂载点的差异
        重点关注配置、外部程序、加载逻辑的差异

        Args:
            source_mount: 源WIM挂载路径 (0WIN11PE\mount)
            target_mount: 目标WIM挂载路径 (0WIN10OLD\mount)

        Returns:
            详细的差异分析结果
        """
        self.logger.info(f"开始分析WIM挂载点差异: {source_mount} vs {target_mount}")

        analysis = {
            "summary": {
                "source_mount": str(source_mount),
                "target_mount": str(target_mount),
                "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "version_differences": self._analyze_version_differences(source_mount, target_mount),
            "config_differences": self._analyze_config_differences(source_mount, target_mount),
            "external_program_differences": self._analyze_external_program_differences(source_mount, target_mount),
            "startup_mechanism_differences": self._analyze_startup_mechanism_differences(source_mount, target_mount),
            "driver_differences": self._analyze_driver_differences(source_mount, target_mount),
            "registry_differences": self._analyze_registry_differences(source_mount, target_mount),
            "service_differences": self._analyze_service_differences(source_mount, target_mount),
            "compatibility_issues": [],
            "migration_recommendations": []
        }

        # 分析兼容性问题
        analysis["compatibility_issues"] = self._identify_compatibility_issues(analysis)

        # 生成迁移建议
        analysis["migration_recommendations"] = self._generate_migration_recommendations(analysis)

        self.logger.info("WIM挂载点差异分析完成")
        return analysis

    def _analyze_version_differences(self, source_mount: Path, target_mount: Path) -> Dict:
        """分析版本差异"""
        source_info = self._detect_windows_version(source_mount)
        target_info = self._detect_windows_version(target_mount)

        return {
            "source": source_info,
            "target": target_info,
            "major_differences": {
                "kernel_version": source_info.get("kernel") != target_info.get("kernel"),
                "build_number": source_info.get("build") != target_info.get("build"),
                "architecture": source_info.get("arch") != target_info.get("arch")
            }
        }

    def _detect_windows_version(self, mount_path: Path) -> Dict:
        """检测Windows版本信息"""
        version_info = {
            "kernel": "Unknown",
            "build": "Unknown",
            "arch": "Unknown",
            "edition": "Unknown"
        }

        try:
            # 从ntdll.dll检测版本
            ntdll_path = mount_path / "Windows" / "System32" / "ntdll.dll"
            if ntdll_path.exists():
                import subprocess
                result = subprocess.run(
                    ['powershell', '-Command', f'(Get-Item "{ntdll_path}").VersionInfo'],
                    capture_output=True, text=True, timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0:
                    version_output = result.stdout
                    # 解析版本信息
                    lines = version_output.split('\n')
                    for line in lines:
                        if 'FileVersion' in line:
                            version_info["kernel"] = line.split(':')[-1].strip()
                        elif 'ProductVersion' in line:
                            version_info["build"] = line.split(':')[-1].strip()

            # 从注册表检测架构和版本
            reg_files = [
                mount_path / "Windows" / "System32" / "config" / "SOFTWARE",
                mount_path / "Windows" / "System32" / "config" / "SYSTEM"
            ]

            for reg_file in reg_files:
                if reg_file.exists():
                    # 简单的架构检测
                    if "x64" in str(reg_file) or "amd64" in str(reg_file):
                        version_info["arch"] = "x64"
                    elif "x86" in str(reg_file):
                        version_info["arch"] = "x86"
                    break

        except Exception as e:
            self.logger.warning(f"版本检测失败: {str(e)}")

        return version_info

    def _analyze_config_differences(self, source_mount: Path, target_mount: Path) -> Dict:
        """分析配置文件差异"""
        config_analysis = {
            "ini_files": {"source_only": [], "target_only": [], "both_modified": []},
            "cmd_files": {"source_only": [], "target_only": [], "both_modified": []},
            "bat_files": {"source_only": [], "target_only": [], "both_modified": []},
            "jcfg_files": {"source_only": [], "target_only": [], "both_modified": []},
            "lua_files": {"source_only": [], "target_only": [], "both_modified": []},
            "xml_files": {"source_only": [], "target_only": [], "both_modified": []},
            "json_files": {"source_only": [], "target_only": [], "both_modified": []},
            "conf_files": {"source_only": [], "target_only": [], "both_modified": []},
            "cfg_files": {"source_only": [], "target_only": [], "both_modified": []},
            "reg_files": {"source_only": [], "target_only": [], "both_modified": []},
            "vbs_files": {"source_only": [], "target_only": [], "both_modified": []},
            "ps1_files": {"source_only": [], "target_only": [], "both_modified": []},
            "py_files": {"source_only": [], "target_only": [], "both_modified": []},
            "registry_hives": {"source_only": [], "target_only": [], "both_modified": []},
            "critical_configs": {}
        }

        # 获取所有类型的配置文件
        source_configs = self._find_all_config_files(source_mount)
        target_configs = self._find_all_config_files(target_mount)

        # 分析每种类型的配置文件
        for file_type in config_analysis.keys():
            if file_type == "registry_hives":
                continue  # 注册表单独处理

            source_files = source_configs.get(file_type, [])
            target_files = target_configs.get(file_type, [])

            self._compare_file_lists(source_files, target_files, config_analysis[file_type], source_mount, target_mount)

        # 分析注册表配置文件
        source_regs = list((source_mount / "Windows" / "System32" / "config").glob("*"))
        target_regs = list((target_mount / "Windows" / "System32" / "config").glob("*"))

        config_analysis["registry_hives"]["source_only"] = [f.name for f in source_regs if f.name not in [t.name for t in target_regs]]
        config_analysis["registry_hives"]["target_only"] = [f.name for f in target_regs if f.name not in [s.name for s in source_regs]]

        # 分析关键配置文件
        critical_configs = [
            "winpeshl.ini", "startnet.cmd", "unattend.xml", "autounattend.xml",
            "InitWinXShell.ini", "WinXShell.jcfg", "PEConfig.ini",
            "InitDesktop.ini", "desktop.ini"
        ]

        for config in critical_configs:
            source_path = source_mount / "Windows" / "System32" / config
            target_path = target_mount / "Windows" / "System32" / config

            config_info = {
                "source_exists": source_path.exists(),
                "target_exists": target_path.exists(),
                "content_diff": None,
                "file_type": config.split('.')[-1] if '.' in config else "unknown"
            }

            if source_path.exists() and target_path.exists():
                try:
                    source_content = source_path.read_text(encoding='utf-8', errors='ignore')
                    target_content = target_path.read_text(encoding='utf-8', errors='ignore')

                    if source_content != target_content:
                        config_info["content_diff"] = self._analyze_text_differences(source_content, target_content)
                except Exception as e:
                    self.logger.warning(f"比较配置文件失败 {config}: {str(e)}")

            config_analysis["critical_configs"][config] = config_info

        return config_analysis

    def _analyze_external_program_differences(self, source_mount: Path, target_mount: Path) -> Dict:
        """分析外部程序差异"""
        program_analysis = {
            "desktop_environments": self._compare_desktop_environments(source_mount, target_mount),
            "third_party_tools": self._compare_third_party_tools(source_mount, target_mount),
            "custom_programs": self._compare_custom_programs(source_mount, target_mount),
            "shell_extensions": self._compare_shell_extensions(source_mount, target_mount)
        }

        return program_analysis

    def _compare_desktop_environments(self, source_mount: Path, target_mount: Path) -> Dict:
        """比较桌面环境"""
        desktop_comparison = {
            "source": self._detect_desktop_environment(source_mount),
            "target": self._detect_desktop_environment(target_mount),
            "differences": []
        }

        source_env = desktop_comparison["source"]
        target_env = desktop_comparison["target"]

        # 检查桌面环境差异
        if source_env["type"] != target_env["type"]:
            desktop_comparison["differences"].append(f"桌面环境类型: {source_env['type']} -> {target_env['type']}")

        # 检查WinXShell配置差异
        if source_env.get("winxshell") and target_env.get("winxshell"):
            source_winx = source_env["winxshell"]
            target_winx = target_env["winxshell"]

            if source_winx.get("config_files") != target_winx.get("config_files"):
                desktop_comparison["differences"].append("WinXShell配置文件不同")

            if source_winx.get("version") != target_winx.get("version"):
                desktop_comparison["differences"].append(f"WinXShell版本: {source_winx.get('version')} -> {target_winx.get('version')}")

        return desktop_comparison

    def _detect_desktop_environment(self, mount_path: Path) -> Dict:
        """检测桌面环境"""
        desktop_info = {
            "type": "Explorer",  # 默认值
            "winxshell": None,
            "cairo_shell": None,
            "custom_shell": None
        }

        system32 = mount_path / "Windows" / "System32"
        program_files = mount_path / "Program Files"

        # 检测WinXShell
        winxshell_paths = [
            system32 / "WinXShell.exe",
            program_files / "WinXShell" / "WinXShell.exe",
            program_files / "WinXShell.exe"
        ]

        for path in winxshell_paths:
            if path.exists():
                desktop_info["type"] = "WinXShell"
                desktop_info["winxshell"] = self._analyze_winxshell_installation(path.parent)
                break

        # 检测Cairo Shell
        cairo_paths = [
            system32 / "CairoDesktop.exe",
            system32 / "CairoShell.exe",
            program_files / "Cairo Shell" / "CairoDesktop.exe"
        ]

        for path in cairo_paths:
            if path.exists():
                desktop_info["type"] = "Cairo Shell"
                desktop_info["cairo_shell"] = self._analyze_cairo_installation(path.parent)
                break

        # 检测自定义Shell
        if (system32 / "explorer.exe").exists():
            if desktop_info["type"] == "Explorer":
                pass  # 保持默认
            else:
                desktop_info["custom_shell"] = "Explorer detected as secondary"

        return desktop_info

    def _analyze_winxshell_installation(self, winxshell_dir: Path) -> Dict:
        """分析WinXShell安装"""
        winx_info = {
            "install_path": str(winxshell_dir),
            "config_files": [],
            "version": "Unknown",
            "plugins": [],
            "themes": []
        }

        try:
            # 查找配置文件
            config_patterns = ["*.jcfg", "*.ini", "*.lua", "*.xml"]
            for pattern in config_patterns:
                for config_file in winxshell_dir.glob(pattern):
                    winx_info["config_files"].append(config_file.name)

            # 查找插件
            plugins_dir = winxshell_dir / "Plugins"
            if plugins_dir.exists():
                winx_info["plugins"] = [p.name for p in plugins_dir.glob("*.dll")]

            # 查找主题
            themes_dir = winxshell_dir / "Themes"
            if themes_dir.exists():
                winx_info["themes"] = [t.name for t in themes_dir.iterdir() if t.is_dir()]

            # 尝试获取版本
            exe_file = winxshell_dir / "WinXShell.exe"
            if exe_file.exists():
                import subprocess
                result = subprocess.run(
                    ['powershell', '-Command', f'(Get-Item "{exe_file}").VersionInfo.FileVersion'],
                    capture_output=True, text=True, timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0:
                    winx_info["version"] = result.stdout.strip()

        except Exception as e:
            self.logger.warning(f"分析WinXShell安装失败: {str(e)}")

        return winx_info

    def _analyze_cairo_installation(self, cairo_dir: Path) -> Dict:
        """分析Cairo Shell安装"""
        cairo_info = {
            "install_path": str(cairo_dir),
            "config_files": [],
            "version": "Unknown",
            "plugins": []
        }

        try:
            # 查找配置文件
            config_patterns = ["*.cfg", "*.xml", "*.conf"]
            for pattern in config_patterns:
                for config_file in cairo_dir.glob(pattern):
                    cairo_info["config_files"].append(config_file.name)

            # 查找插件
            plugins_dir = cairo_dir / "Plugins"
            if plugins_dir.exists():
                cairo_info["plugins"] = [p.name for p in plugins_dir.glob("*.dll")]

        except Exception as e:
            self.logger.warning(f"分析Cairo Shell安装失败: {str(e)}")

        return cairo_info

    def _compare_third_party_tools(self, source_mount: Path, target_mount: Path) -> Dict:
        """比较第三方工具"""
        tools_comparison = {
            "source_tools": [],
            "target_tools": [],
            "source_only": [],
            "target_only": [],
            "version_differences": []
        }

        # 查找第三方工具
        source_tools = self._find_third_party_tools(source_mount)
        target_tools = self._find_third_party_tools(target_mount)

        tools_comparison["source_tools"] = source_tools
        tools_comparison["target_tools"] = target_tools

        # 分析差异
        source_names = {tool["name"]: tool for tool in source_tools}
        target_names = {tool["name"]: tool for tool in target_tools}

        tools_comparison["source_only"] = [name for name in source_names.keys() if name not in target_names]
        tools_comparison["target_only"] = [name for name in target_names.keys() if name not in source_names]

        # 检查版本差异
        common_tools = set(source_names.keys()) & set(target_names.keys())
        for tool_name in common_tools:
            source_ver = source_names[tool_name].get("version", "Unknown")
            target_ver = target_names[tool_name].get("version", "Unknown")
            if source_ver != target_ver and source_ver != "Unknown" and target_ver != "Unknown":
                tools_comparison["version_differences"].append({
                    "name": tool_name,
                    "source_version": source_ver,
                    "target_version": target_ver
                })

        return tools_comparison

    def _find_third_party_tools(self, mount_path: Path) -> List[Dict]:
        """查找第三方工具"""
        tools = []
        search_paths = [
            mount_path / "Program Files",
            mount_path / "Program Files (x86)",
            mount_path / "Windows" / "System32",
            mount_path / "Tools"
        ]

        known_tools = {
            "7z.exe": "7-Zip",
            "procexp.exe": "Process Explorer",
            "autoruns.exe": "Autoruns",
            "ProcessHacker.exe": "Process Hacker",
            "TotalCommander.exe": "Total Commander",
            "explorer++.exe": "Explorer++",
            "Notepad++.exe": "Notepad++",
            "VLC.exe": "VLC Media Player",
            "WinRAR.exe": "WinRAR"
        }

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for tool_file in search_path.rglob("*.exe"):
                tool_name = tool_file.name.lower()

                # 检查已知工具
                display_name = known_tools.get(tool_name, tool_file.stem)

                tool_info = {
                    "name": display_name,
                    "executable": tool_file.name,
                    "path": str(tool_file.relative_to(mount_path)),
                    "size": tool_file.stat().st_size,
                    "version": "Unknown"
                }

                # 尝试获取版本信息
                try:
                    import subprocess
                    result = subprocess.run(
                        ['powershell', '-Command', f'(Get-Item "{tool_file}").VersionInfo.FileVersion'],
                        capture_output=True, text=True, timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        tool_info["version"] = result.stdout.strip()
                except:
                    pass

                tools.append(tool_info)

        return tools

    def _compare_custom_programs(self, source_mount: Path, target_mount: Path) -> Dict:
        """比较自定义程序"""
        custom_comparison = {
            "source_custom_dirs": [],
            "target_custom_dirs": [],
            "differences": []
        }

        # 查找自定义程序目录
        custom_dir_patterns = ["Custom", "MyPrograms", "Portable", "ThirdParty"]

        for pattern in custom_dir_patterns:
            source_path = source_mount / pattern
            target_path = target_mount / pattern

            if source_path.exists():
                custom_comparison["source_custom_dirs"].append({
                    "name": pattern,
                    "size": self._calculate_directory_size(source_path),
                    "file_count": len(list(source_path.rglob("*")))
                })

            if target_path.exists():
                custom_comparison["target_custom_dirs"].append({
                    "name": pattern,
                    "size": self._calculate_directory_size(target_path),
                    "file_count": len(list(target_path.rglob("*")))
                })

        # 分析差异
        source_dirs = {d["name"]: d for d in custom_comparison["source_custom_dirs"]}
        target_dirs = {d["name"]: d for d in custom_comparison["target_custom_dirs"]}

        for dir_name in set(source_dirs.keys()) | set(target_dirs.keys()):
            source_info = source_dirs.get(dir_name, {"size": 0, "file_count": 0})
            target_info = target_dirs.get(dir_name, {"size": 0, "file_count": 0})

            if source_info["size"] != target_info["size"] or source_info["file_count"] != target_info["file_count"]:
                custom_comparison["differences"].append({
                    "directory": dir_name,
                    "source_size": source_info["size"],
                    "target_size": target_info["size"],
                    "source_files": source_info["file_count"],
                    "target_files": target_info["file_count"]
                })

        return custom_comparison

    def _compare_shell_extensions(self, source_mount: Path, target_mount: Path) -> Dict:
        """比较Shell扩展"""
        shell_comparison = {
            "source_extensions": [],
            "target_extensions": [],
            "differences": []
        }

        # 查找Shell扩展
        source_exts = self._find_shell_extensions(source_mount)
        target_exts = self._find_shell_extensions(target_mount)

        shell_comparison["source_extensions"] = source_exts
        shell_comparison["target_extensions"] = target_exts

        source_names = {ext["name"]: ext for ext in source_exts}
        target_names = {ext["name"]: ext for ext in target_exts}

        shell_comparison["differences"] = {
            "source_only": [name for name in source_names.keys() if name not in target_names],
            "target_only": [name for name in target_names.keys() if name not in source_names]
        }

        return shell_comparison

    def _find_shell_extensions(self, mount_path: Path) -> List[Dict]:
        """查找Shell扩展"""
        extensions = []
        reg_files_path = mount_path / "Windows" / "System32" / "config" / "SOFTWARE"

        # 这里应该解析注册表文件来查找Shell扩展
        # 由于复杂性，简化处理：查找常见的扩展DLL
        system32 = mount_path / "Windows" / "System32"
        common_extensions = [
            "shdocvw.dll", "shell32.dll", "comdlg32.dll",
            "explorerframe.dll", "explorer.exe"
        ]

        for ext_file in common_extensions:
            ext_path = system32 / ext_file
            if ext_path.exists():
                extensions.append({
                    "name": ext_file,
                    "path": str(ext_path.relative_to(mount_path)),
                    "size": ext_path.stat().st_size
                })

        return extensions

    def _analyze_startup_mechanism_differences(self, source_mount: Path, target_mount: Path) -> Dict:
        """分析启动机制差异"""
        startup_analysis = {
            "winpeshl": self._compare_winpeshl(source_mount, target_mount),
            "startnet": self._compare_startnet(source_mount, target_mount),
            "peconfig": self._compare_peconfig(source_mount, target_mount),
            "registry_startup": self._compare_registry_startup(source_mount, target_mount),
            "autorun_locations": self._compare_autorun_locations(source_mount, target_mount)
        }

        return startup_analysis

    def _compare_winpeshl(self, source_mount: Path, target_mount: Path) -> Dict:
        """比较winpeshl.ini配置"""
        comparison = {
            "source_exists": False,
            "target_exists": False,
            "commands_diff": [],
            "settings_diff": []
        }

        source_file = source_mount / "Windows" / "System32" / "winpeshl.ini"
        target_file = target_mount / "Windows" / "System32" / "winpeshl.ini"

        comparison["source_exists"] = source_file.exists()
        comparison["target_exists"] = target_file.exists()

        if source_file.exists() and target_file.exists():
            try:
                source_content = self._parse_winpeshl_ini(source_file)
                target_content = self._parse_winpeshl_ini(target_file)

                # 比较命令
                source_commands = source_content.get("commands", [])
                target_commands = target_content.get("commands", [])

                if source_commands != target_commands:
                    comparison["commands_diff"] = {
                        "source_commands": source_commands,
                        "target_commands": target_commands
                    }

                # 比较设置
                source_settings = source_content.get("settings", {})
                target_settings = target_content.get("settings", {})

                if source_settings != target_settings:
                    comparison["settings_diff"] = {
                        "source_settings": source_settings,
                        "target_settings": target_settings
                    }

            except Exception as e:
                self.logger.warning(f"比较winpeshl.ini失败: {str(e)}")

        return comparison

    def _parse_winpeshl_ini(self, ini_file: Path) -> Dict:
        """解析winpeshl.ini文件"""
        content = {
            "commands": [],
            "settings": {}
        }

        try:
            lines = ini_file.read_text(encoding='utf-8', errors='ignore').split('\n')

            for line in lines:
                line = line.strip()
                if line.startswith('Command') and '=' in line:
                    command = line.split('=', 1)[1].strip()
                    if command:
                        content["commands"].append(command)
                elif '=' in line and not line.startswith('['):
                    key, value = line.split('=', 1)
                    content["settings"][key.strip()] = value.strip()

        except Exception as e:
            self.logger.warning(f"解析winpeshl.ini失败: {str(e)}")

        return content

    def _compare_startnet(self, source_mount: Path, target_mount: Path) -> Dict:
        """比较startnet.cmd脚本"""
        comparison = {
            "source_exists": False,
            "target_exists": False,
            "content_diff": None,
            "commands_diff": []
        }

        source_file = source_mount / "Windows" / "System32" / "startnet.cmd"
        target_file = target_mount / "Windows" / "System32" / "startnet.cmd"

        comparison["source_exists"] = source_file.exists()
        comparison["target_exists"] = target_file.exists()

        if source_file.exists() and target_file.exists():
            try:
                source_content = source_file.read_text(encoding='utf-8', errors='ignore')
                target_content = target_file.read_text(encoding='utf-8', errors='ignore')

                if source_content != target_content:
                    comparison["content_diff"] = self._analyze_text_differences(source_content, target_content)

                # 提取并比较命令
                source_commands = self._extract_batch_commands(source_content)
                target_commands = self._extract_batch_commands(target_content)

                if source_commands != target_commands:
                    comparison["commands_diff"] = {
                        "source_commands": source_commands,
                        "target_commands": target_commands
                    }

            except Exception as e:
                self.logger.warning(f"比较startnet.cmd失败: {str(e)}")

        return comparison

    def _extract_batch_commands(self, content: str) -> List[str]:
        """提取批处理命令"""
        commands = []
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            if line and not line.startswith('rem') and not line.startswith('@') and not line.startswith('::'):
                commands.append(line)

        return commands

    def _compare_peconfig(self, source_mount: Path, target_mount: Path) -> Dict:
        """比较PEConfig启动系统"""
        comparison = {
            "source_exists": False,
            "target_exists": False,
            "init_files_diff": [],
            "run_scripts_diff": []
        }

        source_peconfig = source_mount / "Windows" / "System32" / "PEConfig"
        target_peconfig = target_mount / "Windows" / "System32" / "PEConfig"

        comparison["source_exists"] = source_peconfig.exists()
        comparison["target_exists"] = target_peconfig.exists()

        if source_peconfig.exists() and target_peconfig.exists():
            # 比较Run目录中的初始化文件
            source_run = source_peconfig / "Run"
            target_run = target_peconfig / "Run"

            if source_run.exists() and target_run.exists():
                source_inis = list(source_run.glob("*.ini"))
                target_inis = list(target_run.glob("*.ini"))

                source_ini_names = {ini.name: ini for ini in source_inis}
                target_ini_names = {ini.name: ini for ini in target_inis}

                # 找出差异
                for ini_name in set(source_ini_names.keys()) | set(target_ini_names.keys()):
                    if ini_name not in target_ini_names:
                        comparison["init_files_diff"].append(f"源独有的文件: {ini_name}")
                    elif ini_name not in source_ini_names:
                        comparison["init_files_diff"].append(f"目标独有的文件: {ini_name}")
                    else:
                        # 比较文件内容
                        try:
                            source_content = source_ini_names[ini_name].read_text(encoding='utf-8', errors='ignore')
                            target_content = target_ini_names[ini_name].read_text(encoding='utf-8', errors='ignore')

                            if source_content != target_content:
                                comparison["init_files_diff"].append(f"内容不同: {ini_name}")
                        except Exception as e:
                            self.logger.warning(f"比较PEConfig文件失败 {ini_name}: {str(e)}")

        return comparison

    def _compare_registry_startup(self, source_mount: Path, target_mount: Path) -> Dict:
        """比较注册表启动项"""
        comparison = {
            "run_keys_diff": [],
            "services_diff": [],
            "drivers_diff": []
        }

        # 这里应该解析注册表文件来比较启动项
        # 由于复杂性，简化处理
        source_config = source_mount / "Windows" / "System32" / "config" / "SOFTWARE"
        target_config = target_mount / "Windows" / "System32" / "config" / "SOFTWARE"

        if source_config.exists() and target_config.exists():
            # 简单的大小比较
            source_size = source_config.stat().st_size
            target_size = target_config.stat().st_size

            if abs(source_size - target_size) > 1024:  # 差异超过1KB
                comparison["run_keys_diff"].append(f"注册表大小差异显著: 源={source_size}, 目标={target_size}")

        return comparison

    def _compare_autorun_locations(self, source_mount: Path, target_mount: Path) -> Dict:
        """比较自动运行位置"""
        comparison = {
            "startup_folders_diff": [],
            "autorun_inf_diff": []
        }

        # 比较启动文件夹
        startup_paths = [
            "Windows" / "System32" / "config" / "systemprofile" / "Start Menu" / "Programs" / "Startup",
            "Users" / "Default" / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        ]

        for startup_path in startup_paths:
            source_path = source_mount / startup_path
            target_path = target_mount / startup_path

            if source_path.exists() and target_path.exists():
                source_files = [f.name for f in source_path.glob("*") if f.is_file()]
                target_files = [f.name for f in target_path.glob("*") if f.is_file()]

                if set(source_files) != set(target_files):
                    comparison["startup_folders_diff"].append({
                        "path": str(startup_path),
                        "source_only": list(set(source_files) - set(target_files)),
                        "target_only": list(set(target_files) - set(source_files))
                    })

        return comparison

    def _analyze_driver_differences(self, source_mount: Path, target_mount: Path) -> Dict:
        """分析驱动程序差异"""
        driver_analysis = {
            "source_drivers": [],
            "target_drivers": [],
            "source_only": [],
            "target_only": [],
            "version_differences": [],
            "critical_drivers_diff": []
        }

        # 查找驱动程序
        source_drivers = self._find_drivers(source_mount)
        target_drivers = self._find_drivers(target_mount)

        driver_analysis["source_drivers"] = source_drivers
        driver_analysis["target_drivers"] = target_drivers

        # 分析差异
        source_names = {d["inf_file"]: d for d in source_drivers}
        target_names = {d["inf_file"]: d for d in target_drivers}

        driver_analysis["source_only"] = [name for name in source_names.keys() if name not in target_names]
        driver_analysis["target_only"] = [name for name in target_names.keys() if name not in source_names]

        # 检查关键驱动差异
        critical_drivers = [
            "disk.sys", "storahci.sys", "nvme.sys",  # 存储驱动
            "netcfg.dll", "netio.sys", "tcpip.sys",  # 网络驱动
            "vga.sys", "nv4_mini.sys", "atikmdag.sys"  # 显卡驱动
        ]

        for driver in critical_drivers:
            source_has = any(driver.lower() in d["inf_file"].lower() for d in source_drivers)
            target_has = any(driver.lower() in d["inf_file"].lower() for d in target_drivers)

            if source_has != target_has:
                driver_analysis["critical_drivers_diff"].append({
                    "driver": driver,
                    "source_has": source_has,
                    "target_has": target_has
                })

        return driver_analysis

    def _find_drivers(self, mount_path: Path) -> List[Dict]:
        """查找驱动程序"""
        drivers = []
        drivers_dir = mount_path / "Drivers"

        if not drivers_dir.exists():
            return drivers

        try:
            for inf_file in drivers_dir.rglob("*.inf"):
                driver_info = {
                    "inf_file": inf_file.name,
                    "path": str(inf_file.relative_to(mount_path)),
                    "size": inf_file.stat().st_size,
                    "category": self._classify_driver(inf_file),
                    "modified": datetime.fromtimestamp(inf_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                }

                # 查找相关的sys文件
                sys_files = list(inf_file.parent.rglob("*.sys"))
                driver_info["sys_files"] = [f.name for f in sys_files]

                drivers.append(driver_info)

        except Exception as e:
            self.logger.warning(f"查找驱动程序失败: {str(e)}")

        return drivers

    def _analyze_registry_differences(self, source_mount: Path, target_mount: Path) -> Dict:
        """分析注册表差异"""
        registry_analysis = {
            "hive_files_diff": [],
            "size_differences": {},
            "key_differences": {}
        }

        # 比较注册表配置单元文件
        registry_hives = ["SOFTWARE", "SYSTEM", "SAM", "SECURITY", "DEFAULT"]
        config_dir = "Windows" / "System32" / "config"

        for hive in registry_hives:
            source_hive = source_mount / config_dir / hive
            target_hive = target_mount / config_dir / hive

            if source_hive.exists() and target_hive.exists():
                source_size = source_hive.stat().st_size
                target_size = target_hive.stat().st_size

                if source_size != target_size:
                    registry_analysis["size_differences"][hive] = {
                        "source_size": source_size,
                        "target_size": target_size,
                        "difference": source_size - target_size
                    }
            elif source_hive.exists() != target_hive.exists():
                registry_analysis["hive_files_diff"].append(f"{hive}: {'源存在，目标不存在' if source_hive.exists() else '源不存在，目标存在'}")

        return registry_analysis

    def _analyze_service_differences(self, source_mount: Path, target_mount: Path) -> Dict:
        """分析服务差异"""
        service_analysis = {
            "source_services": [],
            "target_services": [],
            "source_only": [],
            "target_only": [],
            "config_differences": []
        }

        # 这里应该解析注册表来获取服务信息
        # 简化处理：查找服务相关的DLL
        source_services = self._find_service_dlls(source_mount)
        target_services = self._find_service_dlls(target_mount)

        service_analysis["source_services"] = source_services
        service_analysis["target_services"] = target_services

        source_names = {s["name"]: s for s in source_services}
        target_names = {s["name"]: s for s in target_services}

        service_analysis["source_only"] = [name for name in source_names.keys() if name not in target_names]
        service_analysis["target_only"] = [name for name in target_names.keys() if name not in source_names]

        return service_analysis

    def _find_service_dlls(self, mount_path: Path) -> List[Dict]:
        """查找服务DLL"""
        services = []
        system32 = mount_path / "Windows" / "System32"

        service_patterns = [
            "*svc*.dll", "*service*.dll", "*srv*.dll"
        ]

        for pattern in service_patterns:
            for dll_file in system32.glob(pattern):
                service_info = {
                    "name": dll_file.stem,
                    "path": str(dll_file.relative_to(mount_path)),
                    "size": dll_file.stat().st_size
                }
                services.append(service_info)

        return services

    def _find_config_files(self, mount_path: Path, extensions: List[str]) -> List[Path]:
        """查找配置文件"""
        config_files = []
        search_paths = [
            mount_path / "Windows" / "System32",
            mount_path / "Windows",
            mount_path / "Program Files",
            mount_path
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for ext in extensions:
                config_files.extend(search_path.rglob(f"*{ext}"))

        return config_files

    def _find_all_config_files(self, mount_path: Path) -> Dict[str, List[Path]]:
        """查找所有类型的配置文件"""
        config_categories = {
            "ini_files": [],
            "cmd_files": [],
            "bat_files": [],
            "jcfg_files": [],
            "lua_files": [],
            "xml_files": [],
            "json_files": [],
            "conf_files": [],
            "cfg_files": [],
            "reg_files": [],
            "vbs_files": [],
            "ps1_files": [],
            "py_files": []
        }

        search_paths = [
            mount_path / "Windows" / "System32",
            mount_path / "Windows",
            mount_path / "Program Files",
            mount_path
        ]

        # 文件扩展名映射
        extension_map = {
            "ini_files": [".ini"],
            "cmd_files": [".cmd"],
            "bat_files": [".bat", ".btm"],
            "jcfg_files": [".jcfg"],
            "lua_files": [".lua"],
            "xml_files": [".xml"],
            "json_files": [".json"],
            "conf_files": [".conf"],
            "cfg_files": [".cfg"],
            "reg_files": [".reg"],
            "vbs_files": [".vbs"],
            "ps1_files": [".ps1"],
            "py_files": [".py"]
        }

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for category, exts in extension_map.items():
                for ext in exts:
                    config_categories[category].extend(search_path.rglob(f"*{ext}"))

        return config_categories

    def _compare_file_lists(self, source_files: List[Path], target_files: List[Path],
                           result_dict: Dict, source_mount: Path, target_mount: Path):
        """比较文件列表"""
        source_names = {f.name: f for f in source_files}
        target_names = {f.name: f for f in target_files}

        result_dict["source_only"] = [name for name in source_names.keys() if name not in target_names]
        result_dict["target_only"] = [name for name in target_names.keys() if name not in source_names]

        # 检查修改过的文件
        common_names = set(source_names.keys()) & set(target_names.keys())
        for name in common_names:
            source_file = source_names[name]
            target_file = target_names[name]

            try:
                source_mtime = source_file.stat().st_mtime
                target_mtime = target_file.stat().st_mtime

                if abs(source_mtime - target_mtime) > 60:  # 差异超过60秒
                    result_dict["both_modified"].append({
                        "name": name,
                        "source_modified": datetime.fromtimestamp(source_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        "target_modified": datetime.fromtimestamp(target_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })
            except Exception as e:
                self.logger.warning(f"比较文件时间戳失败 {name}: {str(e)}")

    def _analyze_text_differences(self, source_content: str, target_content: str) -> Dict:
        """分析文本差异"""
        source_lines = source_content.split('\n')
        target_lines = target_content.split('\n')

        return {
            "source_lines": len(source_lines),
            "target_lines": len(target_lines),
            "line_differences": abs(len(source_lines) - len(target_lines)),
            "content_hash": {
                "source": hash(source_content),
                "target": hash(target_content)
            }
        }

    def _identify_compatibility_issues(self, analysis: Dict) -> List[Dict]:
        """识别兼容性问题"""
        issues = []

        # 检查版本兼容性
        version_diff = analysis["version_differences"]
        if version_diff["major_differences"]["kernel_version"]:
            issues.append({
                "type": "version_incompatible",
                "severity": "high",
                "description": "内核版本不兼容，可能存在API差异",
                "source_version": version_diff["source"].get("kernel"),
                "target_version": version_diff["target"].get("kernel")
            })

        # 检查驱动兼容性
        driver_diff = analysis["driver_differences"]
        if driver_diff["critical_drivers_diff"]:
            issues.append({
                "type": "driver_compatibility",
                "severity": "high",
                "description": "关键驱动程序缺失或不兼容",
                "affected_drivers": driver_diff["critical_drivers_diff"]
            })

        # 检查桌面环境兼容性
        program_diff = analysis["external_program_differences"]
        desktop_diff = program_diff["desktop_environments"]
        if desktop_diff["differences"]:
            issues.append({
                "type": "desktop_environment",
                "severity": "medium",
                "description": "桌面环境配置差异",
                "differences": desktop_diff["differences"]
            })

        # 检查启动脚本差异
        startup_diff = analysis["startup_mechanism_differences"]
        if startup_diff["winpeshl"]["commands_diff"]:
            issues.append({
                "type": "startup_script",
                "severity": "medium",
                "description": "启动脚本命令差异",
                "differences": startup_diff["winpeshl"]["commands_diff"]
            })

        return issues

    def _generate_migration_recommendations(self, analysis: Dict) -> List[Dict]:
        """生成迁移建议"""
        recommendations = []

        # 基于兼容性问题生成建议
        for issue in analysis["compatibility_issues"]:
            if issue["type"] == "version_incompatible":
                recommendations.append({
                    "category": "version_migration",
                    "priority": "high",
                    "action": "检查API兼容性",
                    "description": "需要测试在新版本中是否支持所有使用的API",
                    "affected_components": ["自定义程序", "脚本"]
                })

            elif issue["type"] == "driver_compatibility":
                recommendations.append({
                    "category": "driver_migration",
                    "priority": "high",
                    "action": "迁移关键驱动",
                    "description": "必须迁移所有关键驱动程序，特别是存储和网络驱动",
                    "affected_components": ["驱动程序"]
                })

            elif issue["type"] == "desktop_environment":
                recommendations.append({
                    "category": "desktop_migration",
                    "priority": "medium",
                    "action": "重新配置桌面环境",
                    "description": "可能需要重新配置WinXShell或其他桌面环境",
                    "affected_components": ["桌面环境", "配置文件"]
                })

            elif issue["type"] == "startup_script":
                recommendations.append({
                    "category": "script_migration",
                    "priority": "medium",
                    "action": "更新启动脚本",
                    "description": "需要检查并更新启动脚本以适配新版本",
                    "affected_components": ["启动脚本", "配置文件"]
                })

        # 添加通用建议
        recommendations.extend([
            {
                "category": "backup",
                "priority": "high",
                "action": "完整备份",
                "description": "在执行迁移前完整备份源系统和配置"
            },
            {
                "category": "testing",
                "priority": "high",
                "action": "逐步测试",
                "description": "在测试环境中逐步验证每个组件的功能"
            },
            {
                "category": "rollback",
                "priority": "medium",
                "action": "准备回滚方案",
                "description": "准备快速回滚到原始配置的方案"
            }
        ])

        return recommendations

    def execute_comprehensive_replacement(self,
                                       source_base_dir: Path,
                                       target_base_dir: Path,
                                       output_dir: Path,
                                       enable_dism_fix: bool = True) -> Dict[str, Any]:
        """
        执行全面的版本替换，包括差异分析和修复
        1. 复制源目录结构
        2. 替换boot.wim
        3. 挂载boot.wim
        4. 分析差异
        5. 修复组件差异
        6. 解决外部程序问题
        7. 修复配置文件

        Args:
            source_base_dir: 源目录 (0WIN11PE)
            target_base_dir: 目标目录 (0WIN10OLD)
            output_dir: 输出目录 (WIN10REPLACED_REPLACED)
            enable_dism_fix: 是否启用DISM组件修复

        Returns:
            完整的替换结果
        """
        self.logger.info("开始执行全面WinPE版本替换...")
        self.logger.info(f"源目录: {source_base_dir}")
        self.logger.info(f"目标目录: {target_base_dir}")
        self.logger.info(f"输出目录: {output_dir}")

        result = {
            "success": False,
            "steps": {},
            "errors": [],
            "warnings": [],
            "differences_analysis": None,
            "fixes_applied": {},
            "final_state": {}
        }

        try:
            # 步骤1：复制源目录结构 (保持WIN10REPLACED_REPLACED和0WIN11PE完全一致)
            self.logger.info("步骤1: 复制源目录结构 (WIN10REPLACED_REPLACED ← 0WIN11PE)")
            self.migration_manager._copy_directory_structure(source_base_dir, output_dir)
            result["steps"]["directory_copy"] = "completed"

            # 步骤2：替换boot.wim文件内容 (用0WIN10OLD的boot.wim替换WIN10REPLACED_REPLACED中的boot.wim)
            self.logger.info("步骤2: 替换boot.wim文件内容")
            self.migration_manager._replace_boot_wim(target_base_dir, output_dir)
            result["steps"]["boot_wim_replace"] = "completed"

            # 步骤3：分析现有挂载点的差异 (分析0WIN11PE\mount vs 0WIN10OLD\mount)
            self.logger.info("步骤3: 分析现有挂载点差异")
            source_mount = source_base_dir / "mount"  # 0WIN11PE\mount
            old_mount = target_base_dir / "mount"     # 0WIN10OLD\mount

            if not source_mount.exists():
                self.logger.warning(f"源挂载目录不存在: {source_mount}")
                raise Exception(f"源挂载目录不存在: {source_mount}")

            if not old_mount.exists():
                self.logger.warning(f"目标挂载目录不存在: {old_mount}")
                raise Exception(f"目标挂载目录不存在: {old_mount}")

            self.logger.info(f"分析挂载点差异: {source_mount} vs {old_mount}")
            differences = self.component_analyzer.analyze_mount_differences(source_mount, old_mount)
            result["differences_analysis"] = differences
            result["steps"]["differences_analysis"] = "completed"

            # 步骤4：挂载新的boot.wim以应用修复
            self.logger.info("步骤4: 挂载新的boot.wim准备应用修复")
            self.migration_manager._mount_boot_wim(output_dir)
            result["steps"]["boot_wim_mount"] = "completed"

            # 步骤5：将差异修复应用到WIN10REPLACED_REPLACED\mount
            self.logger.info("步骤5: 应用差异修复到WIN10REPLACED_REPLACED\\mount")
            target_mount = output_dir / "mount"  # WIN10REPLACED_REPLACED\mount
            fixes = self._apply_differences_fixes(source_mount, target_mount, differences, enable_dism_fix)
            result["fixes_applied"] = fixes
            result["steps"]["differences_fixes"] = "completed"

            # 步骤6：最终验证
            self.logger.info("步骤6: 最终验证")
            final_state = self._verify_final_state(target_mount, differences)
            result["final_state"] = final_state
            result["steps"]["final_verification"] = "completed"

            result["success"] = True
            self.logger.info("全面WinPE版本替换完成")
            log_system_event("全面版本替换", "WinPE版本替换成功", "info")

        except Exception as e:
            error_msg = f"全面版本替换失败: {str(e)}"
            self.logger.error(error_msg)
            result["errors"].append(error_msg)
            log_system_event("全面版本替换", error_msg, "error")

        return result

    def _apply_differences_fixes(self, source_mount: Path, target_mount: Path,
                                differences: Dict, enable_dism_fix: bool) -> Dict[str, Any]:
        """应用差异修复"""
        fixes_applied = {
            "config_files": [],
            "external_programs": [],
            "startup_scripts": [],
            "drivers": [],
            "dism_components": [],
            "registry_fixes": []
        }

        try:
            # 修复配置文件差异
            config_fixes = self._fix_config_differences(
                source_mount, target_mount, differences["config_differences"]
            )
            fixes_applied["config_files"] = config_fixes

            # 修复外部程序差异
            program_fixes = self._fix_external_program_differences(
                source_mount, target_mount, differences["external_program_differences"]
            )
            fixes_applied["external_programs"] = program_fixes

            # 修复启动脚本差异
            startup_fixes = self._fix_startup_differences(
                source_mount, target_mount, differences["startup_mechanism_differences"]
            )
            fixes_applied["startup_scripts"] = startup_fixes

            # 修复驱动程序差异
            driver_fixes = self._fix_driver_differences(
                source_mount, target_mount, differences["driver_differences"]
            )
            fixes_applied["drivers"] = driver_fixes

            # 使用DISM修复组件差异（如果启用）
            if enable_dism_fix:
                dism_fixes = self._fix_dism_components_differences(
                    target_mount, differences["version_differences"]
                )
                fixes_applied["dism_components"] = dism_fixes

            # 修复注册表差异
            registry_fixes = self._fix_registry_differences(
                source_mount, target_mount, differences["registry_differences"]
            )
            fixes_applied["registry_fixes"] = registry_fixes

            self.logger.info(f"差异修复完成: {sum(len(fixes) for fixes in fixes_applied.values())} 个修复项")

        except Exception as e:
            self.logger.error(f"应用差异修复失败: {str(e)}")
            raise

        return fixes_applied

    def _fix_config_differences(self, source_mount: Path, target_mount: Path, config_diff: Dict) -> List[str]:
        """修复配置文件差异"""
        fixes = []

        # 修复各种类型的配置文件差异
        file_types = [
            "ini_files", "cmd_files", "bat_files", "jcfg_files", "lua_files",
            "xml_files", "json_files", "conf_files", "cfg_files", "reg_files",
            "vbs_files", "ps1_files", "py_files"
        ]

        for file_type in file_types:
            for config_file in config_diff[file_type]["source_only"]:
                # 处理特殊路径（如PEConfig目录下的文件）
                if config_file == "PEConfig.ini":
                    source_file = source_mount / "Windows" / "System32" / "PEConfig" / "Run" / config_file
                    target_file = target_mount / "Windows" / "System32" / "PEConfig" / "Run" / config_file
                else:
                    source_file = source_mount / "Windows" / "System32" / config_file
                    target_file = target_mount / "Windows" / "System32" / config_file

                if source_file.exists():
                    try:
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_file, target_file)
                        file_type_name = file_type.replace("_files", "").upper()
                        fixes.append(f"复制{file_type_name}文件: {config_file}")
                        self.logger.info(f"已复制{file_type_name}配置文件: {config_file}")
                    except Exception as e:
                        self.logger.warning(f"复制配置文件失败 {config_file}: {str(e)}")

        # 修复关键配置文件差异
        critical_configs = config_diff.get("critical_configs", {})
        for config_name, config_info in critical_configs.items():
            if config_info.get("content_diff"):
                source_file = source_mount / "Windows" / "System32" / config_name
                target_file = target_mount / "Windows" / "System32" / config_name

                # 处理特殊配置文件路径
                if config_name == "PEConfig.ini":
                    source_file = source_mount / "Windows" / "System32" / "PEConfig" / "Run" / config_name
                    target_file = target_mount / "Windows" / "System32" / "PEConfig" / "Run" / config_name

                if source_file.exists():
                    try:
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_file, target_file)
                        fixes.append(f"更新关键配置文件: {config_name}")
                        self.logger.info(f"已更新关键配置文件: {config_name}")
                    except Exception as e:
                        self.logger.warning(f"更新配置文件失败 {config_name}: {str(e)}")

        return fixes

    def _fix_external_program_differences(self, source_mount: Path, target_mount: Path, program_diff: Dict) -> List[str]:
        """修复外部程序差异"""
        fixes = []

        # 修复桌面环境差异
        desktop_env = program_diff.get("desktop_environments", {})
        source_desktop = desktop_env.get("source", {})
        target_desktop = desktop_env.get("target", {})

        # 如果源使用WinXShell而目标没有，则复制WinXShell
        if source_desktop.get("type") == "WinXShell" and target_desktop.get("type") != "WinXShell":
            winxshell_fixes = self._copy_winxshell_environment(source_mount, target_mount, source_desktop)
            fixes.extend(winxshell_fixes)

        # 修复第三方工具差异
        tools_diff = program_diff.get("third_party_tools", {})
        for tool_name in tools_diff.get("source_only", []):
            tool_fixes = self._copy_third_party_tool(source_mount, target_mount, tool_name)
            fixes.extend(tool_fixes)

        # 修复自定义程序差异
        custom_diff = program_diff.get("custom_programs", {})
        for diff_info in custom_diff.get("differences", []):
            dir_name = diff_info["directory"]
            custom_fixes = self._copy_custom_program_directory(source_mount, target_mount, dir_name)
            fixes.extend(custom_fixes)

        return fixes

    def _copy_winxshell_environment(self, source_mount: Path, target_mount: Path, source_desktop: Dict) -> List[str]:
        """复制WinXShell环境"""
        fixes = []
        winxshell_info = source_desktop.get("winxshell")
        if not winxshell_info:
            return fixes

        try:
            source_winx_dir = Path(winxshell_info["install_path"]).relative_to(source_mount)
            target_winx_dir = target_mount / source_winx_dir

            # 复制WinXShell目录
            if source_winx_dir.exists():
                self.migration_manager._copy_directory_with_permissions(source_winx_dir, target_winx_dir)
                fixes.append(f"复制WinXShell环境到: {target_winx_dir}")
                self.logger.info(f"已复制WinXShell环境: {target_winx_dir}")

            # 复制配置文件
            source_system32 = source_mount / "Windows" / "System32"
            target_system32 = target_mount / "Windows" / "System32"

            winx_config_files = ["WinXShell.jcfg", "WinXShell.ini", "InitWinXShell.ini"]
            for config_file in winx_config_files:
                source_config = source_system32 / config_file
                target_config = target_system32 / config_file

                if source_config.exists():
                    shutil.copy2(source_config, target_config)
                    fixes.append(f"复制WinXShell配置: {config_file}")

        except Exception as e:
            self.logger.warning(f"复制WinXShell环境失败: {str(e)}")

        return fixes

    def _copy_third_party_tool(self, source_mount: Path, target_mount: Path, tool_name: str) -> List[str]:
        """复制第三方工具"""
        fixes = []

        # 查找工具在源系统中的位置
        source_tools = self.component_analyzer._find_third_party_tools(source_mount)
        tool_info = next((t for t in source_tools if t["name"] == tool_name), None)

        if tool_info:
            try:
                source_path = source_mount / tool_info["path"]
                target_path = target_mount / tool_info["path"]

                # 确保目标目录存在
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # 复制工具文件
                shutil.copy2(source_path, target_path)
                fixes.append(f"复制第三方工具: {tool_name}")

                # 复制相关文件（如果有的话）
                source_dir = source_path.parent
                target_dir = target_path.parent

                # 复制同名的配置文件
                for ext in [".ini", ".cfg", ".xml", ".dll"]:
                    pattern = f"{source_path.stem}{ext}*"
                    for related_file in source_dir.glob(pattern):
                        related_target = target_dir / related_file.name
                        if related_file.exists() and not related_target.exists():
                            shutil.copy2(related_file, related_target)

                self.logger.info(f"已复制第三方工具: {tool_name}")

            except Exception as e:
                self.logger.warning(f"复制第三方工具失败 {tool_name}: {str(e)}")

        return fixes

    def _copy_custom_program_directory(self, source_mount: Path, target_mount: Path, dir_name: str) -> List[str]:
        """复制自定义程序目录"""
        fixes = []

        source_dir = source_mount / dir_name
        target_dir = target_mount / dir_name

        if source_dir.exists():
            try:
                self.migration_manager._copy_directory_with_permissions(source_dir, target_dir)
                fixes.append(f"复制自定义程序目录: {dir_name}")
                self.logger.info(f"已复制自定义程序目录: {dir_name}")
            except Exception as e:
                self.logger.warning(f"复制自定义程序目录失败 {dir_name}: {str(e)}")

        return fixes

    def _fix_startup_differences(self, source_mount: Path, target_mount: Path, startup_diff: Dict) -> List[str]:
        """修复启动脚本差异"""
        fixes = []

        # 修复winpeshl.ini
        winpeshl_diff = startup_diff.get("winpeshl", {})
        if winpeshl_diff.get("commands_diff"):
            source_file = source_mount / "Windows" / "System32" / "winpeshl.ini"
            target_file = target_mount / "Windows" / "System32" / "winpeshl.ini"

            if source_file.exists():
                try:
                    shutil.copy2(source_file, target_file)
                    fixes.append("更新winpeshl.ini启动配置")
                    self.logger.info("已更新winpeshl.ini启动配置")
                except Exception as e:
                    self.logger.warning(f"更新winpeshl.ini失败: {str(e)}")

        # 修复startnet.cmd
        startnet_diff = startup_diff.get("startnet", {})
        if startnet_diff.get("commands_diff"):
            source_file = source_mount / "Windows" / "System32" / "startnet.cmd"
            target_file = target_mount / "Windows" / "System32" / "startnet.cmd"

            if source_file.exists():
                try:
                    shutil.copy2(source_file, target_file)
                    fixes.append("更新startnet.cmd启动脚本")
                    self.logger.info("已更新startnet.cmd启动脚本")
                except Exception as e:
                    self.logger.warning(f"更新startnet.cmd失败: {str(e)}")

        # 修复PEConfig启动系统
        peconfig_diff = startup_diff.get("peconfig", {})
        if peconfig_diff.get("init_files_diff"):
            source_peconfig = source_mount / "Windows" / "System32" / "PEConfig"
            target_peconfig = target_mount / "Windows" / "System32" / "PEConfig"

            if source_peconfig.exists():
                try:
                    self.migration_manager._copy_directory_with_permissions(source_peconfig, target_peconfig)
                    fixes.append("复制PEConfig启动系统")
                    self.logger.info("已复制PEConfig启动系统")
                except Exception as e:
                    self.logger.warning(f"复制PEConfig失败: {str(e)}")

        return fixes

    def _fix_driver_differences(self, source_mount: Path, target_mount: Path, driver_diff: Dict) -> List[str]:
        """修复驱动程序差异"""
        fixes = []

        # 复制源独有的驱动
        for driver_name in driver_diff.get("source_only", []):
            try:
                source_drivers = source_mount / "Drivers"
                target_drivers = target_mount / "Drivers"

                # 查找驱动文件
                for driver_file in source_drivers.rglob(f"{driver_name}*"):
                    relative_path = driver_file.relative_to(source_drivers)
                    target_file = target_drivers / relative_path

                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(driver_file, target_file)

                fixes.append(f"复制驱动程序: {driver_name}")

            except Exception as e:
                self.logger.warning(f"复制驱动失败 {driver_name}: {str(e)}")

        # 处理关键驱动差异
        for critical_diff in driver_diff.get("critical_drivers_diff", []):
            if critical_diff["source_has"] and not critical_diff["target_has"]:
                # 需要从源系统复制关键驱动
                fixes.append(f"⚠️ 关键驱动缺失: {critical_diff['driver']} (需要手动处理)")
                self.logger.warning(f"关键驱动缺失，需要手动处理: {critical_diff['driver']}")

        return fixes

    def _fix_dism_components_differences(self, target_mount: Path, version_diff: Dict) -> List[str]:
        """使用DISM修复组件差异"""
        fixes = []

        if not self.adk:
            fixes.append("ADK管理器未初始化，跳过DISM组件修复")
            return fixes

        try:
            # 检查版本差异
            if version_diff["major_differences"]["kernel_version"]:
                # 尝试安装必要的WinPE可选组件
                optional_components = [
                    "WinPE-WMI",
                    "WinPE-PowerShell",
                    "WinPE-NetFx",
                    "WinPE-Dot3Svc",
                    "WinPE-Scripting"
                ]

                for component in optional_components:
                    try:
                        # 使用DISM安装组件
                        args = [
                            "/Image", str(target_mount),
                            "/Add-Package",
                            f"/PackagePath:C:\\Program Files (x86)\\Windows Kits\\10\\Assessment and Deployment Kit\\Windows Preinstallation Environment\\amd64\\WinPE_OCs\\{component}.cab"
                        ]

                        success, stdout, stderr = self.adk.run_dism_command(args)

                        if success:
                            fixes.append(f"安装WinPE组件: {component}")
                            self.logger.info(f"已安装WinPE组件: {component}")
                        else:
                            self.logger.warning(f"安装WinPE组件失败 {component}: {stderr}")

                    except Exception as e:
                        self.logger.warning(f"安装WinPE组件异常 {component}: {str(e)}")

        except Exception as e:
            self.logger.warning(f"DISM组件修复失败: {str(e)}")

        return fixes

    def _fix_registry_differences(self, source_mount: Path, target_mount: Path, registry_diff: Dict) -> List[str]:
        """修复注册表差异"""
        fixes = []

        # 复制源独有的注册表配置单元
        for hive_file in registry_diff.get("hive_files_diff", []):
            if "源存在，目标不存在" in hive_file:
                hive_name = hive_file.split(":")[0]
                try:
                    source_hive = source_mount / "Windows" / "System32" / "config" / hive_name
                    target_hive = target_mount / "Windows" / "System32" / "config" / hive_name

                    if source_hive.exists():
                        shutil.copy2(source_hive, target_hive)
                        fixes.append(f"复制注册表配置单元: {hive_name}")
                        self.logger.info(f"已复制注册表配置单元: {hive_name}")

                except Exception as e:
                    self.logger.warning(f"复制注册表配置单元失败 {hive_name}: {str(e)}")

        return fixes

    def _verify_final_state(self, target_mount: Path, original_differences: Dict) -> Dict[str, Any]:
        """验证最终状态"""
        verification = {
            "critical_files": {},
            "desktop_environment": "Unknown",
            "startup_scripts": {},
            "external_tools_count": 0,
            "issues_found": []
        }

        try:
            # 检查关键文件
            critical_files = ["winpeshl.ini", "startnet.cmd", "explorer.exe"]
            system32 = target_mount / "Windows" / "System32"

            for file_name in critical_files:
                file_path = system32 / file_name
                verification["critical_files"][file_name] = {
                    "exists": file_path.exists(),
                    "size": file_path.stat().st_size if file_path.exists() else 0
                }

            # 检测桌面环境
            desktop_info = self.component_analyzer._detect_desktop_environment(target_mount)
            verification["desktop_environment"] = desktop_info["type"]

            # 统计外部工具
            tools = self.component_analyzer._find_third_party_tools(target_mount)
            verification["external_tools_count"] = len(tools)

            # 检查启动脚本
            verification["startup_scripts"] = {
                "winpeshl_exists": (system32 / "winpeshl.ini").exists(),
                "startnet_exists": (system32 / "startnet.cmd").exists(),
                "peconfig_exists": (system32 / "PEConfig").exists()
            }

        except Exception as e:
            verification["issues_found"].append(f"验证过程出错: {str(e)}")
            self.logger.warning(f"最终状态验证失败: {str(e)}")

        return verification

    def _calculate_directory_size(self, directory: Path) -> int:
        """计算目录大小"""
        total_size = 0
        try:
            for item in directory.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
        except Exception:
            pass
        return total_size

    def _classify_driver(self, inf_file: Path) -> str:
        """分类驱动程序"""
        try:
            content = inf_file.read_text(encoding='utf-8', errors='ignore')
            content_upper = content.upper()

            if 'STORAGE' in content_upper or 'SCSI' in content_upper or 'AHCI' in content_upper:
                return "Storage"
            elif 'NETWORK' in content_upper or 'ETHERNET' in content_upper or 'WIFI' in content_upper:
                return "Network"
            elif 'DISPLAY' in content_upper or 'VIDEO' in content_upper or 'GRAPHICS' in content_upper:
                return "Display"
            elif 'AUDIO' in content_upper or 'SOUND' in content_upper:
                return "Audio"
            elif 'USB' in content_upper:
                return "USB"
            else:
                return "Other"
        except Exception:
            return "Unknown"


class ComponentMigrationManager:
    """组件迁移管理器"""

    def __init__(self, adk_manager):
        self.adk_manager = adk_manager
        self.logger = get_logger("ComponentMigrationManager")

    def execute_version_replacement(self,
                                  source_base_dir: Path,
                                  target_base_dir: Path,
                                  output_dir: Path,
                                  migration_config: Dict) -> Dict[str, Any]:
        """
        执行版本替换 - 新流程：复制目录结构 + 替换boot.wim + 挂载

        Args:
            source_base_dir: 源目录 (如: D:\APP\WinPEManager\WinPE_amd64\0WIN11PE)
            target_base_dir: 目标目录 (如: D:\APP\WinPEManager\WinPE_amd64\0WIN10OLD)
            output_dir: 输出目录 (如: D:\APP\WinPEManager\WinPE_amd64\WIN10REPLACED_REPLACED)
            migration_config: 迁移配置

        Returns:
            替换结果
        """
        result = {
            "success": False,
            "steps": {},
            "errors": [],
            "warnings": [],
            "migrated_components": {},
            "output_wim": None
        }

        try:
            self.logger.info("开始WinPE版本替换 - 新流程...")
            self.logger.info(f"源路径: {source_base_dir}")
            self.logger.info(f"目标路径: {target_base_dir}")
            self.logger.info(f"输出目录: {output_dir}")

            # 智能解析输入路径，自动确定基础目录
            source_root = self._find_base_directory(source_base_dir)
            target_root = self._find_base_directory(target_base_dir)

            self.logger.info(f"解析后的源基础目录: {source_root}")
            self.logger.info(f"解析后的目标基础目录: {target_root}")

            # 步骤1：复制源目录的完整结构
            self.logger.info("步骤1: 复制源目录结构")
            self._copy_directory_structure(source_root, output_dir)
            result["steps"]["directory_copy"] = "completed"

            # 步骤2：替换boot.wim文件
            self.logger.info("步骤2: 替换boot.wim文件")
            self._replace_boot_wim(target_root, output_dir)
            result["steps"]["boot_wim_replace"] = "completed"

            # 步骤3：挂载新的boot.wim到mount目录
            self._mount_boot_wim(output_dir)
            result["steps"]["boot_wim_mount"] = "completed"

            # 步骤4：验证和修复
            self._validate_and_fix(output_dir)
            result["steps"]["validation"] = "completed"

            result["success"] = True
            self.logger.info("WinPE版本替换完成")

        except Exception as e:
            error_msg = f"版本替换失败: {str(e)}"
            self.logger.error(error_msg)
            result["errors"].append(error_msg)

        return result

    def _find_base_directory(self, input_path: Path) -> Path:
        """智能解析输入路径，返回基础目录"""
        self.logger.info(f"解析路径: {input_path}")

        # 如果路径以mount结尾，返回父目录
        if input_path.name == "mount":
            base_dir = input_path.parent
            self.logger.info(f"检测到mount路径，返回基础目录: {base_dir}")
            return base_dir

        # 检查是否存在mount子目录
        mount_subdir = input_path / "mount"
        if mount_subdir.exists():
            self.logger.info(f"发现mount子目录，使用输入路径作为基础目录: {input_path}")
            return input_path

        # 检查是否是WinPE相关目录
        if any(pattern in input_path.name.upper() for pattern in ["WIN", "PE", "WIN10", "WIN11"]):
            self.logger.info(f"检测到WinPE相关目录，使用输入路径: {input_path}")
            return input_path

        # 默认返回输入路径
        self.logger.info(f"使用输入路径作为基础目录: {input_path}")
        return input_path

    def _copy_directory_structure(self, source_dir: Path, target_dir: Path):
        """复制完整目录结构"""
        self.logger.info(f"复制目录结构: {source_dir} -> {target_dir}")

        # 删除已存在的目标目录
        if target_dir.exists():
            self.logger.info(f"删除已存在的目录: {target_dir}")
            shutil.rmtree(target_dir, ignore_errors=True)

        # 复制整个目录结构
        try:
            def ignore_sensitive_files(src, names):
                """忽略敏感文件和临时文件"""
                ignored = []
                for name in names:
                    upper_name = name.upper()
                    # 忽略挂载点、临时文件和系统文件
                    if any(pattern in upper_name for pattern in [
                        'MOUNT', 'TEMP', '$RECYCLE.BIN', 'SYSTEM VOLUME INFORMATION',
                        'DESKTOP.INI', 'THUMBS.DB', '.DS_STORE', 'SEARCHES', 'EVERYWHERE.SEARCH-MS',
                        'INDEXED LOCATIONS.SEARCH-MS', 'WINDOWSSHELL.MANIFEST'
                    ]):
                        ignored.append(name)
                return ignored

            # 使用自定义复制函数处理权限问题
            self._copy_with_permission_handling(source_dir, target_dir, ignore_sensitive_files)

            self.logger.info("目录结构复制完成")

        except Exception as e:
            self.logger.error(f"复制目录结构失败: {str(e)}")
            # 如果复制失败，尝试创建基本目录结构
            try:
                self.logger.info("尝试创建基本目录结构...")
                target_dir.mkdir(parents=True, exist_ok=True)

                # 创建基本目录
                basic_dirs = ['boot', 'sources', 'mount', 'Windows', 'Users']
                for dir_name in basic_dirs:
                    (target_dir / dir_name).mkdir(parents=True, exist_ok=True)

                self.logger.info("基本目录结构创建完成")
            except Exception as fallback_e:
                self.logger.error(f"创建基本目录结构也失败: {str(fallback_e)}")
                raise

    def _copy_with_permission_handling(self, src: Path, dst: Path, ignore_func=None):
        """带权限处理的复制函数"""
        import os
        import stat

        if not dst.exists():
            dst.mkdir(parents=True, exist_ok=True)

        errors = []

        for item in src.iterdir():
            if ignore_func and ignore_func(src, [item.name]):
                continue

            try:
                src_item = src / item.name
                dst_item = dst / item.name

                if src_item.is_dir():
                    # 递归复制目录
                    self._copy_with_permission_handling(src_item, dst_item, ignore_func)
                else:
                    # 复制文件，处理权限问题
                    try:
                        shutil.copy2(src_item, dst_item)
                    except PermissionError as pe:
                        # 尝试只读复制
                        try:
                            # 读取文件内容并写入
                            with open(src_item, 'rb') as src_file:
                                content = src_file.read()
                            with open(dst_item, 'wb') as dst_file:
                                dst_file.write(content)
                            self.logger.warning(f"文件权限受限，使用只读复制: {src_item}")
                        except Exception as e2:
                            errors.append((str(src_item), str(dst_item), str(e2)))
                            self.logger.warning(f"跳过文件 (权限/访问问题): {src_item}")
                    except Exception as e:
                        errors.append((str(src_item), str(dst_item), str(e)))
                        self.logger.warning(f"跳过文件 (其他问题): {src_item}")

            except Exception as e:
                errors.append((str(src / item.name), str(dst / item.name), str(e)))
                self.logger.warning(f"跳过项目 (访问问题): {src / item.name}")

        if errors:
            self.logger.warning(f"复制过程中遇到 {len(errors)} 个权限或访问问题")
            # 记录前几个错误详情
            for i, (src_path, dst_path, error) in enumerate(errors[:5]):
                self.logger.warning(f"  错误 {i+1}: {src_path} -> {dst_path}: {error}")
            if len(errors) > 5:
                self.logger.warning(f"  ... 还有 {len(errors) - 5} 个错误未显示")

    def _replace_boot_wim(self, target_base_dir: Path, output_dir: Path):
        """替换boot.wim文件"""
        self.logger.info("替换boot.wim文件...")

        # 查找源boot.wim文件 - 递归搜索目标目录
        source_boot_wim = None
        self.logger.info(f"开始搜索boot.wim文件在: {target_base_dir}")

        # 先检查常见位置
        possible_paths = [
            target_base_dir / "boot.wim",      # 根目录
            target_base_dir / "boot" / "boot.wim",
            target_base_dir / "sources" / "boot.wim",
        ]

        # 检查常见位置
        for path in possible_paths:
            if path.exists():
                source_boot_wim = path
                self.logger.info(f"在常见位置找到源boot.wim: {source_boot_wim}")
                break

        # 如果常见位置没找到，使用递归搜索
        if not source_boot_wim:
            try:
                for wim_file in target_base_dir.rglob("boot.wim"):
                    if wim_file.is_file():
                        source_boot_wim = wim_file
                        self.logger.info(f"通过递归搜索找到源boot.wim: {source_boot_wim}")
                        break
            except Exception as e:
                self.logger.warning(f"递归搜索boot.wim时出错: {str(e)}")

        # 如果还是没找到，列出所有WIM文件供调试
        if not source_boot_wim:
            try:
                all_wims = list(target_base_dir.rglob("*.wim"))
                if all_wims:
                    self.logger.warning("未找到boot.wim，但发现以下WIM文件:")
                    for wim in all_wims[:10]:  # 只显示前10个
                        self.logger.warning(f"  - {wim}")
                else:
                    self.logger.warning(f"在目录中未找到任何WIM文件: {target_base_dir}")
            except Exception as e:
                self.logger.warning(f"列出WIM文件时出错: {str(e)}")

            raise Exception(f"在目标目录中未找到boot.wim文件: {target_base_dir}。请检查boot.wim是否存在于根目录、boot或sources子目录中。")

        # 目标boot.wim路径
        target_boot_wim = output_dir / "boot" / "boot.wim"

        try:
            # 确保目标目录存在
            target_boot_wim.parent.mkdir(parents=True, exist_ok=True)

            # 备份原有的boot.wim（如果存在）
            if target_boot_wim.exists():
                backup_path = target_boot_wim.with_suffix('.wim.backup')
                shutil.move(str(target_boot_wim), str(backup_path))
                self.logger.info(f"备份原有boot.wim到: {backup_path}")

            # 复制新的boot.wim
            shutil.copy2(source_boot_wim, target_boot_wim)
            self.logger.info(f"boot.wim替换成功: {target_boot_wim}")

        except Exception as e:
            self.logger.error(f"替换boot.wim失败: {str(e)}")
            raise

    def _mount_boot_wim(self, output_dir: Path):
        """挂载boot.wim到mount目录"""
        self.logger.info("使用统一WIM管理器挂载boot.wim到mount目录...")

        boot_wim_path = output_dir / "boot" / "boot.wim"
        mount_dir = output_dir / "mount"

        if not boot_wim_path.exists():
            raise Exception(f"boot.wim文件不存在: {boot_wim_path}")

        try:
            # 使用统一WIM管理器挂载
            if self.wim_manager:
                self.logger.info(f"使用统一管理器挂载: {boot_wim_path}")
                success, message = self.wim_manager.mount_wim(output_dir, boot_wim_path)

                if success:
                    self.logger.info(f"boot.wim挂载成功: {mount_dir}")
                    return
                else:
                    self.logger.warning(f"统一管理器挂载失败: {message}，尝试备用方法")
            else:
                self.logger.warning("统一WIM管理器不可用，使用备用方法")

            # 备用方法：清理并创建挂载目录
            if mount_dir.exists():
                # 先尝试卸载（如果已挂载）
                self._unmount_directory(mount_dir)
                shutil.rmtree(mount_dir, ignore_errors=True)

            mount_dir.mkdir(parents=True, exist_ok=True)

            # 使用ADK管理器挂载WIM文件
            dism_path = self.adk_manager.get_dism_path()
            if not dism_path:
                # 尝试手动查找DISM路径
                from pathlib import Path
                possible_dism_paths = [
                    Path('C:/Program Files (x86)/Windows Kits/10/Assessment and Deployment Kit/Deployment Tools/amd64/DISM/dism.exe'),
                    Path('C:/Program Files/Windows Kits/10/Assessment and Deployment Kit/Deployment Tools/amd64/DISM/dism.exe')
                ]

                for path in possible_dism_paths:
                    if path.exists():
                        dism_path = path
                        self.logger.info(f"手动找到DISM工具: {dism_path}")
                        break

                if not dism_path:
                    raise Exception("未找到DISM工具")

            # 构建DISM挂载命令 - Windows格式
            cmd = [
                str(dism_path),
                "/Mount-Image",
                f"/ImageFile:{boot_wim_path}",
                f"/MountDir:{mount_dir}",
                "/Index:1"
            ]

            self.logger.info(f"执行备用DISM挂载命令: {' '.join(cmd)}")

            # 执行挂载命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode == 0:
                self.logger.info(f"boot.wim挂载成功: {mount_dir}")
            else:
                error_msg = f"DISM挂载失败，返回码: {result.returncode}\n错误信息: {result.stderr}"
                self.logger.error(error_msg)
                raise Exception(error_msg)

        except subprocess.TimeoutExpired:
            error_msg = "DISM挂载操作超时"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            self.logger.error(f"挂载boot.wim失败: {str(e)}")
            raise

        # 挂载成功后，添加DISM组件
        try:
            self._add_dism_components(mount_dir)
        except Exception as e:
            self.logger.warning(f"添加DISM组件时出错: {str(e)}")
            self.logger.info("继续执行后续步骤...")

        # 修复WinPE启动路径问题
        try:
            self._fix_winpe_target_path(mount_dir)
        except Exception as e:
            self.logger.warning(f"修复WinPE启动路径时出错: {str(e)}")
            self.logger.info("继续执行后续步骤...")

    def _add_dism_components(self, mount_dir: Path):
        """使用DISM向挂载的WinPE镜像添加组件"""
        self.logger.info("开始使用DISM添加WinPE组件...")

        # 需要添加的常用WinPE组件列表
        winpe_components = [
            "WinPE-WMI",           # WMI支持
            "WinPE-Scripting",     # PowerShell和脚本支持
            "WinPE-SecureStartup", # BitLocker支持
            "WinPE-Dot3Svc",       # WiFi支持
            "WinPE-NetFX",         # .NET Framework支持
            "WinPE-PowerShell",    # PowerShell
            "WinPE-DismCmdlets",   # DISM PowerShell cmdlets
            "WinPE-StorageWMI",    # 存储WMI
            "WinPE-HTA",           # HTML应用程序支持
        ]

        dism_path = self.adk_manager.get_dism_path()
        if not dism_path:
            self.logger.warning("未找到DISM工具，跳过组件添加")
            return

        # 查找WinPE组件包文件
        adk_winpe_path = self._find_winpe_packages_path()
        if not adk_winpe_path:
            self.logger.warning("未找到WinPE组件包，跳过组件添加")
            return

        self.logger.info(f"使用WinPE组件包路径: {adk_winpe_path}")

        success_count = 0
        total_count = len(winpe_components)

        for component in winpe_components:
            try:
                self.logger.info(f"正在添加组件: {component}")

                # 构建DISM添加组件命令
                cab_file = adk_winpe_path / f"{component}.cab"
                if not cab_file.exists():
                    self.logger.warning(f"组件包不存在: {cab_file}")
                    continue

                cmd = [
                    str(dism_path),
                    "/Image:{}".format(str(mount_dir)),
                    "/Add-Package",
                    "/PackagePath:{}".format(str(cab_file))
                ]

                self.logger.info(f"执行DISM命令添加组件 {component}: {' '.join(cmd)}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10分钟超时
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

                if result.returncode == 0:
                    self.logger.info(f"组件 {component} 添加成功")
                    success_count += 1
                else:
                    self.logger.warning(f"组件 {component} 添加失败，返回码: {result.returncode}")
                    if result.stderr:
                        self.logger.warning(f"错误信息: {result.stderr[:200]}...")

            except subprocess.TimeoutExpired:
                self.logger.warning(f"组件 {component} 添加超时")
            except Exception as e:
                self.logger.warning(f"组件 {component} 添加时出错: {str(e)}")

        self.logger.info(f"DISM组件添加完成: {success_count}/{total_count} 个组件添加成功")

    def _find_winpe_packages_path(self) -> Path:
        """查找WinPE组件包路径"""
        possible_paths = [
            Path("C:/Program Files (x86)/Windows Kits/10/Assessment and Deployment Kit/Windows Preinstallation Environment/amd64/WinPE_OCs"),
            Path("C:/Program Files/Windows Kits/10/Assessment and Deployment Kit/Windows Preinstallation Environment/amd64/WinPE_OCs"),
            Path("C:/Program Files (x86)/Windows Kits/10/Windows Preinstallation Environment/amd64/WinPE_OCs"),
            Path("C:/Program Files/Windows Kits/10/Windows Preinstallation Environment/amd64/WinPE_OCs"),
        ]

        for path in possible_paths:
            if path.exists() and any(path.glob("*.cab")):
                self.logger.info(f"找到WinPE组件包路径: {path}")
                return path

        self.logger.warning("未找到WinPE组件包路径")
        return None

    def _fix_winpe_target_path(self, mount_dir: Path):
        """修复WinPE启动时的目标路径问题

        修复Windows PE无法启动的问题：
        实际SYSTEMROOT目录(X:\windows)不同于配置的目录(X:\$windows.nbt\Windows)
        """
        self.logger.info("开始修复WinPE启动路径问题...")

        try:
            # 获取DISM路径
            dism_path = self.adk_manager.get_dism_path()
            if not dism_path:
                # 尝试手动查找DISM路径
                from pathlib import Path
                possible_dism_paths = [
                    Path('C:/Program Files (x86)/Windows Kits/10/Assessment and Deployment Kit/Deployment Tools/amd64/DISM/dism.exe'),
                    Path('C:/Program Files/Windows Kits/10/Assessment and Deployment Kit/Deployment Tools/amd64/DISM/dism.exe')
                ]

                for path in possible_dism_paths:
                    if path.exists():
                        dism_path = path
                        self.logger.info(f"手动找到DISM工具: {dism_path}")
                        break

                if not dism_path:
                    self.logger.warning("未找到DISM工具，跳过路径修复")
                    return

            # 方法1：使用DISM设置正确的目标路径
            self.logger.info("使用DISM设置WinPE目标路径...")

            # 设置目标路径为X:\ (标准的WinPE路径)
            cmd = [
                str(dism_path),
                "/Image:" + str(mount_dir),
                "/Set-TargetPath:X:\\"
            ]

            self.logger.info(f"执行DISM命令: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode == 0:
                self.logger.info("✅ DISM设置目标路径成功")
                log_build_step("路径修复", "DISM设置目标路径成功")
            else:
                self.logger.warning(f"DISM设置目标路径失败: {result.stderr}")
                log_build_step("路径修复", f"DISM设置目标路径失败: {result.stderr}", "warning")

            # 方法1.5：额外设置确保SYSTEMROOT正确
            self.logger.info("确保WinPE SYSTEMROOT路径正确...")
            cmd_systemroot = [
                str(dism_path),
                "/Image:" + str(mount_dir),
                "/Set-Sysroot:X:\\Windows"
            ]

            self.logger.info(f"执行DISM SYSTEMROOT命令: {' '.join(cmd_systemroot)}")

            result_systemroot = subprocess.run(
                cmd_systemroot,
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result_systemroot.returncode == 0:
                self.logger.info("✅ DISM设置SYSTEMROOT成功")
                log_build_step("路径修复", "DISM设置SYSTEMROOT成功")
            else:
                self.logger.warning(f"DISM设置SYSTEMROOT失败: {result_systemroot.stderr}")
                log_build_step("路径修复", f"DISM设置SYSTEMROOT失败: {result_systemroot.stderr}", "warning")

            # 方法2：检查并修复注册表中的路径配置
            self._fix_registry_target_paths(mount_dir)

            # 方法3：验证修复结果
            self._verify_target_path_fix(mount_dir)

            self.logger.info("WinPE启动路径修复完成")

        except subprocess.TimeoutExpired:
            self.logger.warning("DISM路径修复操作超时")
        except Exception as e:
            self.logger.warning(f"修复WinPE启动路径时发生错误: {str(e)}")

    def _fix_registry_target_paths(self, mount_dir: Path):
        """修复注册表中的目标路径配置"""
        self.logger.info("检查并修复注册表中的路径配置...")

        try:
            # 创建WinPE启动配置文件，确保路径正确
            winpeshl_ini = mount_dir / "Windows" / "System32" / "winpeshl.ini"
            if not winpeshl_ini.exists():
                self.logger.info("创建WinPE启动配置文件...")
                winpeshl_content = """[LaunchApps]
%windir%\\System32\\cmd.exe
"""
                try:
                    with open(winpeshl_ini, 'w', encoding='utf-8') as f:
                        f.write(winpeshl_content)
                    self.logger.info("✅ WinPE启动配置文件创建成功")
                except Exception as e:
                    self.logger.warning(f"创建WinPE启动配置文件失败: {str(e)}")

            # 修复启动配置文件中的路径问题
            setupreg_cmd = mount_dir / "Windows" / "System32" / "setupreg.cmd"
            if setupreg_cmd.exists():
                self.logger.info("检查并修复setupreg.cmd中的路径配置...")
                try:
                    with open(setupreg_cmd, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 替换可能存在的错误路径
                    original_content = content
                    content = content.replace('X:\\$windows.~bt\\Windows', 'X:\\Windows')
                    content = content.replace('X:\\$windows.~bt', 'X:\\')

                    if content != original_content:
                        with open(setupreg_cmd, 'w', encoding='utf-8') as f:
                            f.write(content)
                        self.logger.info("✅ setupreg.cmd路径配置修复成功")
                    else:
                        self.logger.info("setupreg.cmd路径配置正常")
                except Exception as e:
                    self.logger.warning(f"修复setupreg.cmd失败: {str(e)}")

            # 检查WinPE注册表文件
            registry_files = [
                mount_dir / "Windows" / "System32" / "config" / "SOFTWARE",
                mount_dir / "Windows" / "System32" / "config" / "SYSTEM"
            ]

            for reg_file in registry_files:
                if reg_file.exists():
                    self.logger.info(f"检查注册表文件: {reg_file.name}")
                    # 使用reg.exe查询和修复注册表中的路径配置
                    if reg_file.name == "SYSTEM":
                        try:
                            # 检查CurrentControlSet\\Control\\Session Manager\\Environment中的SystemRoot值
                            self.logger.info("检查系统环境变量中的SystemRoot设置...")
                            # 这里可以添加reg.exe调用修复注册表
                        except Exception as e:
                            self.logger.warning(f"检查SYSTEM注册表失败: {str(e)}")
                else:
                    self.logger.warning(f"注册表文件不存在: {reg_file}")

        except Exception as e:
            self.logger.warning(f"检查注册表时出错: {str(e)}")

    def _verify_target_path_fix(self, mount_dir: Path):
        """验证目标路径修复结果"""
        self.logger.info("验证目标路径修复结果...")

        try:
            # 检查关键目录结构
            windows_dir = mount_dir / "Windows"
            if not windows_dir.exists():
                self.logger.warning("Windows目录不存在，可能需要创建")

            # 检查关键的启动文件
            critical_files = [
                windows_dir / "System32" / "winload.exe",
                windows_dir / "System32" / "winresume.exe",
                windows_dir / "Panther" / "setupact.log"
            ]

            for file_path in critical_files:
                if file_path.exists():
                    self.logger.info(f"✅ 关键文件存在: {file_path.name}")
                else:
                    self.logger.warning(f"⚠️ 关键文件缺失: {file_path.name}")

        except Exception as e:
            self.logger.warning(f"验证修复结果时出错: {str(e)}")

    def _unmount_directory(self, mount_dir: Path):
        """卸载目录"""
        try:
            # 使用统一WIM管理器卸载
            if self.wim_manager and mount_dir.exists():
                self.logger.info(f"使用统一管理器卸载目录: {mount_dir}")
                # 尝试确定构建目录（mount_dir的父目录）
                build_dir = mount_dir.parent
                success, message = self.wim_manager.unmount_wim(build_dir, commit=False)

                if success:
                    self.logger.info(f"目录卸载成功: {mount_dir}")
                    return
                else:
                    self.logger.warning(f"统一管理器卸载失败: {message}，尝试备用方法")
            else:
                self.logger.warning("统一WIM管理器不可用，使用备用方法")

            # 备用方法：使用DISM卸载
            dism_path = self.adk_manager.get_dism_path()
            if not dism_path:
                # 尝试手动查找DISM路径
                from pathlib import Path
                possible_dism_paths = [
                    Path('C:/Program Files (x86)/Windows Kits/10/Assessment and Deployment Kit/Deployment Tools/amd64/DISM/dism.exe'),
                    Path('C:/Program Files/Windows Kits/10/Assessment and Deployment Kit/Deployment Tools/amd64/DISM/dism.exe')
                ]

                for path in possible_dism_paths:
                    if path.exists():
                        dism_path = path
                        break

            if dism_path and mount_dir.exists():
                cmd = [
                    str(dism_path),
                    "/Unmount-Image",
                    f"/MountDir:{mount_dir}",
                    "/Discard"
                ]

                self.logger.info(f"执行备用DISM卸载命令: {' '.join(cmd)}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

                if result.returncode == 0:
                    self.logger.info(f"目录卸载成功: {mount_dir}")
                else:
                    self.logger.warning(f"DISM卸载失败，尝试强制删除: {result.stderr}")

        except Exception as e:
            self.logger.warning(f"卸载目录时出错: {str(e)}")

    def _prepare_output_directory(self, source_base_dir: Path, target_base_dir: Path, output_dir: Path):
        """准备输出目录，确保结构与源目录一致"""
        self.logger.info(f"准备输出目录: {output_dir}")

        # 删除已存在的目录
        if output_dir.exists():
            shutil.rmtree(output_dir)

        # 创建新的目录结构，复制源目录的结构
        output_dir.mkdir(parents=True, exist_ok=True)

        # 创建与源目录相同的结构
        required_dirs = ["boot", "mount", "efi", "zh-CN"]

        for dir_name in required_dirs:
            (output_dir / dir_name).mkdir(exist_ok=True)

        # 复制根目录文件（如bootmgr, bootmgr.efi等）
        root_files = ["bootmgr", "bootmgr.efi"]
        for file_name in root_files:
            source_file = source_base_dir / file_name
            if source_file.exists():
                target_file = output_dir / file_name
                try:
                    shutil.copy2(source_file, target_file, follow_symlinks=False)
                    self.logger.info(f"复制根文件: {file_name}")
                except Exception as e:
                    self.logger.warning(f"复制根文件失败 {file_name}: {str(e)}")

        self.logger.info("输出目录准备完成")

    def _copy_base_structure(self, target_mount: Path, output_dir: Path):
        """复制基础结构"""
        self.logger.info("复制目标版本的基础结构...")

        output_mount = output_dir / "mount"

        # 复制核心目录结构
        core_dirs = ["Windows", "Program Files", "Users", "EFI", "boot", "sources"]

        for core_dir in core_dirs:
            source_dir = target_mount / core_dir
            target_dir = output_mount / core_dir

            if source_dir.exists():
                self.logger.info(f"复制目录: {core_dir}")
                self._copy_directory_with_permissions(source_dir, target_dir)

        self.logger.info("基础结构复制完成")

    def _migrate_custom_components(self, source_mount: Path, output_dir: Path, config: Dict):
        """迁移自定义组件"""
        self.logger.info("开始迁移自定义组件...")

        output_mount = output_dir / "mount"
        migrated = {}

        # 迁移驱动程序
        if config.get("migrate_drivers", True):
            migrated["drivers"] = self._migrate_drivers(source_mount, output_mount)

        # 迁移桌面环境
        if config.get("migrate_desktop", True):
            migrated["desktop"] = self._migrate_desktop_environment(source_mount, output_mount)

        # 迁移启动脚本
        if config.get("migrate_scripts", True):
            migrated["scripts"] = self._migrate_startup_scripts(source_mount, output_mount)

        # 迁移自定义程序
        if config.get("migrate_programs", True):
            migrated["programs"] = self._migrate_custom_programs(source_mount, output_mount)

        # 迁移配置文件
        if config.get("migrate_config", True):
            migrated["config"] = self._migrate_config_files(source_mount, output_mount)

        self.logger.info(f"自定义组件迁移完成: {list(migrated.keys())}")
        return migrated

    def _migrate_drivers(self, source_mount: Path, output_mount: Path) -> Dict:
        """迁移驱动程序"""
        source_drivers = source_mount / "Drivers"
        output_drivers = output_mount / "Drivers"

        migration_result = {
            "source_exists": source_drivers.exists(),
            "files_migrated": 0,
            "errors": []
        }

        if not source_drivers.exists():
            return migration_result

        try:
            # 创建驱动目录
            output_drivers.mkdir(parents=True, exist_ok=True)

            # 复制所有驱动文件
            for item in source_drivers.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(source_drivers)
                    target_path = output_drivers / rel_path

                    # 确保目标目录存在
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    try:
                        shutil.copy2(item, target_path)
                        migration_result["files_migrated"] += 1
                    except Exception as e:
                        migration_result["errors"].append(f"复制驱动失败 {rel_path}: {str(e)}")

            self.logger.info(f"驱动迁移完成: {migration_result['files_migrated']} 个文件")

        except Exception as e:
            migration_result["errors"].append(f"驱动迁移失败: {str(e)}")

        return migration_result

    def _migrate_desktop_environment(self, source_mount: Path, output_mount: Path) -> Dict:
        """迁移桌面环境"""
        source_system32 = source_mount / "Windows" / "System32"
        output_system32 = output_mount / "Windows" / "System32"

        migration_result = {
            "desktop_files_migrated": [],
            "errors": []
        }

        # 查找桌面环境相关文件
        desktop_patterns = [
            "WinXShell*", "Cairo*", "Desktop*", "Shell*"
        ]

        for pattern in desktop_patterns:
            for source_file in source_system32.glob(pattern):
                if source_file.is_file():
                    target_file = output_system32 / source_file.name

                    try:
                        shutil.copy2(source_file, target_file)
                        migration_result["desktop_files_migrated"].append(source_file.name)
                        self.logger.info(f"迁移桌面文件: {source_file.name}")
                    except Exception as e:
                        migration_result["errors"].append(f"迁移桌面文件失败 {source_file.name}: {str(e)}")

        # 迁移Programs目录
        source_programs = source_system32 / "Programs"
        output_programs = output_system32 / "Programs"

        if source_programs.exists():
            try:
                output_programs.mkdir(parents=True, exist_ok=True)
                self._copy_directory_with_permissions(source_programs, output_programs)
                migration_result["desktop_files_migrated"].append("Programs目录")
                self.logger.info("迁移Programs目录")
            except Exception as e:
                migration_result["errors"].append(f"迁移Programs目录失败: {str(e)}")

        return migration_result

    def _migrate_startup_scripts(self, source_mount: Path, output_mount: Path) -> Dict:
        """迁移启动脚本"""
        source_system32 = source_mount / "Windows" / "System32"
        output_system32 = output_mount / "Windows" / "System32"

        migration_result = {
            "scripts_migrated": [],
            "errors": []
        }

        # 迁移启动脚本文件
        script_files = ["winpeshl.ini", "startnet.cmd", "custom.cmd"]

        for script_file in script_files:
            source_script = source_system32 / script_file
            target_script = output_system32 / script_file

            if source_script.exists():
                try:
                    shutil.copy2(source_script, target_script)
                    migration_result["scripts_migrated"].append(script_file)
                    self.logger.info(f"迁移启动脚本: {script_file}")
                except Exception as e:
                    migration_result["errors"].append(f"迁移脚本失败 {script_file}: {str(e)}")

        # 迁移其他CMD/BAT文件
        source_cmd_files = list(source_system32.glob("*.cmd"))
        source_bat_files = list(source_system32.glob("*.bat"))
        for script_file in source_cmd_files + source_bat_files:
            if script_file.name not in ["startnet.cmd"] and script_file.exists():
                target_script = output_system32 / script_file.name

                try:
                    shutil.copy2(script_file, target_script)
                    migration_result["scripts_migrated"].append(script_file.name)
                except Exception as e:
                    migration_result["errors"].append(f"迁移脚本失败 {script_file.name}: {str(e)}")

        return migration_result

    def _migrate_custom_programs(self, source_mount: Path, output_mount: Path) -> Dict:
        """迁移自定义程序"""
        migration_result = {
            "programs_migrated": [],
            "errors": []
        }

        # 检查各种自定义程序目录
        custom_dirs = [
            source_mount / "Tools",
            source_mount / "Scripts",
            source_mount / "Custom"
        ]

        for custom_dir in custom_dirs:
            if custom_dir.exists():
                target_dir = output_mount / custom_dir.name

                try:
                    self._copy_directory_with_permissions(custom_dir, target_dir)
                    migration_result["programs_migrated"].append(custom_dir.name)
                    self.logger.info(f"迁移自定义目录: {custom_dir.name}")
                except Exception as e:
                    migration_result["errors"].append(f"迁移目录失败 {custom_dir.name}: {str(e)}")

        return migration_result

    def _migrate_config_files(self, source_mount: Path, output_mount: Path) -> Dict:
        """迁移配置文件"""
        source_system32 = source_mount / "Windows" / "System32"
        output_system32 = output_mount / "Windows" / "System32"

        migration_result = {
            "config_files_migrated": [],
            "errors": []
        }

        # 迁移PEConfig目录
        source_peconfig = source_system32 / "PEConfig"
        output_peconfig = output_system32 / "PEConfig"

        if source_peconfig.exists():
            try:
                self._copy_directory_with_permissions(source_peconfig, output_peconfig)
                migration_result["config_files_migrated"].append("PEConfig目录")
                self.logger.info("迁移PEConfig目录")
            except Exception as e:
                migration_result["errors"].append(f"迁移PEConfig失败: {str(e)}")

        return migration_result

    def _copy_boot_wim(self, target_base_dir: Path, output_dir: Path):
        """复制boot.wim文件"""
        self.logger.info("复制boot.wim文件...")

        # boot.wim通常在源目录的boot文件夹中，不在挂载目录中
        source_boot_wim = target_base_dir / "boot" / "boot.wim"
        target_boot_wim = output_dir / "boot" / "boot.wim"

        if source_boot_wim.exists():
            try:
                # 确保目标目录存在
                target_boot_wim.parent.mkdir(parents=True, exist_ok=True)

                # 复制文件
                shutil.copy2(source_boot_wim, target_boot_wim)
                self.logger.info(f"boot.wim复制成功: {target_boot_wim}")

            except Exception as e:
                self.logger.error(f"复制boot.wim失败: {str(e)}")
                raise Exception(f"复制boot.wim失败: {str(e)}")
        else:
            self.logger.warning(f"源boot.wim文件不存在: {source_boot_wim}")
            # 尝试从其他可能的位置查找boot.wim
            alternative_paths = [
                target_base_dir / "sources" / "boot.wim",
                target_base_dir.parent / "boot" / "boot.wim"
            ]

            for alt_path in alternative_paths:
                if alt_path.exists():
                    try:
                        shutil.copy2(alt_path, target_boot_wim)
                        self.logger.info(f"从备用位置复制boot.wim成功: {alt_path}")
                        return
                    except Exception as e:
                        self.logger.warning(f"从备用位置复制boot.wim失败 {alt_path}: {str(e)}")

            self.logger.error("未找到任何可用的boot.wim文件")

    def _validate_and_fix(self, output_dir: Path):
        """验证和修复"""
        self.logger.info("验证和修复输出...")

        output_mount = output_dir / "mount"

        # 检查关键目录
        required_dirs = ["Windows", "Windows/System32", "boot", "sources"]

        for req_dir in required_dirs:
            dir_path = output_mount / req_dir
            if not dir_path.exists():
                self.logger.warning(f"缺少关键目录: {req_dir}")
                dir_path.mkdir(parents=True, exist_ok=True)

        # 检查关键文件
        required_files = [
            "Windows/System32/kernel32.dll",
            "Windows/System32/user32.dll",
            "Windows/System32/ntdll.dll"
        ]

        for req_file in required_files:
            file_path = output_mount / req_file
            if not file_path.exists():
                self.logger.warning(f"缺少关键文件: {req_file}")

        self.logger.info("验证和修复完成")

    def _create_new_wim(self, output_dir: Path) -> Path:
        """创建新的WIM文件"""
        self.logger.info("创建新的WIM文件...")

        output_mount = output_dir / "mount"
        new_wim_path = output_dir / "replaced_winpe.wim"

        # 构建DISM命令
        args = [
            "/Capture-Image",
            f"/ImageDir:{output_mount}",
            f"/DestinationImageFile:{new_wim_path}",
            "/Name:WinPE Version Replaced",
            "/Description:WinPE with component migration and version replacement",
            "/Compress:max"
        ]

        # 执行DISM命令
        success, stdout, stderr = self.adk_manager.run_dism_command(args)

        if success:
            self.logger.info(f"新WIM文件创建成功: {new_wim_path}")
            return new_wim_path
        else:
            error_msg = f"创建WIM文件失败: {stderr}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def _copy_directory_with_permissions(self, src: Path, dst: Path):
        """复制目录并保持权限，处理权限问题"""
        try:
            # 如果目标目录存在，先删除
            if dst.exists():
                try:
                    shutil.rmtree(dst)
                except PermissionError:
                    self.logger.warning(f"无法删除目标目录，尝试强制处理: {dst}")
                    # 尝试递归修改权限后再删除
                    for root, dirs, files in os.walk(dst):
                        for d in dirs:
                            try:
                                os.chmod(os.path.join(root, d), 0o755)
                            except:
                                pass
                        for f in files:
                            try:
                                file_path = Path(root) / f
                                file_path.chmod(0o644)
                            except:
                                pass
                    shutil.rmtree(dst)

            # 复制目录，忽略权限问题
            def ignore_permissions(src_path, names):
                ignored = []
                for name in names:
                    full_path = Path(src_path) / name
                    # 忽略系统文件和有权限问题的目录
                    if any(pattern in str(full_path).upper() for pattern in [
                        'LOGFILES\\WMI\\RTBACKUP',
                        'SYSTEM32\\LOGFILES\\WMI',
                        '$RECYCLE.BIN',
                        'SYSTEM VOLUME INFORMATION',
                        'RECOVERY'
                    ]):
                        ignored.append(name)
                return ignored

            shutil.copytree(src, dst,
                          dirs_exist_ok=True,
                          ignore=ignore_permissions,
                          copy_function=shutil.copy2)

            # 修复权限（跳过有问题的文件）
            for root, dirs, files in os.walk(dst):
                for d in dirs:
                    try:
                        os.chmod(os.path.join(root, d), 0o755)
                    except (PermissionError, OSError):
                        pass
                for f in files:
                    file_path = Path(root) / f
                    try:
                        file_path.chmod(0o644)
                    except (PermissionError, OSError):
                        pass

        except Exception as e:
            self.logger.error(f"复制目录失败: {str(e)}")
            raise


class VersionReplacer:
    """WinPE版本替换器主类"""

    def __init__(self, config_manager, adk_manager, unified_wim_manager=None):
        self.config = config_manager
        self.adk = adk_manager
        self.wim_manager = unified_wim_manager
        self.logger = get_logger("VersionReplacer")

        self.version_detector = WIMVersionDetector(adk_manager)
        self.component_analyzer = ComponentAnalyzer(adk_manager)
        self.migration_manager = ComponentMigrationManager(adk_manager)

    def analyze_components(self, mount_path: Path, output_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        分析组件并生成报告

        Args:
            mount_path: 挂载路径
            output_file: 输出文件路径（可选）

        Returns:
            组件分析结果
        """
        self.logger.info(f"开始分析组件: {mount_path}")

        try:
            # 执行组件分析
            analysis = self.component_analyzer.analyze_wim_components(mount_path)

            # 生成中文报告
            report = self._generate_chinese_report(analysis)

            # 保存报告
            if output_file:
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                self.logger.info(f"组件分析报告已保存: {output_file}")

            return analysis

        except Exception as e:
            error_msg = f"组件分析失败: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def execute_version_replacement(self,
                                  source_mount: Path,
                                  target_mount: Path,
                                  output_dir: Path,
                                  migration_config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        执行完整的版本替换

        Args:
            source_mount: 源WIM挂载路径
            target_mount: 目标WIM挂载路径
            output_dir: 输出目录
            migration_config: 迁移配置

        Returns:
            替换结果
        """
        self.logger.info("开始执行WinPE版本替换...")

        if migration_config is None:
            migration_config = self._get_default_migration_config()

        try:
            # 执行替换
            result = self.migration_manager.execute_version_replacement(
                source_mount, target_mount, output_dir, migration_config
            )

            if result["success"]:
                self.logger.info("WinPE版本替换完成")
                log_system_event("版本替换", "WinPE版本替换成功", "info")
            else:
                self.logger.error("WinPE版本替换失败")
                log_system_event("版本替换", "WinPE版本替换失败", "error")

            return result

        except Exception as e:
            error_msg = f"版本替换执行失败: {str(e)}"
            self.logger.error(error_msg)
            log_system_event("版本替换", error_msg, "error")

            return {
                "success": False,
                "errors": [error_msg],
                "steps": {},
                "migrated_components": {},
                "output_wim": None
            }

    def execute_simple_version_replacement(self,
                                          source_base_dir: Path,
                                          target_base_dir: Path,
                                          output_dir: Path) -> Dict[str, Any]:
        """
        执行简化的版本替换流程
        1. 复制源目录结构
        2. 替换boot.wim
        3. 挂载boot.wim到mount目录

        Args:
            source_base_dir: 源目录 (如: D:\APP\WinPEManager\WinPE_amd64\0WIN11PE)
            target_base_dir: 目标目录 (如: D:\APP\WinPEManager\WinPE_amd64\0WIN10OLD)
            output_dir: 输出目录 (如: D:\APP\WinPEManager\WinPE_amd64\WIN10REPLACED_REPLACED)

        Returns:
            替换结果
        """
        self.logger.info("开始执行简化WinPE版本替换...")
        self.logger.info(f"源目录: {source_base_dir}")
        self.logger.info(f"目标目录: {target_base_dir}")
        self.logger.info(f"输出目录: {output_dir}")

        try:
            # 验证输入目录
            if not source_base_dir.exists():
                raise Exception(f"源目录不存在: {source_base_dir}")
            if not target_base_dir.exists():
                raise Exception(f"目标目录不存在: {target_base_dir}")

            # 执行新的替换流程
            result = self.migration_manager.execute_version_replacement(
                source_base_dir, target_base_dir, output_dir, {}
            )

            if result["success"]:
                self.logger.info("简化WinPE版本替换完成")
                log_system_event("简化版本替换", "WinPE版本替换成功", "info")
            else:
                self.logger.error("简化WinPE版本替换失败")
                log_system_event("简化版本替换", "WinPE版本替换失败", "error")

            return result

        except Exception as e:
            error_msg = f"简化版本替换执行失败: {str(e)}"
            self.logger.error(error_msg)
            log_system_event("简化版本替换", error_msg, "error")

            return {
                "success": False,
                "errors": [error_msg],
                "steps": {},
                "migrated_components": {},
                "output_wim": None
            }

    def _generate_chinese_report(self, analysis: Dict[str, Any]) -> str:
        """生成中文分析报告"""
        report = []
        report.append("# WinPE组件分析报告")
        report.append("")
        report.append(f"分析时间: {analysis['analysis_time']}")
        report.append(f"挂载路径: {analysis['mount_path']}")
        report.append("")

        # 基本信息
        report.append("## 基本信息")
        basic = analysis['basic_info']
        report.append(f"- Windows目录存在: {'是' if basic['windows_dir_exists'] else '否'}")
        report.append(f"- System32目录存在: {'是' if basic['system32_dir_exists'] else '否'}")
        report.append(f"- 总大小: {self._format_size(basic['total_size'])}")
        report.append(f"- 文件数量: {basic['file_count']:,}")
        report.append(f"- 目录数量: {basic['directory_count']:,}")
        report.append("")

        # 核心文件
        report.append("## 核心文件")
        core_files = analysis['core_files']
        for file_name, file_info in core_files.items():
            status = "✓ 存在" if file_info['exists'] else "✗ 不存在"
            size_str = f"({self._format_size(file_info['size'])})" if file_info['exists'] else ""
            report.append(f"- {file_name}: {status} {size_str}")
        report.append("")

        # 自定义组件
        report.append("## 自定义组件")
        custom = analysis['custom_components']
        for comp_name, comp_info in custom.items():
            if isinstance(comp_info, dict):
                status = "✓ 存在" if comp_info.get('exists', False) else "✗ 不存在"
                files = comp_info.get('files', [])
                file_count = len(files) if files else 0
                report.append(f"- {comp_name}: {status} ({file_count} 个文件)")
            else:
                # 如果comp_info不是字典，跳过或处理其他情况
                report.append(f"- {comp_name}: 数据格式错误")
        report.append("")

        # 启动脚本
        report.append("## 启动脚本")
        scripts = analysis['startup_scripts']
        for script_name, script_info in scripts.items():
            if isinstance(script_info, dict):
                if script_info.get('exists', False):
                    report.append(f"- {script_name}: ✓ 存在")
                    commands = script_info.get('commands', [])
                    if commands:
                        for cmd in commands[:3]:  # 只显示前3个命令
                            report.append(f"  - {cmd}")
                        if len(commands) > 3:
                            report.append(f"  - ... 还有 {len(commands) - 3} 个命令")
                else:
                    report.append(f"- {script_name}: ✗ 不存在")
            else:
                # 如果script_info不是字典，跳过或处理其他情况
                report.append(f"- {script_name}: 数据格式错误")
        report.append("")

        # 驱动程序
        report.append("## 驱动程序")
        drivers = analysis['drivers']
        report.append(f"- 驱动目录存在: {'是' if drivers['drivers_dir_exists'] else '否'}")
        report.append(f"- 驱动总数: {drivers['total_drivers']}")

        if drivers['driver_categories']:
            report.append("- 驱动分类:")
            for category, files in drivers['driver_categories'].items():
                report.append(f"  - {category}: {len(files)} 个")
        report.append("")

        # 桌面环境
        report.append("## 桌面环境")
        desktop = analysis['desktop_environment']
        report.append(f"- Shell类型: {desktop['shell_type']}")

        shell_types = ['explorer', 'winxshell', 'cairo_shell']
        for shell_type in shell_types:
            shell_info = desktop[shell_type]
            status = "✓ 存在" if shell_info['exists'] else "✗ 不存在"
            report.append(f"- {shell_type.replace('_', ' ').title()}: {status}")
        report.append("")

        # 完整性检查
        report.append("## 完整性检查")
        integrity = analysis['integrity_check']
        report.append(f"- 整体状态: {integrity['overall_status']}")
        report.append(f"- Windows目录: {'✓' if integrity['windows_directory'] else '✗'}")
        report.append(f"- System32目录: {'✓' if integrity['system32_directory'] else '✗'}")
        report.append(f"- 启动文件: {'✓' if integrity['boot_files']['all_present'] else '✗'}")
        report.append(f"- 注册表文件: {'✓' if integrity['registry_files']['all_present'] else '✗'}")
        report.append(f"- 关键DLL: {'✓' if integrity['critical_dlls']['all_present'] else '✗'}")
        report.append("")

        # 网络组件
        report.append("## 网络组件")
        networking = analysis['networking']
        existing_components = [name for name, info in networking['network_components'].items() if info['exists']]
        report.append(f"- 可用网络组件: {len(existing_components)}")
        for comp in existing_components[:5]:  # 只显示前5个
            report.append(f"  - {comp}")
        if len(existing_components) > 5:
            report.append(f"  - ... 还有 {len(existing_components) - 5} 个组件")
        report.append("")

        # 外部程序和高级组件
        if 'external_programs' in analysis:
            report.append("## 外部程序和高级组件")
            external = analysis['external_programs']

            # WinXShell信息
            if external.get('winxshell', {}).get('exists', False):
                winxshell = external['winxshell']
                report.append("- WinXShell: ✓ 存在")
                if winxshell.get('version'):
                    report.append(f"  - 版本: {winxshell['version']}")
                if winxshell.get('config_files'):
                    report.append(f"  - 配置文件: {len(winxshell['config_files'])} 个")
                if winxshell.get('plugins'):
                    report.append(f"  - 插件: {len(winxshell['plugins'])} 个")

            # 第三方工具
            third_party_tools = []
            third_party_data = external.get('third_party_tools', {})
            if isinstance(third_party_data, dict):
                for tool_name, tool_info in third_party_data.items():
                    if isinstance(tool_info, dict) and tool_info.get('exists', False):
                        third_party_tools.append(tool_name)
            elif isinstance(third_party_data, list):
                # 如果third_party_tools是列表，直接提取工具名
                for tool_info in third_party_data:
                    if isinstance(tool_info, dict):
                        tool_name = tool_info.get('name', '未知工具')
                        if tool_info.get('exists', False):
                            third_party_tools.append(tool_name)
                    elif isinstance(tool_info, str):
                        third_party_tools.append(tool_info)

            if third_party_tools:
                report.append(f"- 第三方工具: {', '.join(third_party_tools)}")

            # 启动机制
            startup_mechanisms = external.get('startup_mechanisms', {})
            if startup_mechanisms.get('peconfig_exists', False):
                report.append("- PEConfig启动机制: ✓ 存在")
                commands = startup_mechanisms.get('peconfig_commands', [])
                if commands:
                    report.append(f"  - 启动命令: {len(commands)} 个")

            if startup_mechanisms.get('winpeshl_exists', False):
                report.append("- Winpeshl启动机制: ✓ 存在")

            # 配置文件统计
            config_files = external.get('config_files', {})
            total_configs = sum(len(files) for files in config_files.values() if isinstance(files, list))
            if total_configs > 0:
                report.append(f"- 配置文件: {total_configs} 个")
                for config_type, files in config_files.items():
                    if files and isinstance(files, list):
                        report.append(f"  - {config_type}: {len(files)} 个")

            report.append("")

        report.append("---")
        report.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(report)

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _get_default_migration_config(self) -> Dict:
        """获取默认迁移配置"""
        return {
            "migrate_drivers": True,
            "migrate_desktop": True,
            "migrate_scripts": True,
            "migrate_programs": True,
            "migrate_config": True,
            "preserve_networking": True,
            "preserve_registry": True
        }