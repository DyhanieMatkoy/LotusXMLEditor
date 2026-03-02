#!/usr/bin/env python3
"""
Build script for Lotus Xml Editor - creates standalone executable
"""

import PyInstaller.__main__
import os
import sys
import shutil

def build_executable():
    """Build the application into a standalone executable"""
    
    # PyInstaller arguments
    args = [
        'main.py',  # Main script
        '--name=lxe',  # Name of the executable
        '--onedir',  # Bundle everything into a single directory
        '--windowed',  # Windows subsystem (no console window)
        '--icon=blotus.ico',  # Application icon
        '--collect-all=PyQt6', # Force collection of PyQt6
        '--hidden-import=PyQt6.Qsci', # Correct QScintilla import
        '--hidden-import=lxml',
        '--hidden-import=chardet',
        '--hidden-import=pygments',
        '--paths=D:\\ptn313\\Lib\\site-packages\\PyQt6', # Add PyQt6 path
        '--add-data=1C Ent_TRANS.xml;.', # Include 1C syntax definition
        '--clean',  # Clean PyInstaller cache
        '--noconfirm',  # Replace output directory without confirmation
    ]
    
    # Manually add PyQt6 binaries to ensure they are included
    pyqt6_dir = r'D:\ptn313\Lib\site-packages\PyQt6'
    if os.path.exists(pyqt6_dir):
        print(f"Found PyQt6 at: {pyqt6_dir}")
        # Add all .pyd files from PyQt6 directory
        count = 0
        for file in os.listdir(pyqt6_dir):
            if file.endswith('.pyd'):
                src = os.path.join(pyqt6_dir, file)
                # Format: src;dest (dest is relative to _internal or top level in onedir)
                # We want them in PyQt6/ inside _internal
                args.append(f'--add-binary={src};PyQt6')
                count += 1
        print(f"Added {count} PyQt6 binary modules manually.")

    print("Building Lotus Xml Editor executable...")
    print(f"Python version: {sys.version}")
    print(f"PyInstaller version: {PyInstaller.__version__}")
    
    try:
        # Run PyInstaller
        PyInstaller.__main__.run(args)
        
        # Post-build fix: Copy PyQt6 .pyd files if missing
        dist_pyqt6 = os.path.join('dist', 'lxe', '_internal', 'PyQt6')
        if os.path.exists(pyqt6_dir) and os.path.exists(dist_pyqt6):
            print(f"Checking for missing PyQt6 binaries in {dist_pyqt6}...")
            for file in os.listdir(pyqt6_dir):
                if file.endswith('.pyd'):
                    src = os.path.join(pyqt6_dir, file)
                    dst = os.path.join(dist_pyqt6, file)
                    if not os.path.exists(dst):
                        print(f"Manually copying {file}...")
                        shutil.copy2(src, dst)
        
        # Get the output directory
        if sys.platform == 'win32':
            dist_path = os.path.join('dist', 'lxe', 'lxe.exe')
        else:
            dist_path = os.path.join('dist', 'lxe', 'lxe')
            
        print(f"\n✅ Build completed successfully!")
        if os.path.exists(dist_path):
            print(f"Executable created at: {dist_path}")
            print(f"File size: {os.path.getsize(dist_path) / 1024 / 1024:.1f} MB")
        else:
             print(f"Build directory created at: {os.path.dirname(dist_path)}")
        
    except Exception as e:
        print(f"\n❌ Build failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)