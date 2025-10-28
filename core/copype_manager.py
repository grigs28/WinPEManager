#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一copype管理器
提供带进度条的copype命令执行功能
"""

import subprocess
import time
import threading
import shutil
from pathlib import Path
from typing import Tuple, Optional, Callable
from utils.logger import get_logger, log_command, log_build_step


class CopypeManager:
    """统一copype管理器"""

    def __init__(self, adk_manager=None, progress_callback=None):
        """
        初始化copype管理器

        Args:
            adk_manager: ADK管理器实例
            progress_callback: 进度回调函数 (percent: int, message: str)
        """
        self.adk_manager = adk_manager
        self.progress_callback = progress_callback
        self.logger = get_logger("CopypeManager")
        self._is_running = False

        # 设置命令输出回调到ADK管理器
        if adk_manager and hasattr(adk_manager, 'set_command_callback'):
            def command_callback(command: str, output: str):
                self.logger.info(f"[copype] {output}")
                print(f"{output} [copype]")
            adk_manager.set_command_callback(command_callback)

    def find_copype_path(self) -> Optional[Path]:
        """查找copype.cmd路径"""
        try:
            # 首先从ADK管理器获取
            if self.adk_manager:
                copype_path = self.adk_manager.get_copype_path()
                if copype_path and copype_path.exists():
                    self.logger.info(f"找到copype路径: {copype_path}")
                    return copype_path

            # 手动搜索常见路径
            possible_paths = [
                Path("C:/Program Files (x86)/Windows Kits/10/Assessment and Deployment Kit/Windows Preinstallation Environment/amd64/copype.cmd"),
                Path("C:/Program Files/Windows Kits/10/Assessment and Deployment Kit/Windows Preinstallation Environment/amd64/copype.cmd"),
                Path("C:/Windows/System32/copype.cmd")
            ]

            for path in possible_paths:
                if path.exists():
                    self.logger.info(f"手动找到copype路径: {path}")
                    return path

            # 尝试从系统PATH查找
            result = subprocess.run(
                ["where", "copype.cmd"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode == 0:
                path_str = result.stdout.strip().split('\n')[0]
                copype_path = Path(path_str)
                if copype_path.exists():
                    self.logger.info(f"从系统PATH找到copype: {copype_path}")
                    return copype_path

            self.logger.error("未找到copype.cmd文件")
            return None

        except Exception as e:
            self.logger.error(f"查找copype路径失败: {str(e)}")
            return None

    def run_copype(self, architecture: str, working_dir: Path, output_dir: str = "WinPE",
                   progress_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """
        运行copype命令（带进度条）

        Args:
            architecture: 架构 (amd64, x86, arm64)
            working_dir: 工作目录
            output_dir: 输出目录名
            progress_callback: 进度回调函数

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        copype_path = self.find_copype_path()
        if not copype_path:
            return False, "未找到copype.cmd文件"

        try:
            self.logger.info(f"开始执行copype命令: {architecture} -> {output_dir}")
            log_command(f"copype {architecture} {output_dir}")

            # 确保工作目录存在
            working_dir.mkdir(parents=True, exist_ok=True)
            output_path = working_dir / output_dir

            # 使用进度回调（如果提供）或默认回调
            callback = progress_callback or self.progress_callback

            # 创建copype命令
            cmd = [str(copype_path), architecture, output_dir]

            self.logger.info(f"执行copype命令: {' '.join(cmd)}")
            print(f"执行命令: {' '.join(cmd)} [copype]")

            # 启动进程
            process = subprocess.Popen(
                cmd,
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 监控输出和进度
            return self._monitor_copype_progress(process, working_dir, output_path, callback)

        except Exception as e:
            error_msg = f"执行copype命令失败: {str(e)}"
            self.logger.error(error_msg)
            print(f"{error_msg} [错误]")
            return False, error_msg

    def _monitor_copype_progress(self, process, working_dir: Path, output_path: Path,
                                progress_callback: Optional[Callable]) -> Tuple[bool, str]:
        """监控copype命令执行进度"""
        start_time = time.time()
        last_progress = 0
        estimated_total_files = 2000  # 估算的文件总数
        current_files = 0

        # 设置默认进度回调
        def default_progress_callback(percent: int, message: str):
            self.logger.info(f"copype进度 {percent}%: {message}")
            print(f"{percent}%: {message} [copype进度]")

        # 使用传入的回调或默认回调
        effective_callback = progress_callback or default_progress_callback

        # 实时监控输出
        output_lines = []
        stage = "initializing"
        last_eta_update = 0

        try:
            while process.poll() is None:
                # 监控文件创建
                if output_path.exists():
                    current_files = self._count_files(output_path)

                    # 更新进度（基于文件数量）
                    if current_files > last_progress:
                        progress = min(current_files * 100 // estimated_total_files, 95)
                        last_progress = progress
                        effective_callback(progress, f"已复制 {current_files} 个文件")

                # 监控标准输出
                line = process.stdout.readline()
                if line:
                    line = line.strip()
                    if line:
                        output_lines.append(line)

                        # 发送命令输出
                        if self.adk_manager and hasattr(self.adk_manager, '_emit_command_output'):
                            self.adk_manager._emit_command_output("copype输出", line)
                        print(f"{line} [copype]")

                        # 解析进度阶段
                        self._parse_copype_stage(line, effective_callback, start_time)

                        # 更新ETA（每5秒更新一次）
                        elapsed = time.time() - start_time
                        if elapsed - last_eta_update > 5 and last_progress > 0:
                            eta_seconds = (elapsed * 100 // last_progress) - elapsed
                            effective_callback(last_progress, f"预计剩余时间: {eta_seconds:.0f}秒")
                            last_eta_update = elapsed

                time.sleep(0.1)

            # 等待进程完成
            return_code = process.wait()
            success = return_code == 0

            # 完成进度
            effective_callback(100, "copype操作完成")

            # 统计最终结果
            final_files = self._count_files(output_path) if output_path.exists() else 0
            elapsed_time = time.time() - start_time

            if success:
                success_msg = f"copype执行成功，创建了 {final_files} 个文件，耗时 {elapsed_time:.2f}秒"
                self.logger.info(success_msg)
                print(f"{success_msg} [成功]")
                return True, success_msg
            else:
                # 输出错误信息
                stderr = process.stderr.read()
                error_msg = f"copype执行失败，返回码: {return_code}"
                if stderr:
                    error_msg += f"\n错误信息: {stderr}"

                self.logger.error(error_msg)
                print(f"{error_msg} [失败]")
                return False, error_msg

        except Exception as e:
            error_msg = f"监控copype进度时发生错误: {str(e)}"
            self.logger.error(error_msg)
            print(f"{error_msg} [异常]")
            return False, error_msg

    def _parse_copype_stage(self, line: str, callback: Callable, start_time: float):
        """解析copype执行阶段"""
        line_lower = line.lower()
        elapsed = time.time() - start_time

        # 识别不同的执行阶段
        if "initializing" in line_lower or "初始化" in line_lower:
            callback(10, "初始化WinPE环境")
        elif "copying" in line_lower or "复制" in line_lower:
            callback(30, "正在复制WinPE文件")
        elif "creating" in line_lower or "创建" in line_lower:
            callback(50, "正在创建WinPE结构")
        elif "generating" in line_lower or "生成" in line_lower:
            callback(70, "正在生成WinPE镜像")
        elif "wim" in line_lower:
            callback(90, "正在处理WIM文件")
        elif "success" in line_lower or "成功" in line_lower:
            callback(95, "即将完成")

    def _count_files(self, directory: Path) -> int:
        """递归统计文件数量"""
        try:
            count = 0
            for item in directory.rglob("*"):
                if item.is_file():
                    count += 1
            return count
        except Exception:
            return 0

    def cleanup_working_directory(self, working_dir: Path) -> bool:
        """清理工作目录"""
        try:
            if working_dir.exists():
                shutil.rmtree(working_dir)
                self.logger.info(f"已清理工作目录: {working_dir}")
                print(f"已清理工作目录: {working_dir} [清理]")
            return True
        except Exception as e:
            error_msg = f"清理工作目录失败: {str(e)}"
            self.logger.error(error_msg)
            print(f"{error_msg} [错误]")
            return False

    def create_winpe_workspace(self, architecture: str, workspace_dir: Path,
                             progress_callback: Optional[Callable] = None) -> Tuple[bool, str, Path]:
        """
        创建WinPE工作空间

        Args:
            architecture: 架构 (amd64, x86, arm64)
            workspace_dir: 工作空间目录
            progress_callback: 进度回调函数

        Returns:
            Tuple[bool, str, Path]: (成功状态, 消息, WinPE目录路径)
        """
        winpe_dir = workspace_dir / "WinPE"

        try:
            self.logger.info(f"开始创建WinPE工作空间: {architecture}")

            # 运行copype
            success, message = self.run_copype(
                architecture,
                workspace_dir,
                "WinPE",
                progress_callback
            )

            if success:
                self.logger.info(f"WinPE工作空间创建成功: {winpe_dir}")
                return True, message, winpe_dir
            else:
                self.logger.error(f"WinPE工作空间创建失败: {message}")
                return False, message, winpe_dir

        except Exception as e:
            error_msg = f"创建WinPE工作空间时发生错误: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, winpe_dir

    def create_winpe_with_progress(self, architecture: str, source_dir: str,
                                 dest_dir: str, progress_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """
        创建WinPE环境（带进度条）

        Args:
            architecture: 架构 (amd64, x86, arm64)
            source_dir: 源目录
            dest_dir: 目标目录
            progress_callback: 进度回调函数

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            source_path = Path(source_dir)
            dest_path = Path(dest_dir)

            # 确保源目录存在
            if not source_path.exists():
                return False, f"源目录不存在: {source_dir}"

            # 创建目标目录
            dest_path.mkdir(parents=True, exist_ok=True)

            # 设置进度回调
            callback = progress_callback or self.progress_callback

            callback(5, f"开始准备WinPE环境...")

            # 调用ADK管理器的copype功能（如果可用）
            if self.adk_manager and hasattr(self.adk_manager, 'create_winpe_workspace'):
                success, message = self.adk_manager.create_winpe_workspace(
                    architecture, dest_path, callback
                )

                if success:
                    callback(100, "WinPE环境创建完成")
                    return True, message
                else:
                    return False, message
            else:
                # 使用内置的copype管理器
                success, message = self.create_winpe_workspace(architecture, dest_path, callback)

                if success:
                    callback(100, "WinPE环境创建完成")
                    return True, message
                else:
                    return False, message

        except Exception as e:
            error_msg = f"创建WinPE环境时发生错误: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def validate_winpe_environment(self, winpe_dir: Path) -> Tuple[bool, str]:
        """验证WinPE环境是否完整"""
        try:
            if not winpe_dir.exists():
                return False, f"WinPE目录不存在: {winpe_dir}"

            # 检查关键文件
            required_files = [
                "boot.wim",
                "boot.sdi",
                "winpe.wim"
            ]

            missing_files = []
            for file_name in required_files:
                file_path = winpe_dir / file_name
                if not file_path.exists():
                    missing_files.append(file_name)

            if missing_files:
                return False, f"缺少必要文件: {', '.join(missing_files)}"

            # 统计文件数量
            file_count = self._count_files(winpe_dir)

            success_msg = f"WinPE环境验证通过，包含 {file_count} 个文件"
            self.logger.info(success_msg)
            print(f"{success_msg} [验证]")

            return True, success_msg

        except Exception as e:
            error_msg = f"验证WinPE环境时发生错误: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg


# 创建全局copype管理器实例
_global_copype_manager = None

def get_copype_manager(adk_manager=None, progress_callback=None) -> CopypeManager:
    """获取全局copype管理器实例"""
    global _global_copype_manager
    if _global_copype_manager is None:
        _global_copype_manager = CopypeManager(adk_manager, progress_callback)
    return _global_copype_manager

def reset_copype_manager():
    """重置全局copype管理器实例"""
    global _global_copype_manager
    _global_copype_manager = None