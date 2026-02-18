
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.Qsci import QsciScintilla, QsciLexerHTML

def test_lexer_styles():
    app = QApplication(sys.argv)
    editor = QsciScintilla()
    lexer = QsciLexerHTML()
    editor.setLexer(lexer)
    
    xml_content = '<root attr="val">text</root>'
    editor.setText(xml_content)
    
    # Force styling
    # editor.recolor() # QScintilla might do this async or on show.
    # We might need to show it to get it to lex.
    editor.show()
    
    # Wait a bit or force lexing
    # Scintilla lexing happens on idle usually.
    
    print("Content:", xml_content)
    print("Styles:")
    
    # We need to access the raw Scintilla object to get style at position
    # editor.SendScintilla(QsciScintilla.SCI_GETSTYLEAT, pos)
    
    # Let's map style IDs to names if possible
    # QsciLexerXML constants
    style_map = {
        QsciLexerHTML.Default: "Default",
        QsciLexerHTML.Tag: "Tag",
        QsciLexerHTML.Attribute: "Attribute",
        QsciLexerHTML.HTMLDoubleQuotedString: "DoubleString",
        QsciLexerHTML.HTMLSingleQuotedString: "SingleString",
        QsciLexerHTML.HTMLComment: "Comment",
        QsciLexerHTML.CDATA: "CDATA",
        QsciLexerHTML.Entity: "Entity",
        QsciLexerHTML.XMLStart: "XMLStart",
    }
    
    # QScintilla doesn't expose all Scintilla constants directly via QsciLexerXML sometimes.
    # But let's see what we get.
    
    # We'll just print the integer style IDs for now.
    
    # Using a timer to let the editor initialize and lex
    from PyQt6.QtCore import QTimer
    
    def check_styles():
        for i, char in enumerate(xml_content):
            # SCI_GETSTYLEAT = 2010
            style = editor.SendScintilla(2010, i)
            style_name = style_map.get(style, str(style))
            print(f"'{char}': {style_name}")
        app.quit()

    QTimer.singleShot(500, check_styles)
    app.exec()

if __name__ == "__main__":
    test_lexer_styles()
