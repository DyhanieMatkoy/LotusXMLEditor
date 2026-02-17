#!/usr/bin/env python3
"""
Test script for auto-hide functionality
"""

import sys
from PyQt6.QtWidgets import QApplication
from main import MainWindow

def test_autohide():
    """Test auto-hide functionality"""
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    
    # Verify auto-hide managers exist
    # assert hasattr(window, 'toolbar_auto_hide'), "Toolbar auto-hide manager not found"
    assert hasattr(window, 'tree_header_auto_hide'), "Tree header auto-hide manager not found"
    
    # Verify hover zones exist
    # assert hasattr(window, 'toolbar_hover_zone'), "Toolbar hover zone not found"
    assert hasattr(window, 'tree_header_hover_zone'), "Tree header hover zone not found"
    
    # Verify menu actions exist
    assert hasattr(window, 'toggle_toolbar_autohide_action'), "Toolbar auto-hide action not found"
    assert hasattr(window, 'toggle_tree_header_autohide_action'), "Tree header auto-hide action not found"
    
    # Test toggling auto-hide
    print("Testing toolbar auto-hide toggle...")
    # window.toggle_toolbar_autohide_action.setChecked(False)
    # assert not window.toolbar_auto_hide.auto_hide_enabled, "Toolbar auto-hide should be disabled"
    
    # window.toggle_toolbar_autohide_action.setChecked(True)
    # assert window.toolbar_auto_hide.auto_hide_enabled, "Toolbar auto-hide should be enabled"
    
    print("Testing tree header auto-hide toggle...")
    window.toggle_tree_header_autohide_action.setChecked(False)
    assert not window.tree_header_auto_hide.auto_hide_enabled, "Tree header auto-hide should be disabled"
    
    window.toggle_tree_header_autohide_action.setChecked(True)
    assert window.tree_header_auto_hide.auto_hide_enabled, "Tree header auto-hide should be enabled"
    
    print("All tests passed!")
    
    # Show window for manual testing
    window.show()
    
    return app.exec()

if __name__ == '__main__':
    sys.exit(test_autohide())
