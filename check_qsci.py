
try:
    from PyQt6.Qsci import QsciScintilla, QsciLexerXML
    print("Import successful")
except ImportError as e:
    print(f"Import failed: {e}")
