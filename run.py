#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinPE管理器启动脚本
用于启动应用程序并进行必要的依赖检查
"""

import sys
import os
import subprocess
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 7):
        print("错误: 需要Python 3.7或更高版本")
        print(f"当前版本: {sys.version}")
        return False
    return True

def check_dependencies():
    """检查必要的依赖包"""
    required_packages = ['PyQt5']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("错误: 缺少必要的依赖包:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n请运行以下命令安装依赖:")
        print("pip install -r requirements.txt")
        return False

    return True

def install_dependencies():
    """自动安装依赖包"""
    print("正在安装依赖包...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("依赖包安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"安装依赖包失败: {e}")
        return False

def main():
    """主函数"""
    print("WinPE制作管理器")
    print("=" * 50)

    # 检查Python版本
    if not check_python_version():
        input("按回车键退出...")
        return 1

    # 检查依赖
    if not check_dependencies():
        choice = input("是否自动安装依赖包? (y/n): ").lower().strip()
        if choice in ['y', 'yes', '是']:
            if not install_dependencies():
                input("按回车键退出...")
                return 1
        else:
            input("按回车键退出...")
            return 1

    # 设置当前工作目录
    project_root = Path(__file__).parent
    os.chdir(project_root)

    try:
        # 导入并启动主程序
        from main import main as app_main
        return app_main()
    except Exception as e:
        print(f"启动程序时发生错误: {e}")
        import traceback
        traceback.print_exc()
        #input("按回车键退出...")
        return 1

if __name__ == "__main__":
    sys.exit(main())