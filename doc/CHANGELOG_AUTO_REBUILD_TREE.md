# Changelog - AutoRebuildTree Feature

## [2025-01-28] - Added AutoRebuildTree Option

### Added
- **AutoRebuildTree setting** in Settings dialog under "Tree Updates" section
  - Default: enabled (tree updates automatically)
  - When disabled: tree does not update automatically on text changes
  
- **Visual indicator** (⚠) next to "Rebuild Tree" button
  - Appears when auto-rebuild is disabled and tree needs update
  - Orange color, 16px font size
  - Tooltip: "Tree needs rebuild - click 'Rebuild Tree' to update"
  - Disappears after manual rebuild (F11)

### Modified
- `main.py`:
  - Added `auto_rebuild_tree` flag (default: True)
  - Added `_tree_needs_rebuild` flag to track rebuild state
  - Added `tree_rebuild_indicator` QLabel widget in toolbar
  - Modified `on_content_changed()` to check auto_rebuild_tree flag
  - Modified `rebuild_tree_with_autoclose()` to hide indicator after rebuild
  - Added loading of `auto_rebuild_tree` setting in `_load_persisted_flags()`

- `settings_dialog.py`:
  - Added "auto_rebuild_tree" setting to "Tree Updates" group
  - Added loading/saving of auto_rebuild_tree from/to QSettings
  - Added application of auto_rebuild_tree to parent window in `_apply_settings_to_parent()`

### Technical Details
- Setting key: `flags/auto_rebuild_tree`
- Storage: QSettings("visxml.net", "LotusXmlEditor")
- Default value: True (auto-rebuild enabled)
- Indicator symbol: ⚠ (Unicode U+26A0)

### Documentation
- Created `doc/AUTO_REBUILD_TREE_FEATURE.md` (English)
- Created `doc/AUTO_REBUILD_TREE_RU.md` (Russian)
- Created test script `test_auto_rebuild_tree.py`

### Use Cases
1. **Large files**: Disable auto-rebuild to improve performance
2. **Batch editing**: Disable auto-rebuild, make multiple changes, rebuild once
3. **Small files**: Keep auto-rebuild enabled for immediate feedback

### Keyboard Shortcuts
- **F11**: Rebuild Tree (manual rebuild)
