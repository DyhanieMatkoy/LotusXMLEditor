@echo off
echo Lotus Xml Editor - Python Version
echo ===================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org
    pause
    exit /b 1
)

REM Check if required packages are installed
echo Checking dependencies...
python -c "import PyQt6" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required packages...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install required packages
        pause
        exit /b 1
    )
)

echo.
echo Starting Visual XML Editor...
echo.

REM Run the main application
python main.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Application crashed or failed to start
    echo Please check the error messages above
    pause
)