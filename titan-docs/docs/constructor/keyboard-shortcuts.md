# Keyboard Shortcuts

All shortcuts are active when focus is on the canvas (not inside a text input or dropdown).

## Canvas operations

| Shortcut | Action |
|---|---|
| `Delete` / `Backspace` | Delete selected node(s) or selected edge |
| `Ctrl+D` | Duplicate selected node |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+Shift+Z` | Redo (alternate) |

## Selection

| Action | How |
|---|---|
| Select a node | Click the node |
| Add node to selection | `Shift+click` the node |
| Remove node from selection | `Shift+click` a selected node |
| Multi-select by area | Click and drag on empty canvas to draw a selection box |
| Deselect all | Click on empty canvas |

## Edge operations

| Action | How |
|---|---|
| Draw an edge | Hover a node → drag from the port (●) on its right edge → release on target node |
| Select an edge | Click the edge line |
| Delete a selected edge | `Delete` / `Backspace` (when no node is selected) |

## Notes

- Shortcuts that conflict with browser defaults (`Ctrl+D` = bookmark) are intercepted only when an input field is **not** focused. If you're typing in a Job ID field, `Ctrl+D` goes to the browser.
- On macOS, `Cmd` can be used in place of `Ctrl` for undo/redo and duplicate.
- Undo/redo history is limited to 60 steps and resets when a DAG is loaded.
