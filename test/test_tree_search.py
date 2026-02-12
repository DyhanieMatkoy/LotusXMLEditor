#!/usr/bin/env python3
"""
Test for tree search filter functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from main import XmlTreeWidget

def test_tree_search_filter():
    """Test the tree search filter functionality"""
    app = QApplication(sys.argv)
    
    # Create tree widget
    tree = XmlTreeWidget()
    
    # Sample XML content
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<root>
    <group name="TestGroup">
        <item id="1">First Item</item>
        <item id="2">Second Item</item>
        <special>Special Node</special>
    </group>
    <metadata>
        <author>Test Author</author>
        <version>1.0</version>
    </metadata>
</root>"""
    
    # Populate tree
    print("Populating tree...")
    tree.populate_tree(sample_xml)
    
    # Test 1: Search for "item"
    print("\nTest 1: Searching for 'item'...")
    tree.set_search_filter("item")
    print(f"Found {len(tree.search_matches)} matches")
    assert len(tree.search_matches) > 0, "Should find items"
    
    # Test 2: Search for "special"
    print("\nTest 2: Searching for 'special'...")
    tree.set_search_filter("special")
    print(f"Found {len(tree.search_matches)} matches")
    assert len(tree.search_matches) > 0, "Should find special node"
    
    # Test 3: Search for "author"
    print("\nTest 3: Searching for 'author'...")
    tree.set_search_filter("author")
    print(f"Found {len(tree.search_matches)} matches")
    assert len(tree.search_matches) > 0, "Should find author node"
    
    # Test 4: Clear search
    print("\nTest 4: Clearing search...")
    tree.set_search_filter("")
    print(f"Matches after clear: {len(tree.search_matches)}")
    assert len(tree.search_matches) == 0, "Should have no matches after clear"
    
    # Test 5: Case insensitive search
    print("\nTest 5: Case insensitive search for 'ITEM'...")
    tree.set_search_filter("ITEM")
    print(f"Found {len(tree.search_matches)} matches")
    assert len(tree.search_matches) > 0, "Should find items (case insensitive)"
    
    print("\n✓ All tests passed!")
    
    # Show the tree for visual verification
    tree.show()
    tree.setWindowTitle("Tree Search Filter Test")
    tree.resize(600, 400)
    
    return app.exec()

if __name__ == '__main__':
    sys.exit(test_tree_search_filter())
