#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
负责管理WinPE制作过程中的各种配置
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger("WinPEManager")


class ConfigManager:
    """配置管理器类"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.config_dir = self.project_root / "config"
        self.config_file = self.config_dir / "winpe_config.json"
        self.default_config = self._get_default_config()
        self.config = self._load_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "winpe": {
                "architecture": "amd64",  # x86, amd64, arm
                "version": "10",  # WinPE版本
                "language": "zh-cn",  # 语言
                "base_winpe": "winpe.wim"  # 基础WinPE镜像
            },
            "adk": {
                "install_path": "",  # ADK安装路径
                "winpe_path": ""  # WinPE加载项路径
            },
            "output": {
                "iso_path": "",  # ISO输出路径
                "usb_path": "",   # U盘制作路径
                "workspace": ""   # 工作空间路径
            },
            "customization": {
                "drivers": [],    # 驱动程序列表
                "packages": [],   # 可选组件列表
                "scripts": [],    # 自定义脚本列表
                "files": []       # 额外文件列表
            },
            "ui": {
                "window_geometry": "",
                "window_state": "",
                "recent_projects": []
            }
        }

    def _load_config(self) -> Dict[str, Any]:
        """从文件加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"配置文件加载成功: {self.config_file}")
                # 合并默认配置和加载的配置
                return self._merge_config(self.default_config, config)
            else:
                logger.info("配置文件不存在，使用默认配置")
                return self.default_config.copy()
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            return self.default_config.copy()

    def _merge_config(self, default: Dict, loaded: Dict) -> Dict:
        """合并配置，确保所有必要的键都存在"""
        result = default.copy()
        for key, value in loaded.items():
            if key in result:
                if isinstance(value, dict) and isinstance(result[key], dict):
                    result[key] = self._merge_config(result[key], value)
                else:
                    result[key] = value
            else:
                result[key] = value
        return result

    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            self.config_dir.mkdir(exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"配置文件保存成功: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的路径

        Args:
            key_path: 配置键路径，如 'winpe.architecture'
            default: 默认值
        """
        keys = key_path.split('.')
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any) -> bool:
        """设置配置值

        Args:
            key_path: 配置键路径，如 'winpe.architecture'
            value: 要设置的值
        """
        try:
            keys = key_path.split('.')
            config = self.config
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            config[keys[-1]] = value
            logger.debug(f"配置更新: {key_path} = {value}")
            return True
        except Exception as e:
            logger.error(f"设置配置失败: {key_path} = {value}, 错误: {str(e)}")
            return False

    def add_driver(self, driver_path: str, description: str = "") -> bool:
        """添加驱动程序"""
        try:
            driver_info = {
                "path": driver_path,
                "description": description,
                "added_time": str(Path(driver_path).stat().st_mtime)
            }
            if driver_info not in self.config["customization"]["drivers"]:
                self.config["customization"]["drivers"].append(driver_info)
                logger.info(f"添加驱动程序: {driver_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"添加驱动程序失败: {str(e)}")
            return False

    def remove_driver(self, driver_path: str) -> bool:
        """移除驱动程序"""
        try:
            drivers = self.config["customization"]["drivers"]
            for i, driver in enumerate(drivers):
                if driver["path"] == driver_path:
                    drivers.pop(i)
                    logger.info(f"移除驱动程序: {driver_path}")
                    return True
            return False
        except Exception as e:
            logger.error(f"移除驱动程序失败: {str(e)}")
            return False

    def add_script(self, script_path: str, description: str = "") -> bool:
        """添加自定义脚本"""
        try:
            script_info = {
                "path": script_path,
                "description": description,
                "added_time": str(Path(script_path).stat().st_mtime)
            }
            if script_info not in self.config["customization"]["scripts"]:
                self.config["customization"]["scripts"].append(script_info)
                logger.info(f"添加脚本: {script_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"添加脚本失败: {str(e)}")
            return False

    def get_available_architectures(self) -> List[str]:
        """获取可用的WinPE架构列表"""
        return ["x86", "amd64", "arm"]

    def get_available_packages(self) -> List[Dict[str, str]]:
        """获取可用的WinPE包列表"""
        return [
            {"id": "WinPE-WMI", "name": "WMI 支持"},
            {"id": "WinPE-NetFx", "name": ".NET Framework 支持"},
            {"id": "WinPE-PowerShell", "name": "PowerShell 支持"},
            {"id": "WinPE-DismCmdlets", "name": "DISM 命令行工具"},
            {"id": "WinPE-SecureStartup", "name": "BitLocker 支持"},
            {"id": "WinPE-StorageWMI", "name": "存储 WMI 支持"},
            {"id": "WinPE-HTA", "name": "HTA 应用程序支持"},
            {"id": "WinPE-RSAT", "name": "远程服务器管理工具"}
        ]