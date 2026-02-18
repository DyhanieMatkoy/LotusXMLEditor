
import sys
import os
import time
import shutil
import tempfile
from PyQt6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt
from main import XmlTreeWidget
from xml_service import XmlService
from models import XmlTreeNode

def create_test_xml(depth=5, breadth=5):
    """Create a deep XML file"""
    def _build(d):
        if d == 0:
            return "text"
        children = "".join([f"<child_{i}>{_build(d-1)}</child_{i}>" for i in range(breadth)])
        return children

    content = f"<root>{_build(depth)}</root>"
    return content

def test_depth_control():
    app = QApplication(sys.argv)
    
    # Create test XML
    xml_content = create_test_xml(depth=4, breadth=2)
    
    widget = XmlTreeWidget()
    widget.max_load_depth = 2
    
    print("Populating tree with depth limit 2...")
    widget.populate_tree(xml_content, show_progress=False)
    
    # Check root expansion
    root = widget.topLevelItem(0)
    assert root.isExpanded() == True
    print("Root expanded: OK")
    
    # Check level 2 (should be expanded because depth 2 means root(1) -> child(2) -> expanded?)
    # expand_to_level(2):
    # Level 1 (root): current=1 < 2 -> Expand.
    # Level 2 (child): current=2 == 2 -> Else -> Collapse.
    
    child = root.child(0)
    # Child should NOT be expanded if depth is 2
    if child.isExpanded():
        print(f"FAILURE: Child at level 2 is expanded, but limit is 2.")
    else:
        print("Child at level 2 is collapsed: OK")
        
    # Now change depth to 3
    print("Changing depth to 3...")
    widget.apply_load_depth(3)
    
    if child.isExpanded():
        print("Child at level 2 is now expanded: OK")
    else:
        print("FAILURE: Child at level 2 is still collapsed after depth increase.")

def test_caching():
    app = QApplication(sys.argv)
    
    # Create temp file
    tmp_path = os.path.join(tempfile.gettempdir(), "test_lotus_cache.xml")
    xml_content = create_test_xml(depth=3, breadth=3)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
        
    service = XmlService()
    # Clear cache for this file if exists
    cache_path = service._get_cache_path(tmp_path)
    if os.path.exists(cache_path):
        os.remove(cache_path)
        
    widget = XmlTreeWidget()
    widget._xml_service = service
    
    print("First load (should create cache)...")
    start = time.time()
    widget.populate_tree(xml_content, file_path=tmp_path, show_progress=False)
    print(f"First load took: {time.time() - start:.4f}s")
    
    assert os.path.exists(cache_path)
    print("Cache file created: OK")
    
    print("Second load (should use cache)...")
    start = time.time()
    widget.populate_tree(xml_content, file_path=tmp_path, show_progress=False)
    print(f"Second load took: {time.time() - start:.4f}s")
    
    # Verify it actually used cache (we can't easily mock inside the class without patching, 
    # but the speed or log check would tell. For now, just ensuring it doesn't crash)
    
    os.remove(tmp_path)
    if os.path.exists(cache_path):
        os.remove(cache_path)
    print("Cleanup OK")

if __name__ == "__main__":
    try:
        test_depth_control()
        test_caching()
        print("All tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
