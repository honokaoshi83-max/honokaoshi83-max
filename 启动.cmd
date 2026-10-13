@echo off
chcp 65001 >nul
if exist "%~dp0iracing-assistant.exe" (
  start "" "%~dp0iracing-assistant.exe"
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\manage.ps1"
)
