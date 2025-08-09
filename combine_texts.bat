@echo off
setlocal enabledelayedexpansion

REM Always work in the folder where this .bat lives
cd /d "%~dp0"

REM If there are no .txt files, exit gracefully
dir /b *.txt >nul 2>&1 || (
  echo No .txt files found in %cd%.
  pause
  exit /b 1
)

set "outfile=combined.txt"
if exist "%outfile%" del "%outfile%"

for %%f in (*.txt) do (
  type "%%f" >> "%outfile%"
  echo.>> "%outfile%"
  echo.>> "%outfile%"
  echo.>> "%outfile%"
)

echo Done! Created "%outfile%" in %cd%.
pause

