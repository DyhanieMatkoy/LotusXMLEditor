# Lotus XML Editor — Complete Features Tree

```
📦 Lotus XML Editor
│
├── 📂 File Operations
│   ├── 📄 New File                          [Ctrl+N]
│   ├── 📂 Open File                         [Ctrl+O]
│   ├── 📦 Open from ZIP                     (direct editing)
│   ├── 💾 Save                              [Ctrl+S]
│   ├── 💾 Save As                           [Ctrl+Shift+S]
│   ├── 📁 Recent Files                      (history)
│   └── 🚪 Exit                              [Ctrl+Q]
│
├── 📂 1C Exchange Integration
│   ├── 📦 ZIP Support
│   │   ├── Open XML from ZIP
│   │   ├── Edit without extraction
│   │   └── Auto-repack on save
│   │
│   ├── 🔗 Exchange Rules Parser
│   │   ├── ПравилаОбмена detection
│   │   ├── Источник/Приемник extraction
│   │   └── Pair metadata (pair.meta.json)
│   │
│   ├── 🔄 Exchange Modes
│   │   ├── Semi-automatic mode
│   │   └── Manual mode
│   │
│   └── 📋 Companion Files
│       ├── Message_*.xml handling
│       └── Rules synchronization
│
├── 📂 Editor
│   ├── 🎨 Syntax Highlighting
│   │   ├── XML syntax coloring
│   │   ├── QSyntaxHighlighter engine
│   │   └── Custom color schemes
│   │
│   ├── ✏️ Editing
│   │   ├── Undo                              [Ctrl+Z]
│   │   ├── Redo                              [Ctrl+Y]
│   │   ├── Cut                               [Ctrl+X]
│   │   ├── Copy                              [Ctrl+C]
│   │   ├── Paste                             [Ctrl+V]
│   │   └── Auto-indentation
│   │
│   ├── 🔍 Find & Replace
│   │   ├── Find                              [Ctrl+F]
│   │   ├── Find Next                         [F3]
│   │   ├── Find Previous                     [Shift+F3]
│   │   ├── Replace                           [Ctrl+H]
│   │   └── Regex support
│   │
│   ├── 📍 Navigation
│   │   ├── Go to Line                        [Ctrl+G]
│   │   ├── Jump to closing tag               [Ctrl+]]
│   │   └── Jump to opening tag               [Ctrl+[]
│   │
│   └── 🔧 XML Tools
│       ├── Format XML                        [Ctrl+Shift+F]
│       └── Validate XML                      [Ctrl+Shift+V]
│
├── 📂 Tree View
│   ├── 🌳 Structure Navigation
│   │   ├── Hierarchical XML display
│   │   ├── Element/attribute display
│   │   ├── Click to navigate
│   │   └── Sync with editor position
│   │
│   ├── 🏷️ Friendly Names
│   │   ├── Human-readable labels
│   │   ├── 1C object type display
│   │   ├── Attribute values in tree
│   │   └── Russian/English names
│   │
│   ├── 🔍 Tree Search
│   │   ├── Filter by text
│   │   ├── Search in attributes
│   │   └── Highlight matches
│   │
│   └── 🔗 Editor Sync
│       ├── Tree ↔ Editor sync
│       ├── Collapse/expand sync
│       └── Folding integration
│
├── 📂 Code Folding
│   ├── 📁 Fold Controls
│   │   ├── Visual fold indicators
│   │   ├── Hover activation
│   │   └── Line number area controls
│   │
│   ├── ⌨️ Folding Shortcuts
│   │   ├── Fold current element              [Ctrl+Shift+[ ]
│   │   ├── Unfold current element            [Ctrl+Shift+] ]
│   │   ├── Unfold all                        [Ctrl+Shift+U]
│   │   ├── Unfold all (alt)                  [Ctrl+Shift+0]
│   │   └── Fold by level                     [Alt+2..9]
│   │
│   └── 🛡️ Safety Features
│       └── Auto-unfold on edit
│
├── 📂 XPath Links
│   ├── 📌 Link Management
│   │   ├── Copy XPath                        [Ctrl+F11]
│   │   ├── Navigate to XPath                 [F12]
│   │   └── Links panel (bottom)
│   │
│   └── 🔗 Navigation
│       ├── Tree highlight on navigate
│       ├── Editor position sync
│       └── Multi-reference support
│
├── 📂 Bookmarks
│   ├── 🔖 Toggle Bookmark                    [Alt+F2]
│   ├── ⬇️ Next Bookmark                      [F2]
│   └── ⬆️ Previous Bookmark                  [Shift+F2]
│
├── 📂 XML Split & Combine
│   ├── ✂️ Split Features
│   │   ├── Threshold-based splitting
│   │   ├── Element-based rules
│   │   ├── Depth-based rules
│   │   ├── Size-based rules
│   │   ├── XPath-based rules
│   │   └── Preserve context option
│   │
│   ├── 🔗 Combine Features
│   │   ├── Merge multiple XML files
│   │   └── Structure preservation
│   │
│   └── ⚙️ Configuration
│       ├── Custom output directory
│       ├── Backup original
│       └── JSON config support
│
├── 📂 Fragment Editor
│   ├── 📝 Edit XML fragments
│   ├── 🪟 Separate window
│   └── 🔄 Sync with main document
│
├── 📂 Visual Navigators
│   ├── 🚇 Metro Navigator                   [Ctrl+M]
│   │   └── Visual structure diagram
│   │
│   ├── 📊 Structure Diagram
│   │   └── Layered view
│   │
│   └── 📋 Multi-column Tree
│       └── Experimental view
│
├── 📂 View Options
│   ├── 🔢 Line Numbers                      [Ctrl+L]
│   │   ├── Toggle display
│   │   └── Relative numbering
│   │
│   ├── 🎨 Themes
│   │   └── Color scheme selection
│   │
│   └── 📐 Layout
│       ├── Panel visibility
│       └── Splitter positions
│
├── 📂 Validation & Output
│   ├── ✅ XML Validation
│   │   ├── Real-time validation
│   │   ├── Error highlighting
│   │   └── Line/column reporting
│   │
│   └── 📋 Output Panels
│       ├── Validation results
│       ├── Statistics
│       └── Links panel
│
├── 📂 Language Profiles (UDL)
│   ├── 📝 Built-in Languages
│   │   ├── XML
│   │   ├── JSON
│   │   └── HTML
│   │
│   └── ⚙️ User-Defined Languages
│       ├── XML profile loading
│       └── Compiled regex cache
│
├── 📂 FTP Support
│   ├── 🌐 FTP Connection
│   ├── 📂 Remote Browse
│   └── 📥 Open from FTP
│
├── 📂 Settings
│   ├── ⚙️ Preferences Dialog
│   ├── 💾 Persistent Settings
│   └── 🔄 Window State Restore
│
└── 📂 Performance
    ├── ⚡ Large File Support
    │   └── Multi-MB file handling
    │
    ├── 🗄️ Caching
    │   ├── UDL regex cache
    │   └── Language cache (disk)
    │
    └── 📊 Statistics
        └── File/element counts
```

---

## Quick Reference Card

| Category | Feature | Shortcut |
|----------|---------|----------|
| **File** | New | `Ctrl+N` |
| | Open | `Ctrl+O` |
| | Save | `Ctrl+S` |
| | Save As | `Ctrl+Shift+S` |
| | Exit | `Ctrl+Q` |
| **Edit** | Undo | `Ctrl+Z` |
| | Redo | `Ctrl+Y` |
| | Find | `Ctrl+F` |
| | Replace | `Ctrl+H` |
| | Go to Line | `Ctrl+G` |
| **Fold** | Fold | `Ctrl+Shift+[` |
| | Unfold | `Ctrl+Shift+]` |
| | Unfold All | `Ctrl+Shift+U` |
| | Fold Level N | `Alt+2..9` |
| **Nav** | Tree Up | `F6` |
| | Tree Down | `F7` |
| | Metro Navigator | `Ctrl+M` |
| **XPath** | Copy XPath | `Ctrl+F11` |
| | Go to XPath | `F12` |
| **Mark** | Toggle Bookmark | `Alt+F2` |
| | Next Bookmark | `F2` |
| | Prev Bookmark | `Shift+F2` |
| **View** | Line Numbers | `Ctrl+L` |
| **Tools** | Format XML | `Ctrl+Shift+F` |
| | Validate XML | `Ctrl+Shift+V` |
| **Help** | Shortcuts | `F1` |

---

## 1C-Specific Features Summary

| Feature | Description |
|---------|-------------|
| **ZIP Support** | Open/edit XML directly in ZIP archives |
| **Exchange Rules** | Parse ПравилаОбмена structure |
| **Source/Destination** | Auto-detect Источник/Приемник |
| **Pair Metadata** | Manage pair.meta.json files |
| **Friendly Names** | Human-readable tree labels |
| **Human-Readable View** | Convert XML to readable format |
| **Message Files** | Handle Message_*.xml companions |
| **Semi-Auto Mode** | Guided exchange workflow |

---

*For detailed documentation, see the `doc/` folder.*
