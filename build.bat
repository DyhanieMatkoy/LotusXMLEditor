@echo off
echo Building Lotus Xml Editor executable...
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo Starting build process...
python build_exe.py

if %errorlevel% equ 0 (
    echo.
    echo ✅ Build completed successfully!
    echo.
    echo The executable can be found in the 'dist' folder.
    echo You can now run Lotus Xml Editor.exe directly!
) else (
    echo.
    echo ❌ Build failed. Please check the error messages above.
)

echo.
pause