#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统日志处理器模块
提供Windows事件日志集成功能
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    import win32evtlog
    import win32evtlogutil
    import win32con
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class SystemLogHandler(logging.Handler):
    """Windows系统日志处理器"""
    
    def __init__(self, app_name: str = "WinPEManager", log_type: str = "Application"):
        """
        初始化系统日志处理器
        
        Args:
            app_name: 应用程序名称
            log_type: 日志类型 (Application, System, Security)
        """
        super().__init__()
        self.app_name = app_name
        self.log_type = log_type
        self.server = None  # 本地计算机
        self.enabled = WIN32_AVAILABLE
        
        if not self.enabled:
            print("警告: win32evtlog模块不可用，系统日志功能将被禁用")
            return
            
        try:
            # 确保应用程序已注册为事件源
            self._register_event_source()
        except Exception as e:
            print(f"注册事件源失败: {e}")
            self.enabled = False
    
    def _register_event_source(self):
        """注册事件源（如果需要管理员权限，则跳过）"""
        try:
            # 尝试注册事件源
            win32evtlogutil.AddSourceToRegistry(
                self.app_name, 
                self.log_type
            )
        except Exception as e:
            # 如果已经注册或权限不足，忽略错误
            if "already exists" not in str(e).lower():
                print(f"注册事件源时出现警告: {e}")
    
    def emit(self, record: logging.LogRecord):
        """发送日志记录到系统事件日志"""
        if not self.enabled:
            return
            
        try:
            # 转换日志级别到Windows事件类型
            event_type = self._get_event_type(record.levelno)
            
            # 格式化消息
            message = self.format(record)
            
            # 添加额外信息
            if hasattr(record, 'exc_info') and record.exc_info:
                message += f"\n异常信息: {self.formatException(record.exc_info)}"
            
            # 写入事件日志
            win32evtlogutil.ReportEvent(
                self.app_name,
                event_type,
                0,  # 事件类别
                0,  # 事件ID
                message=message
            )
            
        except Exception as e:
            # 如果系统日志写入失败，回退到文件日志
            print(f"写入系统日志失败: {e}")
            self._fallback_to_file(record)
    
    def _get_event_type(self, level: int) -> int:
        """将Python日志级别转换为Windows事件类型"""
        if level >= logging.ERROR:
            return win32evtlog.EVENTLOG_ERROR_TYPE
        elif level >= logging.WARNING:
            return win32evtlog.EVENTLOG_WARNING_TYPE
        else:
            return win32evtlog.EVENTLOG_INFORMATION_TYPE
    
    def _fallback_to_file(self, record: logging.LogRecord):
        """回退到文件日志"""
        try:
            fallback_file = Path.cwd() / "logs" / "system_log_fallback.log"
            fallback_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(fallback_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{timestamp} - {record.levelname} - {record.getMessage()}\n")
        except Exception:
            pass  # 最后的回退也失败了，静默忽略
    
    def close(self):
        """关闭处理器"""
        super().close()


class BuildLogHandler(logging.Handler):
    """构建日志专用处理器"""
    
    def __init__(self, build_log_path: Optional[Path] = None):
        """
        初始化构建日志处理器
        
        Args:
            build_log_path: 构建日志文件路径，如果为None则使用默认路径
        """
        super().__init__()
        
        if build_log_path is None:
            build_log_path = Path.cwd() / "logs" / "build_logs"
        
        self.build_log_path = build_log_path
        self.current_log_file = None
        self.build_session_id = self._generate_session_id()
        
        # 确保构建日志目录存在
        self.build_log_path.mkdir(parents=True, exist_ok=True)
    
    def _generate_session_id(self) -> str:
        """生成构建会话ID"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def start_build_session(self, build_info: Dict[str, Any]):
        """开始新的构建会话"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.build_session_id = timestamp
        
        # 创建构建日志文件
        log_filename = f"build_{timestamp}.log"
        self.current_log_file = self.build_log_path / log_filename
        
        # 写入构建会话头部信息
        with open(self.current_log_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"WinPE构建会话开始: {timestamp}\n")
            f.write(f"构建信息: {build_info}\n")
            f.write("=" * 80 + "\n\n")
    
    def end_build_session(self, success: bool, message: str = ""):
        """结束构建会话"""
        if self.current_log_file and self.current_log_file.exists():
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"构建会话结束: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"构建结果: {'成功' if success else '失败'}\n")
                if message:
                    f.write(f"结束信息: {message}\n")
                f.write("=" * 80 + "\n")
    
    def emit(self, record: logging.LogRecord):
        """发送日志记录到构建日志文件"""
        if not self.current_log_file:
            return
            
        try:
            # 确保日志文件存在
            if not self.current_log_file.exists():
                self.current_log_file.touch()
            
            # 格式化消息
            timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
            message = self.format(record)
            
            # 写入构建日志
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {record.levelname}: {message}\n")
                
                # 如果有异常信息，也写入
                if hasattr(record, 'exc_info') and record.exc_info:
                    f.write(f"异常详情: {self.formatException(record.exc_info)}\n")
        
        except Exception as e:
            # 如果构建日志写入失败，回退到标准日志
            print(f"写入构建日志失败: {e}")
    
    def get_current_log_path(self) -> Optional[Path]:
        """获取当前构建日志文件路径"""
        return self.current_log_file
    
    def close(self):
        """关闭处理器"""
        super().close()


class ContextFilter(logging.Filter):
    """上下文过滤器，用于添加额外的上下文信息"""
    
    def __init__(self, context: Dict[str, Any] = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record: logging.LogRecord):
        """为日志记录添加上下文信息"""
        # 添加上下文信息到记录
        for key, value in self.context.items():
            setattr(record, key, value)
        
        # 添加进程和线程信息
        record.process_name = getattr(record, 'processName', 'Unknown')
        record.thread_name = getattr(record, 'threadName', 'Unknown')
        
        return True
    
    def update_context(self, **kwargs):
        """更新上下文信息"""
        self.context.update(kwargs)


def create_system_logger(app_name: str = "WinPEManager") -> Optional[SystemLogHandler]:
    """创建系统日志处理器"""
    try:
        return SystemLogHandler(app_name)
    except Exception as e:
        print(f"创建系统日志处理器失败: {e}")
        return None


def create_build_logger(build_log_path: Optional[Path] = None) -> BuildLogHandler:
    """创建构建日志处理器"""
    return BuildLogHandler(build_log_path)