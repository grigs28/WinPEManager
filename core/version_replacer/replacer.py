#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本替换器主模块
整合所有组件，提供完整的版本替换功能
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

from utils.logger import get_logger, log_command, log_build_step, log_system_event

from .config import VersionReplaceConfig
from .analyzer import ComponentAnalyzer
from .migrator import ComponentMigrator


class VersionReplacer:
    """增强版WinPE版本替换器主类"""

    def __init__(self, config_manager, adk_manager, unified_wim_manager):
        """
        初始化版本替换器

        Args:
            config_manager: 配置管理器
            adk_manager: ADK管理器
            unified_wim_manager: 统一WIM管理器
        """
        self.config = config_manager
        self.adk = adk_manager
        self.wim_manager = unified_wim_manager
        self.logger = get_logger("VersionReplacer")

        # 初始化组件
        self.component_analyzer = ComponentAnalyzer()
        self.component_migrator = ComponentMigrator()

        # 回调函数
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
                migration_result = self.component_migrator.execute_migration(
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

        # 使用配置对象的验证方法
        is_valid, errors = config.validate()
        if not is_valid:
            result["success"] = False
            result["errors"].extend(errors)
            return result

        # 检查挂载状态
        source_mount = config.source_dir / "mount"
        target_mount = config.target_dir / "mount"

        if not source_mount.exists():
            result["warnings"].append("源WIM可能未挂载")

        if not target_mount.exists():
            result["warnings"].append("目标WIM可能未挂载")

        # 检查磁盘空间
        try:
            import shutil

            source_size = 0
            if config.source_dir.exists():
                for item in config.source_dir.rglob("*"):
                    if item.is_file():
                        source_size += item.stat().st_size

            target_size = 0
            if config.target_wim.exists():
                target_size = config.target_wim.stat().st_size

            total_size = source_size + target_size

            free_space = shutil.disk_usage(config.output_dir.parent).free
            if free_space < total_size * 1.5:  # 预留50%额外空间
                result["warnings"].append(f"磁盘空间可能不足，需要约 {total_size / (1024**3):.1f} GB")

        except Exception as e:
            result["warnings"].append(f"无法检查磁盘空间: {str(e)}")

        return result

    def _copy_source_structure(self, config: VersionReplaceConfig) -> Dict[str, Any]:
        """复制源目录结构到输出目录"""
        result = {"success": True, "errors": [], "warnings": []}

        try:
            self._log(f"复制源目录结构: {config.source_dir} -> {config.output_dir}")

            # 创建输出目录
            config.output_dir.mkdir(parents=True, exist_ok=True)

            # 复制源目录结构（不包括mount目录）
            copied_items = 0
            for item in config.source_dir.iterdir():
                if item.name == "mount":
                    continue  # 跳过mount目录

                target_item = config.output_dir / item.name

                if item.is_file():
                    shutil.copy2(item, target_item)
                    copied_items += 1
                elif item.is_dir():
                    copied_items += self._copy_tree_with_permission_handling(item, target_item)

            self._log(f"✅ 源目录结构复制完成，共复制 {copied_items} 个项目")

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

            file_size = config.output_wim.stat().st_size / (1024 * 1024)  # MB
            self._log(f"✅ 目标boot.wim复制完成，文件大小: {file_size:.1f} MB")

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

    def _update_configuration_files(self, output_mount: Path, analysis: Dict[str, Any]) -> Dict[str, Any]:
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

    def _verify_replacement_result(self, output_mount: Path, analysis: Dict[str, Any]) -> Dict[str, Any]:
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

            # 使用组件迁移器验证迁移结果
            migration_plan = analysis["migration_plan"]
            migration_verification = self.component_migrator.verify_migration_result(
                output_mount, migration_plan
            )

            result["verification_details"].update(migration_verification["verification_details"])
            result["warnings"].extend(migration_verification["warnings"])

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

    def _copy_tree_with_permission_handling(self, src: Path, dst: Path) -> int:
        """
        带权限处理的目录复制

        Returns:
            复制的项目数量
        """
        copied_count = 0
        try:
            if not dst.exists():
                dst.mkdir(parents=True, exist_ok=True)

            for item in src.iterdir():
                dst_item = dst / item.name

                if item.is_dir():
                    copied_count += self._copy_tree_with_permission_handling(item, dst_item)
                elif item.is_file():
                    try:
                        shutil.copy2(item, dst_item)
                        copied_count += 1
                    except (PermissionError, OSError):
                        # 处理权限问题
                        if dst_item.exists():
                            dst_item.chmod(stat.S_IWRITE | stat.S_IREAD)
                        shutil.copy(item, dst_item)
                        copied_count += 1

        except Exception as e:
            self.logger.warning(f"复制目录时出现问题: {src} -> {dst}, 错误: {str(e)}")

        return copied_count

    def generate_replacement_report(self, result: Dict[str, Any]) -> str:
        """生成替换报告"""
        report = []
        report.append("=" * 60)
        report.append("WinPE版本替换详细报告")
        report.append("=" * 60)
        report.append("")

        # 基本信息
        config = result.get("config", {})
        if config:
            report.append("配置信息:")
            report.append(f"  源目录: {config.source_dir}")
            report.append(f"  目标目录: {config.target_dir}")
            report.append(f"  输出目录: {config.output_dir}")
            report.append("")

        # 分析结果
        analysis = result.get("analysis", {})
        if analysis:
            report.append("分析结果:")
            report.append(f"  分析时间: {analysis.get('analysis_time', 'Unknown')}")
            report.append("")

            # 迁移计划
            migration_plan = analysis.get("migration_plan", {})
            report.append("迁移计划:")
            report.append(f"  - 核心文件替换: {len(migration_plan.get('replace_core_files', []))} 个")
            report.append(f"  - 外部程序迁移: {len(migration_plan.get('migrate_external_programs', []))} 个")
            report.append(f"  - 启动脚本迁移: {len(migration_plan.get('migrate_startup_scripts', []))} 个")
            report.append(f"  - 驱动程序迁移: {len(migration_plan.get('migrate_drivers', []))} 个")
            report.append("")

        # 步骤结果
        steps = result.get("steps", {})
        if steps:
            report.append("执行步骤:")
            for step_name, step_result in steps.items():
                if isinstance(step_result, dict):
                    success = step_result.get("success", True)
                    status = "✅ 成功" if success else "❌ 失败"
                    report.append(f"  - {step_name}: {status}")

                    # 显示错误和警告
                    errors = step_result.get("errors", [])
                    for error in errors:
                        report.append(f"    错误: {error}")

                    warnings = step_result.get("warnings", [])
                    for warning in warnings:
                        report.append(f"    警告: {warning}")

            report.append("")

        # 最终状态
        success = result.get("success", False)
        report.append(f"最终状态: {'✅ 成功' if success else '❌ 失败'}")

        # 输出路径
        output_path = result.get("output_path")
        if output_path:
            report.append(f"输出路径: {output_path}")

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)

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


# 为了向后兼容，保留原有的创建函数
from .config import create_version_replace_config