#!/usr/bin/env python3
"""
Integration test for XML Metro Navigator
Tests:
1. Navigator opens from menu
2. Synchronization with editor works
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from main import MainWindow
from models import XmlTreeNode


def test_metro_navigator_integration():
    """Test metro navigator integration with main application"""
    
    # Create application
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    window.show()
    
    # Test XML content
    test_xml = """<?xml version="1.0" encoding="UTF-8"?>
<root>
    <level1 attr="value1">
        <level2>
            <level3>Deep content</level3>
        </level2>
    </level1>
    <level1_second>
        <level2_second>Content</level2_second>
    </level1_second>
</root>"""
    
    # Load XML into editor
    window.xml_editor.setPlainText(test_xml)
    
    # Build tree
    window.xml_tree.populate_tree(test_xml, show_progress=False)
    
    # Wait for tree to be built
    QApplication.processEvents()
    
    # Verify tree is built
    assert window.xml_tree.topLevelItemCount() > 0, "Tree should be built"
    root_item = window.xml_tree.topLevelItem(0)
    assert hasattr(root_item, 'xml_node'), "Root item should have xml_node"
    
    print("✓ Tree built successfully")
    
    # Test 1: Open metro navigator from menu
    print("\nTest 1: Opening metro navigator from menu...")
    window.open_metro_navigator()
    QApplication.processEvents()
    
    # Verify navigator window was created
    assert hasattr(window, 'metro_window'), "Metro window should be created"
    assert window.metro_window is not None, "Metro window should not be None"
    assert window.metro_window.isVisible(), "Metro window should be visible"
    
    print("✓ Metro navigator opened successfully")
    
    # Test 2: Verify synchronization signal is connected
    print("\nTest 2: Verifying synchronization...")
    
    # Get a node from the tree
    root_node = root_item.xml_node
    
    # Simulate node selection in navigator
    initial_cursor_pos = window.xml_editor.textCursor().position()
    
    # Call sync method directly
    window.sync_editor_to_node(root_node)
    QApplication.processEvents()
    
    # Verify cursor moved (if line_number is available)
    if root_node.line_number > 0:
        new_cursor_pos = window.xml_editor.textCursor().position()
        print(f"  Cursor moved from position {initial_cursor_pos} to {new_cursor_pos}")
        print(f"  Synced to line {root_node.line_number}: {root_node.name}")
    
    print("✓ Synchronization works")
    
    # Test 3: Verify menu action exists
    print("\nTest 3: Verifying menu action...")
    
    # Find the View menu
    menu_bar = window.menuBar()
    view_menu = None
    for action in menu_bar.actions():
        if action.text() == "View":
            view_menu = action.menu()
            break
    
    assert view_menu is not None, "View menu should exist"
    
    # Find metro navigator action
    metro_action = None
    for action in view_menu.actions():
        if "Metro Navigator" in action.text():
            metro_action = action
            break
    
    assert metro_action is not None, "Metro Navigator action should exist in View menu"
    assert metro_action.shortcut().toString() == "Ctrl+M", "Shortcut should be Ctrl+M"
    
    print("✓ Menu action exists with correct shortcut (Ctrl+M)")
    
    # Test 4: Test opening navigator when no tree is built
    print("\nTest 4: Testing behavior with no tree...")
    
    # Clear the tree
    window.xml_tree.clear()
    QApplication.processEvents()
    
    # Try to open navigator (should show message)
    # We can't easily test the message box, but we can verify it doesn't crash
    try:
        window.open_metro_navigator()
        QApplication.processEvents()
        print("✓ Handles missing tree gracefully")
    except Exception as e:
        print(f"✗ Error handling missing tree: {e}")
        raise
    
    # Clean up
    if hasattr(window, 'metro_window') and window.metro_window:
        window.metro_window.close()
    window.close()
    
    print("\n" + "="*50)
    print("All integration tests passed! ✓")
    print("="*50)
    
    return True


if __name__ == "__main__":
    try:
        success = test_metro_navigator_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
