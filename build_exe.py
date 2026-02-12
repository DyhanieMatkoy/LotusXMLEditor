#!/usr/bin/env python3
"""
Build script for Lotus Xml Editor - creates standalone executable
"""

import PyInstaller.__main__
import os
import sys

def build_executable():
    """Build the application into a standalone executable"""
    
    # PyInstaller arguments
    args = [
        'main.py',  # Main script
        '--name=lxe',  # Name of the executable
        '--onedir',  # Bundle everything into a single directory
        '--windowed',  # Windows subsystem (no console window)
        '--icon=blotus.ico',  # Application icon
        '--hidden-import=PyQt6.QtCore',
        '--hidden-import=PyQt6.QtGui', 
        '--hidden-import=PyQt6.QtWidgets',
        '--hidden-import=lxml',
        '--hidden-import=chardet',
        '--hidden-import=pygments',
        '--hidden-import=qscintilla',
        '--add-data=1C Ent_TRANS.xml;.', # Include 1C syntax definition
        '--clean',  # Clean PyInstaller cache
        '--noconfirm',  # Replace output directory without confirmation
    ]
    
    print("Building Lotus Xml Editor executable...")
    print(f"Python version: {sys.version}")
    print(f"PyInstaller version: {PyInstaller.__version__}")
    
    try:
        # Run PyInstaller
        PyInstaller.__main__.run(args)
        
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