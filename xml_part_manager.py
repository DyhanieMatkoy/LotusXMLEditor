#!/usr/bin/env python3
"""
XML Part Manager - Manages split XML parts and reconstruction
"""

import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import hashlib
import shutil

from xml_splitter import XmlSplitMetadata, XmlSplitConfig, XmlSplitter


class XmlPartManager:
    """Manages XML split parts and provides reconstruction capabilities"""
    
    def __init__(self, split_directory: str):
        self.split_directory = Path(split_directory)
        self.metadata: Optional[XmlSplitMetadata] = None
        self.parts_cache: Dict[str, str] = {}  # path -> content cache
        self.modified_parts: set = set()  # Track which parts have been modified
        
        # Load metadata if it exists
        self._load_metadata()
    
    def _load_metadata(self):
        """Load split metadata from the split directory"""
        metadata_path = self.split_directory / "metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.metadata = XmlSplitMetadata.from_dict(data)
            except Exception as e:
                print(f"Error loading metadata: {e}")
                self.metadata = None
    
    def is_split_project(self) -> bool:
        """Check if the directory contains a valid split project"""
        return (self.metadata is not None and 
                (self.split_directory / "parts").exists())
    
    def get_part_list(self) -> List[Dict[str, Any]]:
        """Get list of all parts with their information"""
        if not self.metadata:
            return []
        
        parts = []
        for xpath, file_path in self.metadata.part_mapping.items():
            full_path = self.split_directory / file_path
            if full_path.exists():
                stat = full_path.stat()
                parts.append({
                    'xpath': xpath,
                    'file_path': file_path,
                    'full_path': str(full_path),
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                    'is_modified': file_path in self.modified_parts
                })
        
        return parts
    
    def get_part_content(self, xpath: str) -> Optional[str]:
        """Get content of a specific part"""
        if not self.metadata or xpath not in self.metadata.part_mapping:
            return None
        
        file_path = self.metadata.part_mapping[xpath]
        
        # Check cache first
        if file_path in self.parts_cache:
            return self.parts_cache[file_path]
        
        # Load from file
        full_path = self.split_directory / file_path
        if full_path.exists():
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.parts_cache[file_path] = content
                return content
            except Exception as e:
                print(f"Error reading part {file_path}: {e}")
        
        return None
    
    def update_part_content(self, xpath: str, content: str) -> bool:
        """Update content of a specific part"""
        if not self.metadata or xpath not in self.metadata.part_mapping:
            return False
        
        file_path = self.metadata.part_mapping[xpath]
        full_path = self.split_directory / file_path
        
        try:
            # Validate XML content
            ET.fromstring(content)
            
            # Write to file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update cache
            self.parts_cache[file_path] = content
            self.modified_parts.add(file_path)
            
            return True
            
        except ET.ParseError as e:
            print(f"Invalid XML content for part {xpath}: {e}")
            return False
        except Exception as e:
            print(f"Error updating part {xpath}: {e}")
            return False
    
    def reconstruct_xml(self) -> Optional[str]:
        """Reconstruct the complete XML from all parts"""
        if not self.metadata:
            return None
        
        try:
            # If there's only one part (original file), return it directly
            if len(self.metadata.part_mapping) == 1 and "/" in self.metadata.part_mapping:
                return self.get_part_content("/")
            
            # For multiple parts, we need to reconstruct
            # This is a simplified reconstruction - in a full implementation,
            # you'd need to properly merge the parts based on the original structure
            
            reconstructed_parts = []
            
            # Add XML declaration
            reconstructed_parts.append('<?xml version="1.0" encoding="UTF-8"?>')
            
            # Create a root element to contain all parts
            root_tag = "reconstructed_xml"
            reconstructed_parts.append(f'<{root_tag}>')
            
            # Add each part
            for xpath, file_path in self.metadata.part_mapping.items():
                if xpath == "/":  # Skip root placeholder
                    continue
                    
                content = self.get_part_content(xpath)
                if content:
                    # Remove XML declaration from part
                    lines = content.split('\n')
                    content_lines = [line for line in lines if not line.strip().startswith('<?xml')]
                    part_content = '\n'.join(content_lines).strip()
                    
                    # Add part with comment
                    reconstructed_parts.append(f'  <!-- Part: {xpath} -->')
                    # Indent the part content
                    indented_content = '\n'.join(f'  {line}' for line in part_content.split('\n'))
                    reconstructed_parts.append(indented_content)
            
            reconstructed_parts.append(f'</{root_tag}>')
            
            return '\n'.join(reconstructed_parts)
            
        except Exception as e:
            print(f"Error reconstructing XML: {e}")
            return None
    
    def validate_parts(self) -> Dict[str, List[str]]:
        """Validate all parts and return any errors"""
        errors = {}
        
        if not self.metadata:
            return {'general': ['No metadata found']}
        
        for xpath, file_path in self.metadata.part_mapping.items():
            part_errors = []
            
            # Check if file exists
            full_path = self.split_directory / file_path
            if not full_path.exists():
                part_errors.append(f"File not found: {file_path}")
                continue
            
            # Validate XML content
            content = self.get_part_content(xpath)
            if content:
                try:
                    ET.fromstring(content)
                except ET.ParseError as e:
                    part_errors.append(f"Invalid XML: {e}")
            else:
                part_errors.append("Could not read content")
            
            if part_errors:
                errors[xpath] = part_errors
        
        return errors
    
    def get_part_statistics(self) -> Dict[str, Any]:
        """Get statistics about the split parts"""
        if not self.metadata:
            return {}
        
        stats = {
            'total_parts': self.metadata.total_parts,
            'modified_parts': len(self.modified_parts),
            'split_timestamp': self.metadata.split_timestamp.isoformat(),
            'original_checksum': self.metadata.checksum,
            'parts_info': []
        }
        
        total_size = 0
        for part_info in self.get_part_list():
            total_size += part_info['size']
            stats['parts_info'].append({
                'xpath': part_info['xpath'],
                'size': part_info['size'],
                'size_kb': round(part_info['size'] / 1024, 2),
                'modified': part_info['modified'].isoformat(),
                'is_modified': part_info['is_modified']
            })
        
        stats['total_size'] = total_size
        stats['total_size_kb'] = round(total_size / 1024, 2)
        
        return stats
    
    def export_reconstructed_xml(self, output_path: str) -> bool:
        """Export the reconstructed XML to a file"""
        reconstructed = self.reconstruct_xml()
        if not reconstructed:
            return False
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(reconstructed)
            return True
        except Exception as e:
            print(f"Error exporting reconstructed XML: {e}")
            return False
    
    def create_backup(self, backup_path: str) -> bool:
        """Create a backup of the entire split project"""
        try:
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            
            shutil.copytree(str(self.split_directory), backup_path)
            return True
        except Exception as e:
            print(f"Error creating backup: {e}")
            return False
    
    def get_dependencies(self) -> List[str]:
        """Get list of external dependencies (if any)"""
        if not self.metadata:
            return []
        return self.metadata.dependencies.copy()
    
    def add_dependency(self, dependency: str):
        """Add an external dependency"""
        if self.metadata and dependency not in self.metadata.dependencies:
            self.metadata.dependencies.append(dependency)
            self._save_metadata()
    
    def remove_dependency(self, dependency: str):
        """Remove an external dependency"""
        if self.metadata and dependency in self.metadata.dependencies:
            self.metadata.dependencies.remove(dependency)
            self._save_metadata()
    
    def _save_metadata(self):
        """Save metadata to file"""
        if not self.metadata:
            return
        
        metadata_path = self.split_directory / "metadata.json"
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving metadata: {e}")
    
    def refresh_cache(self):
        """Clear and refresh the parts cache"""
        self.parts_cache.clear()
        self.modified_parts.clear()
    
    def get_part_by_element_name(self, element_name: str) -> Optional[Tuple[str, str]]:
        """Find a part that contains a specific element name"""
        for xpath, file_path in self.metadata.part_mapping.items():
            content = self.get_part_content(xpath)
            if content and f'<{element_name}' in content:
                return xpath, content
        return None
    
    def search_in_parts(self, search_term: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """Search for a term across all parts"""
        results = []
        
        if not case_sensitive:
            search_term = search_term.lower()
        
        for xpath, file_path in self.metadata.part_mapping.items():
            content = self.get_part_content(xpath)
            if content:
                search_content = content if case_sensitive else content.lower()
                if search_term in search_content:
                    # Find line numbers
                    lines = content.split('\n')
                    matching_lines = []
                    
                    for i, line in enumerate(lines, 1):
                        check_line = line if case_sensitive else line.lower()
                        if search_term in check_line:
                            matching_lines.append({
                                'line_number': i,
                                'content': line.strip(),
                                'start_pos': check_line.find(search_term)
                            })
                    
                    results.append({
                        'xpath': xpath,
                        'file_path': file_path,
                        'matches': len(matching_lines),
                        'matching_lines': matching_lines
                    })
        
        return results


class XmlReconstructor:
    """Advanced XML reconstruction with proper structure preservation"""
    
    def __init__(self, part_manager: XmlPartManager):
        self.part_manager = part_manager
    
    def reconstruct_with_structure(self) -> Optional[str]:
        """Reconstruct XML while preserving the original structure"""
        # This would be a more sophisticated reconstruction
        # that properly merges parts back into their original positions
        # For now, delegate to the part manager's simpler reconstruction
        return self.part_manager.reconstruct_xml()
    
    def validate_reconstruction(self, original_checksum: str) -> bool:
        """Validate that reconstruction matches original structure"""
        reconstructed = self.reconstruct_with_structure()
        if not reconstructed:
            return False
        
        # Calculate checksum of reconstructed content
        reconstructed_checksum = hashlib.md5(reconstructed.encode()).hexdigest()
        
        # Note: This is a simplified check. In practice, you might want
        # to compare structure rather than exact content due to formatting differences
        return reconstructed_checksum == original_checksum