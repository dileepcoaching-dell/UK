@echo off
title CA Article Toolkit Launcher
echo Starting CA Article Toolkit...
python launcher.py
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Could not start the launcher.
    echo Please make sure Python is installed on this computer.
    echo Download Python from: https://www.python.org/downloads/
    echo.
    echo Also install required packages by running:
    echo   pip install streamlit pandas openpyxl xlsxwriter
    echo.
    pause
)
