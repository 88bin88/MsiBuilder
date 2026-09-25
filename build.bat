@echo off
cd /d %~dp0
echo ======================================
echo   MSI Builder Build Script
echo ======================================
echo.

echo [1/3] Cleaning old build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

echo [2/3] Running PyInstaller...
pyinstaller --onefile --windowed --noconsole --name MsiBuilder --add-data "wix;wix" --add-data "hhc;hhc" --hidden-import "PyQt6.QtCore" --hidden-import "PyQt6.QtGui" --hidden-import "PyQt6.QtWidgets" main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Build completed!
echo Output: dist\MsiBuilder.exe
echo.
pause
