#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本管理模块
负责管理应用程序版本信息和版本控制
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger("WinPEManager")


@dataclass
class VersionInfo:
    """版本信息数据类"""
    major: int = 1
    minor: int = 0
    patch: int = 0
    prerelease: Optional[str] = None  # 例如: "alpha", "beta", "rc"
    build: Optional[str] = None  # 构建号

    def __str__(self) -> str:
        """返回版本字符串"""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    @classmethod
    def from_string(cls, version_str: str) -> 'VersionInfo':
        """从版本字符串创建VersionInfo对象"""
        # 匹配语义化版本: major.minor.patch[-prerelease][+build]
        pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9]+))?(?:\+([a-zA-Z0-9]+))?$'
        match = re.match(pattern, version_str.strip())

        if not match:
            raise ValueError(f"无效的版本格式: {version_str}")

        major, minor, patch = map(int, match.group(1, 2, 3))
        prerelease = match.group(4)
        build = match.group(5)

        return cls(major, minor, patch, prerelease, build)

    def bump_major(self) -> 'VersionInfo':
        """升级主版本号"""
        return VersionInfo(self.major + 1, 0, 0)

    def bump_minor(self) -> 'VersionInfo':
        """升级次版本号"""
        return VersionInfo(self.major, self.minor + 1, 0)

    def bump_patch(self) -> 'VersionInfo':
        """升级补丁版本号"""
        return VersionInfo(self.major, self.minor, self.patch + 1)

    def is_prerelease(self) -> bool:
        """检查是否为预发布版本"""
        return self.prerelease is not None

    def is_stable(self) -> bool:
        """检查是否为稳定版本"""
        return not self.is_prerelease()


@dataclass
class ChangelogEntry:
    """变更日志条目"""
    version: str
    release_date: str
    changes: List[Dict[str, str]]  # [{"type": "新增|修复|改进|删除", "description": "描述"}]

    def add_change(self, change_type: str, description: str):
        """添加变更项"""
        self.changes.append({
            "type": change_type,
            "description": description
        })

    def get_changes_by_type(self, change_type: str) -> List[str]:
        """获取特定类型的变更"""
        return [change["description"] for change in self.changes if change["type"] == change_type]


class VersionManager:
    """版本管理器"""

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化版本管理器

        Args:
            project_root: 项目根目录
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent

        self.project_root = Path(project_root)
        self.version_file = self.project_root / "core" / "version.json"
        self.changelog_file = self.project_root / "docs" / "CHANGELOG.md"

        # 确保目录存在
        self.version_file.parent.mkdir(exist_ok=True)
        self.changelog_file.parent.mkdir(exist_ok=True)

        # 初始化版本信息
        self.current_version = self._load_version()
        self.changelog_entries = self._load_changelog()

    def _load_version(self) -> VersionInfo:
        """加载当前版本信息"""
        if self.version_file.exists():
            try:
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return VersionInfo(**data)
            except Exception as e:
                logger.error(f"加载版本文件失败: {e}")

        # 返回默认版本
        return VersionInfo(1, 0, 0)

    def _save_version(self):
        """保存版本信息"""
        try:
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.current_version), f, indent=2, ensure_ascii=False)
            logger.info(f"版本信息已保存: {self.current_version}")
        except Exception as e:
            logger.error(f"保存版本文件失败: {e}")

    def _load_changelog(self) -> List[ChangelogEntry]:
        """加载变更日志"""
        entries = []

        if self.changelog_file.exists():
            try:
                content = self.changelog_file.read_text(encoding='utf-8')
                # 这里简化处理，实际应该解析Markdown格式
                # 目前返回空列表，通过其他方法管理
            except Exception as e:
                logger.error(f"加载变更日志失败: {e}")

        return entries

    def get_current_version(self) -> VersionInfo:
        """获取当前版本"""
        return self.current_version

    def get_version_string(self) -> str:
        """获取当前版本字符串"""
        return str(self.current_version)

    def set_version(self, version: VersionInfo):
        """设置版本"""
        self.current_version = version
        self._save_version()
        logger.info(f"版本已更新为: {self.current_version}")

    def set_version_string(self, version_str: str):
        """通过版本字符串设置版本"""
        version = VersionInfo.from_string(version_str)
        self.set_version(version)

    def bump_version(self, bump_type: str = "patch") -> VersionInfo:
        """升级版本号

        Args:
            bump_type: 升级类型 ("major", "minor", "patch")

        Returns:
            VersionInfo: 新版本信息
        """
        if bump_type == "major":
            new_version = self.current_version.bump_major()
        elif bump_type == "minor":
            new_version = self.current_version.bump_minor()
        elif bump_type == "patch":
            new_version = self.current_version.bump_patch()
        else:
            raise ValueError(f"无效的升级类型: {bump_type}")

        self.set_version(new_version)
        return new_version

    def add_changelog_entry(self, version: Optional[str] = None, changes: Optional[List[Dict[str, str]]] = None):
        """添加变更日志条目

        Args:
            version: 版本号，如果为None则使用当前版本
            changes: 变更列表
        """
        if version is None:
            version = self.get_version_string()

        if changes is None:
            changes = []

        entry = ChangelogEntry(
            version=version,
            release_date=datetime.now().strftime("%Y-%m-%d"),
            changes=changes
        )

        self.changelog_entries.insert(0, entry)  # 添加到开头
        self._update_changelog_file()
        logger.info(f"变更日志条目已添加: {version}")

    def add_change(self, change_type: str, description: str, version: Optional[str] = None):
        """添加单个变更项

        Args:
            change_type: 变更类型 ("新增", "修复", "改进", "删除")
            description: 变更描述
            version: 版本号，如果为None则使用当前版本
        """
        target_version = version or self.get_version_string()

        # 查找是否已存在该版本的条目
        for entry in self.changelog_entries:
            if entry.version == target_version:
                entry.add_change(change_type, description)
                break
        else:
            # 创建新条目
            self.add_changelog_entry(target_version, [{"type": change_type, "description": description}])

        self._update_changelog_file()

    def _update_changelog_file(self):
        """更新变更日志文件"""
        try:
            content = "# 变更日志 (CHANGELOG)\n\n"

            for entry in self.changelog_entries:
                content += f"## [{entry.version}] - {entry.release_date}\n\n"

                # 按类型分组显示变更
                change_types = ["新增", "改进", "修复", "删除"]
                for change_type in change_types:
                    changes = entry.get_changes_by_type(change_type)
                    if changes:
                        content += f"### {change_type}\n\n"
                        for change in changes:
                            content += f"- {change}\n"
                        content += "\n"

                content += "---\n\n"

            self.changelog_file.write_text(content, encoding='utf-8')
            logger.info("变更日志文件已更新")

        except Exception as e:
            logger.error(f"更新变更日志文件失败: {e}")

    def get_changelog(self, limit: int = 10) -> List[ChangelogEntry]:
        """获取变更日志

        Args:
            limit: 返回的条目数量限制

        Returns:
            List[ChangelogEntry]: 变更日志条目列表
        """
        return self.changelog_entries[:limit]

    def get_version_info_dict(self) -> dict:
        """获取版本信息字典"""
        return {
            "version": str(self.current_version),
            "is_prerelease": self.current_version.is_prerelease(),
            "is_stable": self.current_version.is_stable(),
            "release_date": datetime.now().strftime("%Y-%m-%d"),
            "build_info": self._get_build_info()
        }

    def _get_build_info(self) -> dict:
        """获取构建信息"""
        return {
            "python_version": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}.{__import__('sys').version_info.micro}",
            "build_time": datetime.now().isoformat(),
            "platform": __import__('platform').platform()
        }


# 全局版本管理器实例
_version_manager: Optional[VersionManager] = None


def get_version_manager(project_root: Optional[Path] = None) -> VersionManager:
    """
    获取全局版本管理器实例

    Args:
        project_root: 项目根目录

    Returns:
        VersionManager: 版本管理器实例
    """
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionManager(project_root)
    return _version_manager


def get_current_version() -> str:
    """获取当前版本字符串"""
    return get_version_manager().get_version_string()


def bump_version(bump_type: str = "patch") -> str:
    """升级版本号"""
    new_version = get_version_manager().bump_version(bump_type)
    return str(new_version)