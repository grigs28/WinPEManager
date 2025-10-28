#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组件迁移器模块
执行具体的组件迁移操作
"""

import os
import shutil
import stat
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from utils.logger import get_logger


class ComponentMigrator:
    """组件迁移器 - 执行组件迁移操作"""

    def __init__(self):
        self.logger = get_logger("ComponentMigrator")

    def execute_migration(self, migration_plan: Dict[str, Any], source_mount: Path, output_mount: Path) -> Dict[str, Any]:
        """
        执行组件迁移

        Args:
            migration_plan: 迁移计划
            source_mount: 源挂载路径
            output_mount: 输出挂载路径

        Returns:
            迁移结果
        """
        result = {
            "success": True,
            "errors": [],
            "warnings": [],
            "migrated_items": []
        }

        try:
            self.logger.info("开始执行组件迁移...")

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

            self.logger.info(f"组件迁移完成，共迁移 {len(result['migrated_items'])} 个项目")

        except Exception as e:
            result["success"] = False
            result["errors"].append(f"组件迁移异常: {str(e)}")
            self.logger.error(f"组件迁移异常: {str(e)}")

        return result

    def _migrate_external_program(self, program_name: str, source_mount: Path, output_mount: Path) -> bool:
        """
        迁移外部程序

        Args:
            program_name: 程序名称
            source_mount: 源挂载路径
            output_mount: 输出挂载路径

        Returns:
            是否迁移成功
        """
        try:
            source_system32 = source_mount / "Windows" / "System32"
            output_system32 = output_mount / "Windows" / "System32"

            if program_name == "WinXShell":
                return self._migrate_winxshell(source_system32, output_system32, source_mount, output_mount)

            elif program_name == "Cairo Shell":
                return self._migrate_cairo_shell(source_system32, output_system32)

            elif program_name == "Custom Tools":
                return self._migrate_custom_tools(source_system32, output_system32)

            return False

        except Exception as e:
            self.logger.error(f"迁移外部程序 {program_name} 失败: {str(e)}")
            return False

    def _migrate_winxshell(self, source_system32: Path, output_system32: Path, source_mount: Path, output_mount: Path) -> bool:
        """迁移WinXShell"""
        try:
            # 迁移System32中的WinXShell相关文件
            patterns = ["WinXShell*", "*.jcfg", "*.lua"]
            migrated_files = 0

            for pattern in patterns:
                for source_file in source_system32.glob(pattern):
                    if source_file.is_file():
                        target_file = output_system32 / source_file.name
                        success = self._copy_file_with_permission_handling(source_file, target_file)
                        if success:
                            migrated_files += 1
                            self.logger.debug(f"迁移WinXShell文件: {source_file.name}")

            # 迁移Program Files中的WinXShell
            source_programs = source_mount / "Program Files" / "WinXShell"
            if source_programs.exists():
                output_programs = output_mount / "Program Files" / "WinXShell"
                success = self._copy_tree_with_permission_handling(source_programs, output_programs)
                if success:
                    self.logger.info(f"迁移WinXShell程序目录: {source_programs}")
                    migrated_files += len(list(source_programs.rglob("*")))

            self.logger.info(f"WinXShell迁移完成，共迁移 {migrated_files} 个文件")
            return migrated_files > 0

        except Exception as e:
            self.logger.error(f"迁移WinXShell失败: {str(e)}")
            return False

    def _migrate_cairo_shell(self, source_system32: Path, output_system32: Path) -> bool:
        """迁移Cairo Shell"""
        try:
            patterns = ["Cairo*", "*.cairo"]
            migrated_files = 0

            for pattern in patterns:
                for source_file in source_system32.glob(pattern):
                    if source_file.is_file():
                        target_file = output_system32 / source_file.name
                        success = self._copy_file_with_permission_handling(source_file, target_file)
                        if success:
                            migrated_files += 1
                            self.logger.debug(f"迁移Cairo文件: {source_file.name}")

            self.logger.info(f"Cairo Shell迁移完成，共迁移 {migrated_files} 个文件")
            return migrated_files > 0

        except Exception as e:
            self.logger.error(f"迁移Cairo Shell失败: {str(e)}")
            return False

    def _migrate_custom_tools(self, source_system32: Path, output_system32: Path) -> bool:
        """迁移自定义工具"""
        try:
            migrated_files = 0

            for source_file in source_system32.glob("*"):
                if (source_file.is_file() and
                    source_file.suffix.lower() in [".exe", ".msi", ".bat", ".cmd", ".ps1"] and
                    not self._is_system_file(source_file.name)):

                    target_file = output_system32 / source_file.name
                    if not target_file.exists():
                        success = self._copy_file_with_permission_handling(source_file, target_file)
                        if success:
                            migrated_files += 1
                            self.logger.debug(f"迁移自定义工具: {source_file.name}")

            self.logger.info(f"自定义工具迁移完成，共迁移 {migrated_files} 个文件")
            return migrated_files > 0

        except Exception as e:
            self.logger.error(f"迁移自定义工具失败: {str(e)}")
            return False

    def _migrate_startup_script(self, script_path: str, source_mount: Path, output_mount: Path) -> bool:
        """
        迁移启动脚本

        Args:
            script_path: 脚本相对路径
            source_mount: 源挂载路径
            output_mount: 输出挂载路径

        Returns:
            是否迁移成功
        """
        try:
            source_file = source_mount / script_path
            target_file = output_mount / script_path

            if source_file.exists():
                target_file.parent.mkdir(parents=True, exist_ok=True)
                success = self._copy_file_with_permission_handling(source_file, target_file)
                if success:
                    self.logger.debug(f"迁移启动脚本: {script_path}")
                return success

            return False

        except Exception as e:
            self.logger.error(f"迁移启动脚本 {script_path} 失败: {str(e)}")
            return False

    def _migrate_driver(self, driver_path: str, source_mount: Path, output_mount: Path) -> bool:
        """
        迁移驱动程序

        Args:
            driver_path: 驱动相对路径
            source_mount: 源挂载路径
            output_mount: 输出挂载路径

        Returns:
            是否迁移成功
        """
        try:
            source_file = source_mount / driver_path
            target_file = output_mount / driver_path

            if source_file.exists():
                target_file.parent.mkdir(parents=True, exist_ok=True)
                success = self._copy_file_with_permission_handling(source_file, target_file)
                if success:
                    self.logger.debug(f"迁移驱动程序: {driver_path}")
                return success

            return False

        except Exception as e:
            self.logger.error(f"迁移驱动程序 {driver_path} 失败: {str(e)}")
            return False

    def _migrate_custom_components(self, source_mount: Path, output_mount: Path, result: Dict):
        """迁移自定义组件"""
        try:
            migrated_components = []

            # 迁移PEConfig目录
            source_peconfig = source_mount / "Windows" / "System32" / "PEConfig"
            if source_peconfig.exists():
                output_peconfig = output_mount / "Windows" / "System32" / "PEConfig"
                success = self._copy_tree_with_permission_handling(source_peconfig, output_peconfig)
                if success:
                    migrated_components.append("PEConfig目录")
                    self.logger.info("迁移PEConfig目录")

            # 迁移Programs目录
            source_programs = source_mount / "Windows" / "System32" / "Programs"
            if source_programs.exists():
                output_programs = output_mount / "Windows" / "System32" / "Programs"
                success = self._copy_tree_with_permission_handling(source_programs, output_programs)
                if success:
                    migrated_components.append("Programs目录")
                    self.logger.info("迁移Programs目录")

            # 迁移Drivers目录
            source_drivers = source_mount / "Drivers"
            if source_drivers.exists():
                output_drivers = output_mount / "Drivers"
                success = self._copy_tree_with_permission_handling(source_drivers, output_drivers)
                if success:
                    migrated_components.append("Drivers目录")
                    self.logger.info("迁移Drivers目录")

            # 迁移Scripts目录
            source_scripts = source_mount / "Scripts"
            if source_scripts.exists():
                output_scripts = output_mount / "Scripts"
                success = self._copy_tree_with_permission_handling(source_scripts, output_scripts)
                if success:
                    migrated_components.append("Scripts目录")
                    self.logger.info("迁移Scripts目录")

            # 更新结果
            result["migrated_items"].extend(migrated_components)

        except Exception as e:
            self.logger.error(f"迁移自定义组件时出现问题: {str(e)}")
            result["warnings"].append(f"迁移自定义组件时出现问题: {str(e)}")

    def _copy_file_with_permission_handling(self, src: Path, dst: Path) -> bool:
        """
        带权限处理的文件复制

        Args:
            src: 源文件路径
            dst: 目标文件路径

        Returns:
            是否复制成功
        """
        try:
            # 确保目标目录存在
            dst.parent.mkdir(parents=True, exist_ok=True)

            # 如果目标文件存在且是只读的，先删除
            if dst.exists():
                try:
                    # 移除只读属性
                    dst.chmod(stat.S_IWRITE | stat.S_IREAD)
                except (PermissionError, OSError):
                    pass  # 忽略权限错误

            # 复制文件
            shutil.copy2(src, dst)
            return True

        except (PermissionError, OSError) as e:
            # 尝试使用管理员权限的方法
            if e.errno == 13:  # 权限拒绝
                try:
                    # 使用 shutil.copy 而不是 copy2 来跳过元数据
                    shutil.copy(src, dst)
                    self.logger.debug(f"使用备用复制方法成功: {src}")
                    return True
                except Exception as e2:
                    self.logger.warning(f"复制文件失败（权限问题）: {src} - {str(e2)}")
                    return False
            else:
                self.logger.error(f"复制文件失败: {src} - {str(e)}")
                return False

    def _copy_tree_with_permission_handling(self, src: Path, dst: Path) -> bool:
        """
        带权限处理的目录复制

        Args:
            src: 源目录路径
            dst: 目标目录路径

        Returns:
            是否复制成功
        """
        try:
            if not dst.exists():
                dst.mkdir(parents=True, exist_ok=True)

            for item in src.iterdir():
                dst_item = dst / item.name

                if item.is_dir():
                    success = self._copy_tree_with_permission_handling(item, dst_item)
                    if not success:
                        self.logger.warning(f"复制子目录失败: {item}")
                elif item.is_file():
                    success = self._copy_file_with_permission_handling(item, dst_item)
                    if not success:
                        self.logger.warning(f"复制文件失败: {item}")

            return True

        except Exception as e:
            self.logger.error(f"复制目录时出现问题: {src} -> {dst}, 错误: {str(e)}")
            return False

    def _is_system_file(self, filename: str) -> bool:
        """判断是否为系统文件"""
        system_files = {
            "cmd.exe", "powershell.exe", "reg.exe", "sfc.exe", "chkdsk.exe",
            "format.com", "diskpart.exe", "bcdedit.exe", "bootsect.exe",
            "wpeinit.exe", "wpeutil.exe", "winpeshl.exe", "winload.exe",
            "winpe.wim", "setup.exe", "bootmgr.exe"
        }
        return filename.lower() in system_files

    def verify_migration_result(self, output_mount: Path, migration_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证迁移结果

        Args:
            output_mount: 输出挂载路径
            migration_plan: 迁移计划

        Returns:
            验证结果
        """
        result = {
            "success": True,
            "errors": [],
            "warnings": [],
            "verification_details": {}
        }

        try:
            system32 = output_mount / "Windows" / "System32"

            # 验证外部程序迁移
            external_programs = migration_plan.get("migrate_external_programs", [])
            external_verification = {}

            for program in external_programs:
                if program == "WinXShell":
                    winxshell_found = any(system32.glob("WinXShell*"))
                    external_verification["winxshell"] = winxshell_found
                    if not winxshell_found:
                        result["warnings"].append("WinXShell迁移验证失败")

                elif program == "Cairo Shell":
                    cairo_found = any(system32.glob("Cairo*"))
                    external_verification["cairo_shell"] = cairo_found
                    if not cairo_found:
                        result["warnings"].append("Cairo Shell迁移验证失败")

            result["verification_details"]["external_programs"] = external_verification

            # 验证启动脚本迁移
            startup_scripts = migration_plan.get("migrate_startup_scripts", [])
            scripts_verification = {}

            for script in startup_scripts:
                script_path = output_mount / script
                scripts_verification[script] = script_path.exists()
                if not script_path.exists():
                    result["warnings"].append(f"启动脚本迁移验证失败: {script}")

            result["verification_details"]["startup_scripts"] = scripts_verification

            # 验证自定义组件
            custom_components = {
                "peconfig_exists": (system32 / "PEConfig").exists(),
                "programs_exists": (system32 / "Programs").exists(),
                "drivers_exists": (output_mount / "Drivers").exists(),
                "scripts_exists": (output_mount / "Scripts").exists()
            }

            result["verification_details"]["custom_components"] = custom_components

            self.logger.info("迁移结果验证完成")

        except Exception as e:
            result["success"] = False
            result["errors"].append(f"验证迁移结果失败: {str(e)}")

        return result