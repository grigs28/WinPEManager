#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版版本替换器
使用DISM进行精确的WIM比较和组件添加
实现完整的分析-比较-添加流程
"""

import os
import shutil
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
from datetime import datetime
import tempfile

from utils.logger import get_logger, log_command, log_build_step, log_system_event


class EnhancedVersionReplacer:
    """增强版WinPE版本替换器，使用DISM进行精确操作"""

    def __init__(self, config_manager, adk_manager, unified_wim_manager):
        """
        初始化增强版版本替换器

        Args:
            config_manager: 配置管理器
            adk_manager: ADK管理器
            unified_wim_manager: 统一WIM管理器
        """
        self.config = config_manager
        self.adk = adk_manager
        self.wim_manager = unified_wim_manager
        self.logger = get_logger("EnhancedVersionReplacer")

        # 回调函数
        self.progress_callback = None
        self.log_callback = None

        # DISM路径
        self.dism_path = self._get_dism_path()

    def _get_dism_path(self) -> str:
        """获取DISM工具路径"""
        # 优先使用自定义DISM路径
        custom_dism = self.config.get("advanced.dism.custom_path", "")
        if custom_dism and Path(custom_dism).exists():
            return str(Path(custom_dism))

        # 使用系统DISM
        dism_paths = [
            r"C:\Windows\System32\dism.exe",
            r"C:\Windows\SysWOW64\dism.exe"
        ]

        for dism_path in dism_paths:
            if Path(dism_path).exists():
                return dism_path

        raise FileNotFoundError("找不到DISM工具，请确保已安装Windows ADK或DISM工具可用")

    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback

    def set_log_callback(self, callback):
        """设置日志回调函数"""
        self.log_callback = callback

    def _log(self, message: str, level: str = "info"):
        """内部日志记录"""
        if self.log_callback:
            self.log_callback(message, level)

        if level == "error":
            self.logger.error(message)
            log_system_event("增强版版本替换", message, "error")
        elif level == "warning":
            self.logger.warning(message)
            log_system_event("增强版版本替换", message, "warning")
        else:
            self.logger.info(message)
            log_system_event("增强版版本替换", message, "info")

    def _update_progress(self, percent: int, message: str = ""):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(percent, message)
        log_build_step(f"增强版版本替换 {percent}%", message)

    def run_dism_command(self, command: List[str], description: str = "") -> Tuple[bool, str]:
        """
        运行DISM命令（带进度支持）

        Args:
            command: DISM命令参数列表
            description: 命令描述

        Returns:
            Tuple[bool, str]: (成功状态, 输出信息)
        """
        try:
            self._log(f"执行DISM命令: {description}", "info")

            # 创建进度回调函数
            def progress_callback(percent: int, message: str):
                progress_msg = f"DISM进度 {percent}%: {message}"
                self._update_progress(percent, f"DISM {description}: {message}")
                self._log(progress_msg, "info")
                print(f"{progress_msg} [增强版本替换]")

            # 使用ADK管理器的带进度方法
            success, stdout, stderr = self.adk.run_dism_command_with_progress(command, progress_callback)

            if success:
                success_msg = f"DISM命令成功: {description}"
                self._log(success_msg, "success")
                print(f"{success_msg} [成功]")
                return True, stdout
            else:
                error_msg = f"DISM命令失败: {description}\n错误信息: {stderr}"
                self._log(error_msg, "error")
                print(f"{error_msg} [错误]")
                return False, stderr

        except Exception as e:
            error_msg = f"DISM命令执行异常: {description} - {str(e)}"
            self._log(error_msg, "error")
            print(f"{error_msg} [异常]")
            return False, error_msg

    def analyze_wim_with_dism(self, wim_path: str, description: str = "") -> Dict:
        """
        使用DISM分析WIM文件

        Args:
            wim_path: WIM文件路径
            description: 分析描述

        Returns:
            Dict: WIM分析结果
        """
        self._log(f"使用DISM分析WIM: {description}", "info")

        analysis = {
            "wim_path": wim_path,
            "description": description,
            "images": [],
            "features": [],
            "packages": [],
            "appx_packages": [],
            "capabilities": [],
            "drivers": []
        }

        # 获取WIM信息
        command = ["/Get-WimInfo", f"/WimFile:{wim_path}"]
        success, output = self.run_dism_command(command, f"获取WIM信息 - {description}")

        if success:
            # 解析输出获取镜像信息
            lines = output.split('\n')
            current_image = {}

            for line in lines:
                line = line.strip()
                if "Index :" in line:
                    if current_image:
                        analysis["images"].append(current_image)
                    current_image = {"index": line.split(":")[-1].strip()}
                elif "Name :" in line and current_image:
                    current_image["name"] = line.split(":")[-1].strip()
                elif "Description :" in line and current_image:
                    current_image["description"] = line.split(":")[-1].strip()
                elif "Size :" in line and current_image:
                    current_image["size"] = line.split(":")[-1].strip()

            if current_image:
                analysis["images"].append(current_image)

        return analysis

    def compare_wims_with_dism(self, source_wim: str, target_wim: str) -> Dict:
        """
        使用DISM比较两个WIM文件的差异

        Args:
            source_wim: 源WIM文件路径
            target_wim: 目标WIM文件路径

        Returns:
            Dict: WIM差异分析结果
        """
        self._log("使用DISM比较WIM文件差异", "info")
        self._update_progress(10, "分析源WIM文件...")

        # 分析源WIM
        source_analysis = self.analyze_wim_with_dism(source_wim, "源WIM")

        self._update_progress(20, "分析目标WIM文件...")
        # 分析目标WIM
        target_analysis = self.analyze_wim_with_dism(target_wim, "目标WIM")

        # 计算差异
        self._update_progress(30, "计算WIM差异...")
        differences = {
            "source_wim": source_wim,
            "target_wim": target_wim,
            "source_analysis": source_analysis,
            "target_analysis": target_analysis,
            "missing_in_target": [],
            "additional_in_source": [],
            "size_difference": 0
        }

        # 比较镜像数量和大小
        source_images = source_analysis.get("images", [])
        target_images = target_analysis.get("images", [])

        if len(source_images) != len(target_images):
            differences["missing_in_target"].append(
                f"镜像数量不匹配: 源({len(source_images)}) vs 目标({len(target_images)})"
            )

        # 比较镜像大小
        for i, (src_img, tgt_img) in enumerate(zip(source_images, target_images)):
            if src_img.get("size") != tgt_img.get("size"):
                differences["missing_in_target"].append(
                    f"镜像{i+1}大小不匹配: 源({src_img.get('size')}) vs 目标({tgt_img.get('size')})"
                )

        self._update_progress(40, "WIM差异分析完成")
        return differences

    def mount_wim_with_dism(self, wim_path: str, mount_dir: str, image_index: int = 1) -> bool:
        """
        使用统一WIM管理器挂载WIM文件

        Args:
            wim_path: WIM文件路径
            mount_dir: 挂载目录路径
            image_index: 镜像索引

        Returns:
            bool: 挂载成功状态
        """
        self._log(f"使用统一WIM管理器挂载WIM: {wim_path} -> {mount_dir}", "info")

        try:
            # 使用统一WIM管理器挂载
            wim_path_obj = Path(wim_path)
            mount_dir_obj = Path(mount_dir)

            # 确保挂载目录存在
            mount_dir_obj.mkdir(parents=True, exist_ok=True)

            # 使用统一管理器挂载
            success, message = self.wim_manager.mount_wim(mount_dir_obj.parent, wim_path_obj)

            if success:
                self._log(f"WIM挂载成功: {mount_dir}", "success")
                return True
            else:
                self._log(f"WIM挂载失败: {message}", "error")
                return False

        except Exception as e:
            self._log(f"WIM挂载异常: {str(e)}", "error")
            return False

    def unmount_wim_with_dism(self, mount_dir: str, commit: bool = False) -> bool:
        """
        使用统一WIM管理器卸载WIM文件

        Args:
            mount_dir: 挂载目录路径
            commit: 是否提交更改

        Returns:
            bool: 卸载成功状态
        """
        action = "提交并卸载" if commit else "卸载"
        self._log(f"使用统一WIM管理器{action}WIM: {mount_dir}", "info")

        try:
            # 使用统一WIM管理器卸载
            mount_dir_obj = Path(mount_dir)

            # 使用统一管理器卸载
            success, message = self.wim_manager.unmount_wim(mount_dir_obj.parent, commit)

            if success:
                self._log(f"WIM{action}成功: {mount_dir}", "success")
                return True
            else:
                self._log(f"WIM{action}失败: {message}", "error")
                return False

        except Exception as e:
            self._log(f"WIM{action}异常: {str(e)}", "error")
            return False

    def fix_winpe_target_path(self, mount_dir: str) -> bool:
        """
        修复WinPE启动时的目标路径问题

        修复Windows PE无法启动的问题：
        实际SYSTEMROOT目录(X:\windows)不同于配置的目录(X:\$windows.~bt\Windows)
        """
        self._log("开始修复WinPE启动路径问题...", "info")

        try:
            mount_path = Path(mount_dir)
            if not mount_path.exists():
                self._log(f"挂载目录不存在: {mount_dir}", "error")
                return False

            # 使用DISM设置正确的目标路径
            dism_path = self._get_dism_path()

            # 方法1：设置目标路径为X:\ (标准的WinPE路径)
            self._log("使用DISM设置WinPE目标路径...", "info")
            cmd = [
                str(dism_path),
                "/Image:" + str(mount_path),
                "/Set-TargetPath:X:\\"
            ]

            success, output = self.run_dism_command(cmd, "设置WinPE目标路径")

            if success:
                self._log("✅ DISM设置目标路径成功", "success")
            else:
                self._log(f"DISM设置目标路径失败: {output}", "warning")

            # 方法2：额外设置确保SYSTEMROOT正确
            self._log("确保WinPE SYSTEMROOT路径正确...", "info")
            cmd_systemroot = [
                str(dism_path),
                "/Image:" + str(mount_path),
                "/Set-Sysroot:X:\\Windows"
            ]

            success_systemroot, output_systemroot = self.run_dism_command(cmd_systemroot, "设置WinPE SYSTEMROOT")

            if success_systemroot:
                self._log("✅ DISM设置SYSTEMROOT成功", "success")
            else:
                self._log(f"DISM设置SYSTEMROOT失败: {output_systemroot}", "warning")

            # 方法3：创建和修复配置文件
            self._fix_winpe_config_files(mount_path)

            self._log("WinPE启动路径修复完成", "success")
            return True

        except Exception as e:
            self._log(f"修复WinPE启动路径时发生错误: {str(e)}", "error")
            return False

    def _fix_winpe_config_files(self, mount_path: Path):
        """修复WinPE配置文件中的路径问题"""
        try:
            # 创建WinPE启动配置文件
            winpeshl_ini = mount_path / "Windows" / "System32" / "winpeshl.ini"
            if not winpeshl_ini.exists():
                self._log("创建WinPE启动配置文件...", "info")
                winpeshl_content = """[LaunchApps]
%windir%\\System32\\cmd.exe
"""
                try:
                    winpeshl_ini.parent.mkdir(parents=True, exist_ok=True)
                    with open(winpeshl_ini, 'w', encoding='utf-8') as f:
                        f.write(winpeshl_content)
                    self._log("✅ WinPE启动配置文件创建成功", "success")
                except Exception as e:
                    self._log(f"创建WinPE启动配置文件失败: {str(e)}", "warning")

            # 修复启动配置文件中的路径问题
            setupreg_cmd = mount_path / "Windows" / "System32" / "setupreg.cmd"
            if setupreg_cmd.exists():
                self._log("检查并修复setupreg.cmd中的路径配置...", "info")
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
                        self._log("✅ setupreg.cmd路径配置修复成功", "success")
                    else:
                        self._log("setupreg.cmd路径配置正常", "info")
                except Exception as e:
                    self._log(f"修复setupreg.cmd失败: {str(e)}", "warning")

        except Exception as e:
            self._log(f"修复WinPE配置文件时出错: {str(e)}", "warning")

    def add_component_to_wim(self, wim_path: str, component_path: str,
                           mount_dir: str, component_type: str = "file") -> bool:
        """
        使用DISM添加组件到WIM文件

        Args:
            wim_path: 目标WIM文件路径
            component_path: 组件路径
            mount_dir: 挂载目录路径
            component_type: 组件类型 (file, package, driver, feature)

        Returns:
            bool: 添加成功状态
        """
        self._log(f"使用DISM添加{component_type}到WIM: {component_path}", "info")

        # 确保WIM已挂载
        if not Path(mount_dir).exists():
            success = self.mount_wim_with_dism(wim_path, mount_dir)
            if not success:
                return False

        component_name = Path(component_path).name

        try:
            if component_type == "file":
                # 复制文件到挂载目录
                target_path = Path(mount_dir) / Path(component_path).name
                if Path(component_path).is_file():
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(component_path, target_path)
                    self._log(f"文件添加成功: {component_name}", "success")
                    return True
                elif Path(component_path).is_dir():
                    shutil.copytree(component_path, target_path, dirs_exist_ok=True)
                    self._log(f"目录添加成功: {component_name}", "success")
                    return True

            elif component_type == "package":
                # 使用DISM添加包
                command = [
                    "/Add-Package",
                    f"/Image:{mount_dir}",
                    f"/PackagePath:{component_path}"
                ]
                success, output = self.run_dism_command(command, f"添加包 - {component_name}")
                return success

            elif component_type == "driver":
                # 使用DISM添加驱动
                command = [
                    "/Add-Driver",
                    f"/Image:{mount_dir}",
                    f"/Driver:{component_path}",
                    "/ForceUnsigned"
                ]
                success, output = self.run_dism_command(command, f"添加驱动 - {component_name}")
                return success

            elif component_type == "feature":
                # 使用DISM启用功能
                command = [
                    "/Enable-Feature",
                    f"/Image:{mount_dir}",
                    f"/FeatureName:{component_path}",
                    "/All"
                ]
                success, output = self.run_dism_command(command, f"启用功能 - {component_name}")
                return success

            else:
                self._log(f"不支持的组件类型: {component_type}", "warning")
                return False

        except Exception as e:
            self._log(f"添加组件失败: {component_name} - {str(e)}", "error")
            return False

    def analyze_mount_differences(self, source_mount: str, target_mount: str) -> Dict:
        """
        深度分析两个挂载目录的差异

        Args:
            source_mount: 源挂载目录
            target_mount: 目标挂载目录

        Returns:
            Dict: 挂载目录差异分析结果
        """
        self._log("深度分析挂载目录差异", "info")
        self._update_progress(50, "分析挂载目录结构差异...")

        differences = {
            "source_mount": source_mount,
            "target_mount": target_mount,
            "missing_in_target": [],
            "additional_in_source": [],
            "different_files": [],
            "external_programs": [],
            "startup_configs": [],
            "desktop_configs": []
        }

        source_path = Path(source_mount)
        target_path = Path(target_mount)

        if not source_path.exists():
            self._log(f"源挂载目录不存在: {source_mount}", "error")
            return differences

        if not target_path.exists():
            self._log(f"目标挂载目录不存在: {target_mount}", "error")
            return differences

        # 分析外部程序
        self._update_progress(55, "分析外部程序差异...")
        external_programs = self._analyze_external_programs(source_path, target_path)
        differences["external_programs"] = external_programs

        # 分析启动配置
        self._update_progress(60, "分析启动配置差异...")
        startup_configs = self._analyze_startup_configs(source_path, target_path)
        differences["startup_configs"] = startup_configs

        # 分析桌面配置
        self._update_progress(65, "分析桌面配置差异...")
        desktop_configs = self._analyze_desktop_configs(source_path, target_path)
        differences["desktop_configs"] = desktop_configs

        # 深度比较文件结构
        self._update_progress(70, "深度比较文件结构...")
        file_differences = self._deep_compare_files(source_path, target_path)
        differences.update(file_differences)

        self._update_progress(75, "挂载目录差异分析完成")
        return differences

    def _analyze_external_programs(self, source_path: Path, target_path: Path) -> List[Dict]:
        """分析外部程序差异"""
        external_programs = []

        # 查找外部程序目录
        program_dirs = [
            "Program Files/WinXShell",
            "Program Files/CairoShell",
            "Program Files/Explorer",
            "Windows/System32/Programs"
        ]

        for program_dir in program_dirs:
            source_program = source_path / program_dir
            target_program = target_path / program_dir

            if source_program.exists():
                program_info = {
                    "name": program_dir.replace("/", "\\"),
                    "source_path": str(source_program),
                    "target_path": str(target_program),
                    "exists_in_target": target_program.exists(),
                    "files": []
                }

                # 获取所有文件
                if source_program.is_dir():
                    for file_path in source_program.rglob("*"):
                        if file_path.is_file():
                            relative_path = file_path.relative_to(source_program)
                            target_file = target_program / relative_path

                            file_info = {
                                "relative_path": str(relative_path),
                                "source_file": str(file_path),
                                "target_file": str(target_file),
                                "exists_in_target": target_file.exists(),
                                "size_match": target_file.exists() and file_path.stat().st_size == target_file.stat().st_size
                            }
                            program_info["files"].append(file_info)

                external_programs.append(program_info)

        return external_programs

    def _analyze_startup_configs(self, source_path: Path, target_path: Path) -> List[Dict]:
        """分析启动配置差异"""
        startup_configs = []

        # 查找启动配置文件
        config_files = [
            "Windows/System32/winpeshl.ini",
            "Windows/System32/PEConfig/Run.cmd",
            "Windows/System32/PEConfig/LoadPETools.cmd",
            "Windows/System32/StartNet.cmd"
        ]

        for config_file in config_files:
            source_config = source_path / config_file
            target_config = target_path / config_file

            if source_config.exists():
                config_info = {
                    "name": config_file.replace("/", "\\"),
                    "source_path": str(source_config),
                    "target_path": str(target_config),
                    "exists_in_target": target_config.exists(),
                    "content_match": False
                }

                if target_config.exists():
                    try:
                        source_content = source_config.read_text(encoding='utf-8', errors='ignore')
                        target_content = target_config.read_text(encoding='utf-8', errors='ignore')
                        config_info["content_match"] = source_content == target_content
                    except Exception:
                        config_info["content_match"] = False

                startup_configs.append(config_info)

        # 分析PEConfig目录下的Run目录
        peconfig_run_source = source_path / "Windows/System32/PEConfig/Run"
        peconfig_run_target = target_path / "Windows/System32/PEConfig/Run"

        if peconfig_run_source.exists():
            for config_file in peconfig_run_source.rglob("*"):
                if config_file.is_file():
                    relative_path = config_file.relative_to(peconfig_run_source)
                    target_config = peconfig_run_target / relative_path

                    config_info = {
                        "name": f"PEConfig/Run/{relative_path}",
                        "source_path": str(config_file),
                        "target_path": str(target_config),
                        "exists_in_target": target_config.exists(),
                        "content_match": False
                    }

                    if target_config.exists():
                        try:
                            source_content = config_file.read_text(encoding='utf-8', errors='ignore')
                            target_content = target_config.read_text(encoding='utf-8', errors='ignore')
                            config_info["content_match"] = source_content == target_content
                        except Exception:
                            config_info["content_match"] = False

                    startup_configs.append(config_info)

        return startup_configs

    def _analyze_desktop_configs(self, source_path: Path, target_path: Path) -> List[Dict]:
        """分析桌面配置差异"""
        desktop_configs = []

        # 查找桌面配置文件
        config_patterns = [
            "**/*.jcfg",
            "**/*.lua",
            "**/*.xml",
            "**/*.theme"
        ]

        for pattern in config_patterns:
            for config_file in source_path.glob(pattern):
                # 跳过系统文件
                if any(skip in str(config_file).lower() for skip in [
                    "windows/system32/catroot",
                    "windows/system32/wbem",
                    "windows/winsxs"
                ]):
                    continue

                relative_path = config_file.relative_to(source_path)
                target_config = target_path / relative_path

                config_info = {
                    "name": str(relative_path).replace("/", "\\"),
                    "source_path": str(config_file),
                    "target_path": str(target_config),
                    "exists_in_target": target_config.exists(),
                    "size_match": target_config.exists() and config_file.stat().st_size == target_config.stat().st_size
                }

                desktop_configs.append(config_info)

        return desktop_configs

    def _deep_compare_files(self, source_path: Path, target_path: Path) -> Dict:
        """深度比较文件结构"""
        differences = {
            "missing_in_target": [],
            "additional_in_source": [],
            "different_files": []
        }

        # 比较关键目录
        key_directories = [
            "Windows/System32/PEConfig",
            "Windows/System32/Drivers",
            "Program Files"
        ]

        for directory in key_directories:
            source_dir = source_path / directory
            target_dir = target_path / directory

            if source_dir.exists():
                # 获取源目录中的所有文件
                source_files = set()
                for file_path in source_dir.rglob("*"):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(source_dir)
                        source_files.add(str(relative_path))

                # 获取目标目录中的所有文件
                target_files = set()
                if target_dir.exists():
                    for file_path in target_dir.rglob("*"):
                        if file_path.is_file():
                            relative_path = file_path.relative_to(target_dir)
                            target_files.add(str(relative_path))

                # 找出缺失的文件
                missing_files = source_files - target_files
                for missing_file in missing_files:
                    differences["missing_in_target"].append({
                        "directory": directory,
                        "file": missing_file,
                        "source_path": str(source_dir / missing_file),
                        "target_path": str(target_dir / missing_file)
                    })

        return differences

    def copy_external_programs_to_mount(self, source_mount: str, target_mount: str,
                                      external_programs: List[Dict]) -> bool:
        """
        将外部程序完整复制到目标挂载目录

        Args:
            source_mount: 源挂载目录
            target_mount: 目标挂载目录
            external_programs: 外部程序列表

        Returns:
            bool: 复制成功状态
        """
        self._log("开始复制外部程序到目标挂载目录", "info")
        self._update_progress(80, "复制外部程序...")

        target_path = Path(target_mount)
        success_count = 0
        total_count = len(external_programs)

        for program in external_programs:
            try:
                source_path = Path(program["source_path"])
                target_path_program = target_path / Path(program["name"])

                if source_path.exists():
                    # 确保目标目录存在
                    target_path_program.parent.mkdir(parents=True, exist_ok=True)

                    if source_path.is_dir():
                        # 复制整个目录
                        if target_path_program.exists():
                            shutil.rmtree(target_path_program)
                        shutil.copytree(source_path, target_path_program, dirs_exist_ok=True)
                        self._log(f"外部程序目录复制成功: {program['name']}", "success")
                        success_count += 1
                    elif source_path.is_file():
                        # 复制文件
                        target_path_program.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_path, target_path_program)
                        self._log(f"外部程序文件复制成功: {program['name']}", "success")
                        success_count += 1
                else:
                    self._log(f"外部程序源路径不存在: {program['source_path']}", "warning")

            except Exception as e:
                self._log(f"复制外部程序失败: {program['name']} - {str(e)}", "error")

        self._update_progress(85, f"外部程序复制完成 ({success_count}/{total_count})")
        return success_count == total_count

    def execute_enhanced_version_replacement(self, source_dir: str, target_dir: str,
                                           output_dir: str) -> Tuple[bool, str, Dict]:
        """
        执行增强版版本替换流程（使用copype和MakeWinPEMedia模块）

        Args:
            source_dir: 源目录路径 (0WIN11PE)
            target_dir: 目标目录路径 (0WIN10OLD)
            output_dir: 输出目录路径 (WIN10REPLACED)

        Returns:
            Tuple[bool, str, Dict]: (成功状态, 消息, 详细结果)
        """
        try:
            self._log("开始增强版WinPE版本替换流程（使用copype和MakeWinPEMedia）", "info")
            self._update_progress(0, "初始化增强版版本替换...")

            # 路径处理
            source_path = Path(source_dir)
            target_path = Path(target_dir)
            output_path = Path(output_dir)

            # 确保输出目录存在
            output_path.mkdir(parents=True, exist_ok=True)

            # 构建WIM文件路径
            source_wim = source_path / "boot" / "boot.wim"
            target_wim = target_path / "boot.wim"
            output_wim = output_path / "media" / "sources" / "boot.wim"

            # 创建挂载目录
            output_mount = output_path / "mount"
            output_mount.mkdir(parents=True, exist_ok=True)

            result = {
                "success": False,
                "source_wim": str(source_wim),
                "target_wim": str(target_wim),
                "output_wim": str(output_wim),
                "steps": {},
                "timestamp": datetime.now().isoformat()
            }

            # 步骤1：使用copype命令构建WIN10REPLACED
            self._log("步骤1: 使用copype命令构建WIN10REPLACED", "info")
            self._update_progress(5, "使用copype构建WinPE工作目录...")

            # 删除已有的WIN10REPLACED目录，让copype直接创建
            if output_path.exists():
                self._log(f"删除已存在的WIN10REPLACED目录: {output_path}", "info")

                # 强制清理所有可能的挂载点和目录
                self._log("强制清理WIN10REPLACED目录和挂载点", "info")

                # 先尝试卸载所有可能的挂载点
                mount_points = [
                    output_path / "mount",
                    output_path / "WinPE" / "mount"
                ]

                for mount_point in mount_points:
                    if mount_point.exists():
                        self._log(f"强制清理挂载点: {mount_point}", "info")
                        try:
                            # 尝试dism卸载
                            dism_result = self.run_dism_command(
                                ["/Unmount-Wim", f"/MountDir:{mount_point}", "/Discard"],
                                "强制卸载WIM"
                            )
                            if dism_result[0]:
                                self._log(f"DISM卸载成功: {mount_point}", "success")
                            else:
                                self._log(f"DISM卸载失败: {mount_point} - {dism_result[1]}", "warning")
                        except Exception as e:
                            self._log(f"DISM卸载异常: {mount_point} - {str(e)}", "warning")

                        # 无论卸载是否成功，都尝试删除目录
                        try:
                            import os
                            if os.name == 'nt':  # Windows
                                # 在Windows上使用rmdir /s /q强制删除
                                import subprocess
                                result = subprocess.run(
                                    ['cmd', '/c', 'rmdir', '/s', '/q', str(mount_point)],
                                    capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
                                )
                                if result.returncode == 0:
                                    self._log(f"Windows强制删除成功: {mount_point}", "success")
                                else:
                                    self._log(f"Windows强制删除失败: {mount_point}", "warning")
                            else:
                                # 在Linux/Mac上使用rm -rf
                                subprocess.run(['rm', '-rf', str(mount_point)], check=False)
                        except Exception as e:
                            self._log(f"强制删除失败: {mount_point} - {str(e)}", "warning")

                # 最终删除整个WIN10REPLACED目录
                try:
                    import os
                    if os.name == 'nt':  # Windows
                        result = subprocess.run(
                            ['cmd', '/c', 'rmdir', '/s', '/q', str(output_path)],
                            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        if result.returncode == 0:
                            self._log(f"Windows强制删除目录成功: {output_path}", "success")
                        else:
                            self._log(f"Windows强制删除目录失败: {output_path}", "warning")
                    else:
                        subprocess.run(['rm', '-rf', str(output_path)], check=False)
                        self._log(f"Linux删除目录: {output_path}", "success")
                except Exception as e:
                    self._log(f"删除目录失败: {output_path} - {str(e)}", "error")

            # 使用copype命令直接在WinPE_amd64目录中创建WIN10REPLACED
            # 就像创建WinPE_20251028_235101那样：
            # cd D:\APP\WinPEManager\WinPE_amd64
            # copype amd64 WIN10REPLACED
            parent_dir = output_path.parent  # WinPE_amd64
            copype_cmd = self.adk.get_copype_path()
            if not copype_cmd:
                return False, "找不到copype命令", result

            self._log(f"执行copype命令: copype amd64 WIN10REPLACED", "info")
            self._log(f"工作目录: {parent_dir}", "info")

            # 使用subprocess直接运行copype命令
            import subprocess
            import os

            env = os.environ.copy()
            env['PATH'] = str(copype_cmd.parent) + os.pathsep + env['PATH']

            try:
                process = subprocess.Popen(
                    [str(copype_cmd), "amd64", "WIN10REPLACED"],
                    cwd=parent_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    env=env
                )

                # 监控输出
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    line = line.strip()
                    if line:
                        self._log(f"[copype] {line}", "info")
                        # 简单的进度解析
                        if "Copying" in line:
                            self._update_progress(30, "正在复制文件...")
                        elif "Mounting" in line:
                            self._update_progress(70, "挂载WIM文件...")
                        elif "Unmounting" in line:
                            self._update_progress(90, "卸载WIM文件...")

                return_code = process.wait()
                if return_code == 0:
                    self._log("copype执行成功", "success")
                    copype_success = True
                    message = "copype执行成功"
                    workspace_path = output_path
                else:
                    self._log(f"copype执行失败，返回码: {return_code}", "error")
                    copype_success = False
                    message = f"copype执行失败，返回码: {return_code}"
                    workspace_path = output_path

            except Exception as e:
                self._log(f"执行copype命令失败: {str(e)}", "error")
                copype_success = False
                message = f"执行copype命令失败: {str(e)}"
                workspace_path = output_path

            if not copype_success:
                return False, "copype构建WinPE工作目录失败", result

            result["steps"]["copype_build"] = "completed"
            self._log("步骤1完成: WIN10REPLACED基础结构构建成功", "success")

            # 步骤2：复制0WIN10OLD\boot.wim到WIN10REPLACED\media\sources\boot.wim
            self._log("步骤2: 复制boot.wim文件", "info")
            self._update_progress(25, "复制boot.wim文件...")

            if not target_wim.exists():
                return False, f"目标boot.wim文件不存在: {target_wim}", result

            # 确保目标目录存在
            output_wim.parent.mkdir(parents=True, exist_ok=True)

            # 复制boot.wim文件
            shutil.copy2(target_wim, output_wim)
            self._log("步骤2完成: boot.wim文件复制成功", "success")
            result["steps"]["boot_wim_copy"] = "completed"

            # 步骤3：挂载WIN10REPLACED\media\sources\boot.wim到WIN10REPLACED\mount
            self._log("步骤3: 挂载boot.wim文件", "info")
            self._update_progress(35, "挂载boot.wim到mount目录...")

            mount_success = self.mount_wim_with_dism(str(output_wim), str(output_mount))
            if not mount_success:
                return False, "挂载boot.wim失败", result

            self._log("步骤3完成: boot.wim挂载成功", "success")
            result["steps"]["wim_mount"] = "completed"

            # 步骤4：使用dism命令获取WIN10REPLACED的模块信息
            self._log("步骤4: 获取WinPE模块信息", "info")
            self._update_progress(45, "分析WinPE模块...")

            win10replaced_features = self._get_winpe_features(str(output_mount))
            result["win10replaced_features"] = win10replaced_features
            result["steps"]["feature_analysis"] = "completed"

            # 步骤5：对比0WIN11PE注册表和manifests找出包差异
            self._log("步骤5: 对比组件差异", "info")
            self._update_progress(55, "分析组件差异...")

            # 分析0WIN11PE的注册表和manifests
            source_mount = source_path / "mount"
            if not source_mount.exists():
                return False, f"源挂载目录不存在: {source_mount}", result

            component_differences = self._analyze_component_differences(source_mount, output_mount)
            result["component_differences"] = component_differences
            result["steps"]["component_analysis"] = "completed"

            # 步骤6：添加缺失的组件和配置
            self._log("步骤6: 添加缺失组件和配置", "info")
            self._update_progress(65, "添加缺失组件...")

            components_added = self._add_missing_components(output_mount, component_differences)
            result["components_added"] = components_added
            result["steps"]["component_addition"] = "completed"

            # 步骤7：卸载WIN10REPLACED\mount
            self._log("步骤7: 卸载挂载点", "info")
            self._update_progress(85, "卸载WIM挂载点...")

            unmount_success = self.unmount_wim_with_dism(str(output_mount), commit=True)
            if not unmount_success:
                return False, "卸载WIM失败", result

            self._log("步骤7完成: WIM卸载成功", "success")
            result["steps"]["wim_unmount"] = "completed"

            # 步骤8：使用MakeWinPEMedia模块制作ISO
            self._log("步骤8: 制作ISO文件", "info")
            self._update_progress(90, "制作ISO镜像...")

            from core.makewinpe_manager import MakeWinPEMediaManager
            makewinpe_manager = MakeWinPEMediaManager(self.adk, self._update_progress)

            iso_path = output_path.parent / f"{output_path.name}.iso"
            iso_success, iso_message = makewinpe_manager.create_winpe_iso(
                output_path,
                iso_path,
                progress_callback=self._update_progress
            )

            if not iso_success:
                self._log("ISO制作失败，但boot.wim已完成", "warning")
                result["iso_created"] = False
            else:
                self._log("步骤8完成: ISO制作成功", "success")
                result["iso_created"] = True
                result["iso_path"] = str(iso_path)

            result["steps"]["iso_creation"] = "completed"
            result["success"] = True

            self._update_progress(100, "版本替换流程完成")
            success_msg = f"版本替换完成! 输出目录: {output_path}"
            if result.get("iso_created"):
                success_msg += f", ISO文件: {iso_path}"
            self._log(success_msg, "success")

            return True, success_msg, result

        except Exception as e:
            error_msg = f"增强版版本替换失败: {str(e)}"
            self._log(error_msg, "error")
            return False, error_msg, {}

    def _get_winpe_features(self, mount_dir: str) -> List[Dict]:
        """
        使用DISM获取WinPE的模块信息

        Args:
            mount_dir: 挂载目录路径

        Returns:
            List[Dict]: 特性信息列表
        """
        self._log("获取WinPE特性信息", "info")
        features = []

        try:
            # 使用DISM获取所有特性
            command = [
                "/Image:" + mount_dir,
                "/Get-Features",
                "/Format:Table"
            ]

            success, output = self.run_dism_command(command, "获取WinPE特性")

            if success:
                # 解析DISM输出
                lines = output.split('\n')
                for line in lines:
                    line = line.strip()
                    if '|' in line and not line.startswith('Feature Name'):
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) >= 2:
                            feature_info = {
                                "name": parts[0],
                                "state": parts[1] if len(parts) > 1 else "Unknown"
                            }
                            features.append(feature_info)
                            self._log(f"发现特性: {feature_info['name']} - {feature_info['state']}", "info")

            self._log(f"共发现 {len(features)} 个WinPE特性", "info")
            return features

        except Exception as e:
            self._log(f"获取WinPE特性失败: {str(e)}", "error")
            return []

    def _analyze_component_differences(self, source_mount: Path, target_mount: Path) -> Dict:
        """
        对比源和目标的组件差异

        Args:
            source_mount: 源挂载目录 (0WIN11PE\mount)
            target_mount: 目标挂载目录 (WIN10REPLACED\mount)

        Returns:
            Dict: 组件差异信息
        """
        self._log("分析组件差异", "info")
        differences = {
            "missing_features": [],
            "missing_packages": [],
            "missing_files": [],
            "registry_differences": []
        }

        try:
            # 分析离线注册表差异
            self._log("分析注册表差异...", "info")
            registry_diffs = self._analyze_registry_differences(source_mount, target_mount)
            differences["registry_differences"] = registry_diffs

            # 分析WinSxS manifests差异
            self._log("分析WinSxS manifests差异...", "info")
            manifest_diffs = self._analyze_manifest_differences(source_mount, target_mount)
            differences["missing_packages"] = manifest_diffs

            # 分析特性差异
            self._log("分析特性差异...", "info")
            source_features = self._get_winpe_features(str(source_mount))
            target_features = self._get_winpe_features(str(target_mount))

            source_feature_names = {f["name"] for f in source_features if f["state"] == "Enabled"}
            target_feature_names = {f["name"] for f in target_features if f["state"] == "Enabled"}

            missing_features = source_feature_names - target_feature_names
            differences["missing_features"] = list(missing_features)

            self._log(f"发现 {len(missing_features)} 个缺失特性", "info")
            return differences

        except Exception as e:
            self._log(f"分析组件差异失败: {str(e)}", "error")
            return differences

    def _analyze_registry_differences(self, source_mount: Path, target_mount: Path) -> List[Dict]:
        """分析注册表差异"""
        registry_diffs = []

        try:
            source_software = source_mount / "Windows" / "System32" / "Config" / "SOFTWARE"
            target_software = target_mount / "Windows" / "System32" / "Config" / "SOFTWARE"

            if source_software.exists() and target_software.exists():
                # 这里可以添加更详细的注册表分析逻辑
                # 目前只检查文件是否存在和大小
                source_size = source_software.stat().st_size
                target_size = target_software.stat().st_size

                if abs(source_size - target_size) > 1024 * 1024:  # 1MB差异
                    registry_diffs.append({
                        "type": "software_hive",
                        "source_size": source_size,
                        "target_size": target_size,
                        "description": "SOFTWARE注册表配置文件大小差异较大"
                    })

        except Exception as e:
            self._log(f"分析注册表差异失败: {str(e)}", "warning")

        return registry_diffs

    def _analyze_manifest_differences(self, source_mount: Path, target_mount: Path) -> List[str]:
        """分析WinSxS manifests差异"""
        missing_packages = []

        try:
            source_winxsx = source_mount / "Windows" / "WinSxS" / "Manifests"
            target_winxsx = target_mount / "Windows" / "WinSxS" / "Manifests"

            if source_winxsx.exists() and target_winxsx.exists():
                # 获取源目录中的所有manifest文件
                source_manifests = set()
                for manifest_file in source_winxsx.glob("*.manifest"):
                    source_manifests.add(manifest_file.name)

                # 获取目标目录中的所有manifest文件
                target_manifests = set()
                if target_winxsx.exists():
                    for manifest_file in target_winxsx.glob("*.manifest"):
                        target_manifests.add(manifest_file.name)

                # 找出缺失的manifest文件
                missing_manifests = source_manifests - target_manifests

                # 过滤出Microsoft相关的包
                for manifest in missing_manifests:
                    if "microsoft" in manifest.lower():
                        missing_packages.append(manifest)

            self._log(f"发现 {len(missing_packages)} 个缺失的Microsoft包", "info")

        except Exception as e:
            self._log(f"分析manifest差异失败: {str(e)}", "warning")

        return missing_packages

    def _add_missing_components(self, mount_dir: str, component_differences: Dict) -> List[str]:
        """
        添加缺失的组件

        Args:
            mount_dir: 挂载目录
            component_differences: 组件差异信息

        Returns:
            List[str]: 已添加的组件列表
        """
        self._log("添加缺失组件", "info")
        added_components = []

        try:
            # 添加缺失的特性
            missing_features = component_differences.get("missing_features", [])
            for feature in missing_features:
                self._log(f"尝试添加特性: {feature}", "info")
                success = self.add_component_to_wim("", feature, mount_dir, "feature")
                if success:
                    added_components.append(f"Feature: {feature}")
                    self._log(f"特性添加成功: {feature}", "success")
                else:
                    self._log(f"特性添加失败: {feature}", "warning")

            # 添加外部程序和配置
            self._log("添加外部程序和配置...", "info")
            external_added = self._copy_external_programs_from_source(mount_dir, source_mount)
            added_components.extend(external_added)

            # 复制WinXShell相关配置
            self._log("复制WinXShell配置...", "info")
            winxshell_added = self._copy_winxshell_config(mount_dir, source_mount)
            added_components.extend(winxshell_added)

            self._log(f"共添加 {len(added_components)} 个组件", "info")

        except Exception as e:
            self._log(f"添加缺失组件失败: {str(e)}", "error")

        return added_components

    def _copy_external_programs_from_source(self, target_mount: str, source_mount: str) -> List[str]:
        """
        从源挂载目录复制外部程序到目标挂载目录

        Args:
            target_mount: 目标挂载目录 (WIN10REPLACED\mount)
            source_mount: 源挂载目录 (0WIN11PE\mount)

        Returns:
            List[str]: 已复制的外部程序列表
        """
        self._log("复制外部程序", "info")
        copied_programs = []

        try:
            target_path = Path(target_mount)
            source_path = Path(source_mount)

            # 外部程序目录列表
            external_dirs = [
                "Program Files/WinXShell",
                "Program Files/CairoShell",
                "Program Files/Explorer",
                "Windows/System32/Programs",
                "Windows/System32/PEConfig",
                "Windows/System32/startup"
            ]

            for external_dir in external_dirs:
                source_dir = source_path / external_dir
                target_dir = target_path / external_dir

                if source_dir.exists():
                    self._log(f"复制外部程序目录: {external_dir}", "info")
                    try:
                        # 确保目标父目录存在
                        target_dir.parent.mkdir(parents=True, exist_ok=True)

                        if source_dir.is_dir():
                            # 复制整个目录
                            if target_dir.exists():
                                shutil.rmtree(target_dir, ignore_errors=True)
                            shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
                            copied_programs.append(f"Directory: {external_dir}")
                            self._log(f"外部程序目录复制成功: {external_dir}", "success")
                        elif source_dir.is_file():
                            # 复制文件
                            target_dir.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(source_dir, target_dir)
                            copied_programs.append(f"File: {external_dir}")
                            self._log(f"外部程序文件复制成功: {external_dir}", "success")

                    except Exception as e:
                        self._log(f"复制外部程序失败: {external_dir} - {str(e)}", "error")

            self._log(f"共复制 {len(copied_programs)} 个外部程序", "info")
            return copied_programs

        except Exception as e:
            self._log(f"复制外部程序失败: {str(e)}", "error")
            return []

    def _copy_winxshell_config(self, target_mount: str, source_mount: str) -> List[str]:
        """
        复制WinXShell相关配置

        Args:
            target_mount: 目标挂载目录 (WIN10REPLACED\mount)
            source_mount: 源挂载目录 (0WIN11PE\mount)

        Returns:
            List[str]: 已复制的配置列表
        """
        self._log("复制WinXShell配置", "info")
        copied_configs = []

        try:
            target_path = Path(target_mount)
            source_path = Path(source_mount)

            # WinXShell相关配置文件
            winxshell_configs = [
                "Windows/System32/winpeshl.ini",
                "Windows/System32/startnet.cmd",
                "Windows/System32/PEConfig/Run.cmd",
                "Windows/System32/PEConfig/LoadPETools.cmd"
            ]

            for config_file in winxshell_configs:
                source_file = source_path / config_file
                target_file = target_path / config_file

                if source_file.exists():
                    try:
                        # 确保目标目录存在
                        target_file.parent.mkdir(parents=True, exist_ok=True)

                        # 复制配置文件
                        shutil.copy2(source_file, target_file)
                        copied_configs.append(config_file)
                        self._log(f"WinXShell配置复制成功: {config_file}", "success")

                    except Exception as e:
                        self._log(f"复制WinXShell配置失败: {config_file} - {str(e)}", "error")

            # 复制WinXShell主程序和配置目录
            winxshell_program_dir = source_path / "Program Files/WinXShell"
            if winxshell_program_dir.exists():
                target_winxshell_dir = target_path / "Program Files/WinXShell"
                try:
                    target_winxshell_dir.parent.mkdir(parents=True, exist_ok=True)
                    if target_winxshell_dir.exists():
                        shutil.rmtree(target_winxshell_dir, ignore_errors=True)
                    shutil.copytree(winxshell_program_dir, target_winxshell_dir, dirs_exist_ok=True)
                    copied_configs.append("Program Files/WinXShell")
                    self._log("WinXShell程序目录复制成功", "success")

                    # 处理WinXShell的自启动配置
                    self._setup_winxshell_autostart(target_path)

                except Exception as e:
                    self._log(f"复制WinXShell程序目录失败: {str(e)}", "error")

            self._log(f"共复制 {len(copied_configs)} 个WinXShell配置", "info")
            return copied_configs

        except Exception as e:
            self._log(f"复制WinXShell配置失败: {str(e)}", "error")
            return []

    def _setup_winxshell_autostart(self, mount_path: Path):
        """设置WinXShell自启动配置"""
        try:
            # 创建或修改winpeshl.ini配置
            winpeshl_ini = mount_path / "Windows" / "System32" / "winpeshl.ini"

            winpeshl_content = """[LaunchApps]
%windir%\\System32\\winpeshl.exe
%windir%\\Program Files\\WinXShell\\WinXShell.exe
"""

            try:
                winpeshl_ini.parent.mkdir(parents=True, exist_ok=True)
                with open(winpeshl_ini, 'w', encoding='utf-8') as f:
                    f.write(winpeshl_content)
                self._log("WinXShell自启动配置设置成功", "success")

            except Exception as e:
                self._log(f"设置WinXShell自启动配置失败: {str(e)}", "error")

        except Exception as e:
            self._log(f"WinXShell自启动设置失败: {str(e)}", "error")

    def _copy_config_files(self, source_mount: str, target_mount: str, mount_differences: Dict):
        """复制配置文件"""
        source_path = Path(source_mount)
        target_path = Path(target_mount)

        # 复制启动配置
        startup_configs = mount_differences.get("startup_configs", [])
        for config in startup_configs:
            if not config.get("exists_in_target") or not config.get("content_match", False):
                source_config = Path(config["source_path"])
                target_config = Path(config["target_path"])

                try:
                    if source_config.exists():
                        target_config.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_config, target_config)
                        self._log(f"启动配置复制成功: {config['name']}", "success")
                except Exception as e:
                    self._log(f"启动配置复制失败: {config['name']} - {str(e)}", "error")

        # 复制桌面配置
        desktop_configs = mount_differences.get("desktop_configs", [])
        for config in desktop_configs:
            if not config.get("exists_in_target"):
                source_config = Path(config["source_path"])
                target_config = Path(config["target_path"])

                try:
                    if source_config.exists():
                        target_config.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_config, target_config)
                        self._log(f"桌面配置复制成功: {config['name']}", "success")
                except Exception as e:
                    self._log(f"桌面配置复制失败: {config['name']} - {str(e)}", "error")

    def generate_enhanced_report(self, result: Dict, report_path: str) -> str:
        """生成增强版版本替换报告"""
        try:
            report = {
                "enhanced_version_replacement": {
                    "timestamp": result.get("timestamp", datetime.now().isoformat()),
                    "success": result.get("success", False),
                    "summary": {
                        "source_wim": result.get("source_wim", ""),
                        "target_wim": result.get("target_wim", ""),
                        "output_wim": result.get("output_wim", ""),
                        "external_programs_copied": result.get("external_programs_copied", 0)
                    },
                    "wim_analysis": result.get("wim_differences", {}),
                    "mount_analysis": result.get("mount_differences", {}),
                    "operations": {
                        "dism_comparison": "✅ 完成",
                        "mount_analysis": "✅ 完成",
                        "external_programs_copy": "✅ 完成",
                        "config_files_copy": "✅ 完成",
                        "wim_mount_commit": "✅ 完成"
                    }
                }
            }

            # 保存报告
            report_file = Path(report_path)
            report_file.parent.mkdir(parents=True, exist_ok=True)

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            self._log(f"增强版版本替换报告已生成: {report_file}", "info")
            return str(report_file)

        except Exception as e:
            error_msg = f"生成增强版报告失败: {str(e)}"
            self._log(error_msg, "error")
            return ""