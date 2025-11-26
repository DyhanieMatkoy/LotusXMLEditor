# Release Notes

## Unreleased

Date: 2025-10-03

### Highlights
- Persistent UDL regex cache stored under AppData to speed up language switching.
- Folding tags feature verified and documented, including hotkeys and tree synchronization.

### Improvements
- UDL language profile compilation now uses a memory+disk cache, avoiding expensive regex reassembly.
- Language switching reuses cached compiled rules where available.

### Features
- Folding controls:
  - `Ctrl+Shift+[` folds the current element.
  - `Ctrl+Shift+]` unfolds the current element.
  - `Ctrl+Shift+0` unfolds all.
- Tree view collapse/expand actions synchronize with editor folding.

### Notes
- UDL cache file location (Windows): `%APPDATA%\LotusXmlEditor\language_cache.json` or Qt `AppDataLocation` if available.
- If UDL definitions change, you can delete the cache file; it will be regenerated automatically.

### Bug Fixes
- Minor documentation updates for keyboard shortcuts and performance guidance.

### Known Issues
- Very large XML files can still take time to fully re-highlight.
- Initial compile for a new UDL profile may take longer before caching is effective.