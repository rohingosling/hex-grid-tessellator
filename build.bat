@echo off
REM Build the standalone HEX Grid Tessellator executable (dist\hextessellator.exe)
REM Stamps version + build date, runs PyInstaller via hextessellator.spec, then smoke-tests the exe.
REM Usage: build.bat

cls
.venv\Scripts\python.exe scripts\build.py
