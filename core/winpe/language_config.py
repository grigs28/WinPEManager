#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语言配置模块
负责WinPE系统语言和区域设置
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger("WinPEManager")


class LanguageConfig:
    """WinPE语言配置管理器"""

    def __init__(self, config_manager, adk_manager, parent_callback=None):
        self.config = config_manager
        self.adk = adk_manager
        self.parent_callback = parent_callback

    def configure_language_settings(self, current_build_path: Path) -> Tuple[bool, str]:
        """配置WinPE系统语言和区域设置

        Args:
            current_build_path: 当前构建路径

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not current_build_path:
                return False, "工作空间未初始化"

            mount_dir = current_build_path / "mount"
            if not mount_dir.exists() or not list(mount_dir.iterdir()):
                logger.warning("WinPE镜像未挂载，跳过语言配置")
                return True, "镜像未挂载，跳过语言配置"

            # 获取当前语言设置
            current_language = self.config.get("winpe.language", "en-US")
            logger.info(f"🌐 配置WinPE系统语言设置: {current_language}")

            # 语言映射到DISM参数
            language_mapping = {
                "zh-CN": {
                    "syslocale": "zh-CN",
                    "userlocale": "zh-CN",
                    "inputlocale": "0804:00000804"
                },
                "zh-TW": {
                    "syslocale": "zh-TW",
                    "userlocale": "zh-TW",
                    "inputlocale": "0404:00000404"
                },
                "zh-HK": {
                    "syslocale": "zh-HK",
                    "userlocale": "zh-HK",
                    "inputlocale": "0C04:00000C04"
                },
                "ja-JP": {
                    "syslocale": "ja-JP",
                    "userlocale": "ja-JP",
                    "inputlocale": "0411:00000411"
                },
                "ko-KR": {
                    "syslocale": "ko-KR",
                    "userlocale": "ko-KR",
                    "inputlocale": "0412:00000412"
                },
                "en-US": {
                    "syslocale": "en-US",
                    "userlocale": "en-US",
                    "inputlocale": "0409:00000409"
                }
            }

            lang_config = language_mapping.get(current_language, language_mapping["en-US"])

            logger.info(f"   设置系统区域: {lang_config['syslocale']}")
            logger.info(f"   设置用户区域: {lang_config['userlocale']}")
            logger.info(f"   设置输入法: {lang_config['inputlocale']}")

            # 使用DISM设置系统语言
            # DISM语言设置命令需要指定镜像路径
            mount_dir_str = str(mount_dir)
            dism_commands = [
                ["/image:" + mount_dir_str, "/set-syslocale:" + lang_config["syslocale"]],
                ["/image:" + mount_dir_str, "/set-userlocale:" + lang_config["userlocale"]],
                ["/image:" + mount_dir_str, "/set-inputlocale:" + lang_config["inputlocale"]]
            ]

            success_count = 0
            for cmd_args in dism_commands:
                try:
                    logger.info(f"   执行DISM命令: {' '.join(cmd_args)}")
                    success, stdout, stderr = self.adk.run_dism_command(cmd_args)

                    if success:
                        success_count += 1
                        logger.info(f"   ✅ 语言设置命令成功: {cmd_args[1]}")
                    else:
                        logger.warning(f"   ⚠️ 语言设置命令失败: {cmd_args[1]} - {stderr}")

                except Exception as e:
                    logger.error(f"   ❌ 执行语言设置命令时发生错误: {str(e)}")

            if success_count == len(dism_commands):
                logger.info(f"✅ WinPE语言配置完成: {current_language}")
                return True, f"语言配置成功: {current_language}"
            elif success_count > 0:
                logger.warning(f"⚠️ WinPE语言配置部分完成: {success_count}/{len(dism_commands)} 个命令成功")
                return True, f"语言配置部分完成: {success_count}/{len(dism_commands)} 个命令成功"
            else:
                logger.error(f"❌ WinPE语言配置失败")
                return False, "语言配置失败"

        except Exception as e:
            error_msg = f"配置语言设置时发生错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def get_supported_languages(self) -> List[Dict[str, Any]]:
        """获取支持的语言列表

        Returns:
            List[Dict[str, Any]]: 支持的语言列表
        """
        try:
            supported_languages = [
                {
                    "code": "zh-CN",
                    "name": "中文(简体)",
                    "display_name": "Chinese (Simplified)",
                    "syslocale": "zh-CN",
                    "userlocale": "zh-CN",
                    "inputlocale": "0804:00000804"
                },
                {
                    "code": "zh-TW",
                    "name": "中文(繁体)",
                    "display_name": "Chinese (Traditional)",
                    "syslocale": "zh-TW",
                    "userlocale": "zh-TW",
                    "inputlocale": "0404:00000404"
                },
                {
                    "code": "zh-HK",
                    "name": "中文(香港)",
                    "display_name": "Chinese (Hong Kong)",
                    "syslocale": "zh-HK",
                    "userlocale": "zh-HK",
                    "inputlocale": "0C04:00000C04"
                },
                {
                    "code": "ja-JP",
                    "name": "日本語",
                    "display_name": "Japanese",
                    "syslocale": "ja-JP",
                    "userlocale": "ja-JP",
                    "inputlocale": "0411:00000411"
                },
                {
                    "code": "ko-KR",
                    "name": "한국어",
                    "display_name": "Korean",
                    "syslocale": "ko-KR",
                    "userlocale": "ko-KR",
                    "inputlocale": "0412:00000412"
                },
                {
                    "code": "en-US",
                    "name": "English",
                    "display_name": "English (United States)",
                    "syslocale": "en-US",
                    "userlocale": "en-US",
                    "inputlocale": "0409:00000409"
                }
            ]

            return supported_languages

        except Exception as e:
            logger.error(f"获取支持的语言列表时发生错误: {str(e)}")
            return []

    def get_language_packages(self, language_code: str) -> List[str]:
        """获取指定语言所需的包列表

        Args:
            language_code: 语言代码

        Returns:
            List[str]: 所需的包列表
        """
        try:
            from core.winpe_packages import WinPEPackages
            winpe_packages = WinPEPackages()
            return winpe_packages.get_language_packages(language_code)
        except Exception as e:
            logger.error(f"获取语言包列表时发生错误: {str(e)}")
            return []

    def validate_language_code(self, language_code: str) -> bool:
        """验证语言代码是否有效

        Args:
            language_code: 语言代码

        Returns:
            bool: 是否有效
        """
        try:
            supported_languages = self.get_supported_languages()
            return any(lang["code"] == language_code for lang in supported_languages)
        except Exception as e:
            logger.error(f"验证语言代码时发生错误: {str(e)}")
            return False

    def create_language_config_file(self, current_build_path: Path, language_code: str) -> Tuple[bool, str]:
        """创建语言配置文件

        Args:
            current_build_path: 当前构建路径
            language_code: 语言代码

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not self.validate_language_code(language_code):
                return False, f"无效的语言代码: {language_code}"

            # 获取语言配置
            supported_languages = self.get_supported_languages()
            lang_config = None
            for lang in supported_languages:
                if lang["code"] == language_code:
                    lang_config = lang
                    break

            if not lang_config:
                return False, f"找不到语言配置: {language_code}"

            # 创建配置目录
            config_dir = current_build_path / "config"
            config_dir.mkdir(exist_ok=True)

            # 保存语言配置
            config_file = config_dir / "language_config.json"

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(lang_config, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ 语言配置文件已保存: {config_file}")
            return True, f"语言配置文件创建成功: {language_code}"

        except Exception as e:
            error_msg = f"创建语言配置文件时发生错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def apply_winpe_settings(self, current_build_path: Path) -> Tuple[bool, str]:
        """应用WinPE专用设置 - Microsoft官方标准配置

        Args:
            current_build_path: 当前构建路径

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not current_build_path:
                return False, "工作空间未初始化"

            logger.info("🔧 开始应用WinPE专用设置")

            # 从配置中读取WinPE专用设置
            enable_settings = self.config.get("winpe.enable_winpe_settings", True)
            if not enable_settings:
                logger.info("WinPE专用设置已禁用，跳过此步骤")
                return True, "WinPE专用设置已禁用"

            # WinPE标准配置
            winpe_config = {
                'scratch_space': self.config.get("winpe.scratch_space_mb", 128),  # 从配置读取
                'target_path': self.config.get("winpe.target_path", "X:"),      # 从配置读取
                'enable_winpe_networking': True,
                'enable_winpe_wmi': True,
                'enable_winpe_scripting': True
            }

            # copype模式下，WIM文件位于 media/sources/boot.wim
            wim_file_path = current_build_path / "media" / "sources" / "boot.wim"
            # 获取挂载路径 (WIM文件所在目录 + /mount)
            mount_dir = wim_file_path.parent / "mount"
            if not mount_dir.exists():
                logger.info("WinPE镜像未挂载，尝试挂载...")
                from .mount_manager import MountManager
                mount_manager = MountManager(self.config, self.adk, self.parent_callback)
                success, message = mount_manager.mount_winpe_image(wim_file_path)
                if not success:
                    logger.warning(f"无法挂载WinPE镜像: {message}")
                    # 继续执行其他设置

            # 设置暂存空间
            if mount_dir.exists():
                logger.info(f"设置WinPE暂存空间: {winpe_config['scratch_space']}MB")
                success, stdout, stderr = self.adk.run_dism_command([
                    '/Image:' + str(mount_dir),
                    f'/Set-ScratchSpace:{winpe_config["scratch_space"]}'
                ])

                if success:
                    logger.info(f"✅ 暂存空间设置成功: {winpe_config['scratch_space']}MB")
                else:
                    logger.warning(f"⚠️ 暂存空间设置失败: {stderr}")

                # 设置目标路径
                target_path = winpe_config['target_path']
                logger.info(f"设置WinPE目标路径: {target_path}")
                
                # 验证目标路径格式
                if not target_path or not target_path.endswith(':'):
                    logger.warning(f"⚠️ 目标路径格式无效: {target_path}，跳过此设置")
                else:
                    success, stdout, stderr = self.adk.run_dism_command([
                        '/Image:' + str(mount_dir),
                        f'/Set-TargetPath:{target_path}'
                    ])

                    if success:
                        logger.info(f"✅ 目标路径设置成功: {target_path}")
                    else:
                        logger.warning(f"⚠️ 目标路径设置失败: {stderr}")
                        # 如果设置失败，这不是致命错误，继续执行其他设置
                        logger.info("ℹ️ 目标路径设置失败不会影响WinPE的正常功能")

            # 配置WinPE启动参数
            self._configure_winpe_boot_settings(current_build_path, winpe_config)

            # 创建WinPE专用配置文件
            self._create_winpe_config_files(current_build_path, winpe_config)

            logger.info("✅ WinPE专用设置应用完成")
            return True, "WinPE专用设置应用成功"

        except Exception as e:
            error_msg = f"应用WinPE设置失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _configure_winpe_boot_settings(self, current_build_path: Path, config: dict) -> None:
        """配置WinPE启动设置"""
        try:
            logger.info("配置WinPE启动设置...")

            # 创建WinPE启动配置文件
            media_path = current_build_path / "media"

            # 创建WinPE启动脚本（可选）
            winstart_path = media_path / "Windows" / "System32" / "winpe.cmd"
            if winstart_path.parent.exists():
                winstart_content = '''@echo off
REM WinPE启动脚本
echo 正在启动Windows PE环境...
REM 自定义启动命令可以添加在这里
'''
                try:
                    with open(winstart_path, 'w', encoding='utf-8') as f:
                        f.write(winstart_content)
                    logger.info("✅ WinPE启动脚本已创建")
                except Exception as e:
                    logger.warning(f"创建WinPE启动脚本失败: {e}")

        except Exception as e:
            logger.error(f"配置WinPE启动设置失败: {e}")

    def _create_winpe_config_files(self, current_build_path: Path, config: dict) -> None:
        """创建WinPE配置文件"""
        try:
            logger.info("创建WinPE配置文件...")

            # 创建配置目录
            config_dir = current_build_path / "config"
            config_dir.mkdir(exist_ok=True)

            # 保存WinPE配置
            config_file = config_dir / "winpe_settings.json"

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ WinPE配置文件已保存: {config_file}")

        except Exception as e:
            logger.error(f"创建WinPE配置文件失败: {e}")

    def get_current_language_config(self) -> Optional[Dict[str, Any]]:
        """获取当前语言配置

        Returns:
            Optional[Dict[str, Any]]: 当前语言配置，如果找不到则返回None
        """
        try:
            current_language = self.config.get("winpe.language", "en-US")
            supported_languages = self.get_supported_languages()
            
            for lang in supported_languages:
                if lang["code"] == current_language:
                    return lang
            
            return None

        except Exception as e:
            logger.error(f"获取当前语言配置时发生错误: {str(e)}")
            return None

    def set_language(self, language_code: str) -> Tuple[bool, str]:
        """设置系统语言

        Args:
            language_code: 语言代码

        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        try:
            if not self.validate_language_code(language_code):
                return False, f"无效的语言代码: {language_code}"

            # 更新配置
            self.config.set("winpe.language", language_code)
            
            logger.info(f"语言设置已更新为: {language_code}")
            return True, f"语言设置成功: {language_code}"

        except Exception as e:
            error_msg = f"设置语言时发生错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
