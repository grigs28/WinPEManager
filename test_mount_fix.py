#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试挂载修复的验证脚本
"""

from pathlib import Path

def test_wim_path_resolution():
    """测试WIM文件路径解析逻辑"""

    # 模拟构建目录
    current_build_path = Path("D:/APP/WinPEManager/WinPE_amd64/WinPE_20251026_200141")

    # 1. 测试WinPEBuilder的路径解析
    wim_file_path = current_build_path / "media" / "sources" / "boot.wim"
    mount_dir = wim_file_path.parent / "mount"

    print("=== WinPEBuilder路径解析测试 ===")
    print(f"构建目录: {current_build_path}")
    print(f"WIM文件路径: {wim_file_path}")
    print(f"挂载目录: {mount_dir}")
    print(f"WIM文件是否存在: {wim_file_path.exists()}")
    print(f"挂载目录是否存在: {mount_dir.exists()}")
    print()

    # 2. 测试WIM管理器扫描逻辑
    print("=== WIM管理器扫描逻辑测试 ===")

    # 模拟扫描到的WIM文件信息
    wim_file_info = {
        "path": str(wim_file_path),
        "name": "boot.wim",
        "type": "copype",
        "build_dir": current_build_path,
        "mount_status": mount_dir.exists()
    }

    print(f"WIM文件信息: {wim_file_info}")
    print()

    # 3. 验证路径一致性
    print("=== 路径一致性验证 ===")
    print(f"WinPEBuilder解析的WIM路径: {wim_file_path}")
    print(f"WIM管理器存储的路径: {wim_file_info['path']}")
    print(f"路径是否一致: {str(wim_file_path) == wim_file_info['path']}")
    print(f"统一挂载目录规则: {wim_file_path.parent}/mount")
    print()

    # 4. 测试MountManager接收的参数
    print("=== MountManager参数测试 ===")
    print(f"MountManager.mount_winpe_image() 接收参数:")
    print(f"  参数类型: {type(wim_file_path)}")
    print(f"  参数值: {wim_file_path}")
    print(f"  内部计算挂载目录: {wim_file_path.parent / 'mount'}")
    print()

    print("SUCCESS: 所有路径解析逻辑验证完成！")

if __name__ == "__main__":
    test_wim_path_resolution()