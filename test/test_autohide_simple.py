#!/usr/bin/env python3
"""
Simple test for auto-hide setup
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

def test_setup():
    """Test auto-hide setup without showing GUI"""
    app = QApplication(sys.argv)
    
    # Import after QApplication is created
    from main import MainWindow
    
    print("Creating MainWindow...")
    window = MainWindow()
    
    # Check if auto-hide managers were created
    print(f"Has toolbar_auto_hide: {hasattr(window, 'toolbar_auto_hide')}")
    print(f"Has tree_header_auto_hide: {hasattr(window, 'tree_header_auto_hide')}")
    
    if hasattr(window, 'toolbar_auto_hide'):
        print(f"Toolbar auto-hide enabled: {window.toolbar_auto_hide.auto_hide_enabled}")
        print(f"Toolbar widget: {window.toolbar_auto_hide.widget}")
        print(f"Toolbar original height: {window.toolbar_auto_hide.original_height}")
    
    if hasattr(window, 'tree_header_auto_hide'):
        print(f"Tree header auto-hide enabled: {window.tree_header_auto_hide.auto_hide_enabled}")
        print(f"Tree header widget: {window.tree_header_auto_hide.widget}")
        print(f"Tree header original height: {window.tree_header_auto_hide.original_height}")
    
    # Check menu actions
    print(f"Has toolbar toggle action: {hasattr(window, 'toggle_toolbar_autohide_action')}")
    print(f"Has tree header toggle action: {hasattr(window, 'toggle_tree_header_autohide_action')}")
    
    # Exit after checks
    QTimer.singleShot(500, app.quit)
    
    return app.exec()

if __name__ == '__main__':
    sys.exit(test_setup())
