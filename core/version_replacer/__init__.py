#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinPE版本替换模块
提供WinPE版本替换的完整功能
"""

from .analyzer import ComponentAnalyzer
from .migrator import ComponentMigrator
from .config import VersionReplaceConfig, create_version_replace_config
from .enhanced_replacer import EnhancedVersionReplacer

__all__ = [
    'ComponentAnalyzer',
    'ComponentMigrator',
    'VersionReplaceConfig',
    'EnhancedVersionReplacer',
    'create_version_replace_config'
]