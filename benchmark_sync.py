
import time
import os
import sys

# Mock logic
if __name__ == "__main__":
    sys.path.append(os.getcwd())
    
    from xml_service import XmlService
    from models import XmlTreeNode

    # Generate a large XML file for testing (approx 5MB)
    def generate_large_xml(filename, num_elements=50000):
        print(f"Generating {filename} with {num_elements} elements...")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            f.write('<root>\n')
            for i in range(num_elements):
                f.write(f'  <item id="{i}">\n')
                f.write(f'    <name>Item {i}</name>\n')
                f.write(f'    <value>{i * 100}</value>\n')
                f.write(f'    <description>Line number test {i}</description>\n')
                f.write(f'  </item>\n')
            f.write('</root>\n')
        print(f"Generated {os.path.getsize(filename) / 1024 / 1024:.2f} MB file.")

    test_file = "benchmark_test.xml"
    if not os.path.exists(test_file):
        generate_large_xml(test_file)
        
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    service = XmlService()
    
    print("\n--- Benchmarking XmlService.build_xml_tree (Optimized) ---")
    start_time = time.time()
    root_node = service.build_xml_tree(content)
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"build_xml_tree took: {duration:.4f} seconds")
    
    if root_node:
        print(f"Root node children count: {len(root_node.children)}")
        # Verify line numbers are present
        first_child = root_node.children[0]
        print(f"First child line number: {first_child.line_number}")
        if first_child.line_number > 0:
            print("SUCCESS: Line numbers are present.")
        else:
            print("FAILURE: Line numbers are missing.")
    else:
        print("Failed to build tree")

    # Clean up
    # os.remove(test_file)
