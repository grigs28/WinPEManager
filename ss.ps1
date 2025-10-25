# 1 自身提权
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoExit", "-File", "`"$PSCommandPath`""
    exit
}

# 2 让原 ADK 批处理在 CMD 里跑，并把最终环境变量导回当前 PowerShell
$bat = "${env:ProgramFiles(x86)}\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\DandISetEnv.bat"
cmd /c "`"$bat`" >nul && set" | ForEach-Object {
    if ($_ -match '^(.*?)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
    }
}

# 3 切到工作目录
Set-Location D:\APP\WinPEManager

# 4 启动 GUI
& python.exe run.py