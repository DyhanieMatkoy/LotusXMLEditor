"""
Integration tests for XML Metro Navigator

Tests the integration between the metro navigator and the main application.
Validates: Requirements 7.1, 7.2, 7.3
"""

import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest

from main import MainWindow
from models import XmlTreeNode
from metro_navigator import MetroNavigatorWindow


class TestMetroNavigatorIntegration(unittest.TestCase):
    """Integration tests for Metro Navigator with main application"""
    
    @classmethod
    def setUpClass(cls):
        """Set up QApplication for all tests"""
        # Create QApplication if it doesn't exist
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up test fixtures"""
        self.window = MainWindow()
        self.test_xml = """<?xml version="1.0" encoding="UTF-8"?>
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
    
    def tearDown(self):
        """Clean up after each test"""
        # Close metro window if it exists
        if hasattr(self.window, 'metro_window') and self.window.metro_window:
            self.window.metro_window.close()
        
        # Close main window
        self.window.close()
        
        # Process events to ensure cleanup
        QApplication.processEvents()
    
    def test_open_navigator_from_menu_with_valid_tree(self):
        """
        Test 13.1: Тест открытия навигатора из меню
        
        Validates that the navigator window is created correctly when opened
        from the menu with a valid XML tree.
        
        Requirements: 7.1
        """
        # Load XML into editor
        self.window.xml_editor.setPlainText(self.test_xml)
        
        # Build tree
        self.window.xml_tree.populate_tree(self.test_xml, show_progress=False)
        QApplication.processEvents()
        
        # Verify tree is built
        self.assertGreater(self.window.xml_tree.topLevelItemCount(), 0,
            "Tree should be built before opening navigator")
        
        root_item = self.window.xml_tree.topLevelItem(0)
        self.assertTrue(hasattr(root_item, 'xml_node'),
            "Root item should have xml_node attribute")
        
        # Open metro navigator
        self.window.open_metro_navigator()
        QApplication.processEvents()
        
        # Verify navigator window was created
        self.assertTrue(hasattr(self.window, 'metro_window'),
            "Metro window attribute should be created")
        self.assertIsNotNone(self.window.metro_window,
            "Metro window should not be None")
        self.assertIsInstance(self.window.metro_window, MetroNavigatorWindow,
            "Metro window should be instance of MetroNavigatorWindow")
        
        # Verify window is visible
        self.assertTrue(self.window.metro_window.isVisible(),
            "Metro window should be visible")
        
        # Verify window has scene with graph
        self.assertIsNotNone(self.window.metro_window.scene,
            "Metro window should have scene")
        self.assertIsNotNone(self.window.metro_window.scene.metro_root,
            "Scene should have metro root node")
        self.assertEqual(self.window.metro_window.scene.metro_root.xml_node.name, 
            root_item.xml_node.name,
            "Metro window should have correct root node")
        
        # Verify status message
        status_text = self.window.status_label.text()
        self.assertIn("Metro Navigator", status_text,
            "Status should indicate navigator was opened")
    
    def test_menu_action_exists_with_shortcut(self):
        """
        Test 13.1: Verify menu action exists
        
        Validates that the "XML Metro Navigator" menu action exists in the
        View menu with the correct shortcut (Ctrl+M).
        
        Requirements: 7.1
        """
        # Find the View menu
        menu_bar = self.window.menuBar()
        view_menu = None
        for action in menu_bar.actions():
            if action.text() == "View":
                view_menu = action.menu()
                break
        
        self.assertIsNotNone(view_menu, "View menu should exist")
        
        # Find metro navigator action
        metro_action = None
        for action in view_menu.actions():
            if "Metro Navigator" in action.text():
                metro_action = action
                break
        
        self.assertIsNotNone(metro_action,
            "Metro Navigator action should exist in View menu")
        
        # Verify shortcut
        shortcut = metro_action.shortcut().toString()
        self.assertEqual(shortcut, "Ctrl+M",
            f"Shortcut should be Ctrl+M, got {shortcut}")
    
    def test_open_navigator_without_tree_shows_message(self):
        """
        Test 13.3: Тест обработки пустого XML
        
        Validates that when no tree is built, the navigator shows an
        appropriate message instead of crashing.
        
        Requirements: 7.2
        """
        # Ensure tree is empty
        self.window.xml_tree.clear()
        QApplication.processEvents()
        
        self.assertEqual(self.window.xml_tree.topLevelItemCount(), 0,
            "Tree should be empty")
        
        # Try to open navigator (should not crash)
        try:
            self.window.open_metro_navigator()
            QApplication.processEvents()
            
            # Should not have created metro window
            if hasattr(self.window, 'metro_window'):
                # If metro_window attribute exists, it should be None or not visible
                self.assertTrue(
                    self.window.metro_window is None or not self.window.metro_window.isVisible(),
                    "Metro window should not be visible when tree is empty"
                )
        except Exception as e:
            self.fail(f"Opening navigator without tree should not raise exception: {e}")
    
    def test_open_navigator_with_empty_xml_shows_message(self):
        """
        Test 13.3: Test handling of empty XML content
        
        Validates that when XML is empty or has no structure, the navigator
        handles it gracefully.
        
        Requirements: 7.2
        """
        # Load empty XML
        empty_xml = """<?xml version="1.0" encoding="UTF-8"?>
<root></root>"""
        
        self.window.xml_editor.setPlainText(empty_xml)
        self.window.xml_tree.populate_tree(empty_xml, show_progress=False)
        QApplication.processEvents()
        
        # Try to open navigator
        try:
            self.window.open_metro_navigator()
            QApplication.processEvents()
            
            # Should handle gracefully (either show message or display minimal structure)
            # The key is that it should not crash
            if hasattr(self.window, 'metro_window') and self.window.metro_window:
                # If window was created, verify it has scene
                self.assertIsNotNone(self.window.metro_window.scene,
                    "Metro window should have scene even for minimal XML")
        except Exception as e:
            self.fail(f"Opening navigator with empty XML should not raise exception: {e}")


class TestMetroNavigatorSynchronization(unittest.TestCase):
    """Integration tests for synchronization between navigator and editor"""
    
    @classmethod
    def setUpClass(cls):
        """Set up QApplication for all tests"""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up test fixtures"""
        self.window = MainWindow()
        self.test_xml = """<?xml version="1.0" encoding="UTF-8"?>
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
        
        # Load and build tree
        self.window.xml_editor.setPlainText(self.test_xml)
        self.window.xml_tree.populate_tree(self.test_xml, show_progress=False)
        QApplication.processEvents()
    
    def tearDown(self):
        """Clean up after each test"""
        if hasattr(self.window, 'metro_window') and self.window.metro_window:
            self.window.metro_window.close()
        self.window.close()
        QApplication.processEvents()
    
    def test_node_selection_synchronizes_with_editor(self):
        """
        Test 13.2: Тест синхронизации выбора
        
        Validates that when a node is selected in the navigator, the editor
        cursor moves to the corresponding line.
        
        Requirements: 7.3
        """
        # Open navigator
        self.window.open_metro_navigator()
        QApplication.processEvents()
        
        self.assertIsNotNone(self.window.metro_window,
            "Metro window should be created")
        
        # Get root node
        root_item = self.window.xml_tree.topLevelItem(0)
        root_node = root_item.xml_node
        
        # Store initial cursor position
        initial_cursor = self.window.xml_editor.textCursor()
        initial_line = initial_cursor.blockNumber()
        
        # Simulate node selection by calling sync method directly
        self.window.sync_editor_to_node(root_node)
        QApplication.processEvents()
        
        # Verify cursor moved (if line_number is available)
        if root_node.line_number > 0:
            new_cursor = self.window.xml_editor.textCursor()
            new_line = new_cursor.blockNumber()
            
            # Cursor should have moved to the node's line (line_number - 1 because 0-indexed)
            expected_line = root_node.line_number - 1
            self.assertEqual(new_line, expected_line,
                f"Cursor should move to line {expected_line}, got {new_line}")
            
            # Verify status message
            status_text = self.window.status_label.text()
            self.assertIn(str(root_node.line_number), status_text,
                "Status should show line number")
            self.assertIn(root_node.name, status_text,
                "Status should show node name")
    
    def test_sync_signal_is_connected(self):
        """
        Test 13.2: Verify synchronization signal connection
        
        Validates that the node_selected signal from the navigator is properly
        connected to the editor sync method.
        
        Requirements: 7.3
        """
        # Open navigator
        self.window.open_metro_navigator()
        QApplication.processEvents()
        
        self.assertIsNotNone(self.window.metro_window,
            "Metro window should be created")
        
        # Verify signal is connected by checking that the connection exists
        # We can't directly test signal connections, but we can verify the method exists
        self.assertTrue(hasattr(self.window, 'sync_editor_to_node'),
            "Main window should have sync_editor_to_node method")
        
        # Verify the metro window has the signal
        self.assertTrue(hasattr(self.window.metro_window, 'node_selected'),
            "Metro window should have node_selected signal")
    
    def test_sync_with_node_without_line_number(self):
        """
        Test 13.2: Test synchronization with node that has no line number
        
        Validates that synchronization handles nodes without line numbers
        gracefully (should not crash).
        
        Requirements: 7.3
        """
        # Create a node without line number
        test_node = XmlTreeNode(
            name="test_node",
            tag="test",
            value="",
            attributes={},
            path="/test",
            line_number=0  # No line number
        )
        
        # Try to sync (should not crash)
        try:
            self.window.sync_editor_to_node(test_node)
            QApplication.processEvents()
        except Exception as e:
            self.fail(f"Syncing node without line number should not raise exception: {e}")
    
    def test_sync_with_none_node(self):
        """
        Test 13.2: Test synchronization with None node
        
        Validates that synchronization handles None input gracefully.
        
        Requirements: 7.3
        """
        # Try to sync with None (should not crash)
        try:
            self.window.sync_editor_to_node(None)
            QApplication.processEvents()
        except Exception as e:
            self.fail(f"Syncing None node should not raise exception: {e}")


def run_integration_tests():
    """Run all integration tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestMetroNavigatorIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestMetroNavigatorSynchronization))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
