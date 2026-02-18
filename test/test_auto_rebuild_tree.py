"""
Test script for AutoRebuildTree feature
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

def test_auto_rebuild_tree_setting():
    """Test that AutoRebuildTree setting is properly saved and loaded"""
    app = QApplication(sys.argv)
    
    # Test saving setting
    settings = QSettings("visxml.net", "LotusXmlEditor")
    
    # Test 1: Save auto_rebuild_tree as True
    settings.setValue("flags/auto_rebuild_tree", True)
    value = settings.value("flags/auto_rebuild_tree", False, type=bool)
    assert value == True, f"Expected True, got {value}"
    print("✓ Test 1 passed: auto_rebuild_tree saved as True")
    
    # Test 2: Save auto_rebuild_tree as False
    settings.setValue("flags/auto_rebuild_tree", False)
    value = settings.value("flags/auto_rebuild_tree", True, type=bool)
    assert value == False, f"Expected False, got {value}"
    print("✓ Test 2 passed: auto_rebuild_tree saved as False")
    
    # Test 3: Default value when not set
    settings.remove("flags/auto_rebuild_tree")
    value = settings.value("flags/auto_rebuild_tree", True, type=bool)
    assert value == True, f"Expected True (default), got {value}"
    print("✓ Test 3 passed: auto_rebuild_tree defaults to True")
    
    print("\n✓ All tests passed!")
    
    # Cleanup
    settings.setValue("flags/auto_rebuild_tree", True)  # Reset to default

if __name__ == "__main__":
    test_auto_rebuild_tree_setting()
