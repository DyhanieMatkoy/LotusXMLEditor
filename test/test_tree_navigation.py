import os
import unittest
import xml.etree.ElementTree as ET

from xml_service import XmlService


def parse_indexed_path(path: str):
    """Parse index-aware path like '/root[1]/child[2]/sub[1]' into [(tag, index), ...]."""
    parts = []
    for segment in path.strip().split('/'):
        if not segment:
            continue
        if '[' in segment and segment.endswith(']'):
            tag = segment[: segment.index('[')]
            idx = int(segment[segment.index('[') + 1 : -1])
        else:
            tag, idx = segment, 1
        parts.append((tag, idx))
    return parts


def find_element_by_indexed_path(root: ET.Element, path: str):
    """Find an element in ElementTree using index-aware path segments."""
    segments = parse_indexed_path(path)
    current = root
    # The first segment corresponds to root itself; verify it, then proceed through children
    if not segments:
        return None
    root_tag, root_idx = segments[0]
    if current.tag != root_tag or root_idx != 1:
        # If root_idx is not 1, this XML structure isn't supported by this simple checker
        return None
    for tag, idx in segments[1:]:
        same_tag_children = [c for c in list(current) if c.tag == tag]
        if idx <= 0 or idx > len(same_tag_children):
            return None
        current = same_tag_children[idx - 1]
    return current


class TestTreeBackedNavigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_dir = os.path.dirname(os.path.abspath(__file__))
        cls.original_xml_path = os.path.join(cls.base_dir, 'original.xml')
        assert os.path.exists(cls.original_xml_path), f"original.xml not found at {cls.original_xml_path}"
        with open(cls.original_xml_path, 'r', encoding='utf-8') as f:
            cls.content = f.read()
        cls.service = XmlService()
        cls.tree_root = cls.service.build_xml_tree(cls.content)
        assert cls.tree_root is not None, "Failed to build XML tree for original.xml"

        # Build a flat list of nodes for comprehensive checks
        cls.all_nodes = []

        def walk(node):
            cls.all_nodes.append(node)
            for ch in getattr(node, 'children', []) or []:
                walk(ch)

        walk(cls.tree_root)

        # Prepare ElementTree root for cross-validation
        cls.et_root = ET.fromstring(cls.content)
        cls.lines = cls.content.split('\n')

    def test_paths_are_unique(self):
        paths = [n.path for n in self.all_nodes if getattr(n, 'path', None)]
        self.assertEqual(len(paths), len(set(paths)), "Duplicate paths found in tree nodes")

    def test_parent_paths_align(self):
        # For each node with parent, parent.path should equal path without last segment
        for n in self.all_nodes:
            parent = getattr(n, 'parent_node', None)
            if not parent:
                # Root node
                continue
            self.assertTrue(n.path.startswith('/'), f"Node path missing leading '/': {n.path}")
            parent_path_expected = '/'.join(n.path.split('/')[:-1])
            self.assertEqual(parent.path, parent_path_expected,
                             f"Parent path mismatch for node {n.path}: expected {parent_path_expected}, got {parent.path}")

    def test_sibling_indexing_is_sequential(self):
        # For each parent, verify children with same tag have sequential [i] indices starting at 1
        from collections import defaultdict
        for n in self.all_nodes:
            children = getattr(n, 'children', []) or []
            if not children:
                continue
            buckets = defaultdict(list)
            for ch in children:
                buckets[ch.tag].append(ch)
            for tag, group in buckets.items():
                # Extract indices from paths
                indices = [parse_indexed_path(ch.path)[-1][1] for ch in group]
                self.assertEqual(indices, list(range(1, len(group) + 1)),
                                 f"Indices for siblings '{tag}' under {n.path} not sequential: {indices}")

    def test_path_maps_to_element_tree(self):
        # Cross-check that each node's path resolves to the corresponding ET element
        checked = 0
        for n in self.all_nodes:
            el = find_element_by_indexed_path(self.et_root, n.path)
            self.assertIsNotNone(el, f"Path did not resolve in ET: {n.path}")
            self.assertEqual(el.tag, n.tag, f"Tag mismatch for path {n.path}: tree '{n.tag}', ET '{el.tag}'")
            # If node value is non-empty, check text matches (trimmed). Formatting/whitespace can differ.
            if getattr(n, 'value', ''):
                self.assertEqual((el.text or '').strip(), n.value.strip(),
                                 f"Text mismatch at {n.path}")
            checked += 1
            # Keep this comprehensive; do not limit unless extremely large
        self.assertGreater(checked, 0, "No nodes checked for path→ET mapping")

    def test_line_numbers_reasonable(self):
        # Ensure line numbers are within bounds and plausibly point at the opening tag line
        total_lines = len(self.lines)
        for n in self.all_nodes:
            ln = getattr(n, 'line_number', 0) or 0
            self.assertTrue(0 < ln <= total_lines, f"Invalid line number {ln} for {n.path}")
            line = self.lines[ln - 1]
            # Heuristic: the opening tag line should include '<tag'
            self.assertIn(f"<{n.tag}", line,
                          f"Line {ln} does not contain opening tag for {n.path}; got: {line[:80]}")


if __name__ == '__main__':
    unittest.main(verbosity=2)