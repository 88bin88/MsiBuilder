@echo off
rem 编译自解压启动器 stub（使用系统自带 .NET Framework 4.x 的 csc.exe）
setlocal
set CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe
if not exist "%CSC%" set CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe
if not exist "%CSC%" (
  echo [ERROR] 找不到 csc.exe，请先安装 .NET Framework 4.x
  exit /b 1
)
"%CSC%" /target:winexe /platform:anycpu /optimize+ /nologo /codepage:65001 /r:System.Windows.Forms.dll /out:"%~dp0msi_stub.exe" "%~dp0msi_stub.cs"
if errorlevel 1 exit /b 1
echo [OK] stub 编译完成: %~dp0msi_stub.exe