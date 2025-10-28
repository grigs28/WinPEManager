#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本替换配置模块
定义版本替换的配置类和数据结构
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional


@dataclass
class VersionReplaceConfig:
    """版本替换配置"""

    # 目录配置
    source_dir: Path        # 源目录 (0WIN11PE)
    target_dir: Path        # 目标目录 (0WIN10OLD)
    output_dir: Path        # 输出目录 (WIN10REPLACED)

    # WIM文件配置
    source_wim: Path        # 源WIM文件 (0WIN11PE\boot\boot.wim)
    target_wim: Path        # 目标WIM文件 (0WIN10OLD\boot.wim)
    output_wim: Path        # 输出WIM文件 (WIN10REPLACED\boot\boot.wim)

    # 挂载配置
    mount_dir: Path         # 挂载目录 (WIN10REPLACED\mount)

    # 迁移选项
    migrate_options: Dict[str, bool] = None

    def __post_init__(self):
        """确保路径是Path对象并设置默认选项"""
        # 转换为Path对象
        self.source_dir = Path(self.source_dir)
        self.target_dir = Path(self.target_dir)
        self.output_dir = Path(self.output_dir)
        self.source_wim = Path(self.source_wim)
        self.target_wim = Path(self.target_wim)
        self.output_wim = Path(self.output_wim)
        self.mount_dir = Path(self.mount_dir)

        # 设置默认迁移选项
        if self.migrate_options is None:
            self.migrate_options = {
                'migrate_external_programs': True,
                'migrate_startup_scripts': True,
                'migrate_drivers': True,
                'migrate_custom_components': True,
                'preserve_source_structure': True,
                'replace_core_files': False,  # 保持源的核心文件，只替换目标版本特定文件
                'update_configurations': True
            }

    def validate(self) -> tuple[bool, list[str]]:
        """
        验证配置的有效性

        Returns:
            tuple[bool, list[str]]: (是否有效, 错误消息列表)
        """
        errors = []

        # 检查源目录
        if not self.source_dir.exists():
            errors.append(f"源目录不存在: {self.source_dir}")
        else:
            # 检查源目录结构
            if not (self.source_dir / "boot").exists():
                errors.append(f"源目录缺少boot文件夹: {self.source_dir / 'boot'}")
            if not self.source_wim.exists():
                errors.append(f"源WIM文件不存在: {self.source_wim}")

        # 检查目标目录
        if not self.target_dir.exists():
            errors.append(f"目标目录不存在: {self.target_dir}")
        else:
            if not self.target_wim.exists():
                errors.append(f"目标WIM文件不存在: {self.target_wim}")

        # 检查输出目录父目录
        if not self.output_dir.parent.exists():
            errors.append(f"输出目录的父目录不存在: {self.output_dir.parent}")

        return len(errors) == 0, errors

    def get_migration_plan_summary(self) -> Dict[str, Any]:
        """获取迁移计划摘要"""
        return {
            "source_info": {
                "directory": str(self.source_dir),
                "wim_file": str(self.source_wim),
                "version_hint": "WIN11" if "WIN11" in str(self.source_dir).upper() else "Unknown"
            },
            "target_info": {
                "directory": str(self.target_dir),
                "wim_file": str(self.target_wim),
                "version_hint": "WIN10" if "WIN10" in str(self.target_dir).upper() else "Unknown"
            },
            "output_info": {
                "directory": str(self.output_dir),
                "wim_file": str(self.output_wim),
                "mount_dir": str(self.mount_dir)
            },
            "migration_options": self.migrate_options
        }


def create_version_replace_config(
    source_dir: str,
    target_dir: str,
    output_dir: str,
    **kwargs
) -> VersionReplaceConfig:
    """
    创建版本替换配置

    Args:
        source_dir: 源目录路径
        target_dir: 目标目录路径
        output_dir: 输出目录路径
        **kwargs: 其他配置选项

    Returns:
        VersionReplaceConfig: 版本替换配置对象
    """
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
        mount_dir=output_path / "mount",
        **kwargs
    )

    return config


def validate_paths_for_replacement(
    source_dir: str,
    target_dir: str,
    output_dir: str
) -> tuple[bool, list[str]]:
    """
    验证路径是否适合进行版本替换

    Args:
        source_dir: 源目录路径
        target_dir: 目标目录路径
        output_dir: 输出目录路径

    Returns:
        tuple[bool, list[str]]: (是否有效, 消息列表)
    """
    messages = []

    try:
        config = create_version_replace_config(source_dir, target_dir, output_dir)
        is_valid, errors = config.validate()

        if not is_valid:
            return False, errors

        # 检查挂载状态
        source_mount = config.source_dir / "mount"
        target_mount = config.target_dir / "mount"

        if not source_mount.exists():
            messages.append("警告: 源WIM可能未挂载")

        if not target_mount.exists():
            messages.append("警告: 目标WIM可能未挂载")

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
                messages.append(f"警告: 磁盘空间可能不足，需要约 {total_size / (1024**3):.1f} GB")

        except Exception as e:
            messages.append(f"无法检查磁盘空间: {str(e)}")

        return True, messages

    except Exception as e:
        return False, [f"路径验证失败: {str(e)}"]