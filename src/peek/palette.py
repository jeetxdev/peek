import time
from pathlib import Path
from typing import ClassVar

from textual import events, work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.fuzzy import Matcher
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option
from textual.worker import get_current_worker

from peek.commands import PALETTE_KEYS, EditorCommand
from peek.file_search import ProjectFile, list_project_files, search_files
from peek.palette_rows import palette_row, text_match_row
from peek.text_search import TextMatch, search_text

PROMPT = "Search files, > for commands, % for text in files"
NO_MATCHES = "No matches"
SEARCHING = "Searching…"
TEXT_SEARCH_HINT = "Type to search the text of every file in this project"
COMMANDS_ONLY_PREFIX = ">"
TEXT_SEARCH_PREFIX = "%"
TEXT_SEARCH_GROUP = "text-search"
TEXT_SEARCH_DELAY_SECONDS = 0.15
TEXT_SEARCH_UPDATE_SECONDS = 0.1

type PaletteItem = EditorCommand | ProjectFile | TextMatch
type PaletteChoice = str | Path | TextMatch


class ActionPalette(ModalScreen[PaletteChoice | None]):
  """Searches commands, files and file contents. Dismisses with what was picked."""

  DEFAULT_CSS = """
  ActionPalette {
    align: center top;
  }
  ActionPalette > Vertical {
    width: 80;
    max-width: 90%;
    height: auto;
    margin-top: 2;
    border: round $primary;
    background: $surface;
  }
  ActionPalette OptionList {
    border: none;
    height: auto;
    max-height: 16;
    margin-top: 1;
    background: $surface;
  }
  """

  BINDINGS: ClassVar[list[BindingType]] = [
    Binding("escape", "close", show=False),
    Binding(PALETTE_KEYS, "close", show=False),
    Binding("up", "move_highlight('up')", show=False),
    Binding("down", "move_highlight('down')", show=False),
  ]

  def __init__(
    self,
    commands: tuple[EditorCommand, ...],
    root: Path,
    initial_query: str = "",
  ) -> None:
    super().__init__()
    self._commands = commands
    self._root = root
    self._initial_query = initial_query
    self._files: list[ProjectFile] = []
    self._shown: list[PaletteItem] = []

  def compose(self) -> ComposeResult:
    with Vertical():
      # Selecting on focus would make the first keystroke replace the initial query.
      yield Input(self._initial_query, placeholder=PROMPT, compact=True, select_on_focus=False)
      options = OptionList()
      # Keeps typing in the search box working after a click. Focus moving on
      # mouse down also shifted the row a click landed on.
      options.can_focus = False
      yield options

  def on_mount(self) -> None:
    self.query_one(Input).action_end()
    self._show_matches(self._initial_query)
    self._load_files()

  @work(thread=True, exit_on_error=False)
  def _load_files(self) -> None:
    worker = get_current_worker()
    files = list_project_files(self._root, lambda: worker.is_cancelled)
    if not worker.is_cancelled:
      self.app.call_from_thread(self._set_files, files)

  def _set_files(self, files: list[ProjectFile]) -> None:
    self._files = files
    query = self.query_one(Input).value
    if not query.startswith(TEXT_SEARCH_PREFIX):
      self._show_matches(query)

  def on_input_changed(self, event: Input.Changed) -> None:
    self._show_matches(event.value)

  def on_input_submitted(self) -> None:
    options = self.query_one(OptionList)
    if options.highlighted is not None:
      options.action_select()

  def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
    choice = self._shown[event.option_index]
    match choice:
      case EditorCommand():
        self.dismiss(choice.action)
      case ProjectFile():
        self.dismiss(choice.path)
      case TextMatch():
        self.dismiss(choice)

  def on_click(self, event: events.Click) -> None:
    if event.widget is self:
      self.dismiss(None)

  def action_close(self) -> None:
    self.dismiss(None)

  def action_move_highlight(self, direction: str) -> None:
    options = self.query_one(OptionList)
    if direction == "up":
      options.action_cursor_up()
    else:
      options.action_cursor_down()

  def _matching_commands(self, query: str) -> list[EditorCommand]:
    matcher = Matcher(query)
    return [
      command
      for command in self._commands
      if not query or matcher.match(command.name) > 0
    ]

  def _show_matches(self, query: str) -> None:
    self.workers.cancel_group(self, TEXT_SEARCH_GROUP)
    if query.startswith(TEXT_SEARCH_PREFIX):
      text = query.removeprefix(TEXT_SEARCH_PREFIX)
      self._show_rows([], SEARCHING if text else TEXT_SEARCH_HINT)
      if text:
        self._run_text_search(text)
      return

    commands_only = query.startswith(COMMANDS_ONLY_PREFIX)
    text = query.removeprefix(COMMANDS_ONLY_PREFIX).strip()
    files = [] if commands_only else search_files(self._files, text)
    self._show_rows([*files, *self._matching_commands(text)], NO_MATCHES)

  def _show_rows(self, items: list[PaletteItem], empty_message: str) -> None:
    self._shown = items
    options = self.query_one(OptionList)
    options.clear_options()
    if items:
      options.add_options([self._option_for(item) for item in items])
      options.highlighted = 0
    else:
      options.add_option(Option(empty_message, disabled=True))

  def _option_for(self, item: PaletteItem) -> Option:
    match item:
      case EditorCommand():
        return Option(palette_row(item.name, item.shortcut or ""))
      case ProjectFile():
        return Option(palette_row(item.path.name, item.folder))
      case TextMatch():
        return Option(text_match_row(item))

  @work(thread=True, exclusive=True, group=TEXT_SEARCH_GROUP, exit_on_error=False)
  def _run_text_search(self, text: str) -> None:
    worker = get_current_worker()

    def is_cancelled() -> bool:
      return worker.is_cancelled

    # Waiting first lets fast typing cancel this before any file is read.
    time.sleep(TEXT_SEARCH_DELAY_SECONDS)
    if is_cancelled():
      return

    files = self._files or list_project_files(self._root, is_cancelled)
    pending: list[TextMatch] = []
    last_update = time.monotonic()
    for match in search_text(sorted(files, key=lambda file: file.relative_path), text, is_cancelled):
      pending.append(match)
      if time.monotonic() - last_update >= TEXT_SEARCH_UPDATE_SECONDS:
        self.app.call_from_thread(self._add_text_matches, text, pending)
        pending = []
        last_update = time.monotonic()
    if not is_cancelled():
      self.app.call_from_thread(self._add_text_matches, text, pending, True)

  def _add_text_matches(self, text: str, matches: list[TextMatch], finished: bool = False) -> None:
    # A result can already be queued here when the query changes.
    if self.query_one(Input).value != f"{TEXT_SEARCH_PREFIX}{text}":
      return
    if not self._shown:
      self._show_rows(list(matches), NO_MATCHES if finished else SEARCHING)
    elif matches:
      # Appending keeps the highlighted row in place while results stream in.
      self._shown.extend(matches)
      self.query_one(OptionList).add_options([self._option_for(match) for match in matches])
