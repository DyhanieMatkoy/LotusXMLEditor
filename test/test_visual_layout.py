"""
Visual test for Metro Navigator layout algorithm

This script creates a test XML structure and visualizes the layout
to verify that nodes are positioned correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import XmlTreeNode
from metro_navigator import extract_three_levels_from_tree, convert_to_metro_graph, MetroLayoutEngine


def create_test_tree():
    """Create a test XML tree with 3 levels"""
    # Root node
    root = XmlTreeNode(
        name="root[1]",
        tag="root",
        value="",
        attributes={"version": "1.0"},
        path="/root[1]",
        line_number=1
    )
    
    # Level 1 - 3 children
    for i in range(1, 4):
        child1 = XmlTreeNode(
            name=f"section[{i}]",
            tag="section",
            value="",
            attributes={"id": f"sec{i}"},
            path=f"/root[1]/section[{i}]",
            line_number=i + 1
        )
        root.children.append(child1)
        
        # Level 2 - varying number of children
        num_grandchildren = i * 2  # 2, 4, 6 children
        for j in range(1, num_grandchildren + 1):
            child2 = XmlTreeNode(
                name=f"item[{j}]",
                tag="item",
                value=f"Item {j}",
                attributes={"name": f"item{j}"},
                path=f"/root[1]/section[{i}]/item[{j}]",
                line_number=10 * i + j
            )
            child1.children.append(child2)
    
    return root


def visualize_layout(positions, metro_root):
    """Print a simple ASCII visualization of the layout"""
    print("\n" + "="*80)
    print("LAYOUT VISUALIZATION")
    print("="*80)
    
    # Collect all nodes
    def collect_nodes(node):
        result = [node]
        for child in node.children:
            result.extend(collect_nodes(child))
        return result
    
    all_nodes = collect_nodes(metro_root)
    
    # Group by level
    by_level = {}
    for node in all_nodes:
        if node.level not in by_level:
            by_level[node.level] = []
        by_level[node.level].append(node)
    
    # Print statistics
    print(f"\nTotal nodes: {len(all_nodes)}")
    print(f"Levels: {sorted(by_level.keys())}")
    for level in sorted(by_level.keys()):
        print(f"  Level {level}: {len(by_level[level])} nodes")
    
    # Print positions
    print("\nNode Positions:")
    print("-" * 80)
    for level in sorted(by_level.keys()):
        print(f"\nLevel {level}:")
        nodes = sorted(by_level[level], key=lambda n: positions[n.xpath][0])
        for node in nodes:
            x, y = positions[node.xpath]
            print(f"  {node.display_name:20s} -> ({x:7.1f}, {y:7.1f})")
    
    # Check spacing properties
    print("\n" + "="*80)
    print("SPACING VERIFICATION")
    print("="*80)
    
    # Check minimum distance between all pairs
    min_dist = float('inf')
    min_pair = None
    node_list = list(positions.items())
    
    for i in range(len(node_list)):
        for j in range(i + 1, len(node_list)):
            xpath1, pos1 = node_list[i]
            xpath2, pos2 = node_list[j]
            
            dx = pos2[0] - pos1[0]
            dy = pos2[1] - pos1[1]
            dist = (dx*dx + dy*dy) ** 0.5
            
            if dist < min_dist:
                min_dist = dist
                min_pair = (xpath1, xpath2)
    
    print(f"\nMinimum distance between nodes: {min_dist:.2f} pixels")
    if min_pair:
        print(f"  Between: {min_pair[0]} and {min_pair[1]}")
    print(f"  Required minimum: 80.0 pixels")
    print(f"  Status: {'✓ PASS' if min_dist >= 80.0 else '✗ FAIL'}")
    
    # Check vertical spacing between levels
    print("\nVertical spacing between levels:")
    sorted_levels = sorted(by_level.keys())
    for i in range(len(sorted_levels) - 1):
        level1 = sorted_levels[i]
        level2 = sorted_levels[i + 1]
        
        y1_avg = sum(positions[n.xpath][1] for n in by_level[level1]) / len(by_level[level1])
        y2_avg = sum(positions[n.xpath][1] for n in by_level[level2]) / len(by_level[level2])
        
        v_dist = abs(y2_avg - y1_avg)
        print(f"  Level {level1} to {level2}: {v_dist:.2f} pixels")
        print(f"    Required minimum: 120.0 pixels")
        print(f"    Status: {'✓ PASS' if v_dist >= 120.0 else '✗ FAIL'}")
    
    # Check horizontal alignment within levels
    print("\nHorizontal alignment within levels:")
    for level in sorted(by_level.keys()):
        if len(by_level[level]) > 1:
            y_positions = [positions[n.xpath][1] for n in by_level[level]]
            y_range = max(y_positions) - min(y_positions)
            print(f"  Level {level}: Y range = {y_range:.2f} pixels")
            print(f"    Required maximum: 10.0 pixels")
            print(f"    Status: {'✓ PASS' if y_range <= 10.0 else '✗ FAIL'}")


def main():
    """Run visual layout test"""
    print("Creating test XML tree...")
    test_tree = create_test_tree()
    
    print("Extracting three levels...")
    limited_tree = extract_three_levels_from_tree(test_tree)
    
    print("Converting to metro graph...")
    metro_root = convert_to_metro_graph(limited_tree)
    
    print("Computing layout...")
    engine = MetroLayoutEngine()
    positions = engine.compute_layout(metro_root)
    
    print(f"Layout computed for {len(positions)} nodes")
    
    # Visualize the results
    visualize_layout(positions, metro_root)
    
    print("\n" + "="*80)
    print("LAYOUT TEST COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()
