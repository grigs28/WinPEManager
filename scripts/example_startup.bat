@echo off
REM WinPE启动脚本示例
REM 这个脚本会在WinPE启动时自动执行

echo ==========================================
echo WinPE 启动脚本
echo ==========================================

REM 设置环境变量
set WINPE_SCRIPT_DIR=%~dp0
echo 脚本目录: %WINPE_SCRIPT_DIR%

REM 检查网络连接
echo 正在检查网络连接...
ping -n 1 8.8.8.8 > nul 2>&1
if %errorlevel% equ 0 (
    echo 网络连接正常
) else (
    echo 网络连接不可用
)

REM 显示系统信息
echo.
echo 系统信息:
echo ----------
ver
echo 当前用户: %USERNAME%
echo 计算机名: %COMPUTERNAME%

REM 显示磁盘信息
echo.
echo 磁盘信息:
echo ----------
wmic logicaldisk get size,freespace,caption

REM 显示网络配置
echo.
echo 网络配置:
echo ----------
ipconfig /all

echo.
echo ==========================================
echo 启动脚本执行完成
echo ==========================================

REM 可以在这里添加更多自定义命令

pause