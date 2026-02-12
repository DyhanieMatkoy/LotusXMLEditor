# Settings Help

## Editor
**Show Line Numbers**
Display line numbers in the editor margin. Useful for code navigation and referencing specific lines.

## Tree Updates
**Auto Rebuild Tree**
Automatically rebuild the XML tree structure when the text in the editor changes.
- **Enabled**: Tree updates automatically as you type (after a short delay).
- **Disabled**: You must manually refresh the tree.
### 1. **UpdTree** (Switch in Status Bar / Toolbar)
**Role: The "Master Power Switch"**
*   **What it does:** It completely connects or disconnects the editor from the tree.
*   **When OFF:** The application stops "listening" to your typing entirely.
    *   No automatic updates.
    *   No warning indicators.
    *   **Maximum Performance:** Best for extremely large files where even checking for changes causes lag.
*   **When ON:** The application listens to your changes and then looks at the *Auto Rebuild Tree* setting to decide what to do next.
### 2. **Auto Rebuild Tree** (Option in Settings)
**Role: The "Behavior Mode" (Only works if UpdTree is ON)**
*   **What it does:** Decides *how* to handle changes when they are detected.
*   **When ON (Default):**
    *   Waits for you to stop typing (5 seconds).
    *   Automatically rebuilds the tree.
*   **When OFF:**
    *   Does **NOT** rebuild the tree automatically.
    *   Instead, it shows an orange warning icon (**⚠**) next to the "Rebuild Tree" button.
    *   This tells you: *"The text has changed, but I haven't touched the tree. Press F11 when you are ready."*

**Debounce Interval (ms)**
The delay in milliseconds before updating the tree after you stop typing.
- Increasing this value reduces CPU usage but makes the tree update less responsive.
- Default is 5000ms (5 seconds).

## Auto-Hide
**Toolbar Auto-hide**
Automatically hide the main toolbar when not in use to maximize screen space.
- Hover over the top edge to reveal it.

**Tree Header Auto-hide**
Automatically hide the tree view's header (level buttons) when not in use.
- Hover over the top of the tree panel to reveal it.

**Tree Column Header Auto-hide**
Automatically hide the tree column headers ("Element", "Value") when not in use.
- Hover over the column header area to reveal it.

**Tab Bar Auto-hide**
Automatically hide the document tab bar when only one tab is open.
- Hover over the top of the editor area to reveal it.

## Zip Archive
**Default File Pattern**
The default filename pattern to select when opening a Zip archive.
- Example: `ExchangeRules.xml`
- This helps quickly locate the main XML file in complex archives.

## Debug
**Debug Mode**
Enable console debug messages for troubleshooting.
- **Enabled**: Prints detailed logs to the console.
- **Disabled**: Keeps the console output clean.
