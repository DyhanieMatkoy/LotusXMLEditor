# Tabbed MDI and Hotkeys

This document describes the tabbed multiple-document interface (MDI) added to the Visual XML Editor, including how to use tabs, control tree updates on tab switches, and keyboard shortcuts for working with XML selections across tabs.

## Tabbed MDI

- The right panel now hosts a `QTabWidget` where each tab contains an `XmlEditorWidget`.
- The active editor tab is tracked by `self.xml_editor` for compatibility with existing logic.
- Tabs are closable. If all tabs are closed, a new empty editor tab is created automatically.

## Tree Update Toggle

- Toolbar switch: `Update Tree on Tab Switch` (checkable) controls whether the left XML tree rebuilds when switching tabs.
- When enabled, changing tabs repopulates the tree from the active editor’s content.
- Status bar reflects the current state: enabled or disabled.

## Keyboard Shortcuts

- `F4` — Select XML node near the cursor.
  - First press selects the deepest element under the cursor.
  - Repeated presses select the immediate parent element each time, climbing the hierarchy.

- `F5` — Move selection to a new tab and insert a link.
  - If no selection, `F4` logic is applied to select an element.
  - The selected text is moved into a new tab titled `Subdoc N`.
  - A link comment replaces the selection in the original editor: `<!-- TABREF: tab-N -->`.

- `Shift+F5` — Replace link with edited text from its tab.
  - Place the cursor on or near a `TABREF` comment.
  - The link is replaced with the current content from the associated tab.

## Link Format and Mapping

- Links are inserted as XML comments to preserve document validity: `<!-- TABREF: tab-N -->`.
- The application maintains an internal mapping from `tab-N` to the created subdocument tab.
- If the referenced tab is closed, replacing the link will be a no-op.

## Notes

- Element selection uses a lightweight range detector that respects common XML constructs (elements, self-closing tags, comments, CDATA, processing instructions). Malformed XML may reduce accuracy.
- For very large documents, consider disabling `Update Tree on Tab Switch` to reduce rebuild overhead.

## Tips

- Use `F4` to quickly select nested elements and progressively widen selection to parent elements.
- Use `F5` and `Shift+F5` to refactor parts of the XML into separate tabs and reinsert them when ready.