#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows ADK管理模块
负责检测和管理Windows ADK环境
"""

import os
import subprocess
import winreg
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger("WinPEManager")


class ADKManager:
    """Windows ADK管理器类"""

    # 注册表路径
    ADK_REGISTRY_PATHS = [
        r"SOFTWARE\Microsoft\Windows Kits\Installed Roots",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows Kits\Installed Roots"
    ]

    # 常见的ADK安装路径
    COMMON_ADK_PATHS = [
        r"C:\Program Files (x86)\Windows Kits\10",
        r"C:\Program Files\Windows Kits\10",
        r"C:\Program Files (x86)\Windows Kits\11",
        r"C:\Program Files\Windows Kits\11"
    ]

    def __init__(self):
        self.adk_path = None
        self.winpe_path = None
        self.adk_version = None
        self.winpe_versions = {}

    def detect_adk(self) -> Tuple[bool, str]:
        """检测Windows ADK安装情况

        Returns:
            Tuple[bool, str]: (是否安装, 版本信息或错误信息)
        """
        try:
            # 从注册表查找ADK安装路径
            adk_path = self._find_adk_from_registry()
            if adk_path and adk_path.exists():
                self.adk_path = adk_path
                self.adk_version = self._get_adk_version(adk_path)
                logger.info(f"找到Windows ADK: {adk_path} (版本: {self.adk_version})")
                return True, f"Windows ADK {self.adk_version} 已安装"

            # 搜索常见安装路径
            adk_path = self._search_common_paths()
            if adk_path and adk_path.exists():
                self.adk_path = adk_path
                self.adk_version = self._get_adk_version(adk_path)
                logger.info(f"找到Windows ADK: {adk_path} (版本: {self.adk_version})")
                return True, f"Windows ADK {self.adk_version} 已安装"

            return False, "未找到Windows ADK安装"

        except Exception as e:
            logger.error(f"检测ADK失败: {str(e)}")
            return False, f"检测ADK时发生错误: {str(e)}"

    def detect_winpe_addon(self) -> Tuple[bool, str]:
        """检测WinPE加载项安装情况

        Returns:
            Tuple[bool, str]: (是否安装, 版本信息或错误信息)
        """
        if not self.adk_path:
            return False, "请先安装Windows ADK"

        try:
            # 查找WinPE相关路径
            winpe_path = self.adk_path / "Assessment and Deployment Kit" / "Windows Preinstallation Environment"
            if winpe_path.exists():
                self.winpe_path = winpe_path
                # 检测不同架构的WinPE
                for arch in ["x86", "amd64", "arm64"]:
                    arch_path = winpe_path / arch
                    if arch_path.exists():
                        self.winpe_versions[arch] = self._get_winpe_version(arch_path)

                logger.info(f"找到WinPE加载项: {winpe_path}")
                return True, f"WinPE加载项已安装，支持架构: {list(self.winpe_versions.keys())}"
            else:
                return False, "WinPE加载项未安装"

        except Exception as e:
            logger.error(f"检测WinPE加载项失败: {str(e)}")
            return False, f"检测WinPE加载项时发生错误: {str(e)}"

    def _find_adk_from_registry(self) -> Optional[Path]:
        """从注册表查找ADK安装路径"""
        try:
            for reg_path in self.ADK_REGISTRY_PATHS:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                        kits_root = winreg.QueryValueEx(key, "KitsRoot10")[0]
                        return Path(kits_root)
                except (FileNotFoundError, OSError):
                    continue
        except Exception as e:
            logger.error(f"从注册表读取ADK路径失败: {str(e)}")
        return None

    def _search_common_paths(self) -> Optional[Path]:
        """搜索常见的ADK安装路径"""
        for path_str in self.COMMON_ADK_PATHS:
            path = Path(path_str)
            if path.exists() and (path / "Assessment and Deployment Kit").exists():
                return path
        return None

    def _get_adk_version(self, adk_path: Path) -> str:
        """获取ADK版本信息"""
        try:
            # 尝试从版本文件读取
            version_file = adk_path / "SDKManifest.xml"
            if version_file.exists():
                with open(version_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 简单的版本号提取
                    if "Version" in content:
                        import re
                        version_match = re.search(r'Version="([^"]+)"', content)
                        if version_match:
                            return version_match.group(1)

            # 从目录名推断版本
            if "11" in str(adk_path):
                return "11"
            elif "10" in str(adk_path):
                return "10"
            else:
                return "未知"
        except Exception:
            return "未知"

    def _get_winpe_version(self, winpe_path: Path) -> str:
        """获取WinPE版本信息"""
        try:
            # 检查是否有winpe.wim文件
            wim_files = list(winpe_path.glob("**/winpe.wim"))
            if wim_files:
                return "已安装"
            else:
                return "未完整安装"
        except Exception:
            return "未知"

    def get_available_architectures(self) -> List[str]:
        """获取可用的WinPE架构"""
        if not self.winpe_path:
            return []

        architectures = []
        for arch in ["x86", "amd64", "arm64"]:
            arch_path = self.winpe_path / arch
            if arch_path.exists():
                # 检查是否有必要的文件
                winpe_wim = arch_path / "en-us" / "winpe.wim"
                if winpe_wim.exists() or (arch_path / "winpe.wim").exists():
                    architectures.append(arch)

        return architectures

    def get_deployment_tools_path(self) -> Optional[Path]:
        """获取部署工具路径"""
        if not self.adk_path:
            return None

        deploy_tools_path = self.adk_path / "Assessment and Deployment Kit" / "Deployment Tools"
        if deploy_tools_path.exists():
            return deploy_tools_path
        return None

    def get_dandisetenv_path(self) -> Optional[Path]:
        """获取DandISetEnv.bat文件路径"""
        deploy_tools_path = self.get_deployment_tools_path()
        if not deploy_tools_path:
            return None

        dandisetenv_path = deploy_tools_path / "DandISetEnv.bat"
        if dandisetenv_path.exists():
            return dandisetenv_path
        return None

    def check_current_environment(self) -> bool:
        """检查当前环境是否已经正确设置

        Returns:
            bool: 环境是否正确设置
        """
        try:
            # 检查PATH中是否包含DISM工具路径
            dism_path = self.get_dism_path()
            if not dism_path:
                return False

            # 检查DISM工具是否可以直接访问
            import shutil
            system_dism = shutil.which("dism.exe")
            if system_dism:
                # 比较路径是否一致
                try:
                    return str(dism_path).lower() == str(system_dism).lower()
                except:
                    pass

            # 检查PATH环境变量是否包含ADK路径
            path_env = os.environ.get('PATH', '').lower()
            adk_path_str = str(self.adk_path).lower()
            deploy_tools_str = str(self.get_deployment_tools_path()).lower() if self.get_deployment_tools_path() else ""

            return adk_path_str in path_env or deploy_tools_str in path_env

        except Exception as e:
            logger.error(f"检查当前环境失败: {str(e)}")
            return False

    def load_adk_environment(self) -> Tuple[bool, str]:
        """加载ADK环境变量

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        # 首先检查当前环境是否已经正确设置
        if self.check_current_environment():
            logger.info("当前环境已正确设置，无需重复加载")
            return True, "当前环境已正确设置"

        dandisetenv_path = self.get_dandisetenv_path()
        if not dandisetenv_path:
            return False, "找不到DandISetEnv.bat文件"

        try:
            import tempfile
            import subprocess

            # 创建临时批处理文件来捕获环境变量
            with tempfile.NamedTemporaryFile(mode='w', suffix='.bat', delete=False) as temp_bat:
                temp_bat.write(f'@echo off\n')
                temp_bat.write(f'call "{dandisetenv_path}"\n')
                temp_bat.write(f'set > "{temp_bat.name}.env"\n')
                temp_bat_path = temp_bat.name

            env_file_path = temp_bat_path + ".env"

            try:
                # 执行批处理文件
                result = subprocess.run(
                    [temp_bat_path],
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    capture_output=True
                )

                # 读取环境变量
                if os.path.exists(env_file_path):
                    with open(env_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        env_lines = f.readlines()

                    # 解析并设置环境变量
                    for line in env_lines:
                        line = line.strip()
                        if '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key] = value

                    logger.info("ADK环境变量已加载")

                    # 重新初始化ADK路径，因为环境变量已更新
                    self.adk_path = None
                    self.winpe_path = None
                    self.adk_version = None
                    self.winpe_versions = {}

                    success, message = self.detect_adk()
                    if success:
                        logger.info("ADK路径已重新初始化")
                    else:
                        logger.warning(f"重新检测ADK失败: {message}")

                    return True, "ADK环境变量加载成功"
                else:
                    return False, "无法读取环境变量文件"

            finally:
                # 清理临时文件
                for temp_file in [temp_bat_path, env_file_path]:
                    try:
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                    except:
                        pass

        except Exception as e:
            error_msg = f"加载ADK环境失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_copype_path(self) -> Optional[Path]:
        """获取copype工具路径"""
        # 首先尝试系统环境变量
        import shutil
        system_copype = shutil.which("copype.cmd")
        if system_copype:
            logger.debug(f"从PATH中找到copype.cmd: {system_copype}")
            return Path(system_copype)

        deploy_tools_path = self.get_deployment_tools_path()
        if not deploy_tools_path:
            logger.debug("部署工具路径不存在，无法查找copype")
            return None

        # 在部署工具目录中查找copype.cmd
        copype_paths = [
            deploy_tools_path / "copype.cmd",
            deploy_tools_path / "amd64" / "copype.cmd",
            deploy_tools_path / "x86" / "copype.cmd"
        ]

        logger.debug(f"搜索copype.cmd路径: {copype_paths}")

        for copype_path in copype_paths:
            if copype_path.exists():
                logger.debug(f"找到copype.cmd: {copype_path}")
                return copype_path

        # 在ADK安装根目录中查找
        if self.adk_path:
            adk_copype_paths = [
                self.adk_path / "Assessment and Deployment Kit" / "Windows Preinstallation Environment" / "copype.cmd",
                self.adk_path / "Assessment and Deployment Kit" / "Deployment Tools" / "copype.cmd"
            ]

            for copype_path in adk_copype_paths:
                if copype_path.exists():
                    logger.debug(f"在ADK根目录中找到copype.cmd: {copype_path}")
                    return copype_path

        # 在WinPE目录中查找
        if self.winpe_path:
            winpe_copype_paths = [
                self.winpe_path / "copype.cmd",
                self.winpe_path.parent / "copype.cmd"
            ]

            for arch_path in self.winpe_path.iterdir():
                if arch_path.is_dir() and arch_path.name in ["amd64", "x86", "arm64"]:
                    copype_in_arch = arch_path / "copype.cmd"
                    winpe_copype_paths.append(copype_in_arch)
                    # 也在arch_path的父目录中查找
                    winpe_copype_paths.append(arch_path.parent / "copype.cmd")

            for copype_path in winpe_copype_paths:
                if copype_path.exists():
                    logger.debug(f"在WinPE目录中找到copype.cmd: {copype_path}")
                    return copype_path

        logger.debug("未找到copype.cmd工具")
        return None

    def get_dism_path(self) -> Optional[Path]:
        """获取DISM工具路径"""
        deploy_tools_path = self.get_deployment_tools_path()
        if not deploy_tools_path:
            return None

        # 查找DISM.exe
        dism_paths = [
            deploy_tools_path / "amd64" / "DISM" / "dism.exe",
            deploy_tools_path / "x86" / "DISM" / "dism.exe"
        ]

        for dism_path in dism_paths:
            if dism_path.exists():
                return dism_path

        # 尝试系统环境变量
        import shutil
        system_dism = shutil.which("dism.exe")
        if system_dism:
            return Path(system_dism)

        return None

    def run_copype_command(self, architecture: str, working_dir: Path, capture_output: bool = True) -> Tuple[bool, str, str]:
        """运行copype命令（简化版本）

        Args:
            architecture: WinPE架构 (amd64, x86, arm64)
            working_dir: 工作目录路径
            capture_output: 是否捕获输出

        Returns:
            Tuple[bool, str, str]: (成功状态, 标准输出, 错误输出)
        """
        copype_path = self.get_copype_path()
        if not copype_path:
            return False, "", "找不到copype工具"

        try:
            # 确保工作目录不存在（copype需要创建新目录）
            # 重要：copype工具会自己创建目标目录，我们不能预先创建
            if working_dir.exists():
                logger.warning(f"目标目录已存在，删除以供copype重新创建: {working_dir}")
                import shutil
                shutil.rmtree(working_dir, ignore_errors=True)
                logger.debug("目录已删除，copype将创建完整的目录结构")

            # 确保父目录存在（但目标目录本身必须由copype创建）
            working_dir.parent.mkdir(parents=True, exist_ok=True)

            # 确保使用短文件名路径
            copype_path_short = self.get_short_path(str(copype_path))
            winpe_path_short = self.get_short_path(str(self.winpe_path)) if self.winpe_path else ""
            working_dir_short = self.get_short_path(str(working_dir))

            # 构建环境变量
            env = os.environ.copy()
            env['WINPEROOT'] = winpe_path_short

            # 简单直接的copype命令 - 不需要复杂的环境加载
            cmd = f'"{copype_path_short}" {architecture} "{working_dir_short}"'

            logger.info(f"执行copype: {architecture} -> {working_dir}")
            logger.debug(f"copype路径: {copype_path}")
            logger.debug(f"WINPEROOT: {env.get('WINPEROOT', 'None')}")
            logger.debug(f"架构目录: {Path(self.winpe_path) / architecture if self.winpe_path else '未知'}")

            # 执行命令
            result = subprocess.run(
                cmd,
                cwd=str(working_dir.parent),
                capture_output=True,
                text=False,
                shell=True,  # 使用shell=True因为命令是字符串格式
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            success = result.returncode == 0

            # 处理输出
            from utils.encoding import safe_decode
            stdout = safe_decode(result.stdout) if success else ""
            stderr = safe_decode(result.stderr)

            if success:
                logger.info("copype执行成功")
                logger.info(f"WinPE目录结构已创建在: {working_dir}")
                if stdout:
                    logger.debug(f"copype输出: {stdout}")

                # 验证copype是否创建了必要的文件
                expected_files = [
                    working_dir / "media" / "sources" / "boot.wim",
                    working_dir / "bootbins"  # 修正：新版本ADK使用bootbins而不是fwfiles
                ]

                missing_files = []
                for f in expected_files:
                    if not f.exists():
                        missing_files.append(str(f))

                if missing_files:
                    logger.warning(f"copype执行后缺少文件: {', '.join(missing_files)}")

            else:
                logger.error(f"copype执行失败，返回码: {result.returncode}")
                if stderr:
                    logger.error(f"错误信息: {stderr}")
                if stdout:
                    logger.debug(f"标准输出: {stdout}")
                logger.error(f"执行的命令: {cmd}")

                # 添加详细的错误诊断信息
                if result.returncode == 1:
                    logger.error("返回码1诊断:")
                    if self.winpe_path:
                        arch_dir = Path(self.winpe_path) / architecture
                        logger.error(f"  - 架构目录: {arch_dir} {'存在' if arch_dir.exists() else '不存在'}")
                    logger.error(f"  - WINPEROOT: {env.get('WINPEROOT', '未设置')}")
                    logger.error("  - 建议检查ADK安装完整性")

            return success, stdout, stderr

        except Exception as e:
            error_msg = f"执行copype命令时发生错误: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg

    def run_dism_command(self, args: List[str], capture_output: bool = True) -> Tuple[bool, str, str]:
        """运行DISM命令

        Args:
            args: DISM命令参数
            capture_output: 是否捕获输出

        Returns:
            Tuple[bool, str, str]: (成功状态, 标准输出, 错误输出)
        """
        dism_path = self.get_dism_path()
        if not dism_path:
            return False, "", "找不到DISM工具"

        try:
            # 构建完整命令
            cmd = [str(dism_path)] + args
            logger.info(f"执行DISM命令: {' '.join(cmd)}")
            logger.debug(f"DISM路径: {dism_path}")
            logger.debug(f"命令参数: {args}")

            if capture_output:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=False,
                    timeout=300,  # 5分钟超时
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                success = result.returncode == 0

                # 使用编码工具处理输出
                from utils.encoding import safe_decode
                stdout = safe_decode(result.stdout)
                stderr = safe_decode(result.stderr)
            else:
                result = subprocess.run(
                    cmd,
                    timeout=300,  # 5分钟超时
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                success = result.returncode == 0
                stdout = ""
                stderr = ""

            if success:
                logger.info("DISM命令执行成功")
                if stdout:
                    logger.debug(f"DISM输出: {stdout}")
            else:
                logger.error(f"DISM命令执行失败，返回码: {result.returncode}")
                logger.error(f"错误输出: {stderr}")
                if stdout:
                    logger.debug(f"标准输出: {stdout}")
                logger.error(f"执行的命令: {' '.join(cmd)}")

            return success, stdout, stderr

        except subprocess.TimeoutExpired as e:
            error_msg = f"DISM命令执行超时 (5分钟): {str(e)}"
            logger.error(error_msg)
            logger.error(f"超时的命令: {' '.join(cmd)}")
            return False, "", error_msg
        except Exception as e:
            error_msg = f"执行DISM命令时发生错误: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg

    def check_admin_privileges(self) -> bool:
        """检查是否具有管理员权限"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def get_adk_install_status(self) -> Dict[str, any]:
        """获取ADK完整安装状态"""
        adk_installed, adk_message = self.detect_adk()
        winpe_installed, winpe_message = self.detect_winpe_addon()

        dandisetenv_path = self.get_dandisetenv_path()
        has_dandisetenv = dandisetenv_path is not None

        # 检查当前环境是否正确设置
        environment_ready = has_dandisetenv and self.check_current_environment()

        return {
            "adk_installed": adk_installed,
            "adk_message": adk_message,
            "winpe_installed": winpe_installed,
            "winpe_message": winpe_message,
            "adk_path": str(self.adk_path) if self.adk_path else "",
            "winpe_path": str(self.winpe_path) if self.winpe_path else "",
            "available_architectures": self.get_available_architectures(),
            "dism_path": str(self.get_dism_path()) if self.get_dism_path() else "",
            "copype_path": str(self.get_copype_path()) if self.get_copype_path() else "",
            "dandisetenv_path": str(dandisetenv_path) if dandisetenv_path else "",
            "has_dandisetenv": has_dandisetenv,
            "environment_ready": environment_ready,
            "has_admin": self.check_admin_privileges()
        }
    def get_short_path(self, long_path: str) -> str:
        """获取短文件名路径（8.3格式）以兼容copype"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Windows API获取短文件名
            buf = ctypes.create_unicode_buffer(260)
            result = ctypes.windll.kernel32.GetShortPathNameW(long_path, buf, 260)
            
            if result == 0:
                # 如果获取失败，返回原路径（这在现代Windows系统中是正常的）
                logger.debug(f"无法获取短文件名，使用原路径: {long_path}")
                return long_path
            else:
                short_path = buf.value
                logger.debug(f"短文件名: {long_path} -> {short_path}")
                return short_path
                
        except Exception as e:
            # 异常时也返回原路径，这在现代Windows系统中是正常的
            logger.debug(f"获取短文件名失败，使用原路径: {long_path} ({e})")
            return long_path
