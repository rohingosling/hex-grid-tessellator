@echo off
REM Run the HEX Grid Tessellator
REM Usage: run.bat [options]
REM   --debug                 Print detailed parameters and statistics
REM   --width / --height N    Image dimensions in pixels
REM   --import_settings FILE  Load parameters from a JSON file
REM   --export_settings FILE  Save parameters to a JSON file
REM   --help                  Show help and exit

cls
.venv\Scripts\python.exe -X utf8 src/main.py %*
