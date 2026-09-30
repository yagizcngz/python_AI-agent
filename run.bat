@echo off
setlocal

:: Set UTF-8 code page for proper rendering of Unicode characters, borders, and tree icons
chcp 65001 >nul

:: Ensure Python uses UTF-8 standard IO streams
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:: Run Python AI Agent
py app\main.py %*
