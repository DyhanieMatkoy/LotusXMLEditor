
import sys
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from main import XmlEditorWidget

app = QApplication(sys.argv)

class TestHighlight(unittest.TestCase):
    def test_highlight_occurrences(self):
        editor = XmlEditorWidget()
        editor.setUtf8(True)
        text = "test text test"
        editor.setText(text)
        
        # Select "test"
        # QScintilla selection: line_from, index_from, line_to, index_to
        editor.setSelection(0, 0, 0, 4)
        
        # Manually call highlight (signal connection is in MainWindow usually, but here connected in init)
        # But we need to ensure the signal is emitted or call it directly
        editor.highlight_all_occurrences()
        
        # Check indicators
        # indicator 8
        # We can check if indicator is present at specific position
        # editor.SendScintilla(QsciScintilla.SCI_INDICATORVALUEAT, 8, position) -> value
        # But Qsci API might wrap it.
        # hasIndicator(indicator, line) -> bool? No.
        # Let's use SendScintilla
        
        # SCI_INDICATORVALUEAT = 2502 returns the value (which might be 0/1 or arbitrary).
        # SCI_INDICATORALLONFOR = 2506 returns a bitmap of all indicators at position.
        
        mask = editor.SendScintilla(2506, 0) # Position 0
        print(f"Mask at 0: {mask}")
        self.assertTrue(mask & (1 << 8), "Indicator 8 should be present at position 0")
        
        mask = editor.SendScintilla(2506, 5) # Position 5
        print(f"Mask at 5: {mask}")
        self.assertFalse(mask & (1 << 8), "Indicator 8 should NOT be present at position 5")
        
        mask = editor.SendScintilla(2506, 10) # Position 10
        print(f"Mask at 10: {mask}")
        self.assertTrue(mask & (1 << 8), "Indicator 8 should be present at position 10")

if __name__ == '__main__':
    unittest.main()
