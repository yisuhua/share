@chcp 65001 >nul
@echo off
cd /d "%~dp0"
if exist "runtime\python.exe" (
    "runtime\python.exe" -B tools\install_windows.py
) else (
    py -3 tools\install_windows.py
)
if errorlevel 1 pause
