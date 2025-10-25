#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编码处理工具
提供安全的文本编码和解码功能
"""

import locale
from typing import Optional, Union


def safe_decode(data: bytes, fallback_encoding: str = 'gbk') -> str:
    """
    安全解码字节数据

    Args:
        data: 要解码的字节数据
        fallback_encoding: 备用编码，默认为gbk

    Returns:
        str: 解码后的字符串
    """
    if not data:
        return ""

    # 尝试UTF-8编码
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        pass

    # 尝试系统默认编码
    try:
        system_encoding = locale.getpreferredencoding() or 'utf-8'
        if system_encoding != 'utf-8':
            return data.decode(system_encoding, errors='replace')
    except:
        pass

    # 尝试备用编码
    try:
        return data.decode(fallback_encoding, errors='replace')
    except:
        pass

    # 最后尝试latin-1（不会失败）
    return data.decode('latin-1', errors='replace')


def safe_read_text_file(file_path, encoding: str = 'utf-8') -> str:
    """
    安全读取文本文件

    Args:
        file_path: 文件路径
        encoding: 首选编码

    Returns:
        str: 文件内容
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        # 如果UTF-8失败，尝试系统编码
        system_encoding = locale.getpreferredencoding() or 'utf-8'
        if system_encoding != encoding:
            try:
                with open(file_path, 'r', encoding=system_encoding, errors='replace') as f:
                    return f.read()
            except:
                pass

        # 最后尝试二进制模式然后解码
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
                return safe_decode(data)
        except:
            return f"无法读取文件: {file_path}"


def get_system_encoding() -> str:
    """
    获取系统编码

    Returns:
        str: 系统编码名称
    """
    return locale.getpreferredencoding() or 'utf-8'


def is_chinese_system() -> bool:
    """
    检查是否为中文系统

    Returns:
        bool: 是否为中文系统
    """
    system_encoding = get_system_encoding().lower()
    return 'gb' in system_encoding or 'cp936' in system_encoding or 'big5' in system_encoding