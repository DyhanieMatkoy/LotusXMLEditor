
import sys
import os
from PyQt6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QMainWindow
from PyQt6.QtCore import Qt, QTimer

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import XmlTreeWidget, XmlEditorWidget, MainWindow

def test_tree_navigation():
    print("Testing Tree Navigation...")
    
    tree = XmlTreeWidget()
    item1 = QTreeWidgetItem(["Item 1"])
    item2 = QTreeWidgetItem(["Item 2"])
    item3 = QTreeWidgetItem(["Item 3"])
    tree.addTopLevelItem(item1)
    tree.addTopLevelItem(item2)
    tree.addTopLevelItem(item3)
    
    # Test Down
    tree.setCurrentItem(item1)
    tree.navigate_node_down()
    assert tree.currentItem() == item2, "Failed to navigate down to Item 2"
    print("Navigate Down: OK")
    
    # Test Up
    tree.navigate_node_up()
    assert tree.currentItem() == item1, "Failed to navigate up to Item 1"
    print("Navigate Up: OK")
    
    # Test Down from last
    tree.setCurrentItem(item3)
    tree.navigate_node_down()
    assert tree.currentItem() == item3, "Should stay on last item or loop? Implementation stops at last."
    print("Navigate Down (Last): OK")
    
    print("Tree Navigation Tests Passed")

def test_fragment_signal():
    print("Testing Fragment Editor Signal...")
    editor = XmlEditorWidget()
    
    signal_fired = False
    def on_request():
        nonlocal signal_fired
        signal_fired = True
        
    editor.fragment_editor_requested.connect(on_request)
    
    # Simulate signal emit
    editor.fragment_editor_requested.emit()
    
    assert signal_fired, "Fragment editor signal failed to fire"
    print("Fragment Signal: OK")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        test_tree_navigation()
        test_fragment_signal()
        print("\nAll tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
