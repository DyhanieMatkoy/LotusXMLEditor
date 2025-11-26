"""
XML Syntax Highlighter for PyQt6
Provides syntax highlighting for XML content in the editor
"""

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QColor, QTextCharFormat, QFont, QSyntaxHighlighter


class XmlHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for XML content
    
    Adds optional visibility toggles for specific token categories. The toggles work by
    setting foreground colors to match the editor background, effectively rendering the
    selected token types invisible without altering the underlying text.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Define highlighting rules
        self.highlighting_rules = []
        self.is_dark_theme = False
        
        # Visibility toggles (default visible)
        self.hide_symbols = False  # Angle brackets '<' and '>'
        self.hide_tags = False     # Element tag names
        self.hide_values = False   # Attribute values (both '"value"' and '\'value\'')
        
        # Background color used to "hide" tokens (updated by set_dark_theme)
        self.bg_color = QColor("#ffffff")
        
        # XML declaration
        xml_declaration_format = QTextCharFormat()
        xml_declaration_format.setForeground(QColor("#0000FF"))  # Blue
        xml_declaration_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'<\?xml.*?\?>'),
            xml_declaration_format
        ))
        
        # XML comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#008000"))  # Green
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((
            QRegularExpression(r'<!--.*?-->'),
            comment_format
        ))
        
        # XML element names (including Cyrillic characters)
        element_format = QTextCharFormat()
        element_format.setForeground(QColor("#A31515"))  # Dark red
        element_format.setFontWeight(QFont.Weight.Bold)
        # Cyrillic Unicode ranges: \u0400-\u04FF (basic Cyrillic), \u0500-\u052F (Cyrillic supplement)
        self.highlighting_rules.append((
            QRegularExpression(r'<[/?\s]*([A-Za-zЀ-ӿԀ-ԯ_:][A-Za-z0-9Ѐ-ӿԀ-ԯ_:\-]*)'),
            element_format
        ))
        
        # XML attribute names (including Cyrillic characters)
        attribute_format = QTextCharFormat()
        attribute_format.setForeground(QColor("#FF0000"))  # Red
        # Cyrillic Unicode ranges: \u0400-\u04FF (basic Cyrillic), \u0500-\u052F (Cyrillic supplement)
        self.highlighting_rules.append((
            QRegularExpression(r'\s([A-Za-zЀ-ӿԀ-ԯ_:][A-Za-z0-9Ѐ-ӿԀ-ԯ_:\-]*)\s*='),
            attribute_format
        ))
        
        # XML attribute values
        attribute_value_format = QTextCharFormat()
        attribute_value_format.setForeground(QColor("#0000FF"))  # Blue
        self.highlighting_rules.append((
            QRegularExpression(r'="([^"]*)"'),
            attribute_value_format
        ))
        
        # XML attribute values (single quotes)
        attribute_value_single_format = QTextCharFormat()
        attribute_value_single_format.setForeground(QColor("#0000FF"))  # Blue
        self.highlighting_rules.append((
            QRegularExpression(r"='([^']*)'"),
            attribute_value_single_format
        ))
        
        # XML processing instructions (including Cyrillic characters)
        pi_format = QTextCharFormat()
        pi_format.setForeground(QColor("#808080"))  # Gray
        pi_format.setFontItalic(True)
        # Cyrillic Unicode ranges: \u0400-\u04FF (basic Cyrillic), \u0500-\u052F (Cyrillic supplement)
        self.highlighting_rules.append((
            QRegularExpression(r'<\?[A-Za-zЀ-ӿԀ-ԯ_:][A-Za-z0-9Ѐ-ӿԀ-ԯ_:\-]*.*?\?>'),
            pi_format
        ))
        
        # XML CDATA sections
        cdata_format = QTextCharFormat()
        cdata_format.setForeground(QColor("#8B4513"))  # Brown
        cdata_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'<\!\[CDATA\[.*?\]\]>'),
            cdata_format
        ))
        
        # XML DOCTYPE declaration
        doctype_format = QTextCharFormat()
        doctype_format.setForeground(QColor("#800080"))  # Purple
        doctype_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'<\!DOCTYPE.*?>'),
            doctype_format
        ))
        
        # XML entity references (including Cyrillic characters)
        entity_format = QTextCharFormat()
        entity_format.setForeground(QColor("#FF00FF"))  # Magenta
        entity_format.setFontWeight(QFont.Weight.Bold)
        # Cyrillic Unicode ranges: \u0400-\u04FF (basic Cyrillic), \u0500-\u052F (Cyrillic supplement)
        self.highlighting_rules.append((
            QRegularExpression(r'&[A-Za-zЀ-ӿԀ-ԯ_:][A-Za-z0-9Ѐ-ӿԀ-ԯ_:\-]*;'),
            entity_format
        ))
        
        # XML numeric character references
        numeric_entity_format = QTextCharFormat()
        numeric_entity_format.setForeground(QColor("#FF00FF"))  # Magenta
        numeric_entity_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'&#\d+;'),
            numeric_entity_format
        ))
        
        # XML hex character references
        hex_entity_format = QTextCharFormat()
        hex_entity_format.setForeground(QColor("#FF00FF"))  # Magenta
        hex_entity_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'&#x[0-9A-Fa-f]+;'),
            hex_entity_format
        ))
        
        # Numbers in attribute values
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#000080"))  # Navy
        self.highlighting_rules.append((
            QRegularExpression(r'="(\d+(\.\d+)?)"'),
            number_format
        ))
        
        # Boolean values in attributes
        boolean_format = QTextCharFormat()
        boolean_format.setForeground(QColor("#800000"))  # Maroon
        boolean_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'="(true|false)"', QRegularExpression.PatternOption.CaseInsensitiveOption),
            boolean_format
        ))
        
        # XML namespace declarations (including Cyrillic characters)
        namespace_format = QTextCharFormat()
        namespace_format.setForeground(QColor("#008080"))  # Teal
        namespace_format.setFontWeight(QFont.Weight.Bold)
        # Cyrillic Unicode ranges: \u0400-\u04FF (basic Cyrillic), \u0500-\u052F (Cyrillic supplement)
        self.highlighting_rules.append((
            QRegularExpression(r'xmlns(?::[A-Za-zЀ-ӿԀ-ԯ_][A-Za-z0-9Ѐ-ӿԀ-ԯ_:\-]*)?\s*='),
            namespace_format
        ))
    
    def set_visibility_options(self, hide_symbols: bool = None, hide_tags: bool = None, hide_values: bool = None):
        """Update visibility toggles and rebuild highlighting rules.
        
        - hide_symbols: when True, angle brackets '<' and '>' are rendered with background color.
        - hide_tags: when True, element tag names are rendered with background color.
        - hide_values: when True, attribute values (both quoted types), numbers, and booleans are rendered with background color.
        """
        if hide_symbols is not None:
            self.hide_symbols = hide_symbols
        if hide_tags is not None:
            self.hide_tags = hide_tags
        if hide_values is not None:
            self.hide_values = hide_values
        
        # Block signals during rehighlight to avoid triggering textChanged
        doc = self.document()
        if doc:
            doc.blockSignals(True)
        
        # Rebuild rules using current theme colors and visibility toggles
        self.set_dark_theme(self.is_dark_theme)
        
        # Restore signals
        if doc:
            doc.blockSignals(False)
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text"""
        # Apply each highlighting rule
        for pattern, format in self.highlighting_rules:
            match = pattern.globalMatch(text)
            while match.hasNext():
                m = match.next()
                start = m.capturedStart()
                length = m.capturedLength()
                self.setFormat(start, length, format)
        
        # Handle multi-line comments separately
        self._highlight_multiline_comments(text)
        
    def _highlight_multiline_comments(self, text: str):
        """Highlight XML comments that span multiple text blocks.
        
        Tracks whether the previous block was inside a comment using block state,
        and applies the comment format across block boundaries to cover sequences
        like <!-- ... --> spanning multiple lines.
        """
        comment_format = QTextCharFormat()
        if self.is_dark_theme:
            comment_format.setForeground(QColor("#6A9955"))  # Light green (dark theme)
        else:
            comment_format.setForeground(QColor("#008000"))  # Green (light theme)
        comment_format.setFontItalic(True)
        
        start_tag = "<!--"
        end_tag = "-->"
        
        in_comment = (self.previousBlockState() == 1)
        pos = 0
        text_len = len(text)
        
        # Continue a comment from previous block
        if in_comment:
            end_idx = text.find(end_tag, pos)
            if end_idx == -1:
                # Entire block is inside comment
                self.setFormat(0, text_len, comment_format)
                self.setCurrentBlockState(1)
                return
            else:
                # Comment ends in this block
                self.setFormat(0, end_idx + len(end_tag), comment_format)
                pos = end_idx + len(end_tag)
                self.setCurrentBlockState(0)
                in_comment = False
        
        # Find new comment starts; if no end, mark continuation
        while True:
            start_idx = text.find(start_tag, pos)
            if start_idx == -1:
                break
            end_idx = text.find(end_tag, start_idx)
            if end_idx == -1:
                self.setFormat(start_idx, text_len - start_idx, comment_format)
                self.setCurrentBlockState(1)
                return
            else:
                self.setFormat(start_idx, end_idx + len(end_tag) - start_idx, comment_format)
                pos = end_idx + len(end_tag)
        
        # Not in a comment at end of processing
        self.setCurrentBlockState(0)
    
    def set_dark_theme(self, dark_theme=True):
        """Toggle between light and dark theme colors, and apply visibility overrides.
        
        This rebuilds the highlighting rules with theme-appropriate colors, then applies
        visibility toggles by overriding specific token colors to the editor background.
        """
        self.is_dark_theme = dark_theme
        
        # Block signals during rehighlight to avoid triggering textChanged
        doc = self.document()
        if doc:
            doc.blockSignals(True)
        
        # Update background color used to hide tokens
        self.bg_color = QColor("#1e1e1e") if dark_theme else QColor("#ffffff")
        
        # Base theme colors
        if dark_theme:
            xml_declaration_color = QColor("#569CD6")  # Light blue
            comment_color = QColor("#6A9955")         # Light green
            element_color = QColor("#4FC1FF")         # Light cyan
            attribute_color = QColor("#9CDCFE")       # Light blue
            attribute_value_color = QColor("#CE9178") # Light orange
            pi_color = QColor("#808080")              # Gray
            cdata_color = QColor("#D7BA7D")           # Light yellow
            doctype_color = QColor("#C586C0")         # Light purple
            entity_color = QColor("#DCDCAA")          # Light yellow
            number_color = QColor("#B5CEA8")          # Light green
            boolean_color = QColor("#569CD6")         # Light blue
            namespace_color = QColor("#4EC9B0")       # Light teal
            bracket_color = QColor("#808080")         # Gray
        else:
            xml_declaration_color = QColor("#0000FF")  # Blue
            comment_color = QColor("#008000")          # Green
            element_color = QColor("#A31515")          # Dark red
            attribute_color = QColor("#FF0000")        # Red
            attribute_value_color = QColor("#0000FF")  # Blue
            pi_color = QColor("#808080")               # Gray
            cdata_color = QColor("#8B4513")           # Brown
            doctype_color = QColor("#800080")          # Purple
            entity_color = QColor("#FF00FF")           # Magenta
            number_color = QColor("#000080")           # Navy
            boolean_color = QColor("#800000")          # Maroon
            namespace_color = QColor("#008080")        # Teal
            bracket_color = QColor("#808080")          # Gray
        
        # Apply visibility overrides
        if self.hide_tags:
            element_color = self.bg_color
        if self.hide_values:
            attribute_value_color = self.bg_color
            number_color = self.bg_color
            boolean_color = self.bg_color
        if self.hide_symbols:
            bracket_color = self.bg_color
        
        # Rebuild the highlighting rules with updated colors
        self.highlighting_rules = []
        
        # XML declaration
        xml_declaration_format = QTextCharFormat()
        xml_declaration_format.setForeground(xml_declaration_color)
        xml_declaration_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'<\?xml.*?\?>'),
            xml_declaration_format
        ))
        
        # XML comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(comment_color)
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((
            QRegularExpression(r'<!--.*?-->'),
            comment_format
        ))
        
        # XML element names (including Cyrillic characters)
        element_format = QTextCharFormat()
        element_format.setForeground(element_color)
        element_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'<[/?\s]*([A-Za-zЀ-ӿԀ-ԯ_:][A-Za-z0-9Ѐ-ӿԀ-ԯ_:\-]*)'),
            element_format
        ))
        
        # XML attribute names (including Cyrillic characters)
        attribute_format = QTextCharFormat()
        attribute_format.setForeground(attribute_color)
        self.highlighting_rules.append((
            QRegularExpression(r'\s([A-Za-zЀ-ӿԀ-ԯ_:][A-Za-z0-9Ѐ-ӿԀ-ԯ_:\-]*)\s*='),
            attribute_format
        ))
        
        # XML attribute values (double quotes)
        attribute_value_format = QTextCharFormat()
        attribute_value_format.setForeground(attribute_value_color)
        self.highlighting_rules.append((
            QRegularExpression(r'="([^"]*)"'),
            attribute_value_format
        ))
        
        # XML attribute values (single quotes)
        attribute_value_single_format = QTextCharFormat()
        attribute_value_single_format.setForeground(attribute_value_color)
        self.highlighting_rules.append((
            QRegularExpression(r"='([^']*)'"),
            attribute_value_single_format
        ))
        
        # XML processing instructions
        pi_format = QTextCharFormat()
        pi_format.setForeground(pi_color)
        pi_format.setFontItalic(True)
        self.highlighting_rules.append((
            QRegularExpression(r'<\?[A-Za-zЀ-ӿԀ-ԯ_:][A-Za-z0-9Ѐ-ӿԀ-ԯ_:\-]*.*?\?>'),
            pi_format
        ))
        
        # XML CDATA sections
        cdata_format = QTextCharFormat()
        cdata_format.setForeground(cdata_color)
        cdata_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'<\!\[CDATA\[.*?\]\]>'),
            cdata_format
        ))
        
        # XML DOCTYPE declaration
        doctype_format = QTextCharFormat()
        doctype_format.setForeground(doctype_color)
        doctype_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'<\!DOCTYPE.*?>'),
            doctype_format
        ))
        
        # XML entity references
        entity_format = QTextCharFormat()
        entity_format.setForeground(entity_color)
        entity_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'&[A-Za-zЀ-ӿԀ-ԯ_:][A-Za-z0-9Ѐ-ӿԀ-ԯ_:\-]*;'),
            entity_format
        ))
        
        # XML numeric character references
        numeric_entity_format = QTextCharFormat()
        numeric_entity_format.setForeground(entity_color)
        numeric_entity_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'&#\d+;'),
            numeric_entity_format
        ))
        
        # XML hex character references
        hex_entity_format = QTextCharFormat()
        hex_entity_format.setForeground(entity_color)
        hex_entity_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'&#x[0-9A-Fa-f]+;'),
            hex_entity_format
        ))
        
        # Numbers in attribute values
        number_format = QTextCharFormat()
        number_format.setForeground(number_color)
        self.highlighting_rules.append((
            QRegularExpression(r'="(\d+(\.\d+)?)"'),
            number_format
        ))
        
        # Boolean values in attributes
        boolean_format = QTextCharFormat()
        boolean_format.setForeground(boolean_color)
        boolean_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'="(true|false)"', QRegularExpression.PatternOption.CaseInsensitiveOption),
            boolean_format
        ))
        
        # XML namespace declarations
        namespace_format = QTextCharFormat()
        namespace_format.setForeground(namespace_color)
        namespace_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'xmlns(?::[A-Za-zЀ-ӿԀ-ԯ_][A-Za-z0-9Ѐ-ӿԀ-ԯ_:\-]*)?\s*='),
            namespace_format
        ))
        
        # Angle bracket symbols '<' and '>' as a separate rule (placed last to override others)
        bracket_format = QTextCharFormat()
        bracket_format.setForeground(bracket_color)
        self.highlighting_rules.append((
            QRegularExpression(r'[<>]'),
            bracket_format
        ))
        
        # Re-highlight the current document
        self.rehighlight()
        
        # Restore signals
        if doc:
            doc.blockSignals(False)


class JsonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for JSON content (bonus feature)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.highlighting_rules = []
        
        # JSON keys
        key_format = QTextCharFormat()
        key_format.setForeground(QColor("#A31515"))  # Dark red
        key_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'"([^"]+)"\s*:'),
            key_format
        ))
        
        # JSON strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#0000FF"))  # Blue
        self.highlighting_rules.append((
            QRegularExpression(r'"([^"]*)"'),
            string_format
        ))
        
        # JSON numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#098658"))  # Greenish
        self.highlighting_rules.append((
            QRegularExpression(r'\b\d+(\.\d+)?([eE][+-]?\d+)?\b'),
            number_format
        ))
        
        # JSON booleans
        boolean_format = QTextCharFormat()
        boolean_format.setForeground(QColor("#0000FF"))  # Blue
        boolean_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'\b(true|false)\b'),
            boolean_format
        ))
        
        # JSON null
        null_format = QTextCharFormat()
        null_format.setForeground(QColor("#0000FF"))  # Blue
        null_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'\bnull\b'),
            null_format
        ))
        
        # JSON braces and brackets
        bracket_format = QTextCharFormat()
        bracket_format.setForeground(QColor("#808080"))  # Gray
        self.highlighting_rules.append((
            QRegularExpression(r'[{}\[\]]'),
            bracket_format
        ))
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text"""
        for pattern, format in self.highlighting_rules:
            match = pattern.globalMatch(text)
            while match.hasNext():
                m = match.next()
                start = m.capturedStart()
                length = m.capturedLength()
                self.setFormat(start, length, format)


class HtmlHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for HTML content (bonus feature)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.highlighting_rules = []
        
        # HTML tags
        tag_format = QTextCharFormat()
        tag_format.setForeground(QColor("#569CD6"))  # Light blue
        tag_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((
            QRegularExpression(r'<[^>]+>'),
            tag_format
        ))
        
        # HTML attributes
        attribute_format = QTextCharFormat()
        attribute_format.setForeground(QColor("#92C5EC"))  # Light blue
        self.highlighting_rules.append((
            QRegularExpression(r'\s([a-zA-Z-]+)\s*='),
            attribute_format
        ))
        
        # HTML attribute values
        attribute_value_format = QTextCharFormat()
        attribute_value_format.setForeground(QColor("#CE9178"))  # Orange
        self.highlighting_rules.append((
            QRegularExpression(r'="([^"]*)"'),
            attribute_value_format
        ))
        
        # HTML comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))  # Green
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((
            QRegularExpression(r'<!--.*?-->'),
            comment_format
        ))
        
        # HTML entities
        entity_format = QTextCharFormat()
        entity_format.setForeground(QColor("#D7BA7D"))  # Light orange
        self.highlighting_rules.append((
            QRegularExpression(r'&[a-zA-Z][a-zA-Z0-9]*;'),
            entity_format
        ))
        
        # HTML numeric entities
        numeric_entity_format = QTextCharFormat()
        numeric_entity_format.setForeground(QColor("#D7BA7D"))  # Light orange
        self.highlighting_rules.append((
            QRegularExpression(r'&#\d+;'),
            numeric_entity_format
        ))
        
        # HTML hex entities
        hex_entity_format = QTextCharFormat()
        hex_entity_format.setForeground(QColor("#D7BA7D"))  # Light orange
        self.highlighting_rules.append((
            QRegularExpression(r'&#x[0-9A-Fa-f]+;'),
            hex_entity_format
        ))
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text"""
        for pattern, format in self.highlighting_rules:
            match = pattern.globalMatch(text)
            while match.hasNext():
                m = match.next()
                start = m.capturedStart()
                length = m.capturedLength()
                self.setFormat(start, length, format)


    def _highlight_multiline_comments(self, text: str):
        """Highlight XML comments that span multiple text blocks.
        
        This method tracks whether the previous block was inside a comment using
        the block state, and applies the comment format across block boundaries.
        It complements the single-line comment rule by ensuring multi-line
        sequences "<!-- ... -->" are consistently styled.
        """
        # Determine comment format based on current theme
        comment_format = QTextCharFormat()
        if self.is_dark_theme:
            comment_format.setForeground(QColor("#6A9955"))  # Light green (dark theme)
        else:
            comment_format.setForeground(QColor("#008000"))  # Green (light theme)
        comment_format.setFontItalic(True)
        
        start_tag = "<!--"
        end_tag = "-->"
        
        in_comment = (self.previousBlockState() == 1)
        pos = 0
        text_len = len(text)
        
        # If continuing a comment from previous block, search for the end
        if in_comment:
            end_idx = text.find(end_tag, pos)
            if end_idx == -1:
                # Entire block is inside comment
                self.setFormat(0, text_len, comment_format)
                self.setCurrentBlockState(1)
                return
            else:
                # Comment ends in this block
                self.setFormat(0, end_idx + len(end_tag), comment_format)
                pos = end_idx + len(end_tag)
                self.setCurrentBlockState(0)
                in_comment = False
        
        # Find any new comment starts and handle possible unmatched end
        while True:
            start_idx = text.find(start_tag, pos)
            if start_idx == -1:
                break
            end_idx = text.find(end_tag, start_idx)
            if end_idx == -1:
                # Comment continues to next block
                self.setFormat(start_idx, text_len - start_idx, comment_format)
                self.setCurrentBlockState(1)
                return
            else:
                # Comment fully within this block
                self.setFormat(start_idx, end_idx + len(end_tag) - start_idx, comment_format)
                pos = end_idx + len(end_tag)
        
        # Not in a comment at end of processing
        self.setCurrentBlockState(0)