@echo off
rem Dusklight Setup Studio for Windows: opens the assistant in its own window.
setlocal
cd /d "%~dp0WorkshopKit"
if exist "app\windows-x64\electron.exe" (
    start "" "app\windows-x64\electron.exe" "%~dp0WorkshopKit\gui-frame" "--maker-dir=%~dp0WorkshopKit"
    exit /b 0
)
rem Without the window app: the assistant in the browser.
title Dusklight Setup Studio
"runtime\windows-x64\python\python.exe" -s -E -B -m dsk_weave6bdf gui
if errorlevel 1 pause
