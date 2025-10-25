@echo off
chcp 65001 > nul
title WinPE制作管理器

echo ==========================================
echo WinPE制作管理器启动脚本
echo ==========================================
echo.

REM 检查Python是否安装
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.7或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo 检测到Python环境
python --version

echo.
echo 正在启动WinPE制作管理器...
echo.

REM 启动Python程序
python run.py

if %errorlevel% neq 0 (
    echo.
    echo 程序异常退出，错误代码: %errorlevel%
    pause
)