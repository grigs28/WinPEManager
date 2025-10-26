#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinPE可选组件数据模块
包含所有WinPE可选组件的详细信息和树形结构
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger("WinPEManager")


@dataclass
class OptionalComponent:
    """可选组件数据类"""
    name: str  # 组件名称
    package_name: str  # 包名称
    description: str  # 描述
    category: str  # 分类
    icon: str  # 图标名称
    dependencies: List[str]  # 依赖的包
    features: List[str]  # 提供的功能
    tooltip: str  # 鼠标提示
    selected: bool = False  # 是否选中
    source: str = "official"  # 组件来源：official（官方）或 external（外部）


class WinPEPackages:
    """WinPE可选组件管理器"""

    def __init__(self):
        self.components = self._build_components_tree()

    def _build_components_tree(self) -> Dict[str, OptionalComponent]:
        """构建组件树形结构"""
        components = {}

        # 基础平台组件 - Microsoft官方组件
        components["WinPE-WMI"] = OptionalComponent(
            name="Windows Management Instrumentation",
            package_name="WinPE-WMI",
            description="提供WMI服务支持，用于系统管理和监控",
            category="基础平台",
            icon="🔧",
            dependencies=[],
            features=["系统信息查询", "硬件检测", "事件日志管理", "注册表操作"],
            tooltip="Windows Management Instrumentation (WMI)\nMicrosoft官方组件\n提供系统管理和监控功能\n依赖项：无\n用途：系统检测、硬件管理、日志记录",
            source="official"
        )

        components["WinPE-SecureStartup"] = OptionalComponent(
            name="安全启动",
            package_name="WinPE-SecureStartup",
            description="支持BitLocker和UEFI安全启动",
            category="基础平台",
            icon="🔐",
            dependencies=["WinPE-WMI"],
            features=["BitLocker加密", "UEFI安全启动", "启动验证", "安全策略"],
            tooltip="安全启动支持\nMicrosoft官方组件\n提供BitLocker和UEFI安全启动功能\n依赖项：WinPE-WMI\n用途：安全加密、启动验证、UEFI支持",
            source="official"
        )

        components["WinPE-PlatformID"] = OptionalComponent(
            name="平台标识",
            package_name="WinPE-PlatformID",
            description="识别系统平台和版本信息",
            category="基础平台",
            icon="🏷",
            dependencies=["WinPE-WMI"],
            features=["平台识别", "版本检测", "系统信息"],
            tooltip="平台标识符\nMicrosoft官方组件\n用于识别WinPE系统版本和平台信息\n依赖项：WinPE-WMI\n用途：系统识别、版本检测",
            source="official"
        )

        # 脚本和自动化组件 - Microsoft官方组件
        components["WinPE-Scripting"] = OptionalComponent(
            name="脚本引擎",
            package_name="WinPE-Scripting",
            description="支持VBScript和JScript脚本执行",
            category="脚本与自动化",
            icon="📜",
            dependencies=[],
            features=["VBScript支持", "JScript支持", "自动化脚本"],
            tooltip="脚本引擎\nMicrosoft官方组件\n提供VBScript和JScript执行环境\n依赖项：无\n用途：自动化脚本、批处理、定制化",
            source="official"
        )

        components["WinPE-HTA"] = OptionalComponent(
            name="HTML应用程序",
            package_name="WinPE-HTA",
            description="支持HTML应用程序运行",
            category="脚本与自动化",
            icon="🌐",
            dependencies=["WinPE-Scripting"],
            features=["HTA应用", "HTML界面", "交互式应用"],
            tooltip="HTML应用程序 (HTA)\nMicrosoft官方组件\n支持HTML应用程序的创建和运行\n依赖项：WinPE-Scripting\n用途：GUI应用、交互界面、自定义工具",
            source="official"
        )

        # PowerShell相关 - Microsoft官方组件
        components["WinPE-PowerShell"] = OptionalComponent(
            name="Windows PowerShell",
            package_name="WinPE-PowerShell",
            description="提供完整的PowerShell环境",
            category="脚本与自动化",
            icon="💻",
            dependencies=["WinPE-WMI"],
            features=["PowerShell命令", "cmdlet支持", "脚本执行"],
            tooltip="Windows PowerShell\nMicrosoft官方组件\n提供完整的PowerShell命令行环境\n依赖项：WinPE-WMI\n用途：系统管理、自动化、脚本编程",
            source="official"
        )

        components["WinPE-DismCmdlets"] = OptionalComponent(
            name="DISM命令行工具",
            package_name="WinPE-DismCmdlets",
            description="DISM PowerShell命令行工具",
            category="脚本与自动化",
            icon="⚙",
            dependencies=["WinPE-PowerShell"],
            features=["DISM cmdlet", "镜像管理", "包管理"],
            tooltip="DISM命令行工具\nMicrosoft官方组件\n提供PowerShell中的DISM命令支持\n依赖项：WinPE-PowerShell\n用途：系统管理、镜像处理、包管理",
            source="official"
        )

        # .NET Framework相关
        # .NET Framework相关 - Microsoft官方组件
        components["WinPE-NetFx"] = OptionalComponent(
            name=".NET Framework",
            package_name="WinPE-NetFx",
            description=".NET Framework 2.0/3.5运行时",
            category=".NET Framework",
            icon="🔮",
            dependencies=[],
            features=[".NET 2.0", ".NET 3.5", "应用程序运行"],
            tooltip=".NET Framework\nMicrosoft官方组件\n提供.NET Framework 2.0/3.5运行环境\n依赖项：无\n用途：.NET应用程序运行、框架支持",
            source="official"
        )

        # ========== 外部/第三方组件 ==========
        # 这些组件不在Microsoft官方可选组件列表中，但常用于WinPE环境

        components["ThirdParty-7Zip"] = OptionalComponent(
            name="7-Zip压缩工具",
            package_name="ThirdParty-7Zip",
            description="开源压缩解压工具，支持多种格式",
            category="文件管理工具",
            icon="📦",
            dependencies=[],
            features=["压缩文件", "解压缩", "多格式支持", "命令行版本"],
            tooltip="7-Zip压缩工具\n第三方开源组件\n提供强大的压缩解压功能\n依赖项：无\n用途：文件压缩、备份、存档管理",
            source="external"
        )

        components["ThirdParty-NotepadPlus"] = OptionalComponent(
            name="Notepad++编辑器",
            package_name="ThirdParty-NotepadPlus",
            description="功能强大的文本编辑器",
            category="文件管理工具",
            icon="📝",
            dependencies=[],
            features=["语法高亮", "多标签页", "插件支持", "多编码支持"],
            tooltip="Notepad++编辑器\n第三方开源组件\n专业的文本和代码编辑器\n依赖项：无\n用途：编辑配置文件、查看日志、代码开发",
            source="external"
        )

        components["ThirdParty-ProcessExplorer"] = OptionalComponent(
            name="Process Explorer",
            package_name="ThirdParty-ProcessExplorer",
            description="Windows任务管理器的增强版",
            category="系统工具",
            icon="🔍",
            dependencies=[],
            features=["进程监控", "DLL查看", "句柄分析", "性能监控"],
            tooltip="Process Explorer\nMicrosoft Sysinternals工具\n高级进程和系统资源监控工具\n依赖项：无\n用途：进程分析、系统诊断、故障排除",
            source="external"
        )

        components["ThirdParty-TotalCommander"] = OptionalComponent(
            name="Total Commander",
            package_name="ThirdParty-TotalCommander",
            description="双面板文件管理器",
            category="文件管理工具",
            icon="🗂️",
            dependencies=[],
            features=["双面板显示", "文件同步", "压缩包支持", "FTP客户端"],
            tooltip="Total Commander\n第三方商业组件\n经典的文件管理器\n依赖项：无\n用途：文件管理、批量操作、网络传输",
            source="external"
        )

        components["ThirdParty-ExplorerPlus"] = OptionalComponent(
            name="Explorer++",
            package_name="ThirdParty-ExplorerPlus",
            description="轻量级文件管理器",
            category="文件管理工具",
            icon="📁",
            dependencies=[],
            features=["标签页浏览", "文件预览", "书签功能", "插件支持"],
            tooltip="Explorer++\n第三方开源组件\n轻量级文件管理器\n依赖项：无\n用途：文件浏览、简单管理、系统维护",
            source="external"
        )

        components["ThirdParty-VLC"] = OptionalComponent(
            name="VLC媒体播放器",
            package_name="ThirdParty-VLC",
            description="开源媒体播放器",
            category="媒体工具",
            icon="🎬",
            dependencies=[],
            features=["视频播放", "音频播放", "字幕支持", "格式兼容"],
            tooltip="VLC媒体播放器\n第三方开源组件\n功能全面的媒体播放器\n依赖项：无\n用途：多媒体文件播放、格式转换",
            source="external"
        )

        components["ThirdParty-DiskGenius"] = OptionalComponent(
            name="DiskGenius磁盘工具",
            package_name="ThirdParty-DiskGenius",
            description="集成磁盘分区管理和数据恢复工具",
            category="系统工具",
            icon="💿",
            dependencies=[],
            features=["分区管理", "数据恢复", "磁盘克隆", "备份还原"],
            tooltip="DiskGenius磁盘工具\n第三方商业组件\n专业的磁盘管理和数据恢复工具\n依赖项：无\n用途：分区操作、数据恢复、系统备份",
            source="external"
        )

        components["ThirdParty-WiFiTool"] = OptionalComponent(
            name="WiFi连接工具",
            package_name="ThirdParty-WiFiTool",
            description="WiFi网络连接和配置工具",
            category="网络工具",
            icon="📶",
            dependencies=[],
            features=["WiFi扫描", "网络连接", "密码管理", "信号分析"],
            tooltip="WiFi连接工具\n第三方组件\nWiFi网络连接和配置管理\n依赖项：无\n用途：无线网络连接、热点管理、网络诊断",
            source="external"
        )

        components["ThirdParty-RemoteDesktop"] = OptionalComponent(
            name="远程桌面工具",
            package_name="ThirdParty-RemoteDesktop",
            description="远程桌面连接和管理工具",
            category="网络工具",
            icon="🖥️",
            dependencies=[],
            features=["远程连接", "桌面控制", "文件传输", "会话管理"],
            tooltip="远程桌面工具\n第三方组件\n远程桌面连接和管理功能\n依赖项：无\n用途：远程协助、系统管理、技术支持",
            source="external"
        )

        components["ThirdParty-Browser"] = OptionalComponent(
            name="轻量级浏览器",
            package_name="ThirdParty-Browser",
            description="适用于WinPE的网页浏览器",
            category="网络工具",
            icon="🌐",
            dependencies=[],
            features=["网页浏览", "下载管理", "书签功能", "基本设置"],
            tooltip="轻量级浏览器\n第三方组件\n适用于WinPE环境的网页浏览器\n依赖项：无\n用途：网页访问、在线资源、文档查阅",
            source="external"
        )

        # 恢复环境组件 - Microsoft官方组件
        components["WinPE-WinRE"] = OptionalComponent(
            name="Windows恢复环境",
            package_name="WinPE-WinRE",
            description="提供系统恢复和修复功能",
            category="恢复环境",
            icon="🛠️",
            dependencies=[],
            features=["系统恢复", "故障排除", "命令行修复"],
            tooltip="Windows恢复环境 (WinRE)\nMicrosoft官方组件\n提供系统恢复和故障排除功能\n依赖项：无\n用途：系统修复、故障诊断、恢复操作",
            source="official"
        )

        components["WinPE-Storage"] = OptionalComponent(
            name="存储管理",
            package_name="WinPE-Storage",
            description="提供磁盘分区和存储管理",
            category="恢复环境",
            icon="💾",
            dependencies=[],
            features=["磁盘分区", "存储管理", "DISM工具"],
            tooltip="存储管理\nMicrosoft官方组件\n提供磁盘分区和存储管理功能\n依赖项：无\n用途：磁盘操作、分区管理、存储工具",
            source="official"
        )

        # 网络和连接组件 - Microsoft官方组件
        components["WinPE-NDIS"] = OptionalComponent(
            name="网络驱动程序接口规范",
            package_name="WinPE-NDIS",
            description="支持网络驱动程序",
            category="网络连接",
            icon="🌐",
            dependencies=[],
            features=["NDIS驱动", "网络连接", "无线支持"],
            tooltip="网络驱动程序接口规范(NDIS)\nMicrosoft官方组件\n支持网络驱动程序的安装和使用\n依赖项：无\n用途：网络连接、驱动安装、网络功能",
            source="official"
        )

        components["WinPE-WLAN"] = OptionalComponent(
            name="无线局域网",
            package_name="WinPE-WLAN",
            description="支持无线网络连接",
            category="网络连接",
            icon="📶",
            dependencies=["WinPE-WMI"],
            features=["WIFI支持", "无线连接", "网络配置"],
            tooltip="无线局域网(WLAN)\nMicrosoft官方组件\n提供无线网络连接和配置功能\n依赖项：WinPE-WMI\n用途：无线网络、WIFI连接、网络配置",
            source="official"
        )

        # 诊断和工具组件 - Microsoft官方组件
        components["WinPE-Dot3Svc"] = OptionalComponent(
            name="DirectX诊断服务",
            package_name="WinPE-Dot3Svc",
            description="DirectX诊断和支持",
            category="诊断工具",
            icon="🎮",
            dependencies=[],
            features=["DirectX诊断", "图形支持", "硬件测试"],
            tooltip="DirectX诊断服务\nMicrosoft官方组件\n提供DirectX图形支持和诊断功能\n依赖项：无\n用途：图形应用、硬件测试、诊断工具",
            source="official"
        )

        components["WinPE-RSAT"] = OptionalComponent(
            name="远程服务器管理工具",
            package_name="WinPE-RSAT",
            description="远程服务器管理工具包",
            category="诊断工具",
            icon="🖥",
            dependencies=[],
            features=["服务器管理", "远程工具", "活动目录"],
            tooltip="远程服务器管理工具(RSAT)\nMicrosoft官方组件\n提供服务器管理和远程连接工具\n依赖项：无\n用途：服务器管理、远程连接、活动目录",
            source="official"
        )

        # 安全和防护组件
        components["WinPE-EnhancedStorage"] = OptionalComponent(
            name="增强存储",
            package_name="WinPE-EnhancedStorage",
            description="BitLocker增强存储功能",
            category="安全防护",
            icon="🔐",
            dependencies=["WinPE-WMI", "WinPE-SecureStartup"],
            features=["BitLocker管理", "存储安全", "加密支持"],
            tooltip="增强存储\n提供BitLocker相关的高级存储功能\n依赖项：WinPE-WMI, WinPE-SecureStartup\n用途：加密管理、存储安全、BitLocker"
        )

        # 数据访问组件
        components["WinPE-MDAC"] = OptionalComponent(
            name="Microsoft数据访问组件",
            package_name="WinPE-MDAC",
            description="支持ODBC、OLE DB和ADO数据访问",
            category="数据访问",
            icon="🗄️",
            dependencies=["WinPE-WMI"],
            features=["ODBC支持", "OLE DB支持", "ADO数据对象", "数据库连接"],
            tooltip="Microsoft数据访问组件(MDAC)\n提供ODBC、OLE DB和ADO数据访问支持\n依赖项：WinPE-WMI\n用途：数据库连接、数据访问、企业应用"
        )

        # 附加设置组件
        components["WinPE-Setup-Server"] = OptionalComponent(
            name="服务器设置支持",
            package_name="WinPE-Setup-Server",
            description="服务器设置功能程序包",
            category="服务器支持",
            icon="🖥️",
            dependencies=["WinPE-WMI", "WinPE-Scripting"],
            features=["服务器安装", "网络部署", "远程安装", "批量部署"],
            tooltip="服务器设置支持\n提供服务器安装和部署功能\n依赖项：WinPE-WMI, WinPE-Scripting\n用途：服务器部署、网络安装、批量部署"
        )

        # 启动选项组件
        components["WinPE-SecureBoot"] = OptionalComponent(
            name="安全启动支持",
            package_name="WinPE-SecureBoot",
            description="UEFI安全启动验证支持",
            category="安全防护",
            icon="🛡️",
            dependencies=["WinPE-SecureStartup", "WinPE-WMI"],
            features=["UEFI安全启动", "启动验证", "安全策略", "固件验证"],
            tooltip="安全启动支持\n提供UEFI安全启动和验证功能\n依赖项：WinPE-SecureStartup, WinPE-WMI\n用途：安全启动、固件验证、系统完整性"
        )

        # 恢复工具组件
        components["WinPE-Recovery"] = OptionalComponent(
            name="系统恢复工具",
            package_name="WinPE-Recovery",
            description="完整的系统恢复和修复工具集",
            category="恢复环境",
            icon="🔧",
            dependencies=["WinPE-WinRE", "WinPE-WMI"],
            features=["系统还原", "故障排除", "启动修复", "系统映像恢复"],
            tooltip="系统恢复工具\n提供完整的系统恢复和修复功能\n依赖项：WinPE-WinRE, WinPE-WMI\n用途：系统还原、故障修复、启动问题解决"
        )

        # 文件管理API组件
        components["WinPE-FMAPI"] = OptionalComponent(
            name="文件管理API",
            package_name="WinPE-FMAPI",
            description="文件管理API支持",
            category="基础平台",
            icon="📁",
            dependencies=["WinPE-WMI"],
            features=["文件管理", "API支持", "文件操作"],
            tooltip="文件管理API\n提供文件管理相关的API支持\n依赖项：WinPE-WMI\n用途：文件操作、API调用、文件管理"
        )

        # 字体支持组件
        components["WinPE-Fonts-Legacy"] = OptionalComponent(
            name="旧版字体支持",
            package_name="WinPE-Fonts-Legacy",
            description="旧版应用程序字体支持",
            category="字体支持",
            icon="🔤",
            dependencies=[],
            features=["旧版字体", "应用程序兼容", "字符显示"],
            tooltip="旧版字体支持\n为旧版应用程序提供字体支持\n依赖项：无\n用途：旧版应用兼容、字符显示"
        )

        components["WinPE-FontSupport-WinRE"] = OptionalComponent(
            name="Windows恢复字体",
            package_name="WinPE-FontSupport-WinRE",
            description="Windows恢复环境字体支持",
            category="字体支持",
            icon="🔤",
            dependencies=["WinPE-WinRE"],
            features=["恢复环境字体", "界面显示", "多语言支持"],
            tooltip="Windows恢复字体\n为Windows恢复环境提供字体支持\n依赖项：WinPE-WinRE\n用途：恢复环境界面显示、多语言支持"
        )

        # 亚洲字体支持
        components["WinPE-FontSupport-JA-JP"] = OptionalComponent(
            name="日语字体支持",
            package_name="WinPE-FontSupport-JA-JP",
            description="日语环境字体支持",
            category="字体支持",
            icon="🇯🇵",
            dependencies=["WinPE-Fonts-Legacy"],
            features=["日语显示", "日文界面", "字符集支持"],
            tooltip="日语字体支持\n为日语环境提供字体和字符显示支持\n依赖项：WinPE-Fonts-Legacy\n用途：日语环境、日文应用显示"
        )

        components["WinPE-FontSupport-KO-KR"] = OptionalComponent(
            name="韩语字体支持",
            package_name="WinPE-FontSupport-KO-KR",
            description="韩语环境字体支持",
            category="字体支持",
            icon="🇰🇷",
            dependencies=["WinPE-Fonts-Legacy"],
            features=["韩语显示", "韩文界面", "字符集支持"],
            tooltip="韩语字体支持\n为韩语环境提供字体和字符显示支持\n依赖项：WinPE-Fonts-Legacy\n用途：韩语环境、韩文应用显示"
        )

        components["WinPE-FontSupport-ZH-CN"] = OptionalComponent(
            name="简体中文字体支持",
            package_name="WinPE-FontSupport-ZH-CN",
            description="简体中文环境字体支持",
            category="字体支持",
            icon="🇨🇳",
            dependencies=["WinPE-Fonts-Legacy"],
            features=["中文显示", "中文界面", "字符集支持"],
            tooltip="简体中文字体支持\n为简体中文环境提供字体和字符显示支持\n依赖项：WinPE-Fonts-Legacy\n用途：中文环境、简体中文应用显示"
        )

        components["WinPE-FontSupport-ZH-TW"] = OptionalComponent(
            name="繁体中文字体支持",
            package_name="WinPE-FontSupport-ZH-TW",
            description="繁体中文环境字体支持",
            category="字体支持",
            icon="🇹🇼",
            dependencies=["WinPE-Fonts-Legacy"],
            features=["繁体中文显示", "繁体中文界面", "字符集支持"],
            tooltip="繁体中文字体支持\n为繁体中文环境提供字体和字符显示支持\n依赖项：WinPE-Fonts-Legacy\n用途：繁体中文环境、繁体中文应用显示"
        )

        components["WinPE-FontSupport-ZH-HK"] = OptionalComponent(
            name="香港中文字体支持",
            package_name="WinPE-FontSupport-ZH-HK",
            description="香港中文环境字体支持",
            category="字体支持",
            icon="🇭🇰",
            dependencies=["WinPE-Fonts-Legacy"],
            features=["香港中文显示", "香港中文界面", "字符集支持"],
            tooltip="香港中文字体支持\n为香港中文环境提供字体和字符显示支持\n依赖项：WinPE-Fonts-Legacy\n用途：香港中文环境、香港中文应用显示"
        )

        # 游戏外设支持
        components["WinPE-GamingPeripherals"] = OptionalComponent(
            name="游戏外设支持",
            package_name="WinPE-GamingPeripherals",
            description="游戏控制器和外设支持",
            category="硬件支持",
            icon="🎮",
            dependencies=["WinPE-WMI"],
            features=["游戏手柄", "外设驱动", "控制器支持"],
            tooltip="游戏外设支持\n提供游戏控制器和外设的驱动支持\n依赖项：WinPE-WMI\n用途：游戏手柄、外设设备、控制器"
        )

        # 网络协议支持
        components["WinPE-PPPoE"] = OptionalComponent(
            name="PPPoE协议支持",
            package_name="WinPE-PPPoE",
            description="点对点以太网协议支持",
            category="网络连接",
            icon="🌐",
            dependencies=["WinPE-NDIS"],
            features=["PPPoE连接", "宽带拨号", "网络认证"],
            tooltip="PPPoE协议支持\n提供点对点以太网协议连接支持\n依赖项：WinPE-NDIS\n用途：宽带拨号、网络认证、PPPoE连接"
        )

        components["WinPE-RNDIS"] = OptionalComponent(
            name="远程网络驱动接口",
            package_name="WinPE-RNDIS",
            description="远程网络驱动接口规范支持",
            category="网络连接",
            icon="🔗",
            dependencies=["WinPE-NDIS"],
            features=["RNDIS连接", "USB网络", "远程驱动"],
            tooltip="远程网络驱动接口\n提供USB网络连接和远程驱动支持\n依赖项：WinPE-NDIS\n用途：USB网络适配器、远程网络连接"
        )

        # 安全启动命令行工具
        components["WinPE-SecureBootCmdlets"] = OptionalComponent(
            name="安全启动命令行工具",
            package_name="WinPE-SecureBootCmdlets",
            description="安全启动相关的PowerShell命令",
            category="安全防护",
            icon="🛡️",
            dependencies=["WinPE-PowerShell", "WinPE-SecureStartup"],
            features=["安全启动命令", "PowerShell管理", "启动策略"],
            tooltip="安全启动命令行工具\n提供安全启动相关的PowerShell命令\n依赖项：WinPE-PowerShell, WinPE-SecureStartup\n用途：安全启动管理、PowerShell命令"
        )

        # 旧版安装支持
        components["WinPE-LegacySetup"] = OptionalComponent(
            name="旧版安装支持",
            package_name="WinPE-LegacySetup",
            description="旧版Windows安装程序支持",
            category="部署工具",
            icon="📀",
            dependencies=["WinPE-WMI", "WinPE-Scripting"],
            features=["旧版安装", "兼容性支持", "部署工具"],
            tooltip="旧版安装支持\n为旧版Windows安装程序提供支持\n依赖项：WinPE-WMI, WinPE-Scripting\n用途：旧版系统安装、兼容性部署"
        )

        # 存储WMI组件
        components["WinPE-StorageWMI"] = OptionalComponent(
            name="存储管理WMI",
            package_name="WinPE-StorageWMI",
            description="存储设备的WMI管理支持",
            category="诊断工具",
            icon="💾",
            dependencies=["WinPE-WMI", "WinPE-Storage"],
            features=["存储WMI", "磁盘管理", "存储查询"],
            tooltip="存储管理WMI\n提供存储设备的WMI查询和管理功能\n依赖项：WinPE-WMI, WinPE-Storage\n用途：存储管理、磁盘查询、WMI存储"
        )

        # Windows部署服务工具
        components["WinPE-WDS-Tools"] = OptionalComponent(
            name="Windows部署服务工具",
            package_name="WinPE-WDS-Tools",
            description="Windows部署服务相关工具",
            category="部署工具",
            icon="🚀",
            dependencies=["WinPE-WMI", "WinPE-NDIS"],
            features=["WDS部署", "网络安装", "远程部署"],
            tooltip="Windows部署服务工具\n提供Windows部署服务的客户端工具\n依赖项：WinPE-WMI, WinPE-NDIS\n用途：网络部署、WDS客户端、远程安装"
        )

        # Windows恢复配置
        components["WinPE-WinReCfg"] = OptionalComponent(
            name="Windows恢复配置",
            package_name="WinPE-WinReCfg",
            description="Windows恢复环境配置工具",
            category="恢复环境",
            icon="⚙️",
            dependencies=["WinPE-WinRE", "WinPE-WMI"],
            features=["恢复配置", "恢复选项", "环境设置"],
            tooltip="Windows恢复配置\n提供Windows恢复环境的配置管理\n依赖项：WinPE-WinRE, WinPE-WMI\n用途：恢复环境配置、恢复选项设置"
        )

        return components

    def get_component_tree(self) -> Dict[str, List[str]]:
        """
        获取按分类组织的组件树结构

        Returns:
            Dict[str, List[str]]: 分类到组件名称的映射
        """
        categories = {
            "🔧 Microsoft官方组件": {
                "基础平台": [
                    "WinPE-WMI",
                    "WinPE-SecureStartup",
                    "WinPE-PlatformID",
                    "WinPE-FMAPI"
                ],
                "脚本与自动化": [
                    "WinPE-Scripting",
                    "WinPE-HTA",
                    "WinPE-PowerShell",
                    "WinPE-DismCmdlets"
                ],
                ".NET Framework": [
                    "WinPE-NetFx"
                ],
                "恢复环境": [
                    "WinPE-WinRE",
                    "WinPE-Storage",
                    "WinPE-Recovery",
                    "WinPE-WinReCfg"
                ],
                "网络连接": [
                    "WinPE-NDIS",
                    "WinPE-WLAN",
                    "WinPE-PPPoE",
                    "WinPE-RNDIS"
                ],
                "诊断工具": [
                    "WinPE-Dot3Svc",
                    "WinPE-RSAT",
                    "WinPE-StorageWMI"
                ],
                "安全防护": [
                    "WinPE-EnhancedStorage",
                    "WinPE-SecureBoot",
                    "WinPE-SecureBootCmdlets"
                ],
                "数据访问": [
                    "WinPE-MDAC"
                ],
                "服务器支持": [
                    "WinPE-Setup-Server",
                    "WinPE-LegacySetup",
                    "WinPE-WDS-Tools"
                ],
                "硬件支持": [
                    "WinPE-GamingPeripherals"
                ],
                "字体支持": [
                    "WinPE-Fonts-Legacy",
                    "WinPE-FontSupport-WinRE",
                    "WinPE-FontSupport-JA-JP",
                    "WinPE-FontSupport-KO-KR",
                    "WinPE-FontSupport-ZH-CN",
                    "WinPE-FontSupport-ZH-TW",
                    "WinPE-FontSupport-ZH-HK"
                ]
            },
            "📦 外部/第三方组件": {
                "文件管理工具": [
                    "ThirdParty-7Zip",
                    "ThirdParty-NotepadPlus",
                    "ThirdParty-ExplorerPlus",
                    "ThirdParty-TotalCommander"
                ],
                "系统工具": [
                    "ThirdParty-ProcessExplorer",
                    "ThirdParty-DiskGenius"
                ],
                "网络工具": [
                    "ThirdParty-WiFiTool",
                    "ThirdParty-RemoteDesktop",
                    "ThirdParty-Browser"
                ],
                "媒体工具": [
                    "ThirdParty-VLC"
                ]
            }
        }

        return categories

    def get_dependencies(self, package_name: str) -> List[str]:
        """
        获取组件的依赖关系

        Args:
            package_name: 包名称

        Returns:
            List[str]: 依赖的包列表
        """
        if package_name in self.components:
            return self.components[package_name].dependencies
        return []

    def get_component_by_package_name(self, package_name: str) -> Optional[OptionalComponent]:
        """
        根据包名获取组件

        Args:
            package_name: 包名称

        Returns:
            OptionalComponent: 组件对象
        """
        return self.components.get(package_name)

    def search_components(self, keyword: str) -> List[OptionalComponent]:
        """
        搜索组件

        Args:
            keyword: 搜索关键词

        Returns:
            List[OptionalComponent]: 匹配的组件列表
        """
        keyword = keyword.lower()
        results = []

        for component in self.components.values():
            if (keyword in component.name.lower() or
                keyword in component.description.lower() or
                keyword in component.package_name.lower() or
                any(keyword in feature.lower() for feature in component.features)):
                results.append(component)

        return results

    def get_recommended_packages(self) -> List[str]:
        """
        获取推荐的包列表

        Returns:
            List[str]: 推荐的包名称列表
        """
        return [
            "WinPE-WMI",           # 基础管理
            "WinPE-PowerShell",     # 自动化
            "WinPE-DismCmdlets",   # 系统管理
            "WinPE-Scripting",      # 脚本支持
            "WinPE-WinRE"          # 恢复环境
        ]

    def get_categories_description(self) -> Dict[str, str]:
        """
        获取分类描述

        Returns:
            Dict[str, str]: 分类到描述的映射
        """
        return {
            "基础平台": "WinPE运行的基础平台组件，提供核心系统功能",
            "脚本与自动化": "脚本执行和自动化工具，支持批处理和脚本编程",
            ".NET Framework": ".NET Framework运行环境，支持.NET应用程序",
            "恢复环境": "系统恢复和故障排除工具",
            "网络连接": "网络连接和通信组件",
            "诊断工具": "系统诊断和硬件检测工具",
            "安全防护": "安全功能和加密组件",
            "数据访问": "数据库连接和数据访问组件",
            "服务器支持": "服务器部署和远程安装工具",
            "硬件支持": "特殊硬件设备驱动支持",
            "其他组件": "其他特殊功能组件"
        }

    def get_language_support_mapping(self) -> Dict[str, Dict[str, Any]]:
        """
        获取语言支持映射配置

        Returns:
            Dict[str, Dict[str, Any]]: 语言到相关组件的映射
        """
        return {
            "zh-CN": {
                "name": "简体中文",
                "packages": [
                    "WinPE-Fonts-Legacy",
                    "WinPE-FontSupport-ZH-CN"
                ],
                "description": "简体中文环境支持，包含中文字体和字符集"
            },
            "zh-TW": {
                "name": "繁体中文",
                "packages": [
                    "WinPE-Fonts-Legacy",
                    "WinPE-FontSupport-ZH-TW"
                ],
                "description": "繁体中文环境支持，包含繁体中文字体"
            },
            "zh-HK": {
                "name": "香港中文",
                "packages": [
                    "WinPE-Fonts-Legacy",
                    "WinPE-FontSupport-ZH-HK"
                ],
                "description": "香港中文环境支持，包含香港中文字体"
            },
            "ja-JP": {
                "name": "日语",
                "packages": [
                    "WinPE-Fonts-Legacy",
                    "WinPE-FontSupport-JA-JP"
                ],
                "description": "日语环境支持，包含日语字体和字符集"
            },
            "ko-KR": {
                "name": "韩语",
                "packages": [
                    "WinPE-Fonts-Legacy",
                    "WinPE-FontSupport-KO-KR"
                ],
                "description": "韩语环境支持，包含韩语字体和字符集"
            },
            "en-US": {
                "name": "英语",
                "packages": [],
                "description": "英语环境支持（默认，无需额外字体包）"
            }
        }

    def get_language_packages(self, language_code: str) -> List[str]:
        """
        获取指定语言所需的包列表

        Args:
            language_code: 语言代码

        Returns:
            List[str]: 包名称列表
        """
        language_mapping = self.get_language_support_mapping()
        language_info = language_mapping.get(language_code)

        if language_info:
            return language_info["packages"]
        return []

    def get_language_info(self, language_code: str) -> Optional[Dict[str, Any]]:
        """
        获取语言信息

        Args:
            language_code: 语言代码

        Returns:
            Optional[Dict[str, Any]]: 语言信息
        """
        language_mapping = self.get_language_support_mapping()
        return language_mapping.get(language_code)

    def get_available_languages(self) -> List[Dict[str, str]]:
        """
        获取可用语言列表

        Returns:
            List[Dict[str, str]]: 语言列表
        """
        language_mapping = self.get_language_support_mapping()
        languages = []

        for code, info in language_mapping.items():
            languages.append({
                "code": code,
                "name": info["name"],
                "description": info["description"]
            })

        return languages

    def get_component_count(self) -> int:
        """
        获取组件总数

        Returns:
            int: 组件总数
        """
        return len(self.components)

    def get_official_components(self) -> List[OptionalComponent]:
        """
        获取所有Microsoft官方组件

        Returns:
            List[OptionalComponent]: 官方组件列表
        """
        return [comp for comp in self.components.values() if comp.source == "official"]

    def get_external_components(self) -> List[OptionalComponent]:
        """
        获取所有外部/第三方组件

        Returns:
            List[OptionalComponent]: 外部组件列表
        """
        return [comp for comp in self.components.values() if comp.source == "external"]

    def get_components_by_source(self, source: str) -> List[OptionalComponent]:
        """
        根据来源获取组件列表

        Args:
            source: 组件来源（"official" 或 "external"）

        Returns:
            List[OptionalComponent]: 指定来源的组件列表
        """
        return [comp for comp in self.components.values() if comp.source == source]

    def get_source_statistics(self) -> Dict[str, int]:
        """
        获取组件来源统计信息

        Returns:
            Dict[str, int]: 各来源的组件数量统计
        """
        stats = {"official": 0, "external": 0}
        for comp in self.components.values():
            if comp.source in stats:
                stats[comp.source] += 1
        return stats