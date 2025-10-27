#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一WIM管理器使用示例
演示如何使用模块化的WIM管理功能
"""

from pathlib import Path
from core.unified_manager import UnifiedWIMManager


def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 注意：这里需要实际的config_manager和adk_manager
    # config_manager = YourConfigManager()
    # adk_manager = YourADKManager()
    
    # 初始化管理器
    # wim_manager = UnifiedWIMManager(config_manager, adk_manager)
    
    # 示例路径
    build_dir = Path("D:/WinPE_Build")
    
    print(f"构建目录: {build_dir}")
    
    # 以下代码需要实际的配置管理器和ADK管理器才能运行
    # 这里仅作为示例展示API用法
    
    """
    # 查找WIM文件
    wim_files = wim_manager.find_wim_files(build_dir)
    print(f"找到 {len(wim_files)} 个WIM文件")
    
    # 获取主要WIM文件
    primary_wim = wim_manager.get_primary_wim(build_dir)
    if primary_wim:
        print(f"主要WIM文件: {primary_wim}")
    
    # 挂载WIM文件
    success, message = wim_manager.mount_wim(build_dir)
    if success:
        print(f"挂载成功: {message}")
        
        # 进行一些操作...
        
        # 卸载WIM文件
        success, message = wim_manager.unmount_wim(build_dir, commit=True)
        if success:
            print(f"卸载成功: {message}")
    else:
        print(f"挂载失败: {message}")
    """


def example_advanced_usage():
    """高级功能示例"""
    print("\n=== 高级功能示例 ===")
    
    build_dir = Path("D:/WinPE_Build")
    
    # 以下代码需要实际的配置管理器和ADK管理器才能运行
    
    """
    # 快速挂载检查
    check_result = wim_manager.quick_mount_check(build_dir)
    print("快速检查结果:")
    print(f"  主要WIM: {check_result.get('primary_wim')}")
    print(f"  挂载状态: {check_result.get('mount_status', {}).get('is_mounted')}")
    print(f"  检查通过: {check_result.get('mount_check_passed')}")
    print(f"  建议: {check_result.get('recommendations', [])}")
    
    # 获取构建信息
    build_info = wim_manager.get_build_info(build_dir)
    print(f"\n构建信息:")
    print(f"  WIM文件数量: {build_info.get('total_wim_count', 0)}")
    print(f"  总大小: {build_info.get('total_wim_size', 0) / (1024*1024):.1f} MB")
    print(f"  包含boot.wim: {build_info.get('has_boot_wim', False)}")
    
    # 验证构建结构
    validation = wim_manager.validate_build_structure(build_dir)
    print(f"\n结构验证:")
    print(f"  验证通过: {validation.get('is_valid', False)}")
    print(f"  错误: {validation.get('errors', [])}")
    print(f"  警告: {validation.get('warnings', [])}")
    
    # 智能清理
    cleanup_result = wim_manager.smart_cleanup(build_dir)
    print(f"\n智能清理:")
    print(f"  清理成功: {cleanup_result.get('success', False)}")
    print(f"  执行的操作: {cleanup_result.get('actions_taken', [])}")
    print(f"  警告: {cleanup_result.get('warnings', [])}")
    
    # 获取诊断信息
    diagnostics = wim_manager.get_diagnostics(build_dir)
    print(f"\n诊断信息:")
    print(f"  时间戳: {diagnostics.get('timestamp')}")
    print(f"  系统平台: {diagnostics.get('system_info', {}).get('platform', {}).get('system')}")
    print(f"  模块状态: {diagnostics.get('module_status', {})}")
    """


def example_individual_modules():
    """单独使用各个模块的示例"""
    print("\n=== 单独模块使用示例 ===")
    
    # 可以单独使用各个模块
    from core.unified_manager import PathManager, CheckManager, StatusManager
    
    # 路径管理器
    path_manager = PathManager()
    build_dir = Path("D:/WinPE_Build")
    
    print(f"挂载目录: {path_manager.get_mount_dir(build_dir)}")
    
    # 状态管理器
    status_manager = StatusManager(path_manager)
    
    """
    wim_files = path_manager.find_wim_files(build_dir)
    print(f"找到 {len(wim_files)} 个WIM文件")
    
    mount_status = status_manager.get_mount_status(build_dir)
    print(f"挂载状态: {mount_status.get('is_mounted', False)}")
    
    wim_summary = status_manager.get_wim_summary(build_dir)
    print(f"WIM摘要: {wim_summary}")
    """


def example_error_handling():
    """错误处理示例"""
    print("\n=== 错误处理示例 ===")
    
    """
    # 所有操作都返回 (success, message) 元组
    success, message = wim_manager.mount_wim(build_dir)
    
    if success:
        print("操作成功:", message)
        # 继续后续操作
    else:
        print("操作失败:", message)
        # 处理错误情况
        return
    
    # 使用try-except包装关键操作
    try:
        success, message = wim_manager.create_iso(build_dir)
        if success:
            print("ISO创建成功:", message)
        else:
            print("ISO创建失败:", message)
    except Exception as e:
        print("发生异常:", str(e))
    """


def example_logging():
    """日志记录示例"""
    print("\n=== 日志记录示例 ===")
    
    """
    # 管理器会自动记录详细的日志信息
    # 日志会输出到:
    # 1. 终端控制台
    # 2. 系统日志
    # 3. 文件日志
    # 4. 构建日志 (如果启用构建会话)
    
    # 可以通过utils.logger模块自定义日志配置
    from utils.logger import get_logger
    
    logger = get_logger("MyWIMApp")
    logger.info("开始WIM操作")
    
    success, message = wim_manager.mount_wim(build_dir)
    
    if success:
        logger.info(f"挂载成功: {message}")
    else:
        logger.error(f"挂载失败: {message}")
    """


if __name__ == "__main__":
    print("统一WIM管理器使用示例")
    print("=" * 50)
    
    # 运行各种示例
    example_basic_usage()
    example_advanced_usage()
    example_individual_modules()
    example_error_handling()
    example_logging()
    
    print("\n" + "=" * 50)
    print("示例运行完成")
    print("\n注意:")
    print("- 这些示例需要实际的config_manager和adk_manager才能运行")
    print("- 请根据实际情况修改路径和配置")
    print("- 参考README.md获取详细的使用说明")
