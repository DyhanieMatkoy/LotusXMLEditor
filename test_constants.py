
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.Qsci import QsciScintilla

def test_constants():
    app = QApplication(sys.argv)
    try:
        print(f"SCI_SETMARGINMASK: {QsciScintilla.SCI_SETMARGINMASK}")
    except AttributeError:
        print("SCI_SETMARGINMASK not found in QsciScintilla")
        
    try:
        print(f"SCI_SETMARGINSENSITIVE: {QsciScintilla.SCI_SETMARGINSENSITIVE}")
    except AttributeError:
        print("SCI_SETMARGINSENSITIVE not found in QsciScintilla")

if __name__ == "__main__":
    test_constants()
