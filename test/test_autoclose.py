#!/usr/bin/env python3
"""
Test script for auto-close tags functionality
"""

from xml_service import XmlService

def test_auto_close_tags():
    """Test the auto-close tags feature"""
    service = XmlService()
    
    # Test 1: Simple unclosed tag
    print("Test 1: Simple unclosed tag")
    xml1 = """<?xml version="1.0"?>
<root>
  <item>
    <name>Test</name>
"""
    result1 = service.auto_close_tags(xml1)
    print("Input:")
    print(xml1)
    print("\nOutput:")
    print(result1)
    print("\n" + "="*50 + "\n")
    
    # Test 2: Multiple unclosed tags
    print("Test 2: Multiple unclosed tags")
    xml2 = """<?xml version="1.0"?>
<root>
  <item>
    <name>Test</name>
    <value>123
  <item>
    <name>Test2</name>
"""
    result2 = service.auto_close_tags(xml2)
    print("Input:")
    print(xml2)
    print("\nOutput:")
    print(result2)
    print("\n" + "="*50 + "\n")
    
    # Test 3: Already valid XML
    print("Test 3: Already valid XML")
    xml3 = """<?xml version="1.0"?>
<root>
  <item>
    <name>Test</name>
  </item>
</root>"""
    result3 = service.auto_close_tags(xml3)
    print("Input:")
    print(xml3)
    print("\nOutput:")
    print(result3)
    print("Same as input:", result3 == xml3)
    print("\n" + "="*50 + "\n")
    
    # Test 4: Nested unclosed tags
    print("Test 4: Nested unclosed tags")
    xml4 = """<?xml version="1.0"?>
<root>
  <level1>
    <level2>
      <level3>
        <data>Content</data>
"""
    result4 = service.auto_close_tags(xml4)
    print("Input:")
    print(xml4)
    print("\nOutput:")
    print(result4)
    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    test_auto_close_tags()
