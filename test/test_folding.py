#!/usr/bin/env python3
"""
Test script for code folding functionality
"""

import sys
from PyQt6.QtWidgets import QApplication
from main import XmlEditorWidget

def test_folding():
    """Test basic folding operations"""
    app = QApplication(sys.argv)
    
    editor = XmlEditorWidget()
    
    # Set test XML content
    test_xml = """<?xml version="1.0"?>
<root>
    <element1>
        <child1>Value 1</child1>
        <child2>Value 2</child2>
    </element1>
    <element2>
        <child3>Value 3</child3>
    </element2>
</root>"""
    
    editor.set_content(test_xml)
    editor.set_line_numbers_visible(True)
    
    # Print fold levels
    print("\nFold Levels:")
    SC_FOLDLEVELBASE = 1024
    SC_FOLDLEVELNUMBERMASK = 0x0FFF
    SC_FOLDLEVELHEADERFLAG = 0x2000
    
    for i in range(editor.lines()):
        level_raw = editor.SendScintilla(editor.SCI_GETFOLDLEVEL, i)
        level = level_raw & SC_FOLDLEVELNUMBERMASK
        is_header = bool(level_raw & SC_FOLDLEVELHEADERFLAG)
        indent = level - SC_FOLDLEVELBASE
        content = editor.text(i).strip()
        print(f"Line {i+1}: Level={level} (Indent={indent}), Header={is_header}, Content='{content}'")
    
    print("\nTesting fold operations...")
    
    # Test fold_lines
    print("Folding lines 3-5...")
    editor.fold_lines(3, 5)
    assert len(editor._folded_ranges) == 1, "Should have 1 folded range"
    print("✓ Fold successful")
    
    # Test unfold_lines
    print("Unfolding lines 3-5...")
    editor.unfold_lines(3, 5)
    assert len(editor._folded_ranges) == 0, "Should have 0 folded ranges"
    print("✓ Unfold successful")
    
    # Test fold multiple ranges
    print("Folding multiple ranges...")
    editor.fold_lines(3, 5)
    editor.fold_lines(7, 8)
    assert len(editor._folded_ranges) == 2, "Should have 2 folded ranges"
    print("✓ Multiple folds successful")
    
    # Test unfold_all
    print("Unfolding all...")
    editor.unfold_all()
    assert len(editor._folded_ranges) == 0, "Should have 0 folded ranges after unfold_all"
    print("✓ Unfold all successful")
    
    print("\n✅ All tests passed!")
    
    # Show the editor
    editor.show()
    editor.resize(800, 600)
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(test_folding())
