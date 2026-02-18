#!/usr/bin/env python3
"""
Test script for code folding functionality including levels
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.Qsci import QsciScintilla
from main import XmlEditorWidget

def run_test():
    app = QApplication(sys.argv)
    
    editor = XmlEditorWidget()
    editor.resize(800, 600)
    
    # Set test XML content with multiple levels
    test_xml = """<?xml version="1.0"?>
<root>
    <level1>
        <level2>
            <level3>Value 3</level3>
        </level2>
    </level1>
    <level1_b>
        <level2_b>Value 2b</level2_b>
    </level1_b>
</root>"""
    
    editor.set_content(test_xml)
    editor.set_line_numbers_visible(True)
    editor.show()
    
    def check_folding():
        print("\nChecking folding levels...")
        SC_FOLDLEVELBASE = 1024
        SC_FOLDLEVELNUMBERMASK = 0x0FFF
        SC_FOLDLEVELHEADERFLAG = 0x2000
        
        # Verify levels are calculated
        levels_found = False
        for i in range(editor.lines()):
            level_raw = editor.SendScintilla(editor.SCI_GETFOLDLEVEL, i)
            level = level_raw & SC_FOLDLEVELNUMBERMASK
            is_header = bool(level_raw & SC_FOLDLEVELHEADERFLAG)
            indent = level - SC_FOLDLEVELBASE
            
            # If we see any indent > 0, lexer is working
            if indent > 0:
                levels_found = True
                
            content = editor.text(i).strip()
            # print(f"Line {i+1}: Level={level} (Indent={indent}), Header={is_header}, Content='{content}'")
            
        if not levels_found:
            print("❌ Lexer hasn't calculated levels yet. Retrying...")
            QTimer.singleShot(500, check_folding)
            return

        print("✅ Levels calculated.")
        
        # Test Fold Level 1 (Indent 0)
        # Should fold <root> (Line 2) if it's level 1?
        # <root> is usually Level 1 (Indent 0).
        # <level1> is Level 2 (Indent 1).
        
        print("\nTesting Fold to Level 2...")
        editor.fold_to_level(2)
        
        # Line 3 (<level1>) should be visible (Level 2/Indent 1)
        # But wait, fold_to_level(2) means "Nodes at levels < 2 expanded, >= 2 folded".
        # Level 1 (Indent 0) is < 2. Expanded.
        # Level 2 (Indent 1) is >= 2. Folded.
        
        # Check if Line 3 (<level1>) is folded
        # Line 3 is <level1>. Indent 1 (Level 2).
        # It should be folded.
        
        # Line 2 is <root>. Indent 0 (Level 1).
        # It should be expanded.
        
        # Let's check line 2 (<root>)
        line_root = 1 # 0-based
        is_expanded_root = editor.SendScintilla(editor.SCI_GETFOLDEXPANDED, line_root)
        print(f"Root (Line 2) expanded: {is_expanded_root}")
        
        # Let's check line 3 (<level1>)
        line_l1 = 2 # 0-based
        is_expanded_l1 = editor.SendScintilla(editor.SCI_GETFOLDEXPANDED, line_l1)
        print(f"Level1 (Line 3) expanded: {is_expanded_l1}")
        
        # If line 3 is folded, it is NOT expanded.
        # So we expect is_expanded_l1 to be False.
        
        if not is_expanded_l1:
            print("✅ Level 1 node is folded correctly (as it is >= target level 2? Wait.)")
            # My logic: fold_to_level(2).
            # indent < 1 -> expand.
            # indent >= 1 -> fold.
            
            # Line 3 is Indent 1. 1 >= 1. So it folds.
            pass
        else:
             print("❌ Level 1 node is NOT folded!")

        print("\nTest Complete. Closing...")
        app.quit()

    # Give it some time to lex
    QTimer.singleShot(1000, check_folding)
    
    app.exec()

if __name__ == "__main__":
    run_test()
