# Lotus XML Editor

A modern XML editor with tree view, syntax highlighting, validation, and code folding.

## Features

### Core Features
- **XML Tree View** - Navigate XML structure with expandable tree
- **Syntax Highlighting** - Color-coded XML syntax
- **XML Validation** - Validate XML structure
- **Format XML** - Auto-format XML with proper indentation
- **Find & Replace** - Search and replace text with regex support

### Code Folding (NEW!)
- **Visual Fold Controls** - Click triangles in line number area to fold/unfold
- **Keyboard Shortcuts**:
  - `Ctrl+Shift+[` - Fold current element
  - `Ctrl+Shift+]` - Unfold current element
  - `Ctrl+Shift+U` - Unfold all
- **Hover Indicators** - Fold controls appear on mouse hover
- See [FOLDING_RU.md](FOLDING_RU.md) for detailed guide

### Advanced Features
- **Bookmarks** - Set and navigate bookmarks
- **XPath Links** - Save and navigate to XML elements via XPath (NEW!)
  - `Ctrl+F11` - Copy XPath of current position
  - `F12` - Navigate to XPath link
  - See [XPATH_LINKS_QUICKSTART.md](XPATH_LINKS_QUICKSTART.md) for quick start
- **Line Numbers** - Toggle line numbers (`Ctrl+L`)
- **Fragment Editor** - Edit XML fragments in separate windows
- **Metro Navigator** - Visual XML structure navigator
- **Multi-column Tree** - Experimental multi-column view
- **Structure Diagram** - Layered diagram view

### 1C Exchange
- Import/Export XML files for 1C:Enterprise
- Semi-automatic and manual modes
- ZIP packaging support

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Building Executable

```bash
# Build with PyInstaller
python build_exe.py
```

## Keyboard Shortcuts

### File Operations
- `Ctrl+N` - New file
- `Ctrl+O` - Open file
- `Ctrl+S` - Save file
- `Ctrl+Shift+S` - Save As

### Editing
- `Ctrl+Z` - Undo
- `Ctrl+Y` - Redo
- `Ctrl+F` - Find
- `F3` - Find Next
- `Ctrl+H` - Replace
- `Ctrl+G` - Go to Line

### Code Folding
- `Ctrl+Shift+[` - Fold current element
- `Ctrl+Shift+]` - Unfold current element
- `Ctrl+Shift+U` - Unfold all
- `Alt+2..9` - Fold all elements at level N

### Navigation
- `Ctrl+]` - Jump to matching closing tag
- `Ctrl+[` - Jump to matching opening tag

### View
- `Ctrl+L` - Toggle line numbers
- `Ctrl+M` - Open Metro Navigator
- `F6/F7` - Navigate tree up/down

### Bookmarks
- `Alt+F2` - Toggle bookmark
- `F2` - Next bookmark
- `Shift+F2` - Previous bookmark

### XPath Links
- `Ctrl+F11` - Copy XPath of current position to Links
- `F12` - Navigate to XPath from Links

See `F1` in the application for complete shortcuts list.

## Requirements

- Python 3.8+
- PyQt6
- lxml (optional, for better performance)

## License

See LICENSE file for details.

## Version

See [version.py](version.py) for current version information.
