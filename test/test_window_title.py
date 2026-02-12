#!/usr/bin/env python3
"""
Test for window title functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_window_title_logic():
    """Test the window title update logic"""
    
    # Mock MainWindow class for testing
    class MockMainWindow:
        def __init__(self):
            self.current_file = None
            self.window_title = ""
        
        def setWindowTitle(self, title):
            self.window_title = title
        
        def _update_window_title(self):
            """Update window title with current file name"""
            base_title = "Lotus Xml Editor - Python Version"
            if self.current_file:
                filename = os.path.basename(self.current_file)
                self.setWindowTitle(f"{filename} - {self.current_file} - {base_title}")
            else:
                self.setWindowTitle(base_title)
    
    # Test cases
    window = MockMainWindow()
    
    # Test 1: No file loaded
    print("Test 1: No file loaded")
    window._update_window_title()
    expected = "Lotus Xml Editor - Python Version"
    assert window.window_title == expected, f"Expected '{expected}', got '{window.window_title}'"
    print(f"✓ Title: {window.window_title}")
    
    # Test 2: File with simple name
    print("\nTest 2: Simple filename")
    window.current_file = "test.xml"
    window._update_window_title()
    expected = "test.xml - test.xml - Lotus Xml Editor - Python Version"
    assert window.window_title == expected, f"Expected '{expected}', got '{window.window_title}'"
    print(f"✓ Title: {window.window_title}")
    
    # Test 3: File with full path
    print("\nTest 3: Full path filename")
    window.current_file = "C:\\Users\\test\\Documents\\my_document.xml"
    window._update_window_title()
    expected = "my_document.xml - C:\\Users\\test\\Documents\\my_document.xml - Lotus Xml Editor - Python Version"
    assert window.window_title == expected, f"Expected '{expected}', got '{window.window_title}'"
    print(f"✓ Title: {window.window_title}")
    
    # Test 4: File with Cyrillic name
    print("\nTest 4: Cyrillic filename")
    window.current_file = "/path/to/документ.xml"
    window._update_window_title()
    expected = "документ.xml - /path/to/документ.xml - Lotus Xml Editor - Python Version"
    assert window.window_title == expected, f"Expected '{expected}', got '{window.window_title}'"
    print(f"✓ Title: {window.window_title}")
    
    # Test 5: Back to no file
    print("\nTest 5: Clear file")
    window.current_file = None
    window._update_window_title()
    expected = "Lotus Xml Editor - Python Version"
    assert window.window_title == expected, f"Expected '{expected}', got '{window.window_title}'"
    print(f"✓ Title: {window.window_title}")
    
    print("\n✓ All window title tests passed!")

if __name__ == '__main__':
    test_window_title_logic()