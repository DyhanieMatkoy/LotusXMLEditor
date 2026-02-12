@echo off
REM Backup Project Code
REM Creates a timestamped ZIP archive of the project

setlocal enabledelayedexpansion

echo ========================================
echo Project Backup Utility
echo ========================================
echo.

REM Get current date and time for filename
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%

REM Set backup filename
set BACKUP_NAME=LotusXMLEditor_backup_%TIMESTAMP%.zip
set BACKUP_DIR=backups
set BACKUP_PATH=%BACKUP_DIR%\%BACKUP_NAME%

REM Create backups directory if it doesn't exist
if not exist "%BACKUP_DIR%" (
    echo Creating backups directory...
    mkdir "%BACKUP_DIR%"
)

REM Check if PowerShell is available (for compression)
powershell -Command "exit" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: PowerShell is required for creating ZIP archives
    pause
    exit /b 1
)

echo Creating backup: %BACKUP_NAME%
echo.
echo Including:
echo   - Python source files (*.py)
echo   - Documentation (doc\*)
echo   - Configuration files
echo   - Batch scripts (*.bat)
echo   - Spec files (*.spec)
echo.
echo Excluding:
echo   - Virtual environment (.venv\)
echo   - Build artifacts (build\, dist\, __pycache__)
echo   - Git repository (.git\)
echo   - Large XML files
echo.

REM Create temporary directory for staging files
set TEMP_DIR=%TEMP%\LotusXMLEditor_backup_%RANDOM%
mkdir "%TEMP_DIR%"

REM Copy files to temp directory
echo Copying files...

REM Copy Python files
xcopy /Y /Q *.py "%TEMP_DIR%\" >nul 2>&1

REM Copy batch files
xcopy /Y /Q *.bat "%TEMP_DIR%\" >nul 2>&1

REM Copy spec files
xcopy /Y /Q *.spec "%TEMP_DIR%\" >nul 2>&1

REM Copy documentation
xcopy /Y /Q /E doc "%TEMP_DIR%\doc\" >nul 2>&1

REM Copy test files
xcopy /Y /Q /E test "%TEMP_DIR%\test\" >nul 2>&1

REM Copy .kiro directory (excluding large files)
if exist ".kiro" (
    xcopy /Y /Q /E .kiro "%TEMP_DIR%\.kiro\" >nul 2>&1
)

REM Copy configuration files
if exist ".gitignore" copy /Y ".gitignore" "%TEMP_DIR%\" >nul 2>&1
if exist "README.md" copy /Y "README.md" "%TEMP_DIR%\" >nul 2>&1
if exist "version.py" copy /Y "version.py" "%TEMP_DIR%\" >nul 2>&1

REM Copy icon and splash
if exist "blotus.ico" copy /Y "blotus.ico" "%TEMP_DIR%\" >nul 2>&1
if exist "blotus_splash.jpg" copy /Y "blotus_splash.jpg" "%TEMP_DIR%\" >nul 2>&1

REM Create ZIP archive using PowerShell
echo Creating ZIP archive...
powershell -Command "Compress-Archive -Path '%TEMP_DIR%\*' -DestinationPath '%BACKUP_PATH%' -Force"

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo SUCCESS: Backup created successfully!
    echo ========================================
    echo.
    echo Backup file: %BACKUP_PATH%
    
    REM Get file size
    for %%A in ("%BACKUP_PATH%") do set FILESIZE=%%~zA
    set /a FILESIZE_KB=!FILESIZE! / 1024
    set /a FILESIZE_MB=!FILESIZE_KB! / 1024
    
    if !FILESIZE_MB! gtr 0 (
        echo File size: !FILESIZE_MB! MB
    ) else (
        echo File size: !FILESIZE_KB! KB
    )
    
    echo.
    echo Opening backups folder...
    explorer "%BACKUP_DIR%"
) else (
    echo.
    echo ERROR: Failed to create backup archive
)

REM Cleanup temp directory
echo.
echo Cleaning up...
rmdir /S /Q "%TEMP_DIR%" >nul 2>&1

echo.
echo Done!
pause
