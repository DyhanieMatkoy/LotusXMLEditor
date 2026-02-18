
import sys
import unittest
from PyQt6.QtWidgets import QApplication
from main import MainWindow  # Adjust import if needed, or copy the method

# Mocking the editor part or just testing the logic directly if possible
# Since _compute_enclosing_xml_ranges is a method of MainWindow (or mixed in), 
# and it relies on regex, I can extract it for testing.

import re

def _compute_enclosing_xml_ranges(text: str):
    """Compute element ranges using a simple stack-based parser. Returns list of (tag, start, end)."""
    ranges = []
    stack = []  # list of (tag, start_index)
    # Handle comments and CDATA and PIs by temporarily removing them to avoid mis-parsing
    # Record their spans as atomic ranges too
    comment_pattern = re.compile(r"<!--.*?-->", re.DOTALL)
    cdata_pattern = re.compile(r"<!\[CDATA\[.*?\]\]>", re.DOTALL)
    pi_pattern = re.compile(r"<\?.*?\?>", re.DOTALL)
    doctype_pattern = re.compile(r"<!DOCTYPE.*?>", re.DOTALL)
    special_spans = []
    for pat in (comment_pattern, cdata_pattern, pi_pattern, doctype_pattern):
        for m in pat.finditer(text):
            special_spans.append(("special", m.start(), m.end()))
    # Support Unicode tag names (including Cyrillic), namespaces, and punctuation
    # Tag name: one or more non-space, non-'>' and non'/' characters
    tag_pattern = re.compile(r"<(/?)([^\s>/]+)([^>]*)>", re.UNICODE)
    i = 0
    for m in tag_pattern.finditer(text):
        # Skip special spans region
        skip = False
        for _, s, e in special_spans:
            if m.start() >= s and m.start() < e:
                skip = True
                break
        if skip:
            continue
        is_close = m.group(1) == '/'
        tag = m.group(2)
        rest = m.group(3) or ''
        full_end = m.end()
        # Detect self-closing tags like <tag .../>
        self_closing = rest.rstrip().endswith('/')
        if not is_close and not self_closing:
            stack.append((tag, m.start()))
        elif is_close:
            # pop matching tag
            for si in range(len(stack) - 1, -1, -1):
                if stack[si][0] == tag:
                    open_tag, start_idx = stack.pop(si)
                    ranges.append((tag, start_idx, full_end))
                    break
        else:
            # self-closing element
            ranges.append((tag, m.start(), full_end))
    # Add special spans as ranges
    ranges.extend(special_spans)
    # Sort by span size (smallest first) for deepest-first selection
    ranges.sort(key=lambda r: (r[2] - r[1]))
    return ranges

class TestFoldingLogic(unittest.TestCase):
    def test_basic_xml(self):
        xml = "<root><child>text</child></root>"
        ranges = _compute_enclosing_xml_ranges(xml)
        # Expected: child range, root range
        self.assertEqual(len(ranges), 2)
        self.assertEqual(ranges[0][0], "child")
        self.assertEqual(ranges[1][0], "root")

    def test_xml_with_slashes_in_text(self):
        xml = "<root><path>C://Program Files//App</path></root>"
        ranges = _compute_enclosing_xml_ranges(xml)
        self.assertEqual(len(ranges), 2)
        self.assertEqual(ranges[0][0], "path")
        self.assertEqual(ranges[1][0], "root")
        
    def test_xml_with_slashes_in_attr(self):
        xml = '<root><link href="http://example.com" /></root>'
        ranges = _compute_enclosing_xml_ranges(xml)
        self.assertEqual(len(ranges), 2)
        self.assertEqual(ranges[0][0], "link") # self closing
        self.assertEqual(ranges[1][0], "root")

    def test_nested_with_slashes(self):
        xml = """<root>
    <item>
        <text>Some // text</text>
    </item>
</root>"""
        ranges = _compute_enclosing_xml_ranges(xml)
        # item, text, root
        tags = [r[0] for r in ranges]
        self.assertIn("text", tags)
        self.assertIn("item", tags)
        self.assertIn("root", tags)

if __name__ == "__main__":
    unittest.main()
