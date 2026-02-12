# LXE Build Guide

## Overview
LXE (Lotus XML Editor) can be built as a standalone executable named `lxe.exe` for easy distribution and deployment.

## Build Methods

### Method 1: Quick Build (Recommended)
```batch
build_lxe.bat
```
This script will:
- Check Python and PyInstaller installation
- Clean previous builds
- Build `lxe.exe` in the `dist` folder
- Show file size and open the dist folder

### Method 2: Manual Build
```batch
python build_exe.py
```

### Method 3: Using PyInstaller directly
```batch
pyinstaller lxe.spec
```

## Output
- **Executable**: `dist/lxe.exe`
- **Size**: ~56 MB (single file, all dependencies included)
- **Type**: Windows executable (no console window)

## Running LXE

### Direct execution:
```batch
dist\lxe.exe
```

### Using launcher:
```batch
run_lxe.bat
```

### With file argument:
```batch
dist\lxe.exe "path\to\file.xml"
```

## Build Configuration

The build is configured in:
- `build_exe.py` - Main build script
- `lxe.spec` - PyInstaller specification file

### Key Features:
- **Single file**: All dependencies bundled
- **No console**: Windowed application
- **Icon**: Uses `blotus.ico`
- **Hidden imports**: PyQt6, lxml, pygments included

## Requirements
- Python 3.8+
- PyInstaller
- All project dependencies (PyQt6, lxml, etc.)

## Troubleshooting

### Build fails with missing modules:
Add missing modules to hidden imports in `build_exe.py`:
```python
'--hidden-import=module_name',
```

### Large file size:
The executable includes all dependencies for standalone operation. This is normal for PyQt6 applications.

### Antivirus warnings:
Some antivirus software may flag PyInstaller executables. This is a false positive common with bundled Python applications.

## Distribution
The `lxe.exe` file is completely standalone and can be:
- Copied to any Windows machine
- Run without Python installation
- Distributed as a single file

## File Structure After Build
```
dist/
├── lxe.exe          # Main executable (56MB)
└── [other files]    # Other project files

build/               # Temporary build files (can be deleted)
├── lxe/
└── [build cache]
```

## Clean Build
To ensure a clean build:
```batch
rmdir /s /q build
del dist\lxe.exe
python build_exe.py
```