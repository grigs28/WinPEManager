#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志工具模块
提供统一的日志记录功能
"""

import logging
import os
from pathlib import Path
from datetime import datetime


def setup_logger(log_file_path: Path):
    """设置日志记录器

    Args:
        log_file_path: 日志文件路径
    """
    # 确保日志目录存在
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    # 创建日志记录器
    logger = logging.getLogger("WinPEManager")
    logger.setLevel(logging.DEBUG)

    # 清除现有的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 创建文件处理器
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 设置控制台输出编码
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

    # 创建格式化器
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # 设置格式化器
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)

    # 添加处理器到日志记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("日志系统初始化完成")
    return logger


def log_command(command: str, description: str = ""):
    """记录执行的命令

    Args:
        command: 执行的命令
        description: 命令描述
    """
    logger = logging.getLogger("WinPEManager")
    message = f"执行命令: {command}"
    if description:
        message += f" ({description})"
    logger.info(message)


def log_error(error: Exception, context: str = ""):
    """记录错误信息

    Args:
        error: 异常对象
        context: 错误上下文
    """
    logger = logging.getLogger("WinPEManager")
    message = f"发生错误: {str(error)}"
    if context:
        message += f" (上下文: {context})"
    logger.error(message, exc_info=True)