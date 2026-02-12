@echo off
echo Building LXE (Lotus XML Editor) executable...
echo =============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org
    pause
    exit /b 1
)

REM Check if PyInstaller is installed
echo Checking PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

REM Clean previous builds
echo Cleaning previous builds...
if exist "dist\lxe.exe" del "dist\lxe.exe"
if exist "build" rmdir /s /q "build"

echo.
echo Building lxe.exe...
echo This may take a few minutes...
echo.

REM Build using the updated script
python build_exe.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo ✅ SUCCESS: lxe.exe built successfully!
    echo ========================================
    echo.
    
    REM Show file info
    if exist "dist\lxe.exe" (
        for %%A in ("dist\lxe.exe") do (
            set FILESIZE=%%~zA
            set /a FILESIZE_MB=!FILESIZE! / 1024 / 1024
        )
        setlocal enabledelayedexpansion
        echo Executable: dist\lxe.exe
        echo Size: !FILESIZE_MB! MB
        echo.
        echo You can now run: dist\lxe.exe
        echo.
        echo Opening dist folder...
        explorer "dist"
    ) else (
        echo WARNING: lxe.exe was not found in dist folder
    )
) else (
    echo.
    echo ========================================
    echo ❌ BUILD FAILED
    echo ========================================
    echo Please check the error messages above.
)

echo.
pause