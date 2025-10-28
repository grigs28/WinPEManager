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
        self.command_callback = None  # 命令输出回调函数

    def set_command_callback(self, callback):
        """设置命令输出回调函数

        Args:
            callback: 回调函数，接收(command: str, output: str)参数
        """
        self.command_callback = callback

    def _emit_command_output(self, command: str, output: str):
        """发送命令输出到回调函数

        Args:
            command: 命令描述
            output: 输出内容
        """
        if self.command_callback:
            self.command_callback(command, output)

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
            if path.exists():
                # 检查多种可能的ADK目录结构
                adk_indicators = [
                    "Assessment and Deployment Kit",
                    "Deployment Tools",
                    "Windows Kits",
                    "10" in str(path),
                    "11" in str(path)
                ]

                # 只要路径存在且包含Windows Kits相关内容就认为是可能的ADK路径
                if any(indicator if isinstance(indicator, bool) else (path / indicator).exists()
                      for indicator in [path / "Assessment and Deployment Kit", path / "Deployment Tools"]):
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

    def get_oscdimg_path(self) -> Optional[str]:
        """获取Oscdimg工具路径"""
        deploy_tools_path = self.get_deployment_tools_path()
        if not deploy_tools_path:
            return None

        # 尝试多个可能的架构路径
        oscdimg_paths = [
            deploy_tools_path / "amd64" / "Oscdimg" / "oscdimg.exe",
            deploy_tools_path / "x86" / "Oscdimg" / "oscdimg.exe",
            deploy_tools_path / "arm64" / "Oscdimg" / "oscdimg.exe",
        ]

        for oscdimg_path in oscdimg_paths:
            if oscdimg_path.exists():
                return str(oscdimg_path)

        # 尝试系统PATH
        import shutil
        system_oscdimg = shutil.which("oscdimg.exe")
        if system_oscdimg:
            return system_oscdimg

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
            # 修复路径格式问题 - 确保使用正斜杠
            formatted_args = []
            for arg in args:
                if isinstance(arg, str) and (":" in arg or "\\" in arg):
                    # 将反斜杠转换为正斜杠，并确保路径格式正确
                    arg = arg.replace("\\", "/")
                    if not arg.startswith("/") and ":" in arg:
                        # 这是路径参数，确保格式正确
                        if "/Image:" in arg or "/MountDir:" in arg or "/ImageFile:" in arg:
                            continue  # 保持这些参数的原格式
                formatted_args.append(arg)

            # 构建完整命令
            cmd = [str(dism_path)] + formatted_args
            logger.info(f"执行DISM命令: {' '.join(cmd)}")
            logger.debug(f"DISM路径: {dism_path}")
            logger.debug(f"原始参数: {args}")
            logger.debug(f"格式化参数: {formatted_args}")

            # 添加更详细的日志
            logger.info(f"开始执行DISM命令，参数: {formatted_args}")

            if capture_output:
                # 使用超时机制和更详细的错误处理
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=False,
                    timeout=60,  # 缩短超时时间到60秒，避免长时间阻塞
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                success = result.returncode == 0

                # 使用编码工具处理输出
                from utils.encoding import safe_decode
                stdout = safe_decode(result.stdout) if result.stdout else ""
                stderr = safe_decode(result.stderr) if result.stderr else ""
                
                # 添加更详细的日志
                logger.info(f"DISM命令执行完成，返回码: {result.returncode}")
                if success:
                    logger.info("DISM命令执行成功")
                    if stdout:
                        logger.debug(f"DISM标准输出: {stdout[:200]}...")  # 只记录前200字符
                else:
                    logger.error(f"DISM命令执行失败，返回码: {result.returncode}")
                    logger.error(f"错误输出: {stderr[:200]}...")  # 只记录前200字符
                    if stdout:
                        logger.debug(f"标准输出: {stdout[:200]}...")
            else:
                # 不捕获输出的情况
                result = subprocess.run(
                    cmd,
                    timeout=60,  # 缩短超时时间到60秒
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                success = result.returncode == 0
                stdout = ""
                stderr = ""
                logger.info(f"DISM命令执行完成，返回码: {result.returncode}")

            if success:
                logger.info("DISM命令执行成功")
                if stdout:
                    logger.debug(f"DISM输出: {stdout[:200]}...")  # 只记录前200字符
            else:
                logger.error(f"DISM命令执行失败，返回码: {result.returncode}")
                logger.error(f"错误输出: {stderr[:200]}...")  # 只记录前200字符
                if stdout:
                    logger.debug(f"标准输出: {stdout[:200]}...")
                logger.error(f"执行的命令: {' '.join(cmd)}")

                # 特殊处理常见的DISM错误代码
                if result.returncode == 87:
                    logger.error("DISM错误87分析 - 参数格式问题:")
                    logger.error("可能的原因:")
                    logger.error("1. 路径参数格式错误（应使用正斜杠）")
                    logger.error("2. 参数名称不正确")
                    logger.error("3. 缺少必需的参数")
                    logger.error("4. 参数值格式不正确")
                    logger.error(f"请检查命令格式: {' '.join(cmd)}")

                    # 提供修复建议
                    if any("/Image:" in arg for arg in formatted_args):
                        logger.error("建议检查 /Image 参数格式")
                    if any("/MountDir:" in arg for arg in formatted_args):
                        logger.error("建议检查 /MountDir 参数格式")
                    if any("/ImageFile:" in arg for arg in formatted_args):
                        logger.error("建议检查 /ImageFile 参数格式")

            return success, stdout, stderr

        except subprocess.TimeoutExpired as e:
            error_msg = f"DISM命令执行超时 (60秒): {str(e)}"
            logger.error(error_msg)
            logger.error(f"超时的命令: {' '.join(cmd)}")
            return False, "", error_msg
        except Exception as e:
            error_msg = f"执行DISM命令时发生错误: {str(e)}"
            logger.error(error_msg)
            logger.error(f"错误详情: {repr(e)}")
            return False, "", error_msg

    def check_admin_privileges(self) -> bool:
        """检查是否具有管理员权限"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def get_adk_install_path(self) -> Optional[Path]:
        """获取ADK安装路径

        Returns:
            Optional[Path]: ADK安装路径，如果未找到则返回None
        """
        return self.adk_path

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
    def get_make_winpe_media_path(self) -> Optional[Path]:
        """获取MakeWinPEMedia工具路径"""
        deploy_tools_path = self.get_deployment_tools_path()
        if not deploy_tools_path:
            logger.debug("无法找到部署工具路径")
            self._emit_command_output("ADK检查", "部署工具路径不存在")
            return None

        logger.debug(f"部署工具路径: {deploy_tools_path}")

        # 查找MakeWinPEMedia.cmd
        makewinpe_paths = [
            deploy_tools_path / "amd64" / "MakeWinPEMedia.cmd",
            deploy_tools_path / "x86" / "MakeWinPEMedia.cmd"
        ]

        for makewinpe_path in makewinpe_paths:
            logger.debug(f"检查MakeWinPEMedia路径: {makewinpe_path}")
            if makewinpe_path.exists():
                logger.debug(f"找到MakeWinPEMedia: {makewinpe_path}")
                self._emit_command_output("ADK检查", f"找到MakeWinPEMedia: {makewinpe_path.name}")
                return makewinpe_path
            else:
                logger.debug(f"MakeWinPEMedia不存在: {makewinpe_path}")

        # 尝试系统环境变量
        import shutil
        system_makewinpe = shutil.which("MakeWinPEMedia.cmd")
        if system_makewinpe:
            logger.debug(f"从系统PATH找到MakeWinPEMedia: {system_makewinpe}")
            self._emit_command_output("ADK检查", f"从系统PATH找到MakeWinPEMedia")
            return Path(system_makewinpe)
        else:
            logger.debug("系统PATH中也找不到MakeWinPEMedia")
            self._emit_command_output("ADK检查", "系统PATH中找不到MakeWinPEMedia")

        return None

    def create_iso_with_oscdimg(self, build_dir: Path, iso_path: Path, capture_output: bool = True) -> Tuple[bool, str, str]:
        """使用oscdimg创建ISO文件

        Args:
            build_dir: 包含WinPE文件的构建目录
            iso_path: 目标ISO文件路径
            capture_output: 是否捕获输出

        Returns:
            Tuple[bool, str, str]: (成功状态, 标准输出, 错误输出)
        """
        # 先检查ADK路径，如果未检测到则重新检测
        adk_path = self.get_adk_install_path()
        if not adk_path:
            self._emit_command_output("ADK检查", "ADK路径为空，尝试重新检测...")
            # 手动调用ADK检测
            adk_installed, adk_message = self.detect_adk()
            if not adk_installed:
                error_msg = f"找不到ADK安装路径 - {adk_message}"
                self._emit_command_output("ADK检查", error_msg)

                # 手动搜索常见路径
                self._emit_command_output("ADK检查", "手动搜索常见ADK安装路径...")
                common_paths = self._search_common_paths()
                if common_paths and common_paths.exists():
                    self.adk_path = common_paths
                    adk_path = common_paths
                    self._emit_command_output("ADK检查", f"手动找到ADK路径: {adk_path}")
                else:
                    # 输出详细的搜索路径信息
                    self._emit_command_output("ADK检查", "以下路径均已检查但未找到ADK:")
                    for path in self.adk_common_paths:
                        self._emit_command_output("ADK检查", f"  - {path} {'(存在)' if Path(path).exists() else '(不存在)'}")

                    # 最后尝试：直接搜索oscdimg.exe而不依赖ADK路径
                    self._emit_command_output("最后尝试", "直接搜索oscdimg.exe...")
                    import shutil
                    system_oscdimg = shutil.which("oscdimg.exe")
                    if system_oscdimg:
                        self._emit_command_output("最后尝试", f"从系统PATH找到oscdimg.exe: {system_oscdimg}")
                        oscdimg_path = system_oscdimg
                        # 跳过ADK路径检查，直接使用oscdimg
                        return self._create_iso_direct(oscdimg_path, build_dir, iso_path, boot_dir, capture_output)

                    return False, "", error_msg
            else:
                adk_path = self.adk_path
                self._emit_command_output("ADK检查", f"重新检测成功: {adk_message}")
        else:
            self._emit_command_output("ADK检查", f"找到ADK路径: {adk_path}")

        # 检查部署工具路径
        deploy_tools_path = self.get_deployment_tools_path()
        if not deploy_tools_path:
            error_msg = "找不到部署工具路径"
            self._emit_command_output("部署工具检查", error_msg)
            # 尝试手动构建部署工具路径
            possible_deploy_paths = [
                adk_path / "Assessment and Deployment Kit" / "Deployment Tools",
                adk_path / "Deployment Tools"
            ]
            for path in possible_deploy_paths:
                if path.exists():
                    self._emit_command_output("部署工具检查", f"找到替代部署工具路径: {path}")
                    deploy_tools_path = path
                    break
            if not deploy_tools_path:
                return False, "", error_msg
        else:
            self._emit_command_output("部署工具检查", f"找到部署工具路径: {deploy_tools_path}")

        # 查找oscdimg.exe
        oscdimg_path = self.get_oscdimg_path()
        if not oscdimg_path:
            error_msg = "找不到oscdimg工具"

            # 手动搜索oscdimg.exe
            oscdimg_search_paths = [
                deploy_tools_path / "amd64" / "Oscdimg" / "oscdimg.exe",
                deploy_tools_path / "x86" / "Oscdimg" / "oscdimg.exe",
                deploy_tools_path / "arm64" / "Oscdimg" / "oscdimg.exe"
            ]

            self._emit_command_output("oscdimg搜索", "开始搜索oscdimg.exe...")
            for search_path in oscdimg_search_paths:
                if search_path.exists():
                    oscdimg_path = str(search_path)
                    self._emit_command_output("oscdimg搜索", f"找到oscdimg.exe: {oscdimg_path}")
                    break
                else:
                    self._emit_command_output("oscdimg搜索", f"检查路径: {search_path} - 不存在")

            if not oscdimg_path:
                # 尝试系统PATH
                import shutil
                system_oscdimg = shutil.which("oscdimg.exe")
                if system_oscdimg:
                    oscdimg_path = system_oscdimg
                    self._emit_command_output("oscdimg搜索", f"从系统PATH找到oscdimg.exe: {oscdimg_path}")
                else:
                    error_msg += f" - 已搜索路径: {[str(p) for p in oscdimg_search_paths]}"
                    self._emit_command_output("错误", error_msg)
                    return False, "", error_msg

        try:
            # 确保构建目录存在
            if not build_dir.exists():
                raise Exception(f"构建目录不存在: {build_dir}")

            # 确保boot目录存在
            boot_dir = build_dir / "boot"
            if not boot_dir.exists():
                raise Exception(f"boot目录不存在: {boot_dir}")

            # 如果ISO文件已存在，先删除
            if iso_path.exists():
                logger.info(f"删除现有ISO文件: {iso_path}")
                self._emit_command_output("文件操作", f"删除现有ISO: {iso_path}")
                iso_path.unlink()

            # 确保ISO输出目录存在
            iso_path.parent.mkdir(parents=True, exist_ok=True)

            # 构建完整的oscdimg命令
            cmd = [oscdimg_path]

            # 添加优化和格式参数
            # 注意：-u2参数不能与-j1、-j2、-n、-nt、-d、-oi同时使用
            cmd.extend([
                "-m",                    # 优化文件分配表大小
                "-o",                    # 覆盖现有文件
                "-u2",                   # UDF文件系统版本2.0
                "-udfver102",           # UDF版本1.02（兼容性更好）
                "-lWinPE_Replaced",      # 卷标名
                "-h",                    # 包含隐藏文件
                "-x",                    # 忽略压缩属性
                "-w"                     # 警告覆盖
                # 移除了 -np (长文件名支持) 和 -j1 (Joliet文件系统)，
                # 因为它们与 -u2 冲突。UDF 2.0 本身就支持长文件名和Unicode
            ])

            # 检查并添加启动数据
            bootsect_file = boot_dir / "etfsboot.com"
            efi_file = boot_dir / "efisys.bin"
            efi_noesp_file = boot_dir / "efisys_noesp.bin"

            # 获取ADK中的原始启动文件路径
            adk_boot_files = {}
            deploy_tools_path = self.get_deployment_tools_path()
            if deploy_tools_path:
                adk_etfsboot = deploy_tools_path / "amd64" / "Oscdimg" / "etfsboot.com"
                adk_efisys = deploy_tools_path / "amd64" / "Oscdimg" / "efisys.bin"
                adk_efisys_noesp = deploy_tools_path / "amd64" / "Oscdimg" / "efisys_noesp.bin"

                if adk_etfsboot.exists():
                    adk_boot_files['etfsboot'] = adk_etfsboot
                if adk_efisys.exists():
                    adk_boot_files['efisys'] = adk_efisys
                if adk_efisys_noesp.exists():
                    adk_boot_files['efisys_noesp'] = adk_efisys_noesp

            # 详细启动文件检查
            boot_files_status = []

            # 检查etfsboot.com
            if bootsect_file.exists():
                boot_files_status.append(f"etfsboot.com (本地) ({bootsect_file.stat().st_size} bytes)")
            elif 'etfsboot' in adk_boot_files:
                # 复制ADK中的etfsboot.com到本地
                import shutil
                try:
                    shutil.copy2(adk_boot_files['etfsboot'], bootsect_file)
                    boot_files_status.append(f"etfsboot.com (从ADK复制) ({bootsect_file.stat().st_size} bytes)")
                    self._emit_command_output("文件复制", f"已复制etfsboot.com从ADK到boot目录")
                except Exception as e:
                    boot_files_status.append(f"etfsboot.com (复制失败): {str(e)}")
            else:
                boot_files_status.append("etfsboot.com (缺失)")

            # 检查efisys.bin
            if efi_file.exists():
                boot_files_status.append(f"efisys.bin (本地) ({efi_file.stat().st_size} bytes)")
            elif 'efisys' in adk_boot_files:
                # 复制ADK中的efisys.bin到本地
                import shutil
                try:
                    shutil.copy2(adk_boot_files['efisys'], efi_file)
                    boot_files_status.append(f"efisys.bin (从ADK复制) ({efi_file.stat().st_size} bytes)")
                    self._emit_command_output("文件复制", f"已复制efisys.bin从ADK到boot目录")
                except Exception as e:
                    boot_files_status.append(f"efisys.bin (复制失败): {str(e)}")
            else:
                boot_files_status.append("efisys.bin (缺失)")

            # 检查efisys_noesp.bin
            if efi_noesp_file.exists():
                boot_files_status.append(f"efisys_noesp.bin (本地) ({efi_noesp_file.stat().st_size} bytes)")
            elif 'efisys_noesp' in adk_boot_files:
                # 复制ADK中的efisys_noesp.bin到本地
                import shutil
                try:
                    shutil.copy2(adk_boot_files['efisys_noesp'], efi_noesp_file)
                    boot_files_status.append(f"efisys_noesp.bin (从ADK复制) ({efi_noesp_file.stat().st_size} bytes)")
                    self._emit_command_output("文件复制", f"已复制efisys_noesp.bin从ADK到boot目录")
                except Exception as e:
                    boot_files_status.append(f"efisys_noesp.bin (复制失败): {str(e)}")
            else:
                boot_files_status.append("efisys_noesp.bin (缺失)")

            self._emit_command_output("启动文件检查", ", ".join(boot_files_status))

            # 重新检查启动文件是否已准备就绪
            etfsboot_ready = bootsect_file.exists()
            efisys_ready = efi_file.exists()

            # 构建启动数据参数
            if etfsboot_ready:
                if efisys_ready:
                    # 支持传统BIOS和UEFI启动（双重启动）
                    # 按照用户成功的格式：文件路径需要用引号包围
                    self._emit_command_output("启动模式", "双重启动: 传统BIOS + UEFI")

                    # 验证启动文件
                    if bootsect_file.stat().st_size == 0:
                        raise Exception("etfsboot.com文件为空")
                    if efi_file.stat().st_size == 0:
                        raise Exception("efisys.bin文件为空")

                    # 按照用户成功的格式构建bootdata参数（路径加引号）
                    boot_data = f'2#p0,e,b"{bootsect_file}"#pEF,e,b"{efi_file}"'

                else:
                    # 仅支持传统BIOS启动
                    self._emit_command_output("启动模式", "传统BIOS启动")

                    if bootsect_file.stat().st_size == 0:
                        raise Exception("etfsboot.com文件为空")

                    boot_data = f'2#p0,e,b"{bootsect_file}"'

                cmd.extend(["-bootdata:" + boot_data])
                logger.info(f"添加启动数据: {boot_data}")

                # 输出详细的启动数据信息
                self._emit_command_output("启动数据", f"启动数据参数: {boot_data}")

                # 验证启动文件详细信息
                self._emit_command_output("文件验证", f"etfsboot.com: {bootsect_file.stat().st_size} bytes")
                if efisys_ready:
                    self._emit_command_output("文件验证", f"efisys.bin: {efi_file.stat().st_size} bytes")

                # 验证启动文件完整性
                if bootsect_file.stat().st_size < 1024:  # etfsboot.com应该至少1KB
                    logger.warning(f"etfsboot.com文件大小异常: {bootsect_file.stat().st_size} bytes")
                    self._emit_command_output("警告", f"etfsboot.com文件大小可能异常: {bootsect_file.stat().st_size} bytes")

            else:
                logger.warning("未找到启动文件，将创建非启动ISO")
                self._emit_command_output("警告", "未找到启动文件，创建非启动ISO")

            # 添加源目录和目标文件
            cmd.extend([str(build_dir), str(iso_path)])

            # 输出完整命令行到日志和UI
            # 注意：subprocess.run会正确处理命令列表，不需要额外的引号
            full_command_display = ' '.join([f'"{arg}"' if ' ' in str(arg) and not arg.startswith('"') and not arg.endswith('"') else str(arg) for arg in cmd])
            logger.info(f"完整oscdimg命令: {full_command_display}")
            self._emit_command_output("完整命令", f"oscdimg.exe 命令行:")
            self._emit_command_output("命令详情", full_command_display)

            # 显示实际传递给subprocess的命令列表
            cmd_list_display = '[' + ', '.join([f'"{arg}"' for arg in cmd]) + ']'
            self._emit_command_output("命令列表", f"实际命令参数: {cmd_list_display}")

            # 生成用户提供的标准PowerShell命令格式
            exe_path = cmd[0]
            args = cmd[1:]

            # 按照用户的正确格式生成PowerShell命令
            ps_lines = ['& "' + str(exe_path) + '" `']

            # 每个参数单独一行，用 ` 续行
            for arg in args:
                if ' ' in str(arg) or '"' in str(arg):
                    ps_lines.append('    "' + str(arg) + '" `')
                else:
                    ps_lines.append('    ' + str(arg) + ' `')

            # 移除最后一个 ` 并合并
            ps_lines[-1] = ps_lines[-1].rstrip(' `')
            ps_command = '\n'.join(ps_lines)

            self._emit_command_output("PowerShell命令", ps_command)

            # 同时生成单行版本（用于复制粘贴）
            single_line_args = []
            for arg in args:
                if ' ' in str(arg) or '"' in str(arg):
                    single_line_args.append('"' + str(arg) + '"')
                else:
                    single_line_args.append(str(arg))

            single_line_command = '& "' + str(exe_path) + '" ' + ' '.join(single_line_args)
            self._emit_command_output("单行命令", single_line_command)

            # 输出参数解释
            self._emit_command_output("参数说明", "命令参数说明:")
            param_explanations = [
                "-m: 优化文件分配表大小",
                "-o: 覆盖现有文件",
                "-u2: UDF文件系统版本2.0 (自带长文件名和Unicode支持)",
                "-udfver102: UDF版本1.02(兼容性更好)",
                "-lWinPE_Replaced: 卷标名",
                "-h: 包含隐藏文件",
                "-x: 忽略压缩属性",
                "-w: 警告覆盖",
                "注意: -u2与-j1、-np等参数冲突，UDF 2.0已内置Unicode支持"
            ]
            for explanation in param_explanations:
                self._emit_command_output("参数", explanation)

            # 使用PowerShell执行oscdimg命令（按照用户成功的格式）
            logger.info("使用PowerShell执行oscdimg命令")

            # 构建PowerShell命令
            ps_command = '& "' + str(cmd[0]) + '"'
            for arg in cmd[1:]:
                arg_str = str(arg)
                # 检查是否是bootdata参数（已包含引号）
                if arg_str.startswith('-bootdata:'):
                    # bootdata参数已经包含了正确的引号，直接使用
                    ps_command += ' ' + arg_str
                elif ' ' in arg_str or '"' in arg_str:
                    # 其他包含空格或引号的参数需要加引号
                    ps_command += ' "' + arg_str + '"'
                else:
                    # 普通参数直接添加
                    ps_command += ' ' + arg_str

            logger.info(f"PowerShell命令: {ps_command}")
            self._emit_command_output("执行方式", "使用PowerShell执行")
            self._emit_command_output("完整命令", ps_command)

            # 使用PowerShell执行命令
            ps_cmd = ['powershell.exe', '-Command', ps_command]
            result = subprocess.run(
                ps_cmd,
                capture_output=True,
                text=False,
                timeout=300,  # 5分钟超时
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            success = result.returncode == 0

            # 处理输出
            from utils.encoding import safe_decode
            stdout = safe_decode(result.stdout) if result.stdout else ""
            stderr = safe_decode(result.stderr) if result.stderr else ""

            # 发送命令输出到回调
            if stdout:
                lines = stdout.split('\n')
                for line in lines:
                    if line.strip():
                        self._emit_command_output("oscdimg输出", line.strip())

            if stderr:
                lines = stderr.split('\n')
                for line in lines:
                    if line.strip():
                        self._emit_command_output("oscdimg错误", line.strip())

            logger.info(f"PowerShell oscdimg命令执行完成，返回码: {result.returncode}")

            if success:
                logger.info("PowerShell oscdimg命令执行成功")
                self._emit_command_output("ISO创建完成", f"ISO文件已创建: {iso_path}")
                # 发送100%进度完成信号
                if hasattr(self, '_emit_progress'):
                    self._emit_progress(100, "ISO文件创建完成")
            else:
                logger.error(f"PowerShell oscdimg命令执行失败，返回码: {result.returncode}")
                self._emit_command_output("ISO创建失败", f"返回码: {result.returncode}")

            return success, stdout, stderr

        except subprocess.TimeoutExpired:
            error_msg = "PowerShell oscdimg命令执行超时（5分钟）"
            logger.error(error_msg)
            self._emit_command_output("错误", error_msg)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"PowerShell oscdimg命令执行异常: {str(e)}"
            logger.error(error_msg)
            self._emit_command_output("错误", error_msg)
            return False, "", error_msg

    def _create_iso_direct(self, oscdimg_path: str, build_dir: Path, iso_path: Path, boot_dir: Path, capture_output: bool = True) -> Tuple[bool, str, str]:
        """直接使用oscdimg创建ISO（绕过ADK路径检查）"""
        try:
            # 构建完整的oscdimg命令
            cmd = [oscdimg_path]

            # 添加优化和格式参数（避免与-u2冲突的参数）
            cmd.extend([
                "-m", "-o", "-u2", "-udfver102", "-lWinPE_Replaced",
                "-h", "-x", "-w"
                # 移除 -np 和 -j1，因为与 -u2 冲突
            ])

            # 检查启动文件
            bootsect_file = boot_dir / "etfsboot.com"
            efi_file = boot_dir / "efisys.bin"

            if bootsect_file.exists():
                if efi_file.exists():
                    # 按照用户成功的格式：路径需要用引号包围
                    boot_data = f'2#p0,e,b"{bootsect_file}"#pEF,e,b"{efi_file}"'
                    self._emit_command_output("启动模式", "双重启动: 传统BIOS + UEFI")
                else:
                    boot_data = f'2#p0,e,b"{bootsect_file}"'
                    self._emit_command_output("启动模式", "传统BIOS启动")
                cmd.extend(["-bootdata:" + boot_data])

            # 添加源目录和目标文件
            cmd.extend([str(build_dir), str(iso_path)])

            # 输出完整命令行
            full_command = ' '.join([f'"{arg}"' if ' ' in str(arg) else str(arg) for arg in cmd])
            self._emit_command_output("完整命令", f"直接使用oscdimg创建ISO:")
            self._emit_command_output("命令详情", full_command)

            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=False,
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            success = result.returncode == 0

            # 处理输出
            from utils.encoding import safe_decode
            stdout = safe_decode(result.stdout) if result.stdout else ""
            stderr = safe_decode(result.stderr) if result.stderr else ""

            if success:
                self._emit_command_output("ISO创建完成", f"ISO文件已创建: {iso_path}")
            else:
                self._emit_command_output("ISO创建失败", f"返回码: {result.returncode}")

            return success, stdout, stderr

        except Exception as e:
            error_msg = f"直接创建ISO失败: {str(e)}"
            self._emit_command_output("错误", error_msg)
            return False, "", error_msg

    def run_make_winpe_media_command(self, args: List[str], capture_output: bool = True) -> Tuple[bool, str, str]:
        """运行MakeWinPEMedia命令

        Args:
            args: MakeWinPEMedia命令参数
            capture_output: 是否捕获输出

        Returns:
            Tuple[bool, str, str]: (成功状态, 标准输出, 错误输出)
        """
        makewinpe_path = self.get_make_winpe_media_path()
        if not makewinpe_path:
            error_msg = "找不到MakeWinPEMedia工具"

            # 提供更详细的错误信息
            adk_path = self.get_adk_install_path()
            if not adk_path:
                error_msg += " - 未找到Windows ADK安装，请确保已安装Windows ADK"
            else:
                deploy_tools_path = self.get_deployment_tools_path()
                if not deploy_tools_path:
                    error_msg += f" - ADK已安装但找不到部署工具，请检查ADK安装是否完整"
                else:
                    error_msg += f" - 部署工具路径: {deploy_tools_path}，但找不到MakeWinPEMedia.cmd"

            logger.error(error_msg)
            self._emit_command_output("错误", error_msg)
            return False, "", error_msg

        try:
            # 构建完整命令
            cmd = [str(makewinpe_path)] + args
            logger.info(f"执行MakeWinPEMedia命令: {' '.join(cmd)}")
            logger.debug(f"MakeWinPEMedia路径: {makewinpe_path}")
            logger.debug(f"命令参数: {args}")

            # 添加更详细的日志
            logger.info(f"开始执行MakeWinPEMedia命令，参数: {args}")
            self._emit_command_output("MakeWinPEMedia启动", f"命令: {' '.join(cmd)}")

            # 检查是否为ISO创建命令，如果是，先尝试删除现有ISO文件
            if len(args) >= 3 and args[0].upper() == '/ISO':
                iso_path = args[-1]  # 最后一个参数是ISO路径
                import os
                if os.path.exists(iso_path):
                    logger.info(f"检测到现有ISO文件，将先删除: {iso_path}")
                    self._emit_command_output("文件操作", f"删除现有ISO: {iso_path}")
                    try:
                        os.remove(iso_path)
                        logger.info(f"成功删除现有ISO文件: {iso_path}")
                        self._emit_command_output("文件操作", "现有ISO文件删除成功")
                    except Exception as e:
                        logger.warning(f"无法删除现有ISO文件: {iso_path}, 错误: {str(e)}")
                        self._emit_command_output("文件操作", f"删除ISO文件失败: {str(e)}")

            if capture_output:
                # 使用超时机制和更详细的错误处理
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=False,
                    timeout=120,  # 缩短超时时间到120秒，避免长时间阻塞
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                success = result.returncode == 0

                # 使用编码工具处理输出
                from utils.encoding import safe_decode
                stdout = safe_decode(result.stdout) if result.stdout else ""
                stderr = safe_decode(result.stderr) if result.stderr else ""

                # 发送命令输出到回调
                if stdout:
                    # 将输出分行处理，避免一次性输出太多
                    lines = stdout.split('\n')
                    for i, line in enumerate(lines[:50]):  # 限制前50行
                        if line.strip():
                            self._emit_command_output("命令输出", line.strip())
                        if i >= 49:  # 如果超过50行，显示省略提示
                            self._emit_command_output("命令输出", "... (输出过多，已省略)")
                            break

                if stderr:
                    # 错误输出也分行处理
                    lines = stderr.split('\n')
                    for i, line in enumerate(lines[:20]):  # 错误输出限制前20行
                        if line.strip():
                            self._emit_command_output("错误输出", line.strip())
                        if i >= 19:
                            self._emit_command_output("错误输出", "... (错误输出过多，已省略)")
                            break

                # 添加更详细的日志
                logger.info(f"MakeWinPEMedia命令执行完成，返回码: {result.returncode}")
                self._emit_command_output("命令完成", f"返回码: {result.returncode}")

                if success:
                    logger.info("MakeWinPEMedia命令执行成功")
                    self._emit_command_output("执行结果", "命令执行成功")
                    if stdout:
                        logger.debug(f"MakeWinPEMedia标准输出: {stdout[:200]}...")  # 只记录前200字符
                else:
                    logger.error(f"MakeWinPEMedia命令执行失败，返回码: {result.returncode}")
                    self._emit_command_output("执行结果", "命令执行失败")
                    logger.error(f"错误输出: {stderr[:200]}...")  # 只记录前200字符
                    if stdout:
                        logger.debug(f"标准输出: {stdout[:200]}...")
            else:
                # 不捕获输出的情况
                result = subprocess.run(
                    cmd,
                    timeout=120,  # 缩短超时时间到120秒
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                success = result.returncode == 0
                stdout = ""
                stderr = ""
                logger.info(f"MakeWinPEMedia命令执行完成，返回码: {result.returncode}")

            if success:
                logger.info("MakeWinPEMedia命令执行成功")
                if stdout:
                    logger.debug(f"MakeWinPEMedia输出: {stdout[:200]}...")  # 只记录前200字符
            else:
                logger.error(f"MakeWinPEMedia命令执行失败，返回码: {result.returncode}")
                logger.error(f"错误输出: {stderr[:200]}...")  # 只记录前200字符
                if stdout:
                    logger.debug(f"标准输出: {stdout[:200]}...")
                logger.error(f"执行的命令: {' '.join(cmd)}")

            return success, stdout, stderr

        except subprocess.TimeoutExpired as e:
            error_msg = f"MakeWinPEMedia命令执行超时 (120秒): {str(e)}"
            logger.error(error_msg)
            logger.error(f"超时的命令: {' '.join(cmd)}")
            return False, "", error_msg
        except Exception as e:
            error_msg = f"执行MakeWinPEMedia命令时发生错误: {str(e)}"
            logger.error(error_msg)
            logger.error(f"错误详情: {repr(e)}")
            return False, "", error_msg

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
