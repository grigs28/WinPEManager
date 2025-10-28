#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版WinPE版本替换器
实现完整的WinPE版本替换功能，包括组件分析、迁移和版本更新
"""

import os
import shutil
import subprocess
import stat
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import threading
from dataclasses import dataclass

from utils.logger import get_logger, log_command, log_build_step, log_system_event
from core.unified_manager.wim_manager import UnifiedWIMManager


@dataclass
class VersionReplaceConfig:
    """版本替换配置"""
    source_dir: Path  # 源目录 (0WIN11PE)
    target_dir: Path  # 目标目录 (0WIN10OLD)
    output_dir: Path  # 输出目录 (WIN10REPLACED)
    source_wim: Path  # 源WIM文件
    target_wim: Path  # 目标WIM文件
    output_wim: Path  # 输出WIM文件
    mount_dir: Path   # 挂载目录

    def __post_init__(self):
        """确保路径是Path对象"""
        self.source_dir = Path(self.source_dir)
        self.target_dir = Path(self.target_dir)
        self.output_dir = Path(self.output_dir)
        self.source_wim = Path(self.source_wim)
        self.target_wim = Path(self.target_wim)
        self.output_wim = Path(self.output_wim)
        self.mount_dir = Path(self.mount_dir)


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


class VersionReplacer:
    """增强版WinPE版本替换器主类"""

    def __init__(self, config_manager, adk_manager, unified_wim_manager: UnifiedWIMManager):
        self.config = config_manager
        self.adk = adk_manager
        self.wim_manager = unified_wim_manager
        self.logger = get_logger("VersionReplacer")

        self.component_analyzer = ComponentAnalyzer()
        self.progress_callback = None
        self.log_callback = None

    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback

    def set_log_callback(self, callback):
        """设置日志回调函数"""
        self.log_callback = callback

    def execute_version_replacement(self, config: VersionReplaceConfig) -> Dict[str, Any]:
        """
        执行完整的版本替换流程

        Args:
            config: 版本替换配置

        Returns:
            替换结果
        """
        self.logger.info("开始执行WinPE版本替换...")

        result = {
            "success": False,
            "config": config,
            "steps": {},
            "analysis": {},
            "errors": [],
            "warnings": [],
            "output_path": str(config.output_dir)
        }

        try:
            # 第1步：验证环境
            self._log("验证替换环境...")
            validation_result = self._validate_environment(config)
            result["steps"]["validation"] = validation_result

            if not validation_result["success"]:
                result["errors"].extend(validation_result["errors"])
                return result

            # 第2步：复制源目录结构到输出目录
            self._update_progress(10, "复制源目录结构...")
            copy_result = self._copy_source_structure(config)
            result["steps"]["copy_structure"] = copy_result

            if not copy_result["success"]:
                result["errors"].extend(copy_result["errors"])
                return result

            # 第3步：复制目标boot.wim到输出目录
            self._update_progress(20, "复制目标boot.wim...")
            wim_copy_result = self._copy_target_boot_wim(config)
            result["steps"]["copy_boot_wim"] = wim_copy_result

            if not wim_copy_result["success"]:
                result["errors"].extend(wim_copy_result["errors"])
                return result

            # 第4步：挂载输出WIM进行分析
            self._update_progress(30, "挂载输出WIM进行分析...")
            mount_result = self._mount_output_wim(config)
            result["steps"]["mount_wim"] = mount_result

            if not mount_result["success"]:
                result["errors"].extend(mount_result["errors"])
                return result

            source_mount = mount_result["source_mount"]
            target_mount = mount_result["target_mount"]
            output_mount = mount_result["output_mount"]

            try:
                # 第5步：分析组件差异
                self._update_progress(40, "分析源和目标WIM组件差异...")
                analysis_result = self.component_analyzer.analyze_wim_differences(
                    source_mount, target_mount
                )
                result["analysis"] = analysis_result

                # 第6步：执行组件迁移
                self._update_progress(50, "执行组件迁移...")
                migration_result = self._execute_component_migration(
                    analysis_result["migration_plan"],
                    source_mount,
                    output_mount
                )
                result["steps"]["migration"] = migration_result

                if not migration_result["success"]:
                    result["errors"].extend(migration_result["errors"])
                    # 继续执行，但记录错误

                # 第7步：更新配置文件
                self._update_progress(80, "更新配置文件...")
                config_update_result = self._update_configuration_files(
                    output_mount, analysis_result
                )
                result["steps"]["config_update"] = config_update_result

                # 第8步：验证替换结果
                self._update_progress(90, "验证替换结果...")
                verification_result = self._verify_replacement_result(
                    output_mount, analysis_result
                )
                result["steps"]["verification"] = verification_result

                # 第9步：卸载WIM
                self._update_progress(95, "卸载WIM...")
                unmount_result = self._unmount_output_wim(config)
                result["steps"]["unmount_wim"] = unmount_result

                if unmount_result["success"]:
                    self._update_progress(100, "版本替换完成")
                    result["success"] = True
                    self._log("✅ WinPE版本替换完成!")
                else:
                    result["warnings"].extend(unmount_result["warnings"])

            finally:
                # 确保WIM被正确卸载
                try:
                    self.wim_manager.unmount_wim(config.output_dir, commit=True)
                except Exception as e:
                    self.logger.warning(f"最终卸载WIM时出现问题: {str(e)}")
                    result["warnings"].append(f"最终卸载WIM警告: {str(e)}")

        except Exception as e:
            error_msg = f"版本替换过程中发生异常: {str(e)}"
            self.logger.error(error_msg)
            result["errors"].append(error_msg)

            # 尝试清理
            try:
                self.wim_manager.unmount_wim(config.output_dir, commit=False)
            except:
                pass

        return result

    def _validate_environment(self, config: VersionReplaceConfig) -> Dict[str, Any]:
        """验证替换环境"""
        result = {"success": True, "errors": [], "warnings": []}

        # 检查源目录
        if not config.source_dir.exists():
            result["success"] = False
            result["errors"].append(f"源目录不存在: {config.source_dir}")

        # 检查目标目录
        if not config.target_dir.exists():
            result["success"] = False
            result["errors"].append(f"目标目录不存在: {config.target_dir}")

        # 检查源WIM
        if not config.source_wim.exists():
            result["success"] = False
            result["errors"].append(f"源WIM文件不存在: {config.source_wim}")

        # 检查目标WIM
        if not config.target_wim.exists():
            result["success"] = False
            result["errors"].append(f"目标WIM文件不存在: {config.target_wim}")

        # 检查挂载状态
        source_mount = config.source_dir / "mount"
        target_mount = config.target_dir / "mount"

        if not source_mount.exists():
            result["warnings"].append("源WIM可能未挂载")

        if not target_mount.exists():
            result["warnings"].append("目标WIM可能未挂载")

        return result

    def _copy_source_structure(self, config: VersionReplaceConfig) -> Dict[str, Any]:
        """复制源目录结构到输出目录"""
        result = {"success": True, "errors": [], "warnings": []}

        try:
            self._log(f"复制源目录结构: {config.source_dir} -> {config.output_dir}")

            # 创建输出目录
            config.output_dir.mkdir(parents=True, exist_ok=True)

            # 复制源目录结构（不包括mount目录）
            for item in config.source_dir.iterdir():
                if item.name == "mount":
                    continue  # 跳过mount目录

                target_item = config.output_dir / item.name

                if item.is_file():
                    shutil.copy2(item, target_item)
                elif item.is_dir():
                    self._copy_tree_with_permission_handling(item, target_item)

            self._log("✅ 源目录结构复制完成")

        except Exception as e:
            result["success"] = False
            result["errors"].append(f"复制源目录结构失败: {str(e)}")

        return result

    def _copy_target_boot_wim(self, config: VersionReplaceConfig) -> Dict[str, Any]:
        """复制目标boot.wim到输出目录"""
        result = {"success": True, "errors": [], "warnings": []}

        try:
            self._log(f"复制目标boot.wim: {config.target_wim} -> {config.output_wim}")

            # 确保boot目录存在
            config.output_wim.parent.mkdir(parents=True, exist_ok=True)

            # 复制boot.wim
            shutil.copy2(config.target_wim, config.output_wim)

            self._log("✅ 目标boot.wim复制完成")

        except Exception as e:
            result["success"] = False
            result["errors"].append(f"复制目标boot.wim失败: {str(e)}")

        return result

    def _mount_output_wim(self, config: VersionReplaceConfig) -> Dict[str, Any]:
        """挂载输出WIM进行分析"""
        result = {
            "success": True,
            "errors": [],
            "warnings": [],
            "source_mount": None,
            "target_mount": None,
            "output_mount": None
        }

        try:
            # 挂载输出WIM
            self._log(f"挂载输出WIM: {config.output_wim}")

            mount_success, mount_msg = self.wim_manager.mount_wim(
                config.output_dir, config.output_wim
            )

            if not mount_success:
                result["success"] = False
                result["errors"].append(f"挂载输出WIM失败: {mount_msg}")
                return result

            output_mount = config.mount_dir
            result["output_mount"] = output_mount

            # 设置源和目标挂载路径
            result["source_mount"] = config.source_dir / "mount"
            result["target_mount"] = config.target_dir / "mount"

            self._log("✅ 输出WIM挂载完成")

        except Exception as e:
            result["success"] = False
            result["errors"].append(f"挂载输出WIM异常: {str(e)}")

        return result

    def _execute_component_migration(self, migration_plan: Dict, source_mount: Path, output_mount: Path) -> Dict[str, Any]:
        """执行组件迁移"""
        result = {"success": True, "errors": [], "warnings": [], "migrated_items": []}

        try:
            # 迁移核心文件（如果需要）
            # 注意：这里我们保持源WIM的核心文件，只替换目标版本特定的文件

            # 迁移外部程序
            for program in migration_plan.get("migrate_external_programs", []):
                migration_result = self._migrate_external_program(program, source_mount, output_mount)
                result["migrated_items"].append(f"外部程序: {program}")
                if not migration_result:
                    result["warnings"].append(f"外部程序迁移部分失败: {program}")

            # 迁移启动脚本
            for script in migration_plan.get("migrate_startup_scripts", []):
                migration_result = self._migrate_startup_script(script, source_mount, output_mount)
                result["migrated_items"].append(f"启动脚本: {script}")
                if not migration_result:
                    result["warnings"].append(f"启动脚本迁移失败: {script}")

            # 迁移驱动程序
            for driver in migration_plan.get("migrate_drivers", []):
                migration_result = self._migrate_driver(driver, source_mount, output_mount)
                result["migrated_items"].append(f"驱动程序: {driver}")
                if not migration_result:
                    result["warnings"].append(f"驱动程序迁移失败: {driver}")

            # 迁移自定义组件
            self._migrate_custom_components(source_mount, output_mount, result)

            self._log(f"✅ 组件迁移完成，共迁移 {len(result['migrated_items'])} 个项目")

        except Exception as e:
            result["success"] = False
            result["errors"].append(f"组件迁移异常: {str(e)}")

        return result

    def _migrate_external_program(self, program_name: str, source_mount: Path, output_mount: Path) -> bool:
        """迁移外部程序"""
        try:
            source_system32 = source_mount / "Windows" / "System32"
            output_system32 = output_mount / "Windows" / "System32"

            if program_name == "WinXShell":
                # 迁移WinXShell相关文件
                patterns = ["WinXShell*", "*.jcfg", "*.lua"]
                for pattern in patterns:
                    for source_file in source_system32.glob(pattern):
                        if source_file.is_file():
                            target_file = output_system32 / source_file.name
                            shutil.copy2(source_file, target_file)

                # 迁移Program Files中的WinXShell
                source_programs = source_mount / "Program Files" / "WinXShell"
                if source_programs.exists():
                    output_programs = output_mount / "Program Files" / "WinXShell"
                    shutil.copytree(source_programs, output_programs, dirs_exist_ok=True)

            elif program_name == "Cairo Shell":
                # 迁移Cairo Shell相关文件
                patterns = ["Cairo*", "*.cairo"]
                for pattern in patterns:
                    for source_file in source_system32.glob(pattern):
                        if source_file.is_file():
                            target_file = output_system32 / source_file.name
                            shutil.copy2(source_file, target_file)

            elif program_name == "Custom Tools":
                # 迁移自定义工具
                for source_file in source_system32.glob("*"):
                    if (source_file.is_file() and
                        source_file.suffix.lower() in [".exe", ".msi", ".bat", ".cmd", ".ps1"] and
                        not self._is_system_file(source_file.name)):

                        target_file = output_system32 / source_file.name
                        if not target_file.exists():
                            shutil.copy2(source_file, target_file)

            return True

        except Exception as e:
            self.logger.error(f"迁移外部程序 {program_name} 失败: {str(e)}")
            return False

    def _migrate_startup_script(self, script_path: str, source_mount: Path, output_mount: Path) -> bool:
        """迁移启动脚本"""
        try:
            source_file = source_mount / script_path
            target_file = output_mount / script_path

            if source_file.exists():
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, target_file)
                return True

            return False

        except Exception as e:
            self.logger.error(f"迁移启动脚本 {script_path} 失败: {str(e)}")
            return False

    def _migrate_driver(self, driver_path: str, source_mount: Path, output_mount: Path) -> bool:
        """迁移驱动程序"""
        try:
            source_file = source_mount / driver_path
            target_file = output_mount / driver_path

            if source_file.exists():
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, target_file)
                return True

            return False

        except Exception as e:
            self.logger.error(f"迁移驱动程序 {driver_path} 失败: {str(e)}")
            return False

    def _migrate_custom_components(self, source_mount: Path, output_mount: Path, result: Dict):
        """迁移自定义组件"""
        try:
            # 迁移PEConfig目录
            source_peconfig = source_mount / "Windows" / "System32" / "PEConfig"
            if source_peconfig.exists():
                output_peconfig = output_mount / "Windows" / "System32" / "PEConfig"
                shutil.copytree(source_peconfig, output_peconfig, dirs_exist_ok=True)
                result["migrated_items"].append("PEConfig目录")

            # 迁移Programs目录
            source_programs = source_mount / "Windows" / "System32" / "Programs"
            if source_programs.exists():
                output_programs = output_mount / "Windows" / "System32" / "Programs"
                shutil.copytree(source_programs, output_programs, dirs_exist_ok=True)
                result["migrated_items"].append("Programs目录")

            # 迁移Drivers目录
            source_drivers = source_mount / "Drivers"
            if source_drivers.exists():
                output_drivers = output_mount / "Drivers"
                shutil.copytree(source_drivers, output_drivers, dirs_exist_ok=True)
                result["migrated_items"].append("Drivers目录")

            # 迁移Scripts目录
            source_scripts = source_mount / "Scripts"
            if source_scripts.exists():
                output_scripts = output_mount / "Scripts"
                shutil.copytree(source_scripts, output_scripts, dirs_exist_ok=True)
                result["migrated_items"].append("Scripts目录")

        except Exception as e:
            result["warnings"].append(f"迁移自定义组件时出现问题: {str(e)}")

    def _update_configuration_files(self, output_mount: Path, analysis: Dict) -> Dict[str, Any]:
        """更新配置文件"""
        result = {"success": True, "errors": [], "warnings": []}

        try:
            system32 = output_mount / "Windows" / "System32"

            # 更新winpeshl.ini
            winpeshl_ini = system32 / "winpeshl.ini"
            if winpeshl_ini.exists():
                content = winpeshl_ini.read_text(encoding='utf-8')

                # 添加版本替换标记
                replacement_marker = f"; WinPE Version Replaced - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                if replacement_marker not in content:
                    if content.startswith(";"):
                        content = replacement_marker + content
                    else:
                        content = replacement_marker + "\n" + content

                    winpeshl_ini.write_text(content, encoding='utf-8')
                    result["warnings"].append("已更新winpeshl.ini版本标记")

            # 创建版本信息文件
            version_file = system32 / "PEConfig" / "version_info.txt"
            version_file.parent.mkdir(parents=True, exist_ok=True)

            version_info = f"""WinPE Version Replacement Information
Source: {analysis['source_info']['label']}
Target: {analysis['target_info']['label']}
Replacement Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Migration Plan: {analysis['migration_plan']}
"""
            version_file.write_text(version_info, encoding='utf-8')

            self._log("✅ 配置文件更新完成")

        except Exception as e:
            result["success"] = False
            result["errors"].append(f"更新配置文件失败: {str(e)}")

        return result

    def _verify_replacement_result(self, output_mount: Path, analysis: Dict) -> Dict[str, Any]:
        """验证替换结果"""
        result = {"success": True, "errors": [], "warnings": [], "verification_details": {}}

        try:
            # 验证基本结构
            windows_dir = output_mount / "Windows"
            system32_dir = output_mount / "Windows" / "System32"

            result["verification_details"]["windows_exists"] = windows_dir.exists()
            result["verification_details"]["system32_exists"] = system32_dir.exists()

            # 验证核心文件
            core_files = ["winpe.wim", "winpeshl.exe", "wpeinit.exe", "wpeutil.exe"]
            core_verification = {}
            for file_name in core_files:
                file_path = system32_dir / file_name
                core_verification[file_name] = file_path.exists()

            result["verification_details"]["core_files"] = core_verification

            # 验证迁移的组件
            migration_plan = analysis["migration_plan"]

            # 验证外部程序
            if "WinXShell" in migration_plan.get("migrate_external_programs", []):
                winxshell_found = any(system32_dir.glob("WinXShell*"))
                result["verification_details"]["winxshell_migrated"] = winxshell_found

            # 验证启动脚本
            scripts_migrated = len(migration_plan.get("migrate_startup_scripts", [])) > 0
            result["verification_details"]["startup_scripts_migrated"] = scripts_migrated

            # 验证自定义组件
            peconfig_exists = (system32_dir / "PEConfig").exists()
            programs_exists = (system32_dir / "Programs").exists()
            result["verification_details"]["custom_components"] = {
                "peconfig_exists": peconfig_exists,
                "programs_exists": programs_exists
            }

            self._log("✅ 替换结果验证完成")

        except Exception as e:
            result["success"] = False
            result["errors"].append(f"验证替换结果失败: {str(e)}")

        return result

    def _unmount_output_wim(self, config: VersionReplaceConfig) -> Dict[str, Any]:
        """卸载输出WIM"""
        result = {"success": True, "errors": [], "warnings": []}

        try:
            self._log("卸载输出WIM...")

            unmount_success, unmount_msg = self.wim_manager.unmount_wim(
                config.output_dir, commit=True
            )

            if unmount_success:
                self._log("✅ 输出WIM卸载完成")
            else:
                result["success"] = False
                result["errors"].append(f"卸载输出WIM失败: {unmount_msg}")

        except Exception as e:
            result["success"] = False
            result["errors"].append(f"卸载输出WIM异常: {str(e)}")

        return result

    def _copy_tree_with_permission_handling(self, src: Path, dst: Path):
        """带权限处理的目录复制"""
        try:
            if not dst.exists():
                dst.mkdir(parents=True, exist_ok=True)

            for item in src.iterdir():
                dst_item = dst / item.name

                if item.is_dir():
                    self._copy_tree_with_permission_handling(item, dst_item)
                elif item.is_file():
                    try:
                        shutil.copy2(item, dst_item)
                    except (PermissionError, OSError):
                        # 处理权限问题
                        if dst_item.exists():
                            dst_item.chmod(stat.S_IWRITE | stat.S_IREAD)
                        shutil.copy(item, dst_item)

        except Exception as e:
            self.logger.warning(f"复制目录时出现问题: {src} -> {dst}, 错误: {str(e)}")

    def _is_system_file(self, filename: str) -> bool:
        """判断是否为系统文件"""
        system_files = {
            "cmd.exe", "powershell.exe", "reg.exe", "sfc.exe", "chkdsk.exe",
            "format.com", "diskpart.exe", "bcdedit.exe", "bootsect.exe",
            "wpeinit.exe", "wpeutil.exe", "winpeshl.exe", "winload.exe"
        }
        return filename.lower() in system_files

    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message, level)

        if level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)
        else:
            self.logger.info(message)

    def _update_progress(self, percent: int, message: str = ""):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(percent, message)

        self._log(f"进度 {percent}%: {message}")


def create_version_replace_config(source_dir: str, target_dir: str, output_dir: str) -> VersionReplaceConfig:
    """创建版本替换配置"""
    source_path = Path(source_dir)
    target_path = Path(target_dir)
    output_path = Path(output_dir)

    config = VersionReplaceConfig(
        source_dir=source_path,
        target_dir=target_path,
        output_dir=output_path,
        source_wim=source_path / "boot" / "boot.wim",
        target_wim=target_path / "boot.wim",
        output_wim=output_path / "boot" / "boot.wim",
        mount_dir=output_path / "mount"
    )

    return config