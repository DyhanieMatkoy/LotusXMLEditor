# Lotus Xml Editor - Python Version

A modern XML editor with tree view, syntax highlighting, and validation capabilities, ported from the original C# Avalonia application to Python with PyQt6.

## Features

- **VSCode-like Interface**: Sidebar with XML tree view, main editor area, and bottom panel
- **Auto-Hide UI Elements**: Toolbar, tree header, column headers, and tab bar auto-hide to maximize screen space (NEW!)
- **Syntax Highlighting**: Full XML syntax highlighting with customizable colors
- **XML Tree View**: Hierarchical display of XML structure
- **XML Validation**: Real-time XML validation with detailed error reporting
- **XML Formatting**: Automatic XML formatting with proper indentation
- **Find and Replace**: Search functionality with regex support
- **Go to Line**: Quick navigation to specific line numbers
- **Statistics**: XML document statistics (element count, attributes, etc.)
- **Auto-save**: Automatic backup functionality
- **Multiple Encodings**: Support for UTF-8, Latin-1, and other encodings
- **Recent Files**: Track recently opened files

## Requirements

- Python 3.8 or higher
- PyQt6 (6.5.0 or higher)
- lxml (4.9.0 or higher)
- chardet (5.0.0 or higher)
- pygments (2.15.0 or higher)
- QScintilla (2.14.0 or higher) - optional, for advanced editor features

## Installation

1. Clone or download this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install PyQt6>=6.5.0 lxml>=4.9.0 chardet>=5.0.0 pygments>=2.15.0
```

## Usage

### Running the Application

Simply run the main script:

```bash
python main.py
```

Or use the launcher script (Windows):

```bash
run.bat
```

### Basic Operations

#### File Operations
- **New File**: Ctrl+N or File → New
- **Open File**: Ctrl+O or File → Open
- **Save File**: Ctrl+S or File → Save
- **Save As**: Ctrl+Shift+S or File → Save As
- **Exit**: Ctrl+Q or File → Exit

#### Edit Operations
- **Undo**: Ctrl+Z or Edit → Undo
- **Redo**: Ctrl+Y or Edit → Redo
- **Find**: Ctrl+F or Edit → Find
- **Go to Line**: Ctrl+G or Edit → Go to Line

#### XML Operations
- **Format XML**: Ctrl+Shift+F or XML → Format XML
- **Validate XML**: Ctrl+Shift+V or XML → Validate XML
- **XML Statistics**: XML → XML Statistics

### Interface Layout

The application follows a VSCode-like layout:

```
┌─────────────────────────────────────────────────────────────┐
│ Menu Bar                                                    │
├─────────────────────────────────────────────────────────────┤
│ Tool Bar                                                    │
├─────────────────────┬───────────────────────────────────────┤
│                     │                                       │
│   XML Tree View     │          XML Editor                   │
│   (Sidebar)         │         (Main Area)                   │
│                     │                                       │
│                     │                                       │
├─────────────────────┴───────────────────────────────────────┤
│                    Bottom Panel                           │
│  ┌─────────────┬──────────────┬────────────────────┐     │
│  │   Output    │  Validation  │   Find Results     │     │
│  │             │              │                    │     │
│  └─────────────┴──────────────┴────────────────────┘     │
├─────────────────────────────────────────────────────────────┤
│ Status Bar                                                  │
└─────────────────────────────────────────────────────────────┘
```

### Features in Detail

#### XML Tree View
- Displays XML structure in a hierarchical tree
- Shows element names, attributes, and text content
- Click on tree items to navigate to corresponding XML elements
- Automatically updates when XML content changes

#### XML Editor
- Full syntax highlighting for XML
- Line numbers (when enabled)
- Auto-indentation
- Find and replace functionality
- Go to line navigation

#### Validation Panel
- Real-time XML validation
- Detailed error messages with line and column information
- Highlights validation errors in the bottom panel

#### Output Panel
- Displays XML statistics
- Shows operation results
- Error messages and status information

#### Find Results Panel
- Shows search results across the document
- Line-by-line results with context
- Supports case-sensitive and regex searches

#### Auto-Hide UI Elements (NEW!)

Maximize your screen space with auto-hiding UI elements:

- **Toolbar Auto-Hide**: Command panel automatically hides when not in use
- **Tree Header Auto-Hide**: Level buttons and label hide to maximize tree view
- **Tree Column Header Auto-Hide**: "Element" and "Value" column headers hide automatically
- **Tab Bar Auto-Hide**: Document tabs (Document 1, etc.) hide to maximize editor space
- **Hover Zones**: Thin 3-pixel bars appear where hidden elements are
- **Smooth Animations**: 200ms transitions for polished feel
- **Toggle Controls**: Enable/disable via View menu or keyboard shortcuts
- **Persistent Settings**: Preferences saved across application restarts

**Quick Access:**
- Hover mouse at top edge to reveal toolbar
- Hover at top of tree panel to reveal tree header
- Hover at tree column area to reveal column headers
- Hover at top of editor to reveal tab bar
- Use `Ctrl+Shift+T` to toggle toolbar auto-hide
- Use `Ctrl+Shift+H` to toggle tree header auto-hide
- Use `Ctrl+Shift+E` to toggle tree column header auto-hide
- Use `Ctrl+Shift+B` to toggle tab bar auto-hide

See [AUTO_HIDE_USAGE.md](AUTO_HIDE_USAGE.md) for detailed usage guide.

### Keyboard Shortcuts

#### File Operations
| Shortcut | Action |
|----------|--------|
| Ctrl+N | New file |
| Ctrl+O | Open file |
| Ctrl+S | Save file |
| Ctrl+Shift+S | Save as / Split XML (context) |
| Ctrl+Q | Exit |

#### Edit Operations
| Shortcut | Action |
|----------|--------|
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+F | Find |
| F3 | Find Next |
| Ctrl+G | Go to line |
| Ctrl+L | Delete current line or selected lines |
| Ctrl+/ | Toggle line comment (//) |
| Ctrl+Shift+Up | Move current/selected lines up |
| Ctrl+Shift+Down | Move current/selected lines down |

#### Bookmarks
| Shortcut | Action |
|----------|--------|
| Ctrl+B | Toggle bookmark at cursor |
| Ctrl+Shift+B | Clear all bookmarks |
| F2 | Next bookmark |
| Alt+F2 | Toggle bookmark (menu) |
| Ctrl+Alt+F2 | Previous bookmark |

#### Numbered Bookmarks
| Shortcut | Action |
|----------|--------|
| Ctrl+Shift+1..9 | Set numbered bookmark (1-9) |
| Ctrl+1..9 | Go to numbered bookmark (1-9) |

#### Code Folding
| Shortcut | Action |
|----------|--------|
| Ctrl+Shift+[ | Fold current element |
| Ctrl+Shift+] | Unfold current element |
| Ctrl+Shift+U | Unfold all (Legacy) |
| Alt+0 | Unfold all |
| Alt+1..9 | Fold all elements at level 1-9 |

#### XML Operations
| Shortcut | Action |
|----------|--------|
| Ctrl+Shift+F | Format XML |
| Ctrl+Shift+V | Validate XML |
| Ctrl+Shift+T | Find in Tree |
| Ctrl+Shift+C | Copy current node with subnodes |
| Ctrl+Shift+N | Open node in new window |
| Ctrl+E | Export tree |

#### Code Folding
| Shortcut | Action |
|----------|--------|
| Ctrl+Shift+[ | Fold current element |
| Ctrl+Shift+] | Unfold current element |
| Ctrl+Shift+0 | Unfold all |

#### Editor/Navigation
| Shortcut | Action |
|----------|--------|
| Ctrl+T | Find in Tree (editor) |
| F4 | Select XML node near cursor |
| Ctrl+F4 | Select root element |
| Ctrl+Alt+F4 | Cycle top-level elements |
| F5 | Move selection to new tab with link |
| Shift+F5 | Replace link with edited text from separate tab |
| Alt+←/→/↑/↓ | Tree-backed navigation |

#### View Controls
| Shortcut | Action |
|----------|--------|
| Ctrl+Shift+M | Open Multicolumn Tree (Experimental) |
| Ctrl+Shift+T | Toggle toolbar auto-hide |
| Ctrl+Shift+H | Toggle tree header auto-hide |
| Ctrl+Shift+E | Toggle tree column header auto-hide |

#### Tree View
| Shortcut | Action |
|----------|--------|
| Delete | Hide current node recursively (visual filter) |

### XML Validation

The XML validation feature checks for:

- Well-formed XML structure
- Proper tag matching (opening/closing)
- Valid XML declaration
- Proper attribute formatting
- Unclosed tags
- Invalid characters

### XML Formatting

The XML formatter provides:

- Proper indentation (2 spaces)
- Consistent line breaks
- Removal of unnecessary whitespace
- Preservation of CDATA sections
- Proper formatting of XML declarations

### Auto-save

The application automatically saves backup copies of your work:

- Auto-save interval: 5 minutes
- Backup files have `.autosave` extension
- Backups are cleaned up on application exit
- Only active for files that have been saved at least once

## Architecture

The Python version maintains the core architecture of the original C# application:

```
python_version/
├── main.py              # Main application window and UI
├── xml_service.py       # XML processing service
├── models.py           # Data models and structures
├── highlighter.py      # Syntax highlighting
└── requirements.txt    # Python dependencies
```

### Core Components

1. **MainWindow**: Main application window with VSCode-like layout
2. **XmlService**: Core XML processing functionality
3. **XmlTreeWidget**: Tree view for XML structure
4. **XmlEditorWidget**: Text editor with syntax highlighting
5. **BottomPanel**: Multi-tab panel for output, validation, and find results
6. **Data Models**: Structured representation of XML data and metadata

### Comparison with C# Version

| Feature | C# Version | Python Version |
|---------|------------|----------------|
| UI Framework | Avalonia | PyQt6 |
| XML Parsing | System.Xml | xml.etree.ElementTree |
| Syntax Highlighting | AvaloniaEdit | Custom QSyntaxHighlighter |
| Tree View | Avalonia TreeView | QTreeWidget |
| Text Editor | AvaloniaEdit TextEditor | QTextEdit with QSyntaxHighlighter |
| Validation | Custom validation | xml.etree.ElementTree + custom rules |
| Themes | Avalonia themes | Qt stylesheets |

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure all dependencies are installed
2. **XML Parsing Error**: Check that your XML is well-formed
3. **File Encoding Issues**: The editor supports UTF-8, Latin-1, and other common encodings
4. **Large Files**: For very large XML files, consider using streaming parsers

### Performance

- The application handles files up to several MB efficiently
- For very large files (>10MB), consider splitting into smaller files
- Syntax highlighting may be slower for files with thousands of lines

### UDL Regex Cache

To speed up language switching and custom syntax profiles (UDL), the app caches compiled UDL regex metadata to disk. This avoids re-building large alternation expressions on every run and improves startup and language change performance.

- Cache location (Windows): `%APPDATA%\\LotusXmlEditor\\language_cache.json`.
- If Qt `QStandardPaths` is available, the cache is stored under the app's `AppDataLocation`.
- Fallback: a `language_cache.json` file next to the application if no AppData location is available.

You can delete the cache file if a UDL definition changes and you want to force a rebuild. The application will regenerate it automatically.

## Future Enhancements

Potential improvements for the Python version:

- **Plugin System**: Support for custom plugins
- **Advanced Search**: Full XPath support
- **Schema Validation**: XSD and DTD validation
- **Diff View**: Compare XML files
- **Transformations**: XSLT support
- **Better Performance**: Streaming for large files
- **More Themes**: Additional color schemes
- **Internationalization**: Multi-language support

## License

This Python version maintains the same license as the original C# project.

## Contributing

Feel free to contribute improvements, bug fixes, or new features!

## Credits

Ported from the original C# Avalonia Lotus Xml Editor project.