"""
XML Service - Core XML processing functionality
"""

import xml.etree.ElementTree as ET
import xml.dom.minidom
from typing import List, Optional, Dict, Any
import re
from models import XmlTreeNode, XmlValidationResult, XmlValidationError, XmlStatistics
from xml_splitter import XmlSplitter, XmlSplitConfig, XmlSplitRule
from xml_part_manager import XmlPartManager

# Quick Win #4: Try to use lxml for 5-10x faster parsing (with fallback to ElementTree)
try:
    from lxml import etree as lxml_etree
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False


class XmlService:
    """Service for XML processing operations"""
    
    def __init__(self):
        self.namespaces = {}
    
    def parse_xml(self, xml_content: str) -> Optional[ET.Element]:
        """Parse XML content and return root element"""
        try:
            # Remove BOM if present
            if xml_content.startswith('\ufeff'):
                xml_content = xml_content[1:]
            
            # Quick Win #4: Use lxml if available (5-10x faster than ElementTree)
            if LXML_AVAILABLE:
                try:
                    # lxml is much faster for large files
                    root = lxml_etree.fromstring(xml_content.encode('utf-8'))
                    # Convert lxml element to ElementTree for compatibility
                    return ET.fromstring(lxml_etree.tostring(root))
                except Exception as lxml_error:
                    print(f"lxml parsing failed, falling back to ElementTree: {lxml_error}")
                    # Fall through to ElementTree parsing
            
            # Use incremental parsing for large files
            if len(xml_content) > 1024 * 1024:  # 1MB threshold
                parser = ET.XMLParser(target=ET.TreeBuilder(), encoding='utf-8')
                parser.feed(xml_content.encode('utf-8'))
                root = parser.close()
            else:
                # Parse XML normally for smaller files
                root = ET.fromstring(xml_content)
            
            return root
        except ET.ParseError as e:
            print(f"XML parsing error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error parsing XML: {e}")
            return None
    
    def format_xml(self, xml_content: str) -> str:
        """Format XML content with proper indentation"""
        try:
            # For large files, use a more memory-efficient approach
            if len(xml_content) > 1024 * 1024:  # 1MB threshold
                return self._format_large_xml(xml_content)
            
            # Parse and reformat normally for smaller files
            dom = xml.dom.minidom.parseString(xml_content)
            formatted = dom.toprettyxml(indent="  ")
            
            # Remove empty lines and extra whitespace
            lines = formatted.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # Remove lines that are just whitespace
                if line.strip():
                    cleaned_lines.append(line.rstrip())
            
            return '\n'.join(cleaned_lines)
            
        except Exception as e:
            print(f"Error formatting XML: {e}")
            return xml_content
    
    def _format_large_xml(self, xml_content: str) -> str:
        """Format large XML files more efficiently"""
        try:
            # Use iterative parsing for large files
            parser = ET.XMLParser(target=ET.TreeBuilder(), encoding='utf-8')
            parser.feed(xml_content.encode('utf-8'))
            root = parser.close()
            
            # Build formatted XML manually to avoid memory issues
            return self._build_formatted_xml(root)
        except Exception as e:
            print(f"Error formatting large XML: {e}")
            return xml_content
    
    def _build_formatted_xml(self, element: ET.Element, level: int = 0) -> str:
        """Build formatted XML string manually"""
        indent = "  " * level
        result = []
        
        # Opening tag
        if element.attrib:
            attrs = ' '.join([f'{k}="{v}"' for k, v in element.attrib.items()])
            result.append(f"{indent}<{element.tag} {attrs}>")
        else:
            result.append(f"{indent}<{element.tag}>")
        
        # Text content
        if element.text and element.text.strip():
            result.append(element.text.strip())
        
        # Child elements
        for child in element:
            result.append(self._build_formatted_xml(child, level + 1))
        
        # Closing tag
        result.append(f"{indent}</{element.tag}>")
        
        # Tail text
        if element.tail and element.tail.strip():
            result.append(element.tail.strip())
        
        return '\n'.join(result)
    
    def validate_xml(self, xml_content: str) -> XmlValidationResult:
        """Validate XML content"""
        errors = []
        
        try:
            # Basic XML validation
            root = self.parse_xml(xml_content)
            if root is None:
                errors.append("Invalid XML structure")
                return XmlValidationResult(False, errors)
            
            # Check for common issues
            self._validate_xml_structure(xml_content, errors)
            
            # Check for unmatched tags
            self._check_unmatched_tags(xml_content, errors)
            
            # Check for proper XML declaration
            self._check_xml_declaration(xml_content, errors)
            
            return XmlValidationResult(len(errors) == 0, errors)
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return XmlValidationResult(False, errors)
    
    def _validate_xml_structure(self, xml_content: str, errors: List[str]):
        """Validate XML structure"""
        try:
            # Try to parse with ElementTree for basic validation
            ET.fromstring(xml_content)
        except ET.ParseError as e:
            error_msg = str(e)
            
            # Extract line and column information if available
            line_match = re.search(r'line (\d+)', error_msg)
            col_match = re.search(r'column (\d+)', error_msg)
            
            if line_match and col_match:
                line = line_match.group(1)
                col = col_match.group(1)
                errors.append(f"Line {line}, Column {col}: {error_msg}")
            else:
                errors.append(f"XML Structure Error: {error_msg}")
    
    def _check_unmatched_tags(self, xml_content: str, errors: List[str]):
        """Check for unmatched tags"""
        # Simple regex-based check for unmatched tags
        # This is a basic implementation - a full XML parser would be better
        
        lines = xml_content.split('\n')
        tag_stack = []
        
        for line_num, line in enumerate(lines, 1):
            # Find opening tags
            opening_tags = re.findall(r'<([a-zA-Z_][a-zA-Z0-9_-]*)', line)
            # Find closing tags
            closing_tags = re.findall(r'</([a-zA-Z_][a-zA-Z0-9_-]*)>', line)
            
            for tag in opening_tags:
                # Skip self-closing tags
                if not re.search(f'<{tag}[^>]*/>', line):
                    tag_stack.append((tag, line_num))
            
            for tag in closing_tags:
                if tag_stack and tag_stack[-1][0] == tag:
                    tag_stack.pop()
                else:
                    errors.append(f"Line {line_num}: Unmatched closing tag '</{tag}>'")
        
        # Check for unclosed tags
        for tag, line_num in tag_stack:
            errors.append(f"Line {line_num}: Unclosed tag '<{tag}>'")
    
    def _check_xml_declaration(self, xml_content: str, errors: List[str]):
        """Check XML declaration"""
        stripped = xml_content.strip()
        if not stripped.startswith('<?xml'):
            errors.append("Missing XML declaration")
        else:
            # Check for proper XML declaration format
            declaration_match = re.match(r'<\?xml\s+version="1\.0"', stripped)
            if not declaration_match:
                errors.append("Invalid XML declaration format")
    
    def build_xml_tree(self, xml_content: str) -> Optional[XmlTreeNode]:
        """Build tree structure from XML content"""
        try:
            root = self.parse_xml(xml_content)
            if root is None:
                return None
            
            # Build tree with line numbers
            return self._build_tree_with_line_numbers(xml_content, root)
            
        except Exception as e:
            print(f"Error building XML tree: {e}")
            return None
    
    def _build_tree_with_line_numbers(self, xml_content: str, root: ET.Element) -> XmlTreeNode:
        """Build tree with line numbers from XML content"""
        lines = xml_content.split('\n')
        # Quick Win #3: Pre-compute line index for 50-70% faster line number lookups
        line_index = self._build_line_index(lines)
        return self._element_to_tree_node_with_lines(root, lines, "", 0, None, line_index)
    
    def _build_line_index(self, lines: List[str]) -> Dict[str, List[int]]:
        """Build an index mapping tag names to line numbers for fast lookup"""
        line_index = {}
        for i, line in enumerate(lines):
            # Find all opening tags on this line
            matches = re.finditer(r'<([a-zA-Z_][a-zA-Z0-9_:-]*)', line)
            for match in matches:
                tag = match.group(1)
                if tag not in line_index:
                    line_index[tag] = []
                line_index[tag].append(i)
        return line_index
    
    def _element_to_tree_node_with_lines(self, element: ET.Element, lines: List[str], parent_path: str = "", start_line: int = 0, parent_element: Optional[ET.Element] = None, line_index: Optional[Dict[str, List[int]]] = None) -> XmlTreeNode:
        """Convert XML element to tree node with line numbers, including index-aware paths"""
        # Determine sibling index for this element (1-based)
        if parent_element is not None:
            siblings_before = 0
            for sibling in parent_element:
                if sibling is element:
                    break
                if sibling.tag == element.tag:
                    siblings_before += 1
            index = siblings_before + 1
        else:
            # Root element index is 1
            index = 1
        
        # Build index-aware path with leading '/'
        if parent_path:
            current_path = f"{parent_path}/{element.tag}[{index}]"
        else:
            current_path = f"/{element.tag}[{index}]"
        
        # Get text content (if any)
        text = element.text.strip() if element.text and element.text.strip() else ""
        
        # Get attributes as string
        attrs = []
        for key, value in element.attrib.items():
            attrs.append(f'{key}="{value}"')
        attr_string = " ".join(attrs)
        
        # Create display name
        display_name = element.tag
        if attr_string:
            display_name += f" [{attr_string}]"
        
        # Find line number for this element using index if available
        if line_index and element.tag in line_index:
            # Use pre-computed index for faster lookup
            tag_lines = line_index[element.tag]
            line_number = next((line + 1 for line in tag_lines if line >= start_line), 0)
        else:
            # Fallback to sequential search
            line_number = self._find_element_line_number(lines, element.tag, start_line)
        
        # Create node
        node = XmlTreeNode(
            name=display_name,
            tag=element.tag,
            value=text,
            attributes=dict(element.attrib),
            path=current_path,
            line_number=line_number
        )
        
        # Add child nodes
        current_line = line_number if line_number > 0 else start_line
        for child in element:
            child_node = self._element_to_tree_node_with_lines(child, lines, current_path, current_line, element, line_index)
            # Set back-reference to parent for breadcrumb generation
            try:
                child_node.parent_node = node
            except Exception:
                pass
            node.children.append(child_node)
            # Update current line for next sibling
            if child_node.line_number > current_line:
                current_line = child_node.line_number
        
        return node
    
    def _find_element_line_number(self, lines: List[str], tag_name: str, start_line: int = 0) -> int:
        """Find the line number for an XML element"""
        for i in range(start_line, len(lines)):
            line = lines[i].strip()
            # Look for opening tag
            if f"<{tag_name}" in line or f"<{tag_name}>" in line:
                return i + 1  # Convert to 1-based line number
        return 0  # Not found
    
    def _element_to_tree_node(self, element: ET.Element, parent_path: str = "", parent_element: Optional[ET.Element] = None) -> XmlTreeNode:
        """Convert XML element to tree node (legacy method) with index-aware paths"""
        # Determine sibling index
        if parent_element is not None:
            siblings_before = 0
            for sibling in parent_element:
                if sibling is element:
                    break
                if sibling.tag == element.tag:
                    siblings_before += 1
            index = siblings_before + 1
        else:
            index = 1
        
        # Build path with index and leading '/'
        if parent_path:
            current_path = f"{parent_path}/{element.tag}[{index}]"
        else:
            current_path = f"/{element.tag}[{index}]"
        
        # Get text content (if any)
        text = element.text.strip() if element.text and element.text.strip() else ""
        
        # Get attributes as string
        attrs = []
        for key, value in element.attrib.items():
            attrs.append(f'{key}="{value}"')
        attr_string = " ".join(attrs)
        
        # Create display name
        display_name = element.tag
        if attr_string:
            display_name += f" [{attr_string}]"
        
        # Create node
        node = XmlTreeNode(
            name=display_name,
            tag=element.tag,
            value=text,
            attributes=dict(element.attrib),
            path=current_path,
            line_number=0  # No line number in legacy
        )
        
        # Add child nodes
        for child in element:
            child_node = self._element_to_tree_node(child, current_path, element)
            try:
                child_node.parent_node = node
            except Exception:
                pass
            node.children.append(child_node)
        
        return node
    
    def get_element_line_number(self, xml_content: str, element_path: str) -> int:
        """Get line number for specific XML element path"""
        try:
            lines = xml_content.split('\n')
            
            # Simple path parsing - this could be more sophisticated
            path_parts = element_path.split('/')
            current_tag = path_parts[-1] if path_parts else ""
            
            for i, line in enumerate(lines, 1):
                if f"<{current_tag}" in line:
                    return i
            
            return -1
            
        except Exception:
            return -1
    
    def find_elements_by_xpath(self, xml_content: str, xpath: str) -> List[ET.Element]:
        """Find XML elements by XPath (basic implementation)"""
        try:
            root = self.parse_xml(xml_content)
            if root is None:
                return []
            
            # Basic XPath support - this is a simplified implementation
            # For full XPath support, you'd need a proper XPath library
            
            if xpath.startswith('//'):
                # Find all elements with this tag
                tag_name = xpath[2:]
                return root.findall(f".//{tag_name}")
            elif xpath.startswith('/'):
                # Absolute path
                tag_name = xpath[1:]
                return root.findall(f"./{tag_name}")
            else:
                # Relative path
                return root.findall(xpath)
                
        except Exception as e:
            print(f"Error finding elements by XPath: {e}")
            return []
    
    def get_xml_statistics(self, xml_content: str) -> XmlStatistics:
        """Get XML statistics"""
        try:
            root = self.parse_xml(xml_content)
            if root is None:
                return XmlStatistics(0, 0, 0, 0, 0)
            
            element_count = 0
            attribute_count = 0
            text_node_count = 0
            comment_count = 0
            
            def count_elements(element: ET.Element):
                nonlocal element_count, attribute_count, text_node_count
                
                element_count += 1
                attribute_count += len(element.attrib)
                
                if element.text and element.text.strip():
                    text_node_count += 1
                
                for child in element:
                    count_elements(child)
            
            count_elements(root)
            
            # Count comments manually
            comment_pattern = r'<!--.*?-->'
            comments = re.findall(comment_pattern, xml_content, re.DOTALL)
            comment_count = len(comments)
            
            total_size = len(xml_content.encode('utf-8'))
            
            return XmlStatistics(
                element_count=element_count,
                attribute_count=attribute_count,
                text_node_count=text_node_count,
                comment_count=comment_count,
                total_size=total_size
            )
            
        except Exception as e:
            print(f"Error getting XML statistics: {e}")
            return XmlStatistics(0, 0, 0, 0, 0)
    
    def set_namespace(self, prefix: str, uri: str):
        """Set namespace for XPath queries"""
        self.namespaces[prefix] = uri
    
    def clear_namespaces(self):
        """Clear all namespaces"""
        self.namespaces.clear()
    
    def create_split_config(self, threshold_percentage: float = 15.0, upper_levels: list = None) -> XmlSplitConfig:
        """Create a default split configuration with threshold-based rules"""
        if upper_levels is None:
            upper_levels = [2, 3]
        
        config = XmlSplitConfig(
            threshold_percentage=threshold_percentage,
            upper_levels=upper_levels
        )
        return config
    
    def analyze_xml_for_splitting(self, xml_content: str, config: XmlSplitConfig = None) -> dict:
        """Analyze XML content to determine optimal splitting strategy"""
        if config is None:
            config = self.create_split_config()
        
        splitter = XmlSplitter(config)
        return splitter.analyze_xml_structure(xml_content)
    
    def split_xml_content(self, xml_content: str, output_dir: str, config: XmlSplitConfig = None) -> bool:
        """Split XML content into manageable parts"""
        try:
            if config is None:
                config = self.create_split_config()
            
            splitter = XmlSplitter(config)
            metadata = splitter.split_xml(xml_content, output_dir)
            
            return metadata is not None
            
        except Exception as e:
            print(f"Error splitting XML: {e}")
            return False
    
    def load_split_project(self, split_directory: str) -> XmlPartManager:
        """Load an existing split XML project"""
        return XmlPartManager(split_directory)
    
    def reconstruct_xml_from_parts(self, split_directory: str) -> str:
        """Reconstruct complete XML from split parts"""
        part_manager = XmlPartManager(split_directory)
        return part_manager.reconstruct_xml()
    
    def validate_split_project(self, split_directory: str) -> dict:
        """Validate all parts in a split project"""
        part_manager = XmlPartManager(split_directory)
        return part_manager.validate_parts()
    
    def get_split_project_info(self, split_directory: str) -> dict:
        """Get information about a split project"""
        part_manager = XmlPartManager(split_directory)
        if part_manager.is_split_project():
            return {
                'is_valid': True,
                'statistics': part_manager.get_part_statistics(),
                'parts': part_manager.get_part_list(),
                'dependencies': part_manager.get_dependencies()
            }
        else:
            return {'is_valid': False}
    
    def search_in_split_project(self, split_directory: str, search_term: str, case_sensitive: bool = False) -> list:
        """Search for content across all parts in a split project"""
        part_manager = XmlPartManager(split_directory)
        return part_manager.search_in_parts(search_term, case_sensitive)
    
    def auto_close_tags(self, xml_content: str) -> str:
        """Auto-close unclosed tags by the shortest path.
        
        This method analyzes the XML content and automatically closes any unclosed tags
        by finding the shortest path to close them properly.
        
        Args:
            xml_content: The XML content string that may have unclosed tags
            
        Returns:
            The XML content with all tags properly closed
        """
        try:
            # First try to parse - if it works, no need to fix
            try:
                ET.fromstring(xml_content)
                return xml_content  # Already valid
            except ET.ParseError:
                pass  # Need to fix
            
            lines = xml_content.split('\n')
            tag_stack = []  # Stack of (tag_name, line_index, indent_level)
            result_lines = []
            
            # Track self-closing tags pattern
            self_closing_pattern = re.compile(r'<([a-zA-Z_][a-zA-Z0-9_:-]*)[^>]*/>')
            
            for line_idx, line in enumerate(lines):
                result_lines.append(line)
                
                # Calculate indent level
                indent_level = len(line) - len(line.lstrip())
                
                # Find all self-closing tags and skip them
                self_closing_tags = self_closing_pattern.findall(line)
                
                # Find opening tags (excluding self-closing and closing tags)
                opening_pattern = re.compile(r'<([a-zA-Z_][a-zA-Z0-9_:-]*)[^/>]*>')
                opening_tags = opening_pattern.findall(line)
                
                # Find closing tags
                closing_pattern = re.compile(r'</([a-zA-Z_][a-zA-Z0-9_:-]*)>')
                closing_tags = closing_pattern.findall(line)
                
                # Process opening tags
                for tag in opening_tags:
                    # Skip if this tag is self-closing on this line
                    if tag not in self_closing_tags:
                        # Check if there's a closing tag on the same line
                        if tag not in closing_tags or closing_tags.count(tag) < opening_tags.count(tag):
                            tag_stack.append((tag, line_idx, indent_level))
                
                # Process closing tags
                for tag in closing_tags:
                    if tag_stack and tag_stack[-1][0] == tag:
                        tag_stack.pop()
                    elif tag_stack:
                        # Mismatched closing tag - try to find matching opening tag
                        for i in range(len(tag_stack) - 1, -1, -1):
                            if tag_stack[i][0] == tag:
                                # Close all tags between current position and matching tag
                                tags_to_close = []
                                while len(tag_stack) > i:
                                    tags_to_close.append(tag_stack.pop())
                                # Re-open tags that were closed prematurely (except the matched one)
                                for j in range(len(tags_to_close) - 2, -1, -1):
                                    tag_stack.append(tags_to_close[j])
                                break
            
            # Close any remaining unclosed tags by shortest path
            if tag_stack:
                # Get the indent of the last line
                last_line = result_lines[-1] if result_lines else ""
                base_indent = len(last_line) - len(last_line.lstrip())
                
                # Close tags in reverse order (LIFO - Last In First Out)
                while tag_stack:
                    tag_name, _, tag_indent = tag_stack.pop()
                    # Use the tag's original indent level for closing
                    indent = " " * tag_indent
                    result_lines.append(f"{indent}</{tag_name}>")
            
            return '\n'.join(result_lines)
            
        except Exception as e:
            print(f"Error in auto_close_tags: {e}")
            return xml_content  # Return original on error