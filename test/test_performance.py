#!/usr/bin/env python3
"""
Performance Testing Script for XML Tree Building
Tests the speed improvements from optimizations
"""

import time
import sys
from xml_service import XmlService, LXML_AVAILABLE

def generate_test_xml(depth=5, children_per_node=3):
    """Generate a test XML structure"""
    def build_node(level, max_level, node_id):
        if level >= max_level:
            return f'<leaf id="{node_id}">Value {node_id}</leaf>'
        
        children = []
        for i in range(children_per_node):
            child_id = f"{node_id}.{i}"
            children.append(build_node(level + 1, max_level, child_id))
        
        children_xml = '\n'.join(children)
        return f'<node id="{node_id}" level="{level}">\n{children_xml}\n</node>'
    
    root = build_node(0, depth, "root")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{root}'

def test_parsing_speed(xml_content, iterations=5):
    """Test XML parsing speed"""
    service = XmlService()
    
    print(f"\n{'='*60}")
    print(f"Testing with {len(xml_content):,} bytes of XML")
    print(f"lxml available: {LXML_AVAILABLE}")
    print(f"{'='*60}\n")
    
    # Warm-up
    service.parse_xml(xml_content)
    
    # Test parsing
    parse_times = []
    for i in range(iterations):
        start = time.time()
        root = service.parse_xml(xml_content)
        elapsed = time.time() - start
        parse_times.append(elapsed)
        print(f"Parse iteration {i+1}: {elapsed*1000:.2f}ms")
    
    avg_parse = sum(parse_times) / len(parse_times)
    print(f"\nAverage parse time: {avg_parse*1000:.2f}ms")
    
    # Test tree building
    tree_times = []
    for i in range(iterations):
        start = time.time()
        tree = service.build_xml_tree(xml_content)
        elapsed = time.time() - start
        tree_times.append(elapsed)
        print(f"Tree build iteration {i+1}: {elapsed*1000:.2f}ms")
    
    avg_tree = sum(tree_times) / len(tree_times)
    print(f"\nAverage tree build time: {avg_tree*1000:.2f}ms")
    print(f"Total average time: {(avg_parse + avg_tree)*1000:.2f}ms")
    
    # Count nodes
    def count_nodes(node):
        count = 1
        for child in node.children:
            count += count_nodes(child)
        return count
    
    tree = service.build_xml_tree(xml_content)
    if tree:
        node_count = count_nodes(tree)
        print(f"\nTotal nodes: {node_count:,}")
        print(f"Time per node: {(avg_parse + avg_tree) / node_count * 1000:.3f}ms")

def main():
    print("XML Tree Building Performance Test")
    print("="*60)
    
    # Test different sizes
    test_cases = [
        ("Small (depth=3, children=3)", 3, 3),
        ("Medium (depth=4, children=4)", 4, 4),
        ("Large (depth=5, children=4)", 5, 4),
    ]
    
    for name, depth, children in test_cases:
        print(f"\n\n{name}")
        xml = generate_test_xml(depth, children)
        test_parsing_speed(xml, iterations=3)
    
    print("\n\n" + "="*60)
    print("Performance test complete!")
    print("="*60)
    
    if not LXML_AVAILABLE:
        print("\n⚠️  lxml not installed - install it for 5-10x faster parsing:")
        print("   pip install lxml")

if __name__ == "__main__":
    main()
