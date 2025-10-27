"""
文件操作工具函数
处理Windows文件系统特殊情况，如文件锁定等
"""

import os
import shutil
import time
import stat
from typing import Optional, Callable
from pathlib import Path


def force_remove_file(file_path: str, max_retries: int = 3, delay: float = 1.0) -> bool:
    """
    强制删除文件，处理Windows文件锁定问题

    Args:
        file_path: 要删除的文件路径
        max_retries: 最大重试次数
        delay: 重试间隔（秒）

    Returns:
        bool: 是否成功删除

    Raises:
        OSError: 删除失败时的最后一个异常
    """
    for attempt in range(max_retries):
        try:
            # 首先尝试常规删除
            os.remove(file_path)
            return True

        except PermissionError as e:
            if attempt == max_retries - 1:
                # 最后一次尝试，使用更激进的方法
                try:
                    # 修改文件权限，移除只读属性
                    os.chmod(file_path, stat.S_IWRITE)
                    # 再次尝试删除
                    os.remove(file_path)
                    return True
                except Exception:
                    raise e
            else:
                # 等待一段时间后重试
                time.sleep(delay)

        except OSError as e:
            # 其他类型的错误，直接抛出
            raise e

    return False


def force_remove_tree(directory_path: str, max_retries: int = 3, delay: float = 1.0,
                     progress_callback: Optional[Callable[[str], None]] = None) -> bool:
    """
    强制删除目录树，处理Windows文件锁定问题

    Args:
        directory_path: 要删除的目录路径
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
        progress_callback: 进度回调函数，接收当前处理的文件路径

    Returns:
        bool: 是否成功删除

    Raises:
        OSError: 删除失败时的最后一个异常
    """
    # 安全检查：防止删除重要目录
    if not _is_safe_to_delete(directory_path):
        raise ValueError(f"拒绝删除受保护的目录: {directory_path}")

    def on_error(func, path, exc_info):
        """shutil.rmtree的错误处理回调"""
        if isinstance(exc_info[1], PermissionError):
            # 尝试修改权限
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception:
                # 记录失败的文件，继续处理其他文件
                if progress_callback:
                    progress_callback(f"无法删除: {path}")
        else:
            # 其他错误，重新抛出
            raise exc_info[1]

    for attempt in range(max_retries):
        try:
            # 使用自定义错误处理函数
            shutil.rmtree(directory_path, onerror=on_error)
            return True

        except Exception as e:
            if attempt == max_retries - 1:
                # 最后一次尝试失败，使用逐个文件删除的方式
                try:
                    return _force_remove_tree_manual(directory_path, progress_callback)
                except Exception:
                    raise e
            else:
                # 等待一段时间后重试
                time.sleep(delay)
                if progress_callback:
                    progress_callback(f"重试删除 {directory_path} (尝试 {attempt + 2}/{max_retries})")

    return False


def _force_remove_tree_manual(directory_path: str, progress_callback: Optional[Callable[[str], None]] = None):
    """
    手动递归删除目录，逐个处理每个文件

    Args:
        directory_path: 要删除的目录路径
        progress_callback: 进度回调函数
    """
    # 多次尝试，处理顽固文件和目录
    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            # 先尝试使用shutil的完整删除
            import shutil
            shutil.rmtree(directory_path, ignore_errors=True)

            # 验证目录是否真的被删除了
            if not os.path.exists(directory_path):
                if progress_callback:
                    progress_callback(f"已成功删除目录: {directory_path}")
                return True

            # 如果还存在，继续下面的手动删除逻辑

        except Exception as e:
            if attempt == max_attempts - 1:
                if progress_callback:
                    progress_callback(f"shutil删除失败，尝试手动删除: {str(e)}")
            else:
                continue

    # 手动删除逻辑
    try:
        for root, dirs, files in os.walk(directory_path, topdown=False):
            # 先删除文件
            for name in files:
                file_path = os.path.join(root, name)
                try:
                    force_remove_file(file_path, max_retries=3, delay=0.5)
                    if progress_callback:
                        progress_callback(f"已删除: {file_path}")
                except Exception as e:
                    if progress_callback:
                        progress_callback(f"删除失败: {file_path} - {str(e)}")

            # 再删除空目录
            for name in dirs:
                dir_path = os.path.join(root, name)
                try:
                    # 使用更强的目录删除方法
                    import shutil
                    shutil.rmtree(dir_path, ignore_errors=True)
                    if not os.path.exists(dir_path):
                        if progress_callback:
                            progress_callback(f"已删除目录: {dir_path}")
                except Exception as e:
                    if progress_callback:
                        progress_callback(f"删除目录失败: {dir_path} - {str(e)}")

    except Exception as e:
        if progress_callback:
            progress_callback(f"手动删除过程出错: {str(e)}")

    # 最后多次尝试删除根目录
    for attempt in range(max_attempts):
        try:
            if os.path.exists(directory_path):
                # 尝试删除剩余的空目录
                import shutil
                shutil.rmtree(directory_path, ignore_errors=True)

                # 等待一下让文件系统同步
                import time
                time.sleep(0.5)

                # 再次检查
                if not os.path.exists(directory_path):
                    if progress_callback:
                        progress_callback(f"已删除根目录: {directory_path}")
                    return True

        except Exception as e:
            if progress_callback:
                progress_callback(f"删除根目录尝试 {attempt + 1}: {str(e)}")
            time.sleep(0.5)

    # 如果所有尝试都失败了
    if os.path.exists(directory_path):
        if progress_callback:
            progress_callback(f"警告: 无法完全删除目录 {directory_path}，但可能已删除大部分内容")
        # 不抛出异常，让调用者知道部分成功

    return not os.path.exists(directory_path)


def _is_safe_to_delete(directory_path: str) -> bool:
    """
    安全检查：防止删除重要目录

    Args:
        directory_path: 要检查的目录路径

    Returns:
        bool: 是否可以安全删除

    Raises:
        ValueError: 如果尝试删除受保护的目录
    """
    path = Path(directory_path).resolve()

    # 定义受保护的目录模式
    protected_patterns = [
        # 系统关键目录
        Path("C:\\Windows"),
        Path("C:\\Program Files"),
        Path("C:\\Program Files (x86)"),
        Path("C:\\ProgramData"),
        Path("C:\\Users"),
        Path("C:\\Documents and Settings"),
        # 当前工作目录本身
        Path.cwd(),
        # 项目目录关键文件夹
        Path(__file__).parent.parent,
        # 特殊项目目录
        "core", "ui", "utils", "config", "scripts", "drivers", "templates", "logs", "ico",
        # Git相关
        ".git", ".gitignore", ".gitattributes",
        # Python相关
        "venv", ".venv", "env", ".env", "__pycache__", "*.pyc",
    ]

    # 检查路径是否匹配受保护模式
    path_str = str(path).lower()
    for pattern in protected_patterns:
        if isinstance(pattern, Path):
            if path == pattern or path.is_relative_to(pattern):
                return False
        else:
            # 字符串模式匹配
            if pattern.lower() in path_str:
                return False

    # 定义受保护的目录类型
    workspace_names = ["WinPE_amd64", "WinPE_x86", "WinPE_arm64"]
    protected_project_folders = ["core", "ui", "utils", "config", "scripts", "drivers", "templates", "logs", "ico"]

    # 检查是否在项目目录下
    in_project_dir = any(parent.name == "WinPEManager" for parent in path.parents)

    if in_project_dir:
        # 在项目目录下，进行详细检查
        if path.name == "WinPEManager":
            # 项目根目录，绝对保护
            return False

        if path.name in protected_project_folders:
            # 关键项目文件夹，保护
            return False

        if path.name in workspace_names:
            # 工作空间根目录，不允许删除
            return False

        # WinPE_开头的构建目录允许删除
        # 例如：WinPE_20251027_172520 可以删除
        # WinPE_amd64（工作空间）不能删除

    # 确保不是根目录或系统盘根目录
    if path.is_root() or len(path.parts) <= 2:
        return False

    # 检查是否是特殊目录类型
    dangerous_names = [
        "system32", "syswow64", "drivers", "etc", "boot",
        "windows", "program files", "programdata", "users",
        "documents and settings", "recycler", "$recycle.bin",
        "system volume information"
    ]

    for part in path.parts:
        if part.lower() in dangerous_names:
            return False

    return True


def is_file_locked(file_path: str) -> bool:
    """
    检查文件是否被锁定

    Args:
        file_path: 要检查的文件路径

    Returns:
        bool: 文件是否被锁定
    """
    try:
        # 尝试以独占模式打开文件
        with open(file_path, 'r+b') as f:
            pass
        return False
    except (IOError, PermissionError):
        return True
    except Exception:
        # 文件不存在或其他错误
        return False


def wait_for_file_unlock(file_path: str, timeout: int = 30, check_interval: float = 1.0) -> bool:
    """
    等待文件解锁

    Args:
        file_path: 要等待的文件路径
        timeout: 超时时间（秒）
        check_interval: 检查间隔（秒）

    Returns:
        bool: 文件是否在超时前解锁
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        if not is_file_locked(file_path):
            return True
        time.sleep(check_interval)

    return False