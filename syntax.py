"""
Syntax module for Lotus XML Editor.
Handles User Defined Language (UDL) profiles.
"""
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class LanguageDefinition:
    """Defines a language profile for syntax highlighting."""
    name: str
    extensions: List[str] = field(default_factory=list)
    keywords: Dict[str, str] = field(default_factory=dict)
    styles: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    # Additional properties that might be used
    comment_line: str = ""
    comment_start: str = ""
    comment_end: str = ""
    case_sensitive: bool = False

class LanguageRegistry:
    """Registry for managing available language profiles."""
    def __init__(self):
        self._languages: Dict[str, LanguageDefinition] = {}

    def install(self, ld: LanguageDefinition):
        """Install a language definition."""
        self._languages[ld.name] = ld

    def list(self) -> List[str]:
        """List available language names."""
        return list(self._languages.keys())

    def get(self, name: str) -> Optional[LanguageDefinition]:
        """Get a language definition by name."""
        return self._languages.get(name)

class LanguageProfileCompiler:
    """Compiler for language profiles (Stub)."""
    pass

def load_udl_xml(path: str) -> Optional[LanguageDefinition]:
    """Load a UDL XML file and return a LanguageDefinition."""
    try:
        # Robust loading: Read file as string and sanitize invalid XML 1.0 chars if needed
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Replace invalid XML entities like &#x000C; (Form Feed) which crash ElementTree
        # XML 1.0 only allows #x9 | #xA | #xD | [#x20-#xD7FF] | ...
        import re
        # Remove vertical tab, form feed, etc.
        content = re.sub(r'&#x000[B-C];', '', content)
        
        root = ET.fromstring(content)
        
        # Notepad++ UDL format usually has <UserLang> under <NotepadPlus>
        user_lang = root.find(".//UserLang")
        if user_lang is None:
            # Maybe it is the UserLang element itself
            if root.tag == "UserLang":
                user_lang = root
            else:
                return None
        
        name = user_lang.get("name", "Unknown")
        ext_str = user_lang.get("ext", "")
        extensions = ext_str.split() if ext_str else []
        
        ld = LanguageDefinition(name=name, extensions=extensions)
        
        # Parse Keywords
        keyword_lists = user_lang.find("KeywordLists")
        if keyword_lists is not None:
            for kw in keyword_lists.findall("Keywords"):
                kw_name = kw.get("name", "")
                text = kw.text or ""
                ld.keywords[kw_name] = text
        
        # Parse Styles
        styles = user_lang.find("Styles")
        if styles is not None:
            for style in styles.findall("WordsStyle"):
                style_name = style.get("name", "")
                style_data = {
                    "fgColor": style.get("fgColor", ""),
                    "bgColor": style.get("bgColor", ""),
                    "fontName": style.get("fontName", ""),
                    "fontStyle": style.get("fontStyle", ""),
                }
                ld.styles[style_name] = style_data
                
        return ld
        
    except Exception as e:
        print(f"Error loading UDL XML {path}: {e}")
        return None
