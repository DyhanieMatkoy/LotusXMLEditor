# Lotus Xml Editor — Features & Hotkeys

## Editor
- XML syntax highlighting with `QSyntaxHighlighter`.
- Auto-indentation, find/replace, go to line.
- Format XML (`Ctrl+Shift+F`), validate XML (`Ctrl+Shift+V`).

## Tree View
- Hierarchical XML structure with element/attribute display.
- Click tree items to navigate to corresponding editor locations.
- Collapse/expand syncs with editor folding.

## Folding
- Fold current element: `Ctrl+Shift+[`.
- Unfold current element: `Ctrl+Shift+]`.
- Unfold all: `Ctrl+Shift+0`.
- Auto-unfold safety when content is edited to avoid hidden text inconsistencies.

## Language Profiles (UDL)
- Built-in XML/JSON/HTML highlighters.
- User-defined languages (UDL) loaded from XML profiles.
- Compiled UDL regex cache (memory + disk) for fast language switching.
  - Cache location (Windows): `%APPDATA%\VisualXmlEditor\language_cache.json` or Qt `AppDataLocation`.

## Validation & Output
- Real-time validation panel with line/column errors.
- Output and statistics panels.

## File Operations
- New (`Ctrl+N`), Open (`Ctrl+O`), Save (`Ctrl+S`), Save As (`Ctrl+Shift+S`), Exit (`Ctrl+Q`).

## Editing
- Undo (`Ctrl+Z`), Redo (`Ctrl+Y`), Find (`Ctrl+F`), Go to line (`Ctrl+G`).

## Performance
- Efficient handling for multi‑MB files.
- UDL cache reduces language compile time and rehighlight overhead.