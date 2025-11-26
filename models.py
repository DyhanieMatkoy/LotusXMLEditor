"""
Data models for XML editor
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import os


@dataclass
class XmlTreeNode:
    """Represents a node in the XML tree structure"""
    name: str
    tag: str
    value: Optional[str] = None
    attributes: Dict[str, str] = field(default_factory=dict)
    children: List['XmlTreeNode'] = field(default_factory=list)
    path: str = ""
    line_number: int = 0
    
    def __post_init__(self):
        """Post-initialization processing"""
        if self.value is None:
            self.value = ""


@dataclass
class XmlValidationError:
    """Represents an XML validation error"""
    message: str
    line_number: int = 0
    column_number: int = 0
    error_type: str = "validation"
    severity: str = "error"  # error, warning, info
    
    def __str__(self):
        """String representation of the error"""
        if self.line_number > 0 and self.column_number > 0:
            return f"Line {self.line_number}, Column {self.column_number}: {self.message}"
        elif self.line_number > 0:
            return f"Line {self.line_number}: {self.message}"
        else:
            return self.message


@dataclass
class XmlValidationResult:
    """Result of XML validation"""
    is_valid: bool
    errors: List[XmlValidationError] = field(default_factory=list)
    
    def __post_init__(self):
        """Post-initialization processing"""
        if not self.errors:
            self.errors = []
    
    @property
    def error_count(self) -> int:
        """Get number of errors"""
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        """Get number of warnings (for future use)"""
        return len([e for e in self.errors if e.severity == "warning"])
    
    def add_error(self, message: str, line: int = 0, column: int = 0, error_type: str = "validation"):
        """Add an error to the result"""
        error = XmlValidationError(
            message=message,
            line_number=line,
            column_number=column,
            error_type=error_type
        )
        self.errors.append(error)
        self.is_valid = False
    
    def get_error_messages(self) -> List[str]:
        """Get all error messages as strings"""
        return [str(error) for error in self.errors]


@dataclass
class XmlStatistics:
    """XML document statistics"""
    element_count: int
    attribute_count: int
    text_node_count: int
    comment_count: int
    total_size: int  # in bytes
    
    def __post_init__(self):
        """Post-initialization processing"""
        # Ensure non-negative values
        self.element_count = max(0, self.element_count)
        self.attribute_count = max(0, self.attribute_count)
        self.text_node_count = max(0, self.text_node_count)
        self.comment_count = max(0, self.comment_count)
        self.total_size = max(0, self.total_size)
    
    @property
    def size_kb(self) -> float:
        """Get size in kilobytes"""
        return self.total_size / 1024
    
    @property
    def size_mb(self) -> float:
        """Get size in megabytes"""
        return self.total_size / (1024 * 1024)
    
    def get_size_string(self) -> str:
        """Get human-readable size string"""
        if self.total_size < 1024:
            return f"{self.total_size} bytes"
        elif self.total_size < 1024 * 1024:
            return f"{self.size_kb:.1f} KB"
        else:
            return f"{self.size_mb:.1f} MB"
    
    def __str__(self):
        """String representation of statistics"""
        return (
            f"Elements: {self.element_count}\n"
            f"Attributes: {self.attribute_count}\n"
            f"Text nodes: {self.text_node_count}\n"
            f"Comments: {self.comment_count}\n"
            f"Total size: {self.get_size_string()}"
        )


@dataclass
class XmlFileModel:
    """Represents an XML file with its content and metadata"""
    file_name: str
    content: str = ""
    file_path: str = ""
    is_modified: bool = False
    encoding: str = "UTF-8"
    is_readonly: bool = False
    last_modified: Optional[datetime] = None
    size: int = 0
    
    def __post_init__(self):
        """Post-initialization processing"""
        if not self.file_name and self.file_path:
            self.file_name = os.path.basename(self.file_path)
        
        if not self.last_modified and self.file_path and os.path.exists(self.file_path):
            try:
                timestamp = os.path.getmtime(self.file_path)
                self.last_modified = datetime.fromtimestamp(timestamp)
            except (OSError, IOError):
                self.last_modified = datetime.now()
        
        if self.size == 0 and self.content:
            self.size = len(self.content.encode(self.encoding, errors='replace'))
    
    @classmethod
    def create_new(cls, file_name: str = "untitled.xml") -> 'XmlFileModel':
        """Create a new XML file model"""
        return cls(
            file_name=file_name,
            content='<?xml version="1.0" encoding="UTF-8"?>\n<root>\n</root>',
            is_modified=False,
            last_modified=datetime.now()
        )
    
    @classmethod
    def from_file(cls, file_path: str) -> Optional['XmlFileModel']:
        """Create XML file model from file path"""
        try:
            if not os.path.exists(file_path):
                return None
            
            # Detect encoding
            encoding = cls._detect_encoding(file_path)
            
            with open(file_path, 'r', encoding=encoding) as file:
                content = file.read()
            
            # Get file stats
            stat = os.stat(file_path)
            last_modified = datetime.fromtimestamp(stat.st_mtime)
            size = stat.st_size
            
            return cls(
                file_name=os.path.basename(file_path),
                content=content,
                file_path=file_path,
                encoding=encoding,
                is_modified=False,
                last_modified=last_modified,
                size=size
            )
            
        except (OSError, IOError, UnicodeDecodeError) as e:
            print(f"Error loading file {file_path}: {e}")
            return None
    
    @staticmethod
    def _detect_encoding(file_path: str) -> str:
        """Detect file encoding"""
        # Try common encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    file.read()
                return encoding
            except UnicodeDecodeError:
                continue
        
        # Default to UTF-8 if all else fails
        return 'utf-8'
    
    def save(self, file_path: Optional[str] = None) -> bool:
        """Save the file"""
        if file_path:
            self.file_path = file_path
            self.file_name = os.path.basename(file_path)
        
        if not self.file_path:
            return False
        
        try:
            with open(self.file_path, 'w', encoding=self.encoding) as file:
                file.write(self.content)
            
            # Update metadata
            self.is_modified = False
            stat = os.stat(self.file_path)
            self.last_modified = datetime.fromtimestamp(stat.st_mtime)
            self.size = stat.st_size
            
            return True
            
        except (OSError, IOError) as e:
            print(f"Error saving file {self.file_path}: {e}")
            return False
    
    def update_content(self, new_content: str) -> bool:
        """Update file content"""
        if self.content != new_content:
            self.content = new_content
            self.is_modified = True
            self.size = len(new_content.encode(self.encoding, errors='replace'))
            return True
        return False
    
    def get_display_name(self) -> str:
        """Get display name for UI"""
        if self.is_modified:
            return f"{self.file_name} *"
        return self.file_name
    
    def get_size_string(self) -> str:
        """Get human-readable size string"""
        if self.size < 1024:
            return f"{self.size} bytes"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        else:
            return f"{self.size / (1024 * 1024):.1f} MB"


@dataclass
class PluginInfo:
    """Information about a plugin"""
    name: str
    version: str
    description: str
    author: str
    is_enabled: bool = True
    file_path: str = ""
    
    def __str__(self):
        """String representation"""
        return f"{self.name} v{self.version} by {self.author}"


@dataclass
class ThemeInfo:
    """Information about a theme"""
    name: str
    display_name: str
    is_dark: bool = False
    background_color: str = "#FFFFFF"
    text_color: str = "#000000"
    accent_color: str = "#007ACC"
    
    def __post_init__(self):
        """Post-initialization processing"""
        if self.is_dark:
            if self.background_color == "#FFFFFF":
                self.background_color = "#1E1E1E"
            if self.text_color == "#000000":
                self.text_color = "#D4D4D4"
            if self.accent_color == "#007ACC":
                self.accent_color = "#007ACC"


@dataclass
class AppSettings:
    """Application settings"""
    theme: str = "Light"
    font_family: str = "Consolas"
    font_size: int = 11
    tab_size: int = 4
    show_line_numbers: bool = True
    word_wrap: bool = False
    auto_save_interval: int = 300  # seconds
    recent_files: List[str] = field(default_factory=list)
    max_recent_files: int = 10
    
    def __post_init__(self):
        """Post-initialization processing"""
        if not self.recent_files:
            self.recent_files = []
    
    def add_recent_file(self, file_path: str):
        """Add file to recent files list"""
        # Remove if already exists
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        
        # Add to front
        self.recent_files.insert(0, file_path)
        
        # Limit size
        if len(self.recent_files) > self.max_recent_files:
            self.recent_files = self.recent_files[:self.max_recent_files]
    
    def remove_recent_file(self, file_path: str):
        """Remove file from recent files list"""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)


# Event argument classes for various operations
@dataclass
class FileOperationEventArgs:
    """Event arguments for file operations"""
    file_path: str
    operation: str  # "open", "save", "close", "new"
    success: bool = True
    error_message: str = ""
    
    def __str__(self):
        """String representation"""
        status = "succeeded" if self.success else "failed"
        return f"File {self.operation} {status}: {self.file_path}"


@dataclass
class XmlErrorEventArgs:
    """Event arguments for XML errors"""
    error_message: str
    line_number: int = 0
    column_number: int = 0
    error_type: str = "parse"
    
    def __str__(self):
        """String representation"""
        if self.line_number > 0 and self.column_number > 0:
            return f"XML {self.error_type} error at line {self.line_number}, column {self.column_number}: {self.error_message}"
        elif self.line_number > 0:
            return f"XML {self.error_type} error at line {self.line_number}: {self.error_message}"
        else:
            return f"XML {self.error_type} error: {self.error_message}"


@dataclass
class ThemeChangedEventArgs:
    """Event arguments for theme changes"""
    old_theme: str
    new_theme: str
    is_dark_theme: bool = False
    
    def __str__(self):
        """String representation"""
        return f"Theme changed from '{self.old_theme}' to '{self.new_theme}'"