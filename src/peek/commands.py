from dataclasses import dataclass

PALETTE_KEYS = "ctrl+p,super+p"


@dataclass(frozen=True)
class EditorCommand:
  name: str
  action: str
  keys: str | None = None
  shortcut: str | None = None


# Labels show keys that work in stock Ghostty, which keeps Cmd+C/Z/A/Q for itself.
# The super+ bindings stay so those keys also work if Ghostty is set to pass them on.
COMMANDS = (
  EditorCommand("Save", "save_file", "ctrl+s,super+s", "⌘S"),
  EditorCommand("Undo", "undo", "ctrl+z,super+z", "⌃Z"),
  EditorCommand("Redo", "redo", "ctrl+y,super+y,shift+super+z", "⌃Y"),
  EditorCommand("Cut", "cut", "ctrl+x,super+x", "⌘X"),
  EditorCommand("Copy", "copy", "ctrl+c,super+c", "⌃C"),
  EditorCommand("Paste", "paste", "ctrl+v,super+v", "⌘V"),
  EditorCommand("Select All", "select_all", "ctrl+a,super+a", "⌃A"),
  EditorCommand("Clean Text", "clean_text"),
  # No shortcut: Ghostty keeps Cmd+Shift+F, VS Code's key for this.
  EditorCommand("Search in Project", "search_in_project"),
  EditorCommand("Quit", "quit", "ctrl+q", "⌃Q"),
)
