# Recent Files Feature

## Overview
Added a "Recent Files" submenu to the File menu that displays the 5 most recently opened XML files.

## Features

### Recent Files Menu
- Located in **File → Recent Files**
- Shows up to 5 most recently opened files
- Each entry displays:
  - Number (1-5)
  - Filename
  - Full path as tooltip (hover to see)

### Menu Actions
1. **Click a file** - Opens that file immediately
2. **Clear Recent Files** - Clears the entire recent files list (with confirmation)

### Behavior
- Files are automatically added to the list when opened
- Most recent file appears at the top
- Non-existent files are automatically removed from the list
- If no recent files exist, shows "No recent files" (disabled)
- Recent files persist between application sessions

## Implementation Details

### Configuration
- Recent files stored in: `~/.visxml_recent`
- Maximum files shown: 5 (configurable via `self.max_recent_files`)
- Files are validated on load (non-existent files removed)

### Methods Added
- `_update_recent_files_menu()` - Updates the menu with current files
- `_open_recent_file(file_path)` - Opens a file from the recent list
- `_clear_recent_files()` - Clears the recent files list with confirmation

### Integration
- Menu updates automatically when:
  - Application starts (loads from config)
  - File is opened (added to top of list)
  - File is cleared from list
  - Recent files list is cleared

## Usage

1. **Open files normally** using File → Open or Ctrl+O
2. **Access recent files** via File → Recent Files
3. **Click any recent file** to open it instantly
4. **Clear the list** using "Clear Recent Files" at the bottom of the menu

## Technical Notes
- Uses existing recent files infrastructure (`_load_recent_files`, `_save_recent_files`, `_add_to_recent_files`)
- Menu reference stored in `self.recent_files_menu`
- Integrates seamlessly with existing file opening workflow
