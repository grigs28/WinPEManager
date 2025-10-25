#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
变更日志管理模块
专门负责管理和生成变更日志
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re
import logging

logger = logging.getLogger("WinPEManager")


class ChangelogManager:
    """变更日志管理器"""

    def __init__(self, changelog_path: Optional[Path] = None):
        """
        初始化变更日志管理器

        Args:
            changelog_path: 变更日志文件路径
        """
        if changelog_path is None:
            from pathlib import Path
            changelog_path = Path(__file__).parent.parent / "docs" / "CHANGELOG.md"

        self.changelog_path = Path(changelog_path)
        self._ensure_directory()

    def _ensure_directory(self):
        """确保变更日志目录存在"""
        self.changelog_path.parent.mkdir(parents=True, exist_ok=True)

    def create_changelog(self) -> bool:
        """
        创建初始变更日志文件

        Returns:
            bool: 是否成功创建
        """
        if self.changelog_path.exists():
            logger.info("变更日志文件已存在")
            return True

        try:
            initial_content = self._get_initial_template()
            self.changelog_path.write_text(initial_content, encoding='utf-8')
            logger.info(f"变更日志文件已创建: {self.changelog_path}")
            return True
        except Exception as e:
            logger.error(f"创建变更日志文件失败: {e}")
            return False

    def _get_initial_template(self) -> str:
        """获取初始变更日志模板"""
        return """# 变更日志 (CHANGELOG)

本文档记录了WinPE制作管理器的所有重要变更。

版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

---

## [未发布]

### 新增
- 初始变更日志

### 改进
- 性能优化

### 修复
- 修复已知问题

---

## [1.0.0] - 2024-01-01

### 新增
- WinPE制作管理器初始版本
- 基础WinPE构建功能
- ADK环境检测和管理
- 图形用户界面

### 改进
- 用户友好的界面设计
- 详细的构建日志

### 修复
- 环境检测问题
- 构建流程优化

---

## 版本说明

### 版本号格式
- **主版本号**: 不兼容的API修改
- **次版本号**: 向下兼容的功能性新增
- **修订号**: 向下兼容的问题修正

### 变更类型
- **新增**: 全新功能
- **改进**: 现有功能的优化
- **修复**: 错误修复
- **删除**: 功能移除
- **安全**: 安全相关的修复

### 发布周期
- **主版本**: 根据需要发布
- **次版本**: 每月发布
- **修订版本**: 根据需要发布

---

*最后更新: {current_date}*
""".format(current_date=datetime.now().strftime("%Y-%m-%d"))

    def add_release(self, version: str, date: Optional[str] = None,
                   changes: Optional[List[Dict[str, str]]] = None) -> bool:
        """
        添加新版本发布信息

        Args:
            version: 版本号
            date: 发布日期，如果为None则使用当前日期
            changes: 变更列表 [{"type": "类型", "description": "描述"}]

        Returns:
            bool: 是否成功添加
        """
        if not changes:
            changes = []

        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        try:
            content = self._read_changelog()
            new_content = self._insert_release_section(content, version, date, changes)
            self._write_changelog(new_content)

            logger.info(f"版本 {version} 已添加到变更日志")
            return True

        except Exception as e:
            logger.error(f"添加版本信息失败: {e}")
            return False

    def _read_changelog(self) -> str:
        """读取变更日志内容"""
        if not self.changelog_path.exists():
            return self._get_initial_template()
        return self.changelog_path.read_text(encoding='utf-8')

    def _write_changelog(self, content: str):
        """写入变更日志内容"""
        self.changelog_path.write_text(content, encoding='utf-8')

    def _insert_release_section(self, content: str, version: str, date: str,
                               changes: List[Dict[str, str]]) -> str:
        """插入新版本信息"""
        # 找到"未发布"部分或在开头插入
        unreleased_pattern = r'^## \[未发布\].*?(?=^## |\Z)'

        new_section = self._format_release_section(version, date, changes)

        if re.search(unreleased_pattern, content, re.MULTILINE | re.DOTALL):
            # 在"未发布"部分之后插入
            return re.sub(
                unreleased_pattern,
                lambda m: m.group(0) + '\n\n' + new_section,
                content,
                flags=re.MULTILINE | re.DOTALL
            )
        else:
            # 在第一个版本之前插入
            first_version_pattern = r'^(## \[.*?\])'
            return re.sub(
                first_version_pattern,
                new_section + '\n\n' + r'\1',
                content,
                flags=re.MULTILINE
            )

    def _format_release_section(self, version: str, date: str,
                               changes: List[Dict[str, str]]) -> str:
        """格式化版本发布信息"""
        lines = [f"## [{version}] - {date}", ""]

        # 按类型分组
        change_types = ["新增", "改进", "修复", "删除", "安全"]
        grouped_changes = {}

        for change in changes:
            change_type = change.get("type", "修复")
            if change_type not in grouped_changes:
                grouped_changes[change_type] = []
            grouped_changes[change_type].append(change.get("description", ""))

        # 生成内容
        for change_type in change_types:
            if change_type in grouped_changes and grouped_changes[change_type]:
                lines.append(f"### {change_type}")
                lines.append("")
                for description in grouped_changes[change_type]:
                    lines.append(f"- {description}")
                lines.append("")

        lines.append("---")
        return "\n".join(lines)

    def add_unreleased_change(self, change_type: str, description: str) -> bool:
        """
        添加未发布的变更

        Args:
            change_type: 变更类型
            description: 变更描述

        Returns:
            bool: 是否成功添加
        """
        try:
            content = self._read_changelog()
            new_content = self._add_to_unreleased(content, change_type, description)
            self._write_changelog(new_content)
            logger.info(f"未发布变更已添加: [{change_type}] {description}")
            return True
        except Exception as e:
            logger.error(f"添加未发布变更失败: {e}")
            return False

    def _add_to_unreleased(self, content: str, change_type: str, description: str) -> str:
        """添加到未发布部分"""
        # 查找未发布部分
        unreleased_pattern = r'(## \[未发布\].*?### ' + re.escape(change_type) + r'.*?\n)'

        def add_change_to_type(match):
            section = match.group(1)
            # 在该类型的最后添加新变更
            return section + f"- {description}\n"

        if re.search(unreleased_pattern, content, re.MULTILINE | re.DOTALL):
            # 如果找到了该类型，添加到后面
            return re.sub(
                unreleased_pattern,
                add_change_to_type,
                content,
                flags=re.MULTILINE | re.DOTALL
            )
        else:
            # 如果没有找到该类型，在未发布部分添加新的类型
            return self._add_new_type_to_unreleased(content, change_type, description)

    def _add_new_type_to_unreleased(self, content: str, change_type: str, description: str) -> str:
        """在未发布部分添加新的变更类型"""
        unreleased_pattern = r'(## \[未发布\].*?)(?=\n## |\Z)'

        def insert_new_type(match):
            section = match.group(1)
            new_type = f"\n### {change_type}\n\n- {description}\n"
            return section + new_type

        return re.sub(
            unreleased_pattern,
            insert_new_type,
            content,
            flags=re.MULTILINE | re.DOTALL
        )

    def get_releases(self, limit: int = 10) -> List[Dict[str, any]]:
        """
        获取最近的发布版本

        Args:
            limit: 返回的版本数量

        Returns:
            List[Dict]: 版本信息列表
        """
        content = self._read_changelog()
        releases = []

        # 解析版本信息
        version_pattern = r'^## \[(.*?)\] - (\d{4}-\d{2}-\d{2})'

        for match in re.finditer(version_pattern, content, re.MULTILINE):
            version, date = match.groups()
            if version != "未发布":
                releases.append({
                    "version": version,
                    "date": date
                })

                if len(releases) >= limit:
                    break

        return releases

    def get_unreleased_changes(self) -> Dict[str, List[str]]:
        """
        获取未发布的变更

        Returns:
            Dict[str, List[str]]: 按类型分组的变更列表
        """
        content = self._read_changelog()
        changes = {}

        # 查找未发布部分
        unreleased_pattern = r'## \[未发布\].*?(?=^## |\Z)'
        match = re.search(unreleased_pattern, content, re.MULTILINE | re.DOTALL)

        if match:
            unreleased_content = match.group(0)
            # 解析各种类型的变更
            type_pattern = r'### (.*?)\n\n((?:- .*\n)*)'

            for type_match in re.finditer(type_pattern, unreleased_content):
                change_type = type_match.group(1)
                change_content = type_match.group(2)

                # 提取变更描述
                descriptions = [
                    line[2:].strip()  # 移除 "- " 前缀
                    for line in change_content.strip().split('\n')
                    if line.startswith('- ')
                ]

                if descriptions:
                    changes[change_type] = descriptions

        return changes

    def release_current_version(self, version: str) -> bool:
        """
        发布当前版本（将未发布的变更移动到指定版本）

        Args:
            version: 版本号

        Returns:
            bool: 是否成功发布
        """
        try:
            content = self._read_changelog()
            unreleased_changes = self.get_unreleased_changes()

            if not unreleased_changes:
                logger.warning("没有未发布的变更")
                return False

            # 移除未发布部分
            content = re.sub(
                r'## \[未发布\].*?(?=\n## |\Z)',
                '',
                content,
                flags=re.MULTILINE | re.DOTALL
            )

            # 准备变更列表
            changes = []
            for change_type, descriptions in unreleased_changes.items():
                for description in descriptions:
                    changes.append({
                        "type": change_type,
                        "description": description
                    })

            # 添加新版本信息
            new_content = self._insert_release_section(
                content, version, datetime.now().strftime("%Y-%m-%d"), changes
            )

            # 添加新的未发布部分
            new_content = re.sub(
                r'(^# 变更日志.*?\n)',
                r'\1\n## [未发布]\n\n',
                new_content,
                flags=re.MULTILINE
            )

            self._write_changelog(new_content)
            logger.info(f"版本 {version} 已发布")
            return True

        except Exception as e:
            logger.error(f"发布版本失败: {e}")
            return False


# 全局变更日志管理器实例
_changelog_manager: Optional[ChangelogManager] = None


def get_changelog_manager(changelog_path: Optional[Path] = None) -> ChangelogManager:
    """
    获取全局变更日志管理器实例

    Args:
        changelog_path: 变更日志文件路径

    Returns:
        ChangelogManager: 变更日志管理器实例
    """
    global _changelog_manager
    if _changelog_manager is None:
        _changelog_manager = ChangelogManager(changelog_path)
    return _changelog_manager