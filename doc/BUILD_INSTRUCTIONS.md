# Lotus Xml Editor - Python Version

A modern XML editor with tree view, syntax highlighting, and validation capabilities.

## Features

- **Tree View**: Hierarchical display of XML structure with expandable/collapsible nodes
- **Syntax Highlighting**: Full XML syntax highlighting with Cyrillic character support
- **Bidirectional Sync**: Synchronization between tree view and text editor (both directions)
- **Find in Tree**: Quick navigation to tree nodes using Ctrl+T shortcut
- **Large File Support**: Optimized handling of large XML files (>1MB)
- **Bookmarks**: Navigate through XML using bookmark system (Ctrl+B, Ctrl+Shift+B, F2, Shift+F2)
- **Dark/Light Theme**: Toggle between dark and light themes
- **XML Validation**: Built-in XML validation functionality
- **Breadcrumb Navigation**: Shows current location in XML hierarchy

## Building Executable

The application can be built into a standalone Windows executable using PyInstaller.

### Prerequisites

```bash
pip install -r requirements.txt
pip install pyinstaller
```

### Build Process

#### Option 1: Using the build script
```bash
build.bat
```

#### Option 2: Manual build
```bash
python build_exe.py
```

### Build Output

The executable will be created in the `dist` folder:
- `dist/VisualXmlEditor.exe` - Standalone executable (~59MB)

## Running the Application

### Development Mode
```bash
python main.py
```

### Production Mode
Run the executable directly:
```bash
dist\VisualXmlEditor.exe
```

## Keyboard Shortcuts

- **Ctrl+T**: Find current cursor position in tree view
- **Ctrl+B**: Toggle bookmark at current line
- **Ctrl+Shift+B**: Clear all bookmarks
- **F2**: Navigate to next bookmark
- **Shift+F2**: Navigate to previous bookmark
- **Ctrl+D**: Toggle dark/light theme

## File Support

The application supports XML files with:
- Standard ASCII characters
- Cyrillic characters (Unicode ranges: \u0400-\u04FF, \u0500-\u052F)
- Large files with optimized memory usage
- UTF-8 encoding

## Technical Details

Built with:
- Python 3.13+
- PyQt6 for GUI framework
- PyInstaller for executable packaging
- lxml for XML processing
- Custom XML highlighter with Cyrillic support