#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志工具模块
提供统一的日志记录功能，支持系统日志和构建日志
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from logging.handlers import RotatingFileHandler

# 导入增强的日志处理器
try:
    from utils.system_logger import (
        SystemLogHandler,
        BuildLogHandler,
        ContextFilter,
        create_system_logger,
        create_build_logger
    )
    ENHANCED_LOGGING_AVAILABLE = True
except ImportError:
    ENHANCED_LOGGING_AVAILABLE = False


class EnhancedLogger:
    """增强的日志管理器"""
    
    def __init__(self, name: str = "WinPEManager"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.system_handler = None
        self.build_handler = None
        self.context_filter = None
        self._initialized = False
    
    def setup_enhanced_logging(
        self,
        log_file_path: Path,
        enable_system_log: bool = True,
        enable_build_log: bool = True,
        build_log_path: Optional[Path] = None,
        app_name: str = "WinPEManager",
        context: Dict[str, Any] = None
    ):
        """设置增强的日志系统
        
        Args:
            log_file_path: 主日志文件路径
            enable_system_log: 是否启用系统日志
            enable_build_log: 是否启用构建日志
            build_log_path: 构建日志路径
            app_name: 应用程序名称（用于系统日志）
            context: 上下文信息
        """
        if self._initialized:
            return self.logger
            
        # 确保日志目录存在
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 设置日志级别
        self.logger.setLevel(logging.DEBUG)
        
        # 清除现有处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 创建上下文过滤器
        if ENHANCED_LOGGING_AVAILABLE:
            self.context_filter = ContextFilter(context or {})
            self.logger.addFilter(self.context_filter)
        
        # 1. 创建文件处理器 - 统一输出到logs/run.log，限制2M
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        run_log_path = logs_dir / "run.log"
        file_handler = RotatingFileHandler(
            run_log_path, 
            maxBytes=2*1024*1024,  # 2MB
            backupCount=3, 
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)  # 只记录INFO及以上级别，减少冗余
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # 2. 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置控制台输出编码
        import sys
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
            except:
                pass
        
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 3. 创建系统日志处理器
        if enable_system_log and ENHANCED_LOGGING_AVAILABLE:
            try:
                self.system_handler = create_system_logger(app_name)
                if self.system_handler and self.system_handler.enabled:
                    self.system_handler.setLevel(logging.WARNING)  # 系统日志只记录警告及以上级别
                    system_formatter = logging.Formatter(
                        '%(name)s - %(levelname)s - %(message)s'
                    )
                    self.system_handler.setFormatter(system_formatter)
                    self.logger.addHandler(self.system_handler)
                    self.logger.info("系统日志处理器已启用")
                else:
                    self.logger.warning("系统日志处理器创建失败或不可用")
            except Exception as e:
                self.logger.warning(f"启用系统日志失败: {e}")
        
        # 4. 构建日志统一到主日志，不创建独立文件
        if enable_build_log and ENHANCED_LOGGING_AVAILABLE:
            self.logger.info("构建日志已统一到主日志文件")
        
        self._initialized = True
        self.logger.info("增强日志系统初始化完成")
        return self.logger
    
    def start_build_session(self, build_info: Dict[str, Any]):
        """开始构建会话"""
        if self.build_handler:
            self.build_handler.start_build_session(build_info)
            self.logger.info(f"构建会话开始: {build_info}")
    
    def end_build_session(self, success: bool, message: str = ""):
        """结束构建会话"""
        if self.build_handler:
            self.build_handler.end_build_session(success, message)
            status = "成功" if success else "失败"
            self.logger.info(f"构建会话结束: {status} - {message}")
    
    def get_build_log_path(self) -> Optional[Path]:
        """获取当前构建日志路径"""
        if self.build_handler:
            return self.build_handler.get_current_log_path()
        return None
    
    def update_context(self, **kwargs):
        """更新上下文信息"""
        if self.context_filter:
            self.context_filter.update_context(**kwargs)
    
    def get_logger(self) -> logging.Logger:
        """获取日志记录器"""
        return self.logger


# 全局增强日志管理器实例
_enhanced_logger = None


def setup_logger(
    log_file_path: Path,
    enable_system_log: bool = True,
    enable_build_log: bool = True,
    build_log_path: Optional[Path] = None,
    app_name: str = "WinPEManager",
    context: Dict[str, Any] = None
) -> logging.Logger:
    """设置日志记录器（兼容原有接口，增加增强功能）
    
    Args:
        log_file_path: 日志文件路径
        enable_system_log: 是否启用系统日志
        enable_build_log: 是否启用构建日志
        build_log_path: 构建日志路径
        app_name: 应用程序名称
        context: 上下文信息
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    global _enhanced_logger
    
    if ENHANCED_LOGGING_AVAILABLE:
        _enhanced_logger = EnhancedLogger()
        return _enhanced_logger.setup_enhanced_logging(
            log_file_path=log_file_path,
            enable_system_log=enable_system_log,
            enable_build_log=enable_build_log,
            build_log_path=build_log_path,
            app_name=app_name,
            context=context
        )
    else:
        # 回退到原始实现
        return _setup_legacy_logger(log_file_path)


def _setup_legacy_logger(log_file_path: Path) -> logging.Logger:
    """原始日志设置实现（向后兼容）"""
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

    logger.info("日志系统初始化完成（兼容模式）")
    return logger


def start_build_session(build_info: Dict[str, Any]):
    """开始构建会话"""
    global _enhanced_logger
    if _enhanced_logger:
        _enhanced_logger.start_build_session(build_info)


def end_build_session(success: bool, message: str = ""):
    """结束构建会话"""
    global _enhanced_logger
    if _enhanced_logger:
        _enhanced_logger.end_build_session(success, message)


def get_build_log_path() -> Optional[Path]:
    """获取当前构建日志路径"""
    global _enhanced_logger
    if _enhanced_logger:
        return _enhanced_logger.get_build_log_path()
    return None


def update_log_context(**kwargs):
    """更新日志上下文"""
    global _enhanced_logger
    if _enhanced_logger:
        _enhanced_logger.update_context(**kwargs)


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


def log_build_step(step_name: str, details: str = "", level: str = "info"):
    """记录构建步骤
    
    Args:
        step_name: 步骤名称
        details: 详细信息
        level: 日志级别 (info, warning, error)
    """
    logger = logging.getLogger("WinPEManager")
    message = f"构建步骤: {step_name}"
    if details:
        message += f" - {details}"
    
    if level.lower() == "error":
        logger.error(message)
    elif level.lower() == "warning":
        logger.warning(message)
    else:
        logger.info(message)


def log_system_event(event_type: str, message: str, level: str = "info"):
    """记录系统事件（会同时写入系统日志）
    
    Args:
        event_type: 事件类型
        message: 事件消息
        level: 日志级别
    """
    logger = logging.getLogger("WinPEManager")
    full_message = f"[{event_type}] {message}"
    
    if level.lower() == "error":
        logger.error(full_message)
    elif level.lower() == "warning":
        logger.warning(full_message)
    else:
        logger.info(full_message)


def get_logger(name: str = "WinPEManager") -> logging.Logger:
    """获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 日志记录器实例
    """
    return logging.getLogger(name)
