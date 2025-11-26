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
        '--name=VisualXmlEditor',  # Name of the executable
        '--onefile',  # Bundle everything into a single executable
        '--windowed',  # Windows subsystem (no console window)
        '--icon=NONE',  # No icon specified - can be added later
        '--hidden-import=PyQt6.QtCore',
        '--hidden-import=PyQt6.QtGui', 
        '--hidden-import=PyQt6.QtWidgets',
        '--hidden-import=lxml',
        '--hidden-import=chardet',
        '--hidden-import=pygments',
        '--hidden-import=qscintilla',
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
            dist_path = os.path.join('dist', 'VisualXmlEditor.exe')
        else:
            dist_path = os.path.join('dist', 'VisualXmlEditor')
            
        print(f"\n✅ Build completed successfully!")
        print(f"Executable created at: {dist_path}")
        print(f"File size: {os.path.getsize(dist_path) / 1024 / 1024:.1f} MB")
        
    except Exception as e:
        print(f"\n❌ Build failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)