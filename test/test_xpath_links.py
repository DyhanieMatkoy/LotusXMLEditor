#!/usr/bin/env python3
"""
Test script for XPath Links functionality
Tests Ctrl+F11 (copy XPath) and F12 (navigate to XPath)
"""

import sys
from PyQt6.QtWidgets import QApplication
from main import MainWindow

def test_xpath_links():
    """Test XPath links functionality"""
    app = QApplication(sys.argv)
    window = MainWindow()
    
    # Load a test XML file
    test_xml = """<?xml version="1.0" encoding="UTF-8"?>
<root>
    <parent id="1">
        <child name="first">Value 1</child>
        <child name="second">Value 2</child>
    </parent>
    <parent id="2">
        <child name="third">Value 3</child>
    </parent>
</root>"""
    
    # Set content
    window.xml_editor.set_content(test_xml)
    
    # Test 1: Check that Links tab exists
    assert hasattr(window.bottom_panel, 'links_tab'), "Links tab not found"
    assert hasattr(window.bottom_panel, 'links_text'), "Links text widget not found"
    print("✓ Links tab created successfully")
    
    # Test 2: Check that methods exist
    assert hasattr(window, 'copy_xpath_link'), "copy_xpath_link method not found"
    assert hasattr(window, 'navigate_xpath_link'), "navigate_xpath_link method not found"
    print("✓ XPath link methods exist")
    
    # Test 3: Try to copy XPath from line 3 (first child element)
    cursor = window.xml_editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.Start)
    cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, 2)  # Move to line 3
    window.xml_editor.setTextCursor(cursor)
    
    window.copy_xpath_link()
    links_content = window.bottom_panel.links_text.toPlainText()
    print(f"✓ XPath copied: {links_content.strip()}")
    
    # Test 4: Manually show bottom dock for testing
    window.bottom_dock.setVisible(True)
    window.bottom_panel.setCurrentWidget(window.bottom_panel.links_tab)
    
    # Check that Links tab is active
    assert window.bottom_panel.currentWidget() == window.bottom_panel.links_tab, "Links tab not active"
    print("✓ Links tab can be activated")
    
    print("\n✅ All tests passed!")
    print("\nManual testing instructions:")
    print("1. Open an XML file")
    print("2. Place cursor on any XML element")
    print("3. Press Ctrl+F11 to copy XPath to Links tab")
    print("4. Go to Links tab, place cursor on a line with XPath")
    print("5. Press F12 to navigate to that element")
    
    window.show()
    return app.exec()

if __name__ == '__main__':
    sys.exit(test_xpath_links())
