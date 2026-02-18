
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.Qsci import QsciScintilla, QsciLexerXML

def test_encoding():
    app = QApplication(sys.argv)
    editor = QsciScintilla()
    editor.setUtf8(True)
    
    # Text with Cyrillic: "АБВ" (3 chars, 6 bytes)
    # Line 1: "АБВ\n" (4 chars)
    # Line 2: "DE"
    text = "АБВ\nDE"
    editor.setText(text)
    
    # Check text length
    py_len = len(text)
    print(f"Python text length: {py_len}")
    
    # Check line length
    line0_len = editor.lineLength(0)
    print(f"Scintilla Line 0 length: {line0_len}")
    
    # Set cursor to end of line 0 (before newline)
    editor.setCursorPosition(0, 3)
    line, index = editor.getCursorPosition()
    print(f"Cursor at end of 'АБВ': line={line}, index={index}")
    
    # Check positionFromLineIndex
    pos = editor.positionFromLineIndex(line, index)
    print(f"positionFromLineIndex: {pos}")
    
    # Check SCI_GETCURRENTPOS
    curr_pos = editor.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
    print(f"SCI_GETCURRENTPOS: {curr_pos}")

if __name__ == "__main__":
    test_encoding()
