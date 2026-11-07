from importlib.resources import files
from typing import ClassVar

import tree_sitter_javascript as javascript
import tree_sitter_typescript as typescript
from textual.binding import Binding, BindingType
from textual.widgets import TextArea
from tree_sitter import Language

from peek.clean_text import clean_text
from peek.clipboard import read_system_clipboard
from peek.file_io import TextFile
from peek.languages import is_prose, language_for, uses_tab_indent
from peek.text_search import TextMatch
from peek.theme import SYNTAX_THEME, SYNTAX_THEME_NAME

INDENT_WIDTH = 2
PLACEHOLDER = "Click a file on the left to open it. Press ⌘P to search files and commands."

TYPESCRIPT_HIGHLIGHTS = f"{javascript.HIGHLIGHTS_QUERY}\n{typescript.HIGHLIGHTS_QUERY}"
# The package ships this query but doesn't export it.
JSX_HIGHLIGHTS = (files(javascript) / "queries" / "highlights-jsx.scm").read_text()


class CodeEditor(TextArea):
  # Replaces TextArea's Ctrl+A (start of line), because Ghostty keeps Cmd+A.
  BINDINGS: ClassVar[list[BindingType]] = [Binding("ctrl+a", "select_all", show=False)]

  def __init__(self) -> None:
    super().__init__(
      id="editor",
      tab_behavior="indent",
      show_line_numbers=True,
      soft_wrap=False,
      read_only=True,
      placeholder=PLACEHOLDER,
    )
    self.indent_width = INDENT_WIDTH
    self.register_theme(SYNTAX_THEME)
    self.register_language(
      "typescript",
      Language(typescript.language_typescript()),
      TYPESCRIPT_HIGHLIGHTS,
    )
    self.register_language(
      "tsx",
      Language(typescript.language_tsx()),
      f"{TYPESCRIPT_HIGHLIGHTS}\n{JSX_HIGHLIGHTS}",
    )
    self.register_language(
      "jsx",
      Language(javascript.language()),
      f"{javascript.HIGHLIGHTS_QUERY}\n{JSX_HIGHLIGHTS}",
    )
    self.theme = SYNTAX_THEME_NAME

  def show_file(self, file: TextFile) -> None:
    self.language = None
    self.load_text(file.text)
    self.indent_type = "tabs" if uses_tab_indent(file.text) else "spaces"
    self.soft_wrap = is_prose(file.path)
    self.language = language_for(file.path)
    # TextArea normalizes some content (mixed newlines, form feeds), so saving
    # would rewrite parts of the file the user never touched.
    self.read_only = self.text != file.text
    self.focus()

  def select_match(self, match: TextMatch) -> None:
    self.move_cursor((match.row, match.column))
    self.move_cursor((match.row, match.column + match.length), select=True)
    self.focus()
    # A just-loaded file has no layout yet, so scrolling must wait for it.
    self.call_after_refresh(self.scroll_cursor_visible, center=True)

  def clean_selection_or_file(self) -> int:
    """Cleans the selection, or the whole file without one. Returns characters changed."""
    start, end = self.selection
    has_selection = start != end
    if not has_selection:
      start, end = self.document.start, self.document.end
    cursor = self.cursor_location
    cleaned, changed = clean_text(self.get_text_range(start, end))
    if changed:
      self.replace(cleaned, start, end, maintain_selection_offset=False)
      if not has_selection:
        self.move_cursor(cursor)
    return changed

  def action_paste(self) -> None:
    if self.read_only:
      return
    if text := read_system_clipboard():
      result = self.replace(text, *self.selection, maintain_selection_offset=False)
      self.move_cursor(result.end_location)
