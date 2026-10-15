@echo off
setlocal
cd /d "%~dp0"
py -3 -m share_receiver
if errorlevel 1 (
  echo Share failed to start. Python 3.11+ with Tk is required.
  echo Try: python -m share_receiver
  pause
)
