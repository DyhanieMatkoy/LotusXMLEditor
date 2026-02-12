import re
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QRadioButton, QButtonGroup, QPushButton, QWidget, 
                             QScrollArea, QLabel, QMenuBar, QStackedWidget, QComboBox)
from PyQt6.QtGui import QFont, QAction, QColor
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.Qsci import QsciScintilla, QsciLexerXML

from human_readable import get_human_readable_1c_xml

class FragmentEditorDialog(QDialog):
    """Dialog for editing/viewing XML fragments with selectable syntax highlighting."""
    
    save_requested = pyqtSignal(str)

    def __init__(self, text, language_registry, initial_language='XML', parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fragment Editor")
        self.resize(900, 600)
        self.language_registry = language_registry
        
        # Initialize editor first so menu actions can connect to it
        self.editor = QsciScintilla()
        self.editor.setUtf8(True)
        self.editor.setFont(QFont("Consolas", 11))
        self.editor.setText(text)
        self.editor.setWrapMode(QsciScintilla.WrapMode.WrapNone)
        
        # Configure margins (line numbers)
        self.editor.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.editor.setMarginWidth(0, "0000")
        self.editor.setMarginsForegroundColor(QColor("#808080"))
        self.editor.setMarginsBackgroundColor(QColor("#2b2b2b"))
        
        # Colors
        self.editor.setColor(QColor("#d4d4d4"))
        self.editor.setPaper(QColor("#1e1e1e"))
        self.editor.setCaretForegroundColor(QColor("white"))
        
        # Context Menu
        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self._show_context_menu)

        layout = QVBoxLayout(self)
        
        # Menu
        self.menubar = self._setup_menu()
        layout.setMenuBar(self.menubar)
        
        # Top bar with syntax selection
        top_layout = QHBoxLayout()
        
        # View Mode Selector
        top_layout.addWidget(QLabel("Mode:"))
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["Code Editor", "1C Human Readable"])
        self.view_mode_combo.currentIndexChanged.connect(self._on_view_mode_changed)
        top_layout.addWidget(self.view_mode_combo)
        
        top_layout.addSpacing(20)
        
        self.syntax_label = QLabel("Syntax:")
        top_layout.addWidget(self.syntax_label)
        
        self.syntax_group = QButtonGroup(self)
        self.syntax_group.buttonClicked.connect(self._on_syntax_changed)
        
        # Scroll area for radio buttons if there are many languages
        self.syntax_scroll = QScrollArea()
        self.syntax_scroll.setWidgetResizable(True)
        self.syntax_scroll.setFixedHeight(50)
        self.syntax_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QHBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(15)
        
        # XML option (always present)
        rb_xml = QRadioButton("XML")
        self.syntax_group.addButton(rb_xml)
        scroll_layout.addWidget(rb_xml)
        if initial_language == 'XML':
            rb_xml.setChecked(True)
            
        # Other languages from registry
        languages = self.language_registry.list()
        for lang_name in languages:
            rb = QRadioButton(lang_name)
            self.syntax_group.addButton(rb)
            scroll_layout.addWidget(rb)
            if lang_name == initial_language:
                rb.setChecked(True)
                
        scroll_layout.addStretch()
        self.syntax_scroll.setWidget(scroll_content)
        top_layout.addWidget(self.syntax_scroll)
        
        layout.addLayout(top_layout)
        
        # Stacked Widget for Editor and Viewer
        self.stack = QStackedWidget()
        self.stack.addWidget(self.editor)
        
        self.viewer_1c = QsciScintilla()
        self.viewer_1c.setUtf8(True)
        self.viewer_1c.setFont(QFont("Consolas", 11))
        self.viewer_1c.setReadOnly(True)
        self.viewer_1c.setMargins(0)
        self.viewer_1c.setMarginWidth(0, 0)
        self.viewer_1c.setMarginWidth(1, 0)
        # Match theme
        self.viewer_1c.setColor(QColor("#d4d4d4"))
        self.viewer_1c.setPaper(QColor("#1e1e1e"))
        self.stack.addWidget(self.viewer_1c)
        
        layout.addWidget(self.stack)
        
        # Bottom button bar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self._on_save)
        self.btn_save.setDefault(True)
        btn_layout.addWidget(self.btn_save)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
        
        # Apply initial highlighting
        self._apply_highlighting(initial_language)

    def _on_save(self):
        """Handle save button click"""
        self.save_requested.emit(self.editor.text())
        self.accept()

    def _setup_menu(self):
        menubar = QMenuBar()
        edit_menu = menubar.addMenu("Edit")
        
        undo_action = QAction("Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.editor.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.editor.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("Cut", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self.editor.cut)
        edit_menu.addAction(cut_action)
        
        copy_action = QAction("Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.editor.copy)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.editor.paste)
        edit_menu.addAction(paste_action)
        
        select_all_action = QAction("Select All", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.editor.selectAll)
        edit_menu.addAction(select_all_action)
        
        edit_menu.addSeparator()
        
        toggle_comment_action = QAction("Toggle Comment", self)
        toggle_comment_action.setShortcut("Ctrl+/")
        toggle_comment_action.triggered.connect(self.toggle_comment)
        edit_menu.addAction(toggle_comment_action)

        remove_empty_lines_action = QAction("Remove Empty Lines", self)
        remove_empty_lines_action.triggered.connect(self.remove_empty_lines)
        edit_menu.addAction(remove_empty_lines_action)
        
        return menubar

    def remove_empty_lines(self):
        if not self.editor.hasSelectedText():
            return
            
        self.editor.beginUndoAction()
        try:
            # Get selection range
            lf, if_, lt, it = self.editor.getSelection()
            if lf == -1: return

            selected_text = self.editor.selectedText()
            if not selected_text: return

            lines = selected_text.splitlines()
            # Filter out empty lines or lines with only whitespace
            non_empty_lines = [line for line in lines if line.strip()]
            
            # Join with newlines
            new_text = '\n'.join(non_empty_lines)
            
            if new_text == selected_text:
                return
                
            self.editor.replaceSelection(new_text)
        finally:
            self.editor.endUndoAction()

    def _show_context_menu(self, position):
        # QScintilla doesn't return a QMenu directly easily, 
        # but we can create one.
        menu = self.editor.createStandardContextMenu()
        if not menu: # Fallback if QScintilla returns None (unlikely)
            from PyQt6.QtWidgets import QMenu
            menu = QMenu(self)
            
        menu.addSeparator()
        
        toggle_action = menu.addAction("Toggle Comment")
        toggle_action.setShortcut("Ctrl+/")
        toggle_action.triggered.connect(self.toggle_comment)
        
        remove_lines_action = menu.addAction("Remove Empty Lines")
        remove_lines_action.triggered.connect(self.remove_empty_lines)
        
        menu.exec(self.editor.mapToGlobal(position))

    def toggle_comment(self):
        """Toggle comment based on current syntax language."""
        try:
            current_lang = 'XML'
            if self.syntax_group.checkedButton():
                current_lang = self.syntax_group.checkedButton().text()
            
            # Check for 1c-Ent syntax (case-insensitive check)
            is_1c = '1c' in current_lang.lower() or 'ent' in current_lang.lower()
            
            if is_1c:
                self._toggle_line_comments(prefix="//")
            else:
                self._toggle_block_comment()
        except Exception as e:
            print(f"Toggle comment error: {e}")

    def _toggle_line_comments(self, prefix: str = "//"):
        """Toggle comment prefix at beginning of selected lines or current line."""
        self.editor.beginUndoAction()
        try:
            lf, if_, lt, it = self.editor.getSelection()
            
            if lf == -1:
                # No selection, use current line
                lf, _ = self.editor.getCursorPosition()
                lt = lf
            else:
                # If selection ends at start of line, don't include that line
                if lt > lf and it == 0:
                    lt -= 1
            
            # Analyze lines
            all_commented = True
            has_content = False
            
            for i in range(lf, lt + 1):
                text = self.editor.text(i)
                stripped = text.lstrip()
                if stripped:
                    has_content = True
                    if not stripped.startswith(prefix):
                        all_commented = False
                        break
            
            should_uncomment = all_commented and has_content
            
            for i in range(lf, lt + 1):
                text = self.editor.text(i)
                stripped = text.lstrip()
                
                if should_uncomment:
                    if stripped.startswith(prefix):
                        # Find position of prefix
                        prefix_pos = text.find(prefix)
                        if prefix_pos != -1:
                            # Delete prefix
                            self.editor.deleteRange(i, prefix_pos, i, prefix_pos + len(prefix))
                else:
                    if text.strip(): # Comment only if not empty
                        # Insert at start of non-whitespace
                        indent = len(text) - len(stripped)
                        self.editor.insertAt(prefix, i, indent)
                    elif not text.strip() and lf == lt: 
                         # If single empty line, just insert
                         self.editor.insertAt(prefix, i, 0)

        except Exception as e:
            print(f"Toggle line comments error: {e}")
        finally:
            self.editor.endUndoAction()

    def _toggle_block_comment(self, start_marker="<!--", end_marker="-->"):
        """Toggle block comment around selection or current line."""
        self.editor.beginUndoAction()
        try:
            if not self.editor.hasSelectedText():
                # Select current line
                line, _ = self.editor.getCursorPosition()
                len_line = self.editor.lineLength(line)
                self.editor.setSelection(line, 0, line, len_line)
            
            text = self.editor.selectedText()
            if not text: return

            # Check if already commented (simple regex check)
            # Note: This regex is simplified compared to original but should work for basic cases
            pattern = fr"^\s*{re.escape(start_marker)}[\s\S]*{re.escape(end_marker)}\s*$"
            if re.match(pattern, text):
                # Unwrap
                s_idx = text.find(start_marker)
                e_idx = text.rfind(end_marker)
                
                if s_idx != -1 and e_idx != -1 and e_idx > s_idx:
                    inner = text[s_idx+len(start_marker):e_idx]
                    # Try to remove padding spaces
                    if inner.startswith(' ') and inner.endswith(' ') and len(inner) >= 2:
                         inner = inner[1:-1]
                    
                    pre = text[:s_idx]
                    post = text[e_idx+len(end_marker):]
                    new_text = pre + inner + post
                    self.editor.replaceSelection(new_text)
            else:
                # Wrap
                # Handle trailing newline if present to avoid messing up block structure
                # QScintilla selectedText() might not include trailing newline if selected strictly?
                # But if we selected full line, it might.
                
                self.editor.replaceSelection(f"{start_marker} {text} {end_marker}")
                
        except Exception as e:
            print(f"Toggle block comment error: {e}")
        finally:
            self.editor.endUndoAction()

    def _on_syntax_changed(self, button):
        lang = button.text()
        self._apply_highlighting(lang)

    def _apply_highlighting(self, lang_name):
        try:
            # For now, only XML is supported with QScintilla lexer
            # TODO: Implement other lexers or map UDLs
            
            if lang_name == 'XML':
                lexer = QsciLexerXML(self.editor)
                lexer.setDefaultFont(QFont("Consolas", 11))
                
                # Dark theme colors (matching main editor)
                lexer.setColor(QColor("#d4d4d4"), QsciLexerXML.Default)
                lexer.setColor(QColor("#569cd6"), QsciLexerXML.Tag)
                lexer.setColor(QColor("#9cdcfe"), QsciLexerXML.Attribute) # VSCode style
                lexer.setColor(QColor("#ce9178"), QsciLexerXML.HTMLDoubleQuotedString)
                lexer.setColor(QColor("#ce9178"), QsciLexerXML.HTMLSingleQuotedString)
                lexer.setColor(QColor("#6a9955"), QsciLexerXML.HTMLComment)
                lexer.setColor(QColor("#dcdcaa"), QsciLexerXML.CDATA)
                
                self.editor.setLexer(lexer)
            else:
                self.editor.setLexer(None)
                self.editor.setFont(QFont("Consolas", 11))
                self.editor.setColor(QColor("#d4d4d4"))
                self.editor.setPaper(QColor("#1e1e1e"))
                
        except Exception as e:
            print(f"Fragment highlighting error: {e}")
    
    def _on_view_mode_changed(self, index):
        if index == 0: # Code Editor
            self.stack.setCurrentIndex(0)
            self.syntax_label.setVisible(True)
            self.syntax_scroll.setVisible(True)
        else: # 1C Human Readable
            # Generate view
            xml_text = self.editor.text()
            readable_text = get_human_readable_1c_xml(xml_text)
            self.viewer_1c.setText(readable_text)
            
            self.stack.setCurrentIndex(1)
            self.syntax_label.setVisible(False)
            self.syntax_scroll.setVisible(False)
    
    def closeEvent(self, event):
        """Handle dialog close event safely"""
        # QScintilla cleanup not strictly required like highlighter, but good practice
        super().closeEvent(event)
