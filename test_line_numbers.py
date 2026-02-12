#!/usr/bin/env python3
"""
Test script to verify line numbers functionality
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

def test_line_numbers():
    """Test line numbers setting and visibility"""
    app = QApplication(sys.argv)
    
    # Import after QApplication is created
    from main import XmlEditorWidget
    
    # Create editor
    editor = XmlEditorWidget()
    editor.setPlainText("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
    editor.show()  # Show the editor widget
    
    # Test 1: Line numbers should be hidden by default
    print("Test 1: Line numbers hidden by default")
    assert not editor.line_number_widget.isVisible(), "Line numbers should be hidden by default"
    print("✓ PASS")
    
    # Test 2: Show line numbers
    print("\nTest 2: Show line numbers")
    editor.set_line_numbers_visible(True)
    app.processEvents()  # Process events to update UI
    assert editor.line_number_widget.isVisible(), "Line numbers should be visible"
    assert editor.viewportMargins().left() > 0, "Viewport should have left margin"
    print(f"✓ PASS - Left margin: {editor.viewportMargins().left()}px")
    
    # Test 3: Hide line numbers
    print("\nTest 3: Hide line numbers")
    editor.set_line_numbers_visible(False)
    app.processEvents()  # Process events to update UI
    assert not editor.line_number_widget.isVisible(), "Line numbers should be hidden"
    assert editor.viewportMargins().left() == 0, "Viewport should have no left margin"
    print("✓ PASS")
    
    # Test 4: Settings persistence
    print("\nTest 4: Settings persistence")
    settings = QSettings("visxml.net", "LotusXmlEditor")
    
    # Save setting
    settings.setValue("flags/show_line_numbers", True)
    value = settings.value("flags/show_line_numbers", type=bool)
    assert value == True, "Setting should be saved as True"
    print("✓ PASS - Setting saved")
    
    # Clear setting
    settings.setValue("flags/show_line_numbers", False)
    value = settings.value("flags/show_line_numbers", type=bool)
    assert value == False, "Setting should be saved as False"
    print("✓ PASS - Setting cleared")
    
    print("\n" + "="*50)
    print("All tests passed! ✓")
    print("="*50)
    
    return 0

if __name__ == "__main__":
    sys.exit(test_line_numbers())
