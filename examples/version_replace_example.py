#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinPE版本替换功能使用示例
演示如何使用版本替换器进行WinPE版本替换
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.version_replacer import VersionReplacer, ComponentAnalyzer, create_version_replace_config
from core.config_manager import ConfigManager
from core.adk_manager import ADKManager
from core.unified_manager.wim_manager import UnifiedWIMManager


def example_version_replace():
    """版本替换示例"""
    print("WinPE版本替换示例")
    print("=" * 50)

    # 1. 初始化管理器
    config_manager = ConfigManager()
    adk_manager = ADKManager()
    wim_manager = UnifiedWIMManager(config_manager, adk_manager)

    # 2. 创建版本替换器
    version_replacer = VersionReplacer(config_manager, adk_manager, wim_manager)

    # 3. 设置回调函数
    def progress_callback(percent: int, message: str):
        print(f"[{percent:3d}%] {message}")

    def log_callback(message: str, level: str):
        print(f"[{level.upper():<8}] {message}")

    version_replacer.set_progress_callback(progress_callback)
    version_replacer.set_log_callback(log_callback)

    # 4. 配置路径（根据实际情况修改）
    base_dir = Path("D:/APP/WinPEManager/WinPE_amd64")

    source_dir = base_dir / "0WIN11PE"    # 源目录
    target_dir = base_dir / "0WIN10OLD"   # 目标目录
    output_dir = base_dir / "WIN10REPLACED"  # 输出目录

    # 5. 创建配置
    config = create_version_replace_config(
        source_dir=str(source_dir),
        target_dir=str(target_dir),
        output_dir=str(output_dir),
        migrate_options={
            'migrate_external_programs': True,
            'migrate_startup_scripts': True,
            'migrate_drivers': True,
            'migrate_custom_components': True,
            'preserve_source_structure': True,
            'replace_core_files': False,
            'update_configurations': True
        }
    )

    # 6. 验证配置
    is_valid, errors = config.validate()
    if not is_valid:
        print("配置验证失败:")
        for error in errors:
            print(f"  - {error}")
        return False

    print("配置验证通过!")
    print(f"源目录: {config.source_dir}")
    print(f"目标目录: {config.target_dir}")
    print(f"输出目录: {config.output_dir}")
    print()

    # 7. 先分析差异（可选）
    print("分析组件差异...")
    try:
        analyzer = ComponentAnalyzer()
        source_mount = config.source_dir / "mount"
        target_mount = config.target_dir / "mount"

        if source_mount.exists() and target_mount.exists():
            analysis = analyzer.analyze_wim_differences(source_mount, target_mount)
            print("\n" + analyzer.generate_analysis_report(analysis))
        else:
            print("警告: 源或目标WIM未挂载，跳过差异分析")

    except Exception as e:
        print(f"差异分析失败: {str(e)}")

    print()

    # 8. 执行版本替换
    print("开始执行版本替换...")
    try:
        result = version_replacer.execute_version_replacement(config)

        if result["success"]:
            print("\n" + "=" * 50)
            print("版本替换成功完成!")
            print("=" * 50)
            print(version_replacer.generate_replacement_report(result))
            return True
        else:
            print("\n版本替换失败:")
            for error in result["errors"]:
                print(f"错误: {error}")
            for warning in result["warnings"]:
                print(f"警告: {warning}")
            return False

    except Exception as e:
        print(f"版本替换异常: {str(e)}")
        return False


def example_component_analysis():
    """组件分析示例"""
    print("\n组件分析示例")
    print("=" * 50)

    # 创建组件分析器
    analyzer = ComponentAnalyzer()

    # 配置路径
    base_dir = Path("D:/APP/WinPEManager/WinPE_amd64")
    source_mount = base_dir / "0WIN11PE" / "mount"
    target_mount = base_dir / "0WIN10OLD" / "mount"

    if not source_mount.exists() or not target_mount.exists():
        print("错误: 源或目标WIM未挂载")
        print(f"源挂载路径: {source_mount}")
        print(f"目标挂载路径: {target_mount}")
        return

    try:
        # 执行分析
        analysis = analyzer.analyze_wim_differences(source_mount, target_mount)

        # 显示分析报告
        report = analyzer.generate_analysis_report(analysis)
        print(report)

        # 保存分析结果到文件
        output_file = Path("component_analysis_report.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n分析报告已保存到: {output_file}")

    except Exception as e:
        print(f"组件分析失败: {str(e)}")


if __name__ == "__main__":
    print("WinPE版本替换工具示例")
    print("请确保:")
    print("1. 源WIM (0WIN11PE) 已挂载到 mount 目录")
    print("2. 目标WIM (0WIN10OLD) 已挂载到 mount 目录")
    print("3. 有足够的磁盘空间用于输出")
    print()

    # 询问用户选择操作
    print("请选择操作:")
    print("1. 执行完整版本替换")
    print("2. 仅分析组件差异")
    print("0. 退出")

    try:
        choice = input("\n请输入选择 (0-2): ").strip()

        if choice == "1":
            success = example_version_replace()
            if success:
                print("\n版本替换完成! 您可以在输出目录中找到替换后的WinPE。")
            else:
                print("\n版本替换失败，请检查错误信息。")

        elif choice == "2":
            example_component_analysis()

        elif choice == "0":
            print("退出程序")

        else:
            print("无效选择")

    except KeyboardInterrupt:
        print("\n\n用户中断操作")
    except Exception as e:
        print(f"\n程序异常: {str(e)}")
        import traceback
        traceback.print_exc()

    input("\n按回车键退出...")