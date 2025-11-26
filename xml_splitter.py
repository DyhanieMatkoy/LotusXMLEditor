#!/usr/bin/env python3
"""
XML Splitter - Intelligent XML splitting with configurable rules
"""

import os
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
import hashlib


@dataclass
class XmlSplitRule:
    """Configuration for XML splitting rules"""
    rule_type: str  # 'threshold', 'element', 'depth', 'size', 'xpath'
    criteria: str   # threshold percentage, element name, depth number, size limit, xpath
    priority: int = 1
    preserve_context: bool = True  # Keep parent structure
    enabled: bool = True
    
    def __post_init__(self):
        """Validate rule configuration"""
        if self.rule_type not in ['threshold', 'element', 'depth', 'size', 'xpath']:
            raise ValueError(f"Invalid rule type: {self.rule_type}")
    
    @staticmethod
    def create_element_rule(element_name: str, priority: int = 2, preserve_context: bool = True, enabled: bool = True) -> 'XmlSplitRule':
        """Create a rule that splits on a specific element tag name."""
        return XmlSplitRule(
            rule_type='element',
            criteria=element_name,
            priority=priority,
            preserve_context=preserve_context,
            enabled=enabled,
        )
    
    @staticmethod
    def create_depth_rule(depth: int, priority: int = 3, preserve_context: bool = True, enabled: bool = True) -> 'XmlSplitRule':
        """Create a rule that splits elements found at the specified depth level."""
        return XmlSplitRule(
            rule_type='depth',
            criteria=str(depth),
            priority=priority,
            preserve_context=preserve_context,
            enabled=enabled,
        )
    
    @staticmethod
    def create_size_rule(size_limit_bytes: int, priority: int = 4, preserve_context: bool = True, enabled: bool = True) -> 'XmlSplitRule':
        """Create a rule that targets parts based on approximate size limits in bytes (used for planning)."""
        return XmlSplitRule(
            rule_type='size',
            criteria=str(size_limit_bytes),
            priority=priority,
            preserve_context=preserve_context,
            enabled=enabled,
        )
    
    @staticmethod
    def create_xpath_rule(xpath: str, priority: int = 5, preserve_context: bool = True, enabled: bool = True) -> 'XmlSplitRule':
        """Create a rule that splits elements matching a given XPath-like expression."""
        return XmlSplitRule(
            rule_type='xpath',
            criteria=xpath,
            priority=priority,
            preserve_context=preserve_context,
            enabled=enabled,
        )


@dataclass
class XmlSplitConfig:
    """Configuration for XML splitting operation"""
    # Default threshold-based rule
    threshold_percentage: float = 15.0  # Default 15% threshold
    upper_levels: List[int] = field(default_factory=lambda: [2, 3])  # Check levels 2 and 3
    
    # Additional rules
    rules: List[XmlSplitRule] = field(default_factory=list)
    
    # Output configuration
    output_directory: str = ""
    preserve_namespaces: bool = True
    create_index_file: bool = True
    
    # Advanced options
    min_elements_per_part: int = 5
    max_parts: int = 100
    include_comments: bool = True
    
    # Context preservation option to avoid AttributeError in part creation
    preserve_context: bool = True
    
    def __post_init__(self):
        """Initialize default threshold rule if no rules provided"""
        if not self.rules:
            # Create default threshold-based rule
            default_rule = XmlSplitRule(
                rule_type='threshold',
                criteria=f"{self.threshold_percentage}%",
                priority=1,
                preserve_context=True
            )
            self.rules.append(default_rule)
    
    def add_rule(self, rule: XmlSplitRule):
        """Add a new splitting rule"""
        self.rules.append(rule)
        # Sort by priority
        self.rules.sort(key=lambda r: r.priority)
    
    def get_threshold_rule(self) -> Optional[XmlSplitRule]:
        """Get the threshold-based rule if it exists"""
        for rule in self.rules:
            if rule.rule_type == 'threshold' and rule.enabled:
                return rule
        return None


@dataclass
class XmlSplitMetadata:
    """Metadata for split XML operation"""
    original_file: str
    split_timestamp: datetime
    split_config: XmlSplitConfig
    part_mapping: Dict[str, str] = field(default_factory=dict)  # xpath -> file_path
    dependencies: List[str] = field(default_factory=list)       # External references
    checksum: str = ""
    total_parts: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['split_timestamp'] = self.split_timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'XmlSplitMetadata':
        """Create from dictionary (JSON deserialization)"""
        data['split_timestamp'] = datetime.fromisoformat(data['split_timestamp'])
        # Reconstruct XmlSplitConfig
        config_data = data['split_config']
        rules_data = config_data.get('rules', [])
        rules = [XmlSplitRule(**rule_data) for rule_data in rules_data]
        config_data['rules'] = rules
        data['split_config'] = XmlSplitConfig(**config_data)
        return cls(**data)


class XmlSplitter:
    """Main class for intelligent XML splitting"""
    
    def __init__(self, config: XmlSplitConfig):
        self.config = config
        self.element_counts = {}  # Track element counts by level
        self.total_elements = 0
        self.split_points = []  # List of (element, reason) tuples
    
    def analyze_xml_structure(self, xml_content: str) -> Dict[str, Any]:
        """Analyze XML structure to determine optimal split points"""
        try:
            root = ET.fromstring(xml_content)
            self.element_counts = {}
            self.total_elements = 0
            
            # Count elements by level
            self._count_elements_by_level(root, 1)
            
            # Analyze threshold-based splitting
            analysis = {
                'total_elements': self.total_elements,
                'element_counts_by_level': self.element_counts,
                'threshold_analysis': self._analyze_threshold_splitting(root),
                'recommended_splits': self._find_recommended_splits(root)
            }
            
            return analysis
            
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML content: {e}")
    
    def _count_elements_by_level(self, element: ET.Element, level: int):
        """Recursively count elements by their depth level"""
        if level not in self.element_counts:
            self.element_counts[level] = 0
        
        self.element_counts[level] += 1
        self.total_elements += 1
        
        for child in element:
            self._count_elements_by_level(child, level + 1)
    
    def _analyze_threshold_splitting(self, root: ET.Element) -> Dict[str, Any]:
        """Analyze threshold-based splitting for upper levels"""
        threshold_rule = self.config.get_threshold_rule()
        if not threshold_rule:
            return {}
        
        # Extract threshold percentage
        threshold_str = threshold_rule.criteria.rstrip('%')
        threshold_pct = float(threshold_str)
        
        analysis = {
            'threshold_percentage': threshold_pct,
            'upper_levels': self.config.upper_levels,
            'level_analysis': {}
        }
        
        for level in self.config.upper_levels:
            if level in self.element_counts:
                count = self.element_counts[level]
                percentage = (count / self.total_elements) * 100 if self.total_elements > 0 else 0
                
                analysis['level_analysis'][level] = {
                    'element_count': count,
                    'percentage_of_total': percentage,
                    'exceeds_threshold': percentage > threshold_pct,
                    'recommended_for_splitting': percentage > threshold_pct
                }
        
        return analysis
    
    def _find_recommended_splits(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Find recommended split points based on configured rules"""
        splits = []
        
        # Apply threshold-based splitting
        threshold_splits = self._find_threshold_splits(root)
        splits.extend(threshold_splits)
        
        # Apply other rules
        for rule in self.config.rules:
            if not rule.enabled or rule.rule_type == 'threshold':
                continue
                
            if rule.rule_type == 'element':
                element_splits = self._find_element_splits(root, rule)
                splits.extend(element_splits)
            elif rule.rule_type == 'depth':
                depth_splits = self._find_depth_splits(root, rule)
                splits.extend(depth_splits)
        
        # Sort by priority and remove duplicates
        splits.sort(key=lambda s: s.get('priority', 999))
        return splits
    
    def _find_threshold_splits(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Find split points based on threshold analysis"""
        splits = []
        threshold_analysis = self._analyze_threshold_splitting(root)
        
        if not threshold_analysis:
            return splits
        
        # Find elements at levels that exceed threshold
        for level, analysis in threshold_analysis['level_analysis'].items():
            if analysis['recommended_for_splitting']:
                # Find all elements at this level
                elements_at_level = self._find_elements_at_level(root, level)
                
                for element, path in elements_at_level:
                    splits.append({
                        'element': element,
                        'path': path,
                        'level': level,
                        'reason': f"Level {level} exceeds {threshold_analysis['threshold_percentage']}% threshold",
                        'priority': 1,
                        'split_type': 'threshold'
                    })
        
        return splits
    
    def _find_elements_at_level(self, element: ET.Element, target_level: int, current_level: int = 1, path: str = "") -> List[Tuple[ET.Element, str]]:
        """Find all elements at a specific level"""
        elements = []
        current_path = f"{path}/{element.tag}" if path else element.tag
        
        if current_level == target_level:
            elements.append((element, current_path))
        elif current_level < target_level:
            for child in element:
                child_elements = self._find_elements_at_level(child, target_level, current_level + 1, current_path)
                elements.extend(child_elements)
        
        return elements
    
    def _find_element_splits(self, root: ET.Element, rule: XmlSplitRule) -> List[Dict[str, Any]]:
        """Find split points based on element name"""
        splits = []
        element_name = rule.criteria
        
        # Find all elements with the specified name
        for element in root.iter(element_name):
            path = self._get_element_path(root, element)
            splits.append({
                'element': element,
                'path': path,
                'reason': f"Element type '{element_name}' split rule",
                'priority': rule.priority,
                'split_type': 'element'
            })
        
        return splits
    
    def _find_depth_splits(self, root: ET.Element, rule: XmlSplitRule) -> List[Dict[str, Any]]:
        """Find split points based on depth level"""
        splits = []
        target_depth = int(rule.criteria)
        
        elements_at_depth = self._find_elements_at_level(root, target_depth)
        for element, path in elements_at_depth:
            splits.append({
                'element': element,
                'path': path,
                'level': target_depth,
                'reason': f"Depth level {target_depth} split rule",
                'priority': rule.priority,
                'split_type': 'depth'
            })
        
        return splits
    
    def _get_element_path(self, root: ET.Element, target_element: ET.Element) -> str:
        """Get XPath-like path for an element"""
        def find_path(element, path=""):
            current_path = f"{path}/{element.tag}" if path else element.tag
            
            if element is target_element:
                return current_path
            
            for child in element:
                result = find_path(child, current_path)
                if result:
                    return result
            
            return None
        
        return find_path(root) or ""
    
    def split_xml(self, xml_content: str, output_dir: str) -> XmlSplitMetadata:
        """Split XML content according to configuration"""
        # Analyze structure first
        analysis = self.analyze_xml_structure(xml_content)
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create parts directory
        parts_dir = output_path / "parts"
        parts_dir.mkdir(exist_ok=True)
        
        # Parse XML
        root = ET.fromstring(xml_content)
        
        # Generate split metadata
        metadata = XmlSplitMetadata(
            original_file="",  # Will be set by caller
            split_timestamp=datetime.now(),
            split_config=self.config,
            checksum=hashlib.md5(xml_content.encode()).hexdigest()
        )
        
        # Perform splitting based on recommended splits
        recommended_splits = analysis['recommended_splits']
        
        if not recommended_splits:
            # No splits recommended, copy original file
            with open(parts_dir / "original.xml", 'w', encoding='utf-8') as f:
                f.write(xml_content)
            metadata.part_mapping["/"] = "parts/original.xml"
            metadata.total_parts = 1
        else:
            # Create split parts
            part_count = 0
            
            for i, split_info in enumerate(recommended_splits[:self.config.max_parts]):
                element = split_info['element']
                path = split_info['path']
                
                # Create part file
                part_filename = f"part_{i+1:03d}_{element.tag}.xml"
                part_path = parts_dir / part_filename
                
                # Generate XML content for this part
                part_content = self._create_part_content(element, split_info)
                
                with open(part_path, 'w', encoding='utf-8') as f:
                    f.write(part_content)
                
                metadata.part_mapping[path] = f"parts/{part_filename}"
                part_count += 1
            
            metadata.total_parts = part_count
            
            # Create root structure with placeholders
            root_content = self._create_root_with_placeholders(root, recommended_splits)
            with open(parts_dir / "root.xml", 'w', encoding='utf-8') as f:
                f.write(root_content)
        
        # Save metadata
        metadata_path = output_path / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata.to_dict(), f, indent=2)
        
        return metadata
    
    def _create_part_content(self, element: ET.Element, split_info: Dict[str, Any]) -> str:
        """Create XML content for a split part"""
        # Create a new XML document with this element as root
        if self.config.preserve_context:
            # Include parent context if requested
            # For now, just use the element itself
            pass
        
        # Convert element to string
        ET.register_namespace('', '')  # Avoid ns0: prefixes
        xml_str = ET.tostring(element, encoding='unicode')
        
        # Add XML declaration
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'
    
    def _create_root_with_placeholders(self, root: ET.Element, splits: List[Dict[str, Any]]) -> str:
        """Create root XML structure with placeholders for split parts"""
        # For now, create a simple index structure
        # In a full implementation, this would preserve the original structure
        # and replace split elements with include directives
        
        index_root = ET.Element("xml_split_index")
        index_root.set("original_root", root.tag)
        
        for i, split_info in enumerate(splits):
            part_elem = ET.SubElement(index_root, "part")
            part_elem.set("id", str(i+1))
            part_elem.set("path", split_info['path'])
            part_elem.set("file", f"part_{i+1:03d}_{split_info['element'].tag}.xml")
            part_elem.set("reason", split_info['reason'])
        
        xml_str = ET.tostring(index_root, encoding='unicode')
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'