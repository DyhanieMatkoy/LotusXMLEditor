from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import re
import os
import json
import hashlib

from PyQt6.QtCore import QRegularExpression, Qt
try:
    from PyQt6.QtCore import QStandardPaths
except Exception:
    QStandardPaths = None
from PyQt6.QtGui import QColor, QTextCharFormat, QFont, QSyntaxHighlighter


@dataclass
class LanguageDefinition:
    name: str
    origin: str  # 'builtin' or 'udl'
    case_insensitive: bool = True
    keywords: Dict[str, List[str]] = field(default_factory=dict)  # group -> words
    operators: List[str] = field(default_factory=list)
    line_comment: Optional[str] = None
    block_comment: Optional[Tuple[str, str]] = None
    string_delimiters: List[Tuple[str, str]] = field(default_factory=list)
    number_regex: Optional[str] = None
    styles: Dict[str, QTextCharFormat] = field(default_factory=dict)  # category -> format


class LanguageProfileCompiler:
    def __init__(self, definition: LanguageDefinition):
        self.definition = definition
        self.rules: List[Tuple[QRegularExpression, QTextCharFormat]] = []
        # Internal cache
        self._memory_cache: Dict[str, List[Tuple[QRegularExpression, QTextCharFormat]]] = _get_memory_rules_cache()

    def compile(self) -> List[Tuple[QRegularExpression, QTextCharFormat]]:
        flags = Qt.CaseSensitivity.CaseInsensitive if self.definition.case_insensitive else Qt.CaseSensitivity.CaseSensitive

        def fmt(category: str) -> QTextCharFormat:
            return self.definition.styles.get(category, QTextCharFormat())

        # Attempt to load from memory cache first
        digest = _lang_def_digest(self.definition)
        mem_key = f"{self.definition.name}:{digest}"
        cached_rules = self._memory_cache.get(mem_key)
        if cached_rules:
            self.rules = cached_rules
            return self.rules

        # Attempt to load from disk cache of pattern strings
        disk_entry = _load_disk_cache_entry(self.definition.name)
        if disk_entry and disk_entry.get('digest') == digest:
            try:
                compiled: List[Tuple[QRegularExpression, QTextCharFormat]] = []
                for item in disk_entry.get('patterns', []):
                    pattern_str = item.get('pattern')
                    category = item.get('category') or ''
                    rx = QRegularExpression(pattern_str)
                    compiled.append((rx, fmt(category)))
                self.rules = compiled
                _store_memory_rules(mem_key, self.rules)
                return self.rules
            except Exception:
                # Fall through to rebuild if cache entry is malformed
                pass

        # Build patterns from definition, then persist to disk and memory
        pattern_items: List[Tuple[str, str]] = []  # (pattern_str, category)

        # Line comments
        if self.definition.line_comment:
            pattern_items.append((QRegularExpression.escape(self.definition.line_comment) + ".*$", 'LINE COMMENTS'))

        # Block comments
        if self.definition.block_comment:
            start, end = self.definition.block_comment
            pattern_items.append((QRegularExpression.escape(start) + r"[\s\S]*?" + QRegularExpression.escape(end), 'COMMENTS'))

        # Strings
        for start, end in self.definition.string_delimiters:
            pattern_items.append((QRegularExpression.escape(start) + r"[^" + end + r"]*" + QRegularExpression.escape(end), 'STRINGS'))

        # Numbers
        if self.definition.number_regex:
            pattern_items.append((self.definition.number_regex, 'NUMBERS'))

        # Operators
        if self.definition.operators:
            ops = [QRegularExpression.escape(op) for op in self.definition.operators]
            pattern_items.append((r"(" + "|".join(ops) + r")", 'OPERATORS'))

        # Keywords per group
        for group, words in self.definition.keywords.items():
            if words:
                escaped = [QRegularExpression.escape(w) for w in words]
                pattern_items.append((r"\b(" + "|".join(escaped) + r")\b", group.upper()))

        # Compile and store
        compiled: List[Tuple[QRegularExpression, QTextCharFormat]] = []
        for ptn, cat in pattern_items:
            rx = QRegularExpression(ptn)
            compiled.append((rx, fmt(cat)))
        self.rules = compiled

        # Persist to disk
        try:
            _persist_disk_cache_entry(self.definition.name, digest, pattern_items)
        except Exception:
            pass

        # Persist to memory
        _store_memory_rules(mem_key, self.rules)
        return self.rules


class RuleHighlighter(QSyntaxHighlighter):
    def __init__(self, doc, rules: List[Tuple[QRegularExpression, QTextCharFormat]]):
        super().__init__(doc)
        self.rules = rules
        self.is_dark_theme = False

    def highlightBlock(self, text: str):
        for rx, fmt in self.rules:
            it = rx.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

    # Compatibility stubs for XmlHighlighter interface
    def set_visibility_options(self, hide_symbols: bool = None, hide_tags: bool = None, hide_values: bool = None):
        # Generic rule highlighter does not support selective hiding; no-op to avoid errors
        return

    def set_dark_theme(self, dark_theme=True):
        # If themes are desired, styles should be recompiled externally; keep as no-op
        self.is_dark_theme = bool(dark_theme)


class LanguageRegistry:
    def __init__(self):
        self._defs: Dict[str, LanguageDefinition] = {}

    def install(self, definition: LanguageDefinition):
        self._defs[definition.name] = definition

    def get(self, name: str) -> Optional[LanguageDefinition]:
        return self._defs.get(name)

    def list(self) -> List[str]:
        return sorted(self._defs.keys())


# --------------------
# Caching infrastructure
# --------------------

_MEMORY_RULES_CACHE: Dict[str, List[Tuple[QRegularExpression, QTextCharFormat]]] = {}

def _compute_cache_file_path() -> str:
    # Prefer OS AppData location
    try:
        # Use QStandardPaths if available and app is configured
        if QStandardPaths:
            base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
            if base:
                path = os.path.join(base, 'language_cache.json')
                os.makedirs(os.path.dirname(path), exist_ok=True)
                return path
    except Exception:
        pass
    try:
        # Fallback to %APPDATA%\VisualXmlEditor
        appdata = os.environ.get('APPDATA')
        if appdata:
            base = os.path.join(appdata, 'VisualXmlEditor')
            os.makedirs(base, exist_ok=True)
            return os.path.join(base, 'language_cache.json')
    except Exception:
        pass
    # Final fallback: next to the module
    fallback = os.path.join(os.path.dirname(__file__), 'language_cache.json')
    try:
        os.makedirs(os.path.dirname(fallback), exist_ok=True)
    except Exception:
        pass
    return fallback

_CACHE_FILE = _compute_cache_file_path()

def _get_memory_rules_cache() -> Dict[str, List[Tuple[QRegularExpression, QTextCharFormat]]]:
    return _MEMORY_RULES_CACHE

def _store_memory_rules(key: str, rules: List[Tuple[QRegularExpression, QTextCharFormat]]):
    _MEMORY_RULES_CACHE[key] = rules

def _lang_def_digest(defn: LanguageDefinition) -> str:
    payload = {
        'name': defn.name,
        'ci': defn.case_insensitive,
        'line_comment': defn.line_comment,
        'block_comment': defn.block_comment,
        'string_delims': defn.string_delimiters,
        'number_regex': defn.number_regex,
        'operators': defn.operators,
        'keywords': {k: sorted(v) for k, v in defn.keywords.items()},
    }
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def _load_disk_cache() -> Dict[str, dict]:
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}

_DISK_CACHE = _load_disk_cache()

def _load_disk_cache_entry(lang_name: str) -> Optional[dict]:
    try:
        entry = _DISK_CACHE.get(lang_name)
        if isinstance(entry, dict):
            return entry
    except Exception:
        pass
    return None

def _persist_disk_cache_entry(lang_name: str, digest: str, pattern_items: List[Tuple[str, str]]):
    try:
        _DISK_CACHE[lang_name] = {
            'digest': digest,
            'patterns': [{'pattern': p, 'category': c} for (p, c) in pattern_items],
            'version': 1,
        }
        with open(_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(_DISK_CACHE, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _format_from_udl_style(fg: str, bg: Optional[str], font_style: int) -> QTextCharFormat:
    fmt = QTextCharFormat()
    try:
        fmt.setForeground(QColor('#' + fg))
        if bg:
            fmt.setBackground(QColor('#' + bg))
        # Notepad++ fontStyle: bit 1=bold, 2=italic, 4=underline
        if font_style & 1:
            fmt.setFontWeight(QFont.Weight.Bold)
        if font_style & 2:
            fmt.setFontItalic(True)
        if font_style & 4:
            fmt.setFontUnderline(True)
    except Exception:
        pass
    return fmt


def _xml10_char_allowed(cp: int) -> bool:
    """Return True if codepoint is allowed by XML 1.0 spec."""
    return (
        cp in (0x9, 0xA, 0xD) or
        (0x20 <= cp <= 0xD7FF) or
        (0xE000 <= cp <= 0xFFFD) or
        (0x10000 <= cp <= 0x10FFFF)
    )


def _sanitize_udl_xml_text(text: str) -> str:
    """Sanitize UDL XML text to avoid ElementTree parse errors.

    - Strip numeric character references that are invalid under XML 1.0
    - Remove raw control characters not permitted by XML 1.0
    - Drop Notepad++ fontName attributes (not used in our renderer)
    """

    def _replace_hex(m: re.Match) -> str:
        cp = int(m.group(1), 16)
        return m.group(0) if _xml10_char_allowed(cp) else ''

    def _replace_dec(m: re.Match) -> str:
        cp = int(m.group(1), 10)
        return m.group(0) if _xml10_char_allowed(cp) else ''

    # Replace invalid numeric character references
    text = re.sub(r'&#x([0-9A-Fa-f]+);', _replace_hex, text)
    text = re.sub(r'&#([0-9]+);', _replace_dec, text)

    # Remove disallowed raw control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', text)

    # Remove fontName attributes completely; we don't consume them
    text = re.sub(r'\sfontName="[^"]*"', '', text)

    return text


def load_udl_xml(path: str) -> Optional[LanguageDefinition]:
    try:
        import xml.etree.ElementTree as ET
        # Read and sanitize UDL XML to tolerate invalid character references
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()
        sanitized = _sanitize_udl_xml_text(raw)
        root = ET.fromstring(sanitized)
        ul = root.find('.//UserLang')
        name = ul.get('name') if ul is not None else 'UDL'
        ld = LanguageDefinition(name=name, origin='udl')

        settings = ul.find('Settings') if ul is not None else None
        if settings is not None:
            g = settings.find('Global')
            if g is not None:
                ld.case_insensitive = (g.get('caseIgnored', 'yes') == 'yes')

        kw = ul.find('KeywordLists') if ul is not None else None
        if kw is not None:
            # Comments
            comments = kw.find("Keywords[@name='Comments']")
            if comments is not None:
                parts = comments.text.split() if comments.text else []
                # UDL encodes markers; map common pattern: line comment prefix at index 2
                if len(parts) >= 4:
                    ld.line_comment = '//'
            # Operators
            ops = kw.find("Keywords[@name='Operators1']")
            if ops is not None and ops.text:
                ld.operators = ops.text.split()
            # Delimiters (strings)
            delims = kw.find("Keywords[@name='Delimiters']")
            if delims is not None and delims.text:
                text = delims.text
                # Heuristic: support '"' and "'" pairs
                if '"' in text:
                    ld.string_delimiters.append(('"', '"'))
                if "'" in text:
                    ld.string_delimiters.append(("'", "'"))
            # Keyword groups
            for i in range(1, 9):
                tag = kw.find(f"Keywords[@name='Keywords{i}']")
                words = tag.text.split() if (tag is not None and tag.text) else []
                if words:
                    ld.keywords[f'KEYWORDS{i}'] = words

        styles = ul.find('Styles') if ul is not None else None
        if styles is not None:
            for ws in styles.findall('WordsStyle'):
                cat = ws.get('name')
                fg = ws.get('fgColor', 'CCCCCC')
                bg = ws.get('bgColor')
                font_style = int(ws.get('fontStyle', '0'))
                ld.styles[cat] = _format_from_udl_style(fg, bg, font_style)

        return ld
    except Exception as e:
        print(f"UDL load error: {e}")
        return None