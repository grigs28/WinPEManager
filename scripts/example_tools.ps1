# PowerShell工具脚本示例
# 这个脚本提供一些有用的系统维护工具

Write-Host "==========================================" -ForegroundColor Green
Write-Host "WinPE PowerShell 工具集" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

# 显示菜单
function Show-Menu {
    Write-Host "请选择要执行的操作:" -ForegroundColor Yellow
    Write-Host "1. 磁盘管理"
    Write-Host "2. 网络诊断"
    Write-Host "3. 系统信息"
    Write-Host "4. 文件管理器"
    Write-Host "5. 注册表编辑器"
    Write-Host "6. 任务管理器"
    Write-Host "7. 命令提示符"
    Write-Host "8. 退出"
    Write-Host ""
}

# 磁盘管理功能
function Show-DiskManagement {
    Write-Host "磁盘信息:" -ForegroundColor Cyan
    Get-Disk | Format-Table Number, FriendlyName, TotalSize, PartitionStyle

    Write-Host "`n分区信息:" -ForegroundColor Cyan
    Get-Partition | Format-Table DiskNumber, PartitionNumber, DriveLetter, Size, Type

    Write-Host "`n卷信息:" -ForegroundColor Cyan
    Get-Volume | Format-Table DriveLetter, FileSystemLabel, FileSystem, Size, RemainingSize
}

# 网络诊断功能
function Show-NetworkDiagnostics {
    Write-Host "网络适配器:" -ForegroundColor Cyan
    Get-NetAdapter | Format-Table Name, Status, LinkSpeed, MacAddress

    Write-Host "`nIP配置:" -ForegroundColor Cyan
    Get-NetIPConfiguration | Format-Table InterfaceAlias, IPv4Address, IPv6Address

    Write-Host "`n网络连接测试:" -ForegroundColor Cyan
    Test-NetConnection -ComputerName "8.8.8.8" -InformationLevel Detailed
}

# 系统信息功能
function Show-SystemInfo {
    Write-Host "系统信息:" -ForegroundColor Cyan
    Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, TotalPhysicalMemory, CsProcessors

    Write-Host "`n进程信息:" -ForegroundColor Cyan
    Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 Name, CPU, WorkingSet

    Write-Host "`n服务状态:" -ForegroundColor Cyan
    Get-Service | Where-Object {$_.Status -eq "Running"} | Select-Object -First 10 Name, DisplayName, Status
}

# 文件管理器
function Start-FileManager {
    Write-Host "启动文件管理器..." -ForegroundColor Green
    explorer.exe
}

# 主循环
do {
    Show-Menu
    $choice = Read-Host "请输入选项 (1-8)"

    switch ($choice) {
        "1" { Show-DiskManagement }
        "2" { Show-NetworkDiagnostics }
        "3" { Show-SystemInfo }
        "4" { Start-FileManager }
        "5" { regedit.exe }
        "6" { taskmgr.exe }
        "7" { cmd.exe }
        "8" {
            Write-Host "退出程序" -ForegroundColor Green
            break
        }
        default { Write-Host "无效选项，请重新选择" -ForegroundColor Red }
    }

    if ($choice -ne "8") {
        Write-Host "`n按任意键继续..." -ForegroundColor Yellow
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        Clear-Host
    }
} while ($choice -ne "8")

Write-Host "程序结束" -ForegroundColor Green