#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组件分析器模块
分析源和目标WIM的组件差异，生成迁移计划
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

from utils.logger import get_logger


class ComponentAnalyzer:
    """组件分析器 - 分析源和目标WIM的差异"""

    def __init__(self):
        self.logger = get_logger("ComponentAnalyzer")

    def analyze_wim_differences(self, source_mount: Path, target_mount: Path) -> Dict[str, Any]:
        """
        分析源和目标WIM的组件差异

        Args:
            source_mount: 源WIM挂载路径
            target_mount: 目标WIM挂载路径

        Returns:
            差异分析结果
        """
        self.logger.info("开始分析源和目标WIM的组件差异...")

        analysis = {
            "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_info": self._analyze_wim_structure(source_mount, "源WIM"),
            "target_info": self._analyze_wim_structure(target_mount, "目标WIM"),
            "differences": {},
            "migration_plan": {}
        }

        # 分析核心文件差异
        analysis["differences"]["core_files"] = self._compare_core_files(
            source_mount, target_mount
        )

        # 分析外部程序差异
        analysis["differences"]["external_programs"] = self._compare_external_programs(
            source_mount, target_mount
        )

        # 分析启动脚本差异
        analysis["differences"]["startup_scripts"] = self._compare_startup_scripts(
            source_mount, target_mount
        )

        # 分析驱动程序差异
        analysis["differences"]["drivers"] = self._compare_drivers(
            source_mount, target_mount
        )

        # 生成迁移计划
        analysis["migration_plan"] = self._generate_migration_plan(analysis["differences"])

        self.logger.info("WIM组件差异分析完成")
        return analysis

    def _analyze_wim_structure(self, mount_path: Path, label: str) -> Dict[str, Any]:
        """分析WIM基本结构"""
        structure = {
            "label": label,
            "path": str(mount_path),
            "windows_exists": (mount_path / "Windows").exists(),
            "system32_exists": (mount_path / "Windows" / "System32").exists(),
            "boot_exists": (mount_path / "Windows" / "System32" / "winpe.wim").exists(),
            "custom_components": self._find_custom_components(mount_path)
        }

        return structure

    def _compare_core_files(self, source_mount: Path, target_mount: Path) -> Dict[str, Any]:
        """比较核心文件差异"""
        source_system32 = source_mount / "Windows" / "System32"
        target_system32 = target_mount / "Windows" / "System32"

        core_files = [
            "winpe.wim", "winpeshl.exe", "wpeinit.exe", "wpeutil.exe",
            "setup.exe", "winload.exe", "bootmgr.exe"
        ]

        differences = {}
        for file_name in core_files:
            source_file = source_system32 / file_name
            target_file = target_system32 / file_name

            differences[file_name] = {
                "source_exists": source_file.exists(),
                "target_exists": target_file.exists(),
                "source_size": source_file.stat().st_size if source_file.exists() else 0,
                "target_size": target_file.stat().st_size if target_file.exists() else 0,
                "needs_replacement": False
            }

            # 如果目标存在且版本不同，需要替换
            if target_file.exists() and source_file.exists():
                source_size = source_file.stat().st_size
                target_size = target_file.stat().st_size
                if source_size != target_size:
                    differences[file_name]["needs_replacement"] = True
            elif target_file.exists():
                differences[file_name]["needs_replacement"] = True

        return differences

    def _compare_external_programs(self, source_mount: Path, target_mount: Path) -> Dict[str, Any]:
        """比较外部程序差异"""
        source_programs = self._analyze_external_programs(source_mount)
        target_programs = self._analyze_external_programs(target_mount)

        return {
            "source": source_programs,
            "target": target_programs,
            "differences": self._find_program_differences(source_programs, target_programs)
        }

    def _analyze_external_programs(self, mount_path: Path) -> Dict[str, Any]:
        """分析外部程序"""
        programs = {
            "winxshell": self._check_winxshell(mount_path),
            "cairo_shell": self._check_cairo_shell(mount_path),
            "custom_tools": self._find_custom_tools(mount_path),
            "startup_configs": self._find_startup_configs(mount_path)
        }
        return programs

    def _check_winxshell(self, mount_path: Path) -> Dict[str, Any]:
        """检查WinXShell"""
        system32 = mount_path / "Windows" / "System32"
        program_files = mount_path / "Program Files"

        winxshell_info = {
            "installed": False,
            "executable_paths": [],
            "config_files": [],
            "lua_scripts": []
        }

        # 检查System32中的WinXShell文件
        for pattern in ["WinXShell*", "*.jcfg", "*.lua"]:
            for file_path in system32.glob(pattern):
                if file_path.is_file():
                    if file_path.suffix.lower() == ".exe":
                        winxshell_info["executable_paths"].append(str(file_path.relative_to(mount_path)))
                    elif file_path.suffix.lower() in [".jcfg", ".lua"]:
                        winxshell_info["config_files"].append(str(file_path.relative_to(mount_path)))

        # 检查Program Files中的WinXShell
        winxshell_dir = program_files / "WinXShell"
        if winxshell_dir.exists():
            winxshell_info["installed"] = True
            for file_path in winxshell_dir.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(mount_path)
                    if file_path.suffix.lower() == ".exe":
                        winxshell_info["executable_paths"].append(str(rel_path))
                    elif file_path.suffix.lower() == ".lua":
                        winxshell_info["lua_scripts"].append(str(rel_path))

        return winxshell_info

    def _check_cairo_shell(self, mount_path: Path) -> Dict[str, Any]:
        """检查Cairo Shell"""
        system32 = mount_path / "Windows" / "System32"

        cairo_info = {
            "installed": False,
            "executable_paths": [],
            "config_files": []
        }

        # 检查Cairo相关文件
        cairo_patterns = ["Cairo*", "*.cairo", "CairoShell.exe"]
        for pattern in cairo_patterns:
            for file_path in system32.glob(pattern):
                if file_path.is_file():
                    if file_path.suffix.lower() == ".exe":
                        cairo_info["installed"] = True
                        cairo_info["executable_paths"].append(str(file_path.relative_to(mount_path)))
                    else:
                        cairo_info["config_files"].append(str(file_path.relative_to(mount_path)))

        return cairo_info

    def _find_custom_tools(self, mount_path: Path) -> List[str]:
        """查找自定义工具"""
        tools = []
        system32 = mount_path / "Windows" / "System32"

        # 查找常见的第三方工具
        tool_patterns = [
            "*.exe", "*.msi", "*.bat", "*.cmd", "*.ps1"
        ]

        for pattern in tool_patterns:
            for file_path in system32.glob(pattern):
                if file_path.is_file():
                    # 排除系统文件
                    if not self._is_system_file(file_path.name):
                        tools.append(str(file_path.relative_to(mount_path)))

        return tools

    def _find_startup_configs(self, mount_path: Path) -> List[str]:
        """查找启动配置文件"""
        configs = []
        system32 = mount_path / "Windows" / "System32"

        config_patterns = [
            "*.ini", "*.cfg", "*.conf", "*.xml", "*.json"
        ]

        for pattern in config_patterns:
            for file_path in system32.glob(pattern):
                if file_path.is_file():
                    configs.append(str(file_path.relative_to(mount_path)))

        return configs

    def _is_system_file(self, filename: str) -> bool:
        """判断是否为系统文件"""
        system_files = {
            "cmd.exe", "powershell.exe", "reg.exe", "sfc.exe", "chkdsk.exe",
            "format.com", "diskpart.exe", "bcdedit.exe", "bootsect.exe",
            "wpeinit.exe", "wpeutil.exe", "winpeshl.exe", "winload.exe"
        }
        return filename.lower() in system_files

    def _find_program_differences(self, source_programs: Dict, target_programs: Dict) -> Dict[str, Any]:
        """查找程序差异"""
        differences = {
            "winxshell": {
                "source_installed": source_programs["winxshell"]["installed"],
                "target_installed": target_programs["winxshell"]["installed"],
                "needs_migration": source_programs["winxshell"]["installed"] and
                                 not target_programs["winxshell"]["installed"]
            },
            "cairo_shell": {
                "source_installed": source_programs["cairo_shell"]["installed"],
                "target_installed": target_programs["cairo_shell"]["installed"],
                "needs_migration": source_programs["cairo_shell"]["installed"] and
                                 not target_programs["cairo_shell"]["installed"]
            },
            "custom_tools": {
                "source_count": len(source_programs["custom_tools"]),
                "target_count": len(target_programs["custom_tools"]),
                "needs_migration": len(source_programs["custom_tools"]) > 0
            }
        }

        return differences

    def _compare_startup_scripts(self, source_mount: Path, target_mount: Path) -> Dict[str, Any]:
        """比较启动脚本差异"""
        source_scripts = self._find_startup_scripts(source_mount)
        target_scripts = self._find_startup_scripts(target_mount)

        return {
            "source_scripts": source_scripts,
            "target_scripts": target_scripts,
            "missing_in_target": [s for s in source_scripts if s not in target_scripts],
            "needs_migration": len([s for s in source_scripts if s not in target_scripts]) > 0
        }

    def _find_startup_scripts(self, mount_path: Path) -> List[str]:
        """查找启动脚本"""
        scripts = []
        system32 = mount_path / "Windows" / "System32"

        # 检查常见的启动脚本
        script_files = [
            "winpeshl.ini", "startnet.cmd", "launch.cmd", "autorun.cmd"
        ]

        for script_file in script_files:
            script_path = system32 / script_file
            if script_path.exists():
                scripts.append(str(script_path.relative_to(mount_path)))

        # 检查PEConfig目录
        peconfig_dir = system32 / "PEConfig"
        if peconfig_dir.exists():
            for file_path in peconfig_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in [".cmd", ".bat", ".ps1"]:
                    scripts.append(str(file_path.relative_to(mount_path)))

        return scripts

    def _compare_drivers(self, source_mount: Path, target_mount: Path) -> Dict[str, Any]:
        """比较驱动程序差异"""
        source_drivers = self._find_drivers(source_mount)
        target_drivers = self._find_drivers(target_mount)

        return {
            "source_drivers": source_drivers,
            "target_drivers": target_drivers,
            "source_count": len(source_drivers),
            "target_count": len(target_drivers),
            "needs_migration": len(source_drivers) > 0
        }

    def _find_drivers(self, mount_path: Path) -> List[str]:
        """查找驱动程序"""
        drivers = []

        # 检查Drivers目录
        drivers_dir = mount_path / "Drivers"
        if drivers_dir.exists():
            for file_path in drivers_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in [".inf", ".sys", ".dll"]:
                    drivers.append(str(file_path.relative_to(mount_path)))

        return drivers

    def _find_custom_components(self, mount_path: Path) -> Dict[str, Any]:
        """查找自定义组件"""
        components = {
            "peconfig_exists": (mount_path / "Windows" / "System32" / "PEConfig").exists(),
            "programs_dir_exists": (mount_path / "Windows" / "System32" / "Programs").exists(),
            "drivers_dir_exists": (mount_path / "Drivers").exists(),
            "scripts_dir_exists": (mount_path / "Scripts").exists()
        }

        return components

    def _generate_migration_plan(self, differences: Dict[str, Any]) -> Dict[str, Any]:
        """生成迁移计划"""
        plan = {
            "replace_core_files": [],
            "migrate_external_programs": [],
            "migrate_startup_scripts": [],
            "migrate_drivers": [],
            "migrate_custom_components": []
        }

        # 核心文件替换计划
        for file_name, info in differences["core_files"].items():
            if info["needs_replacement"]:
                plan["replace_core_files"].append(file_name)

        # 外部程序迁移计划
        external_diffs = differences["external_programs"]["differences"]
        if external_diffs["winxshell"]["needs_migration"]:
            plan["migrate_external_programs"].append("WinXShell")
        if external_diffs["cairo_shell"]["needs_migration"]:
            plan["migrate_external_programs"].append("Cairo Shell")
        if external_diffs["custom_tools"]["needs_migration"]:
            plan["migrate_external_programs"].append("Custom Tools")

        # 启动脚本迁移计划
        if differences["startup_scripts"]["needs_migration"]:
            plan["migrate_startup_scripts"] = differences["startup_scripts"]["missing_in_target"]

        # 驱动程序迁移计划
        if differences["drivers"]["needs_migration"]:
            plan["migrate_drivers"] = differences["drivers"]["source_drivers"]

        return plan

    def generate_analysis_report(self, analysis: Dict[str, Any]) -> str:
        """生成分析报告"""
        report = []
        report.append("=" * 60)
        report.append("WinPE组件差异分析报告")
        report.append("=" * 60)
        report.append(f"分析时间: {analysis['analysis_time']}")
        report.append("")

        # 基本信息
        report.append("基本信息:")
        report.append(f"  源WIM: {analysis['source_info']['label']}")
        report.append(f"  目标WIM: {analysis['target_info']['label']}")
        report.append("")

        # 核心文件差异
        core_files = analysis['differences']['core_files']
        report.append("核心文件差异:")
        for file_name, info in core_files.items():
            status = "需要替换" if info['needs_replacement'] else "无需替换"
            report.append(f"  - {file_name}: {status}")
        report.append("")

        # 外部程序差异
        external_diffs = analysis['differences']['external_programs']['differences']
        report.append("外部程序差异:")
        report.append(f"  - WinXShell: {'需要迁移' if external_diffs['winxshell']['needs_migration'] else '无需迁移'}")
        report.append(f"  - Cairo Shell: {'需要迁移' if external_diffs['cairo_shell']['needs_migration'] else '无需迁移'}")
        report.append(f"  - 自定义工具: {external_diffs['custom_tools']['source_count']} 个")
        report.append("")

        # 迁移计划摘要
        migration_plan = analysis['migration_plan']
        report.append("迁移计划摘要:")
        report.append(f"  - 核心文件替换: {len(migration_plan['replace_core_files'])} 个")
        report.append(f"  - 外部程序迁移: {len(migration_plan['migrate_external_programs'])} 个")
        report.append(f"  - 启动脚本迁移: {len(migration_plan['migrate_startup_scripts'])} 个")
        report.append(f"  - 驱动程序迁移: {len(migration_plan['migrate_drivers'])} 个")
        report.append("")

        report.append("=" * 60)

        return "\n".join(report)