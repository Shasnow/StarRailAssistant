@echo off
chcp 65001 >nul
fltmc >nul 2>&1
if not "%errorlevel%"=="0" (
    echo Please run this script as administrator.
    powershell -Command "Start-Process 'wt.exe' -ArgumentList 'cmd /c cd /d \"%cd%\" && \"%~f0\" %*' -Verb RunAs"
    exit
)
if exist ".\python\python.exe" (
    .\python\python.exe main.py %*
) else (
    echo Python is not found. Please run SRA.exe to setup the environment first.
    pause
)