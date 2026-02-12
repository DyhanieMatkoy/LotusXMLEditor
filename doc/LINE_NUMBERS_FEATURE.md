# Line Numbers Feature

## Overview
The XML editor now supports displaying line numbers in a sidebar next to the text editor. This feature can be toggled on/off and the setting is persisted across sessions.

## Features

### Line Number Display
- Line numbers are displayed in a dark gray sidebar on the left side of the editor
- The sidebar automatically adjusts its width based on the number of lines
- Line numbers update automatically as you type or scroll
- The editor viewport adjusts to make room for the line numbers when visible

### Settings Integration
The line numbers feature is fully integrated with the application's settings system:

1. **Settings Dialog**: Open Settings (Tools → Settings) to find the "Show Line Numbers" checkbox under the "Editor" section
2. **Persistent**: The setting is saved and restored when you restart the application
3. **All Editors**: The setting applies to all editor tabs in the application

## Usage

### Via Settings Dialog
1. Open the application
2. Go to **Tools → Settings** (or press the Settings button)
3. Find the **Editor** section
4. Check/uncheck **Show Line Numbers**
5. Click **OK** to apply

The line numbers will immediately appear/disappear in all open editor tabs.

### Programmatic Usage
For developers extending the application:

```python
# Show line numbers
editor.set_line_numbers_visible(True)

# Hide line numbers
editor.set_line_numbers_visible(False)

# Check if visible
is_visible = editor.line_number_widget.isVisible()
```

## Implementation Details

### Files Modified
- **main.py**: Added line number widget integration to XmlEditorWidget
- **line_number_widget.py**: New file containing the LineNumberWidget class
- **settings_dialog.py**: Added "Show Line Numbers" setting to the Editor section

### Key Components

#### LineNumberWidget
A custom QWidget that:
- Paints line numbers in a sidebar
- Automatically calculates required width based on line count
- Updates on scroll and content changes
- Uses a dark theme matching the application style

#### XmlEditorWidget Integration
- Creates a LineNumberWidget instance
- Manages visibility and positioning
- Adjusts viewport margins to make room for line numbers
- Connects to text change and scroll events for updates

#### Settings Persistence
- Setting key: `flags/show_line_numbers`
- Default value: `False` (hidden)
- Stored in QSettings: `visxml.net/LotusXmlEditor`

## Testing

### Automated Tests
Run the test suite:
```bash
python test_line_numbers.py
```

Tests verify:
- Default hidden state
- Show/hide functionality
- Viewport margin adjustments
- Settings persistence

### Visual Demo
Run the demo application:
```bash
python demo_line_numbers.py
```

This opens a simple window with buttons to toggle line numbers on/off.

## Technical Notes

### QTextEdit Compatibility
The implementation works with QTextEdit (not QPlainTextEdit) by:
- Using `document().blockCount()` instead of `blockCount()`
- Using `document().documentLayout().blockBoundingRect()` for positioning
- Connecting to `textChanged` and scroll events instead of `blockCountChanged`

### Performance
- Line numbers are only painted for visible blocks
- Width calculation is cached and only updated when needed
- Minimal performance impact even with large files

## Future Enhancements
Possible improvements:
- Highlight current line number
- Click line number to select line
- Right-click context menu on line numbers
- Breakpoint indicators
- Bookmark indicators in the line number area
