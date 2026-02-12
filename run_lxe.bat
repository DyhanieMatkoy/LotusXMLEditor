@echo off
REM Quick launcher for LXE (Lotus XML Editor)

echo Starting LXE (Lotus XML Editor)...

if exist "dist\lxe.exe" (
    start "" "dist\lxe.exe" %*
) else (
    echo ERROR: lxe.exe not found in dist folder
    echo Please run build_lxe.bat first to build the executable
    pause
)