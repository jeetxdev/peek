from pathlib import Path
from typing import ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal
from textual.widgets import DirectoryTree, Static, TextArea

from peek.commands import COMMANDS, PALETTE_KEYS
from peek.dialogs import CANCEL, DELETE, DISCARD, OVERWRITE, SAVE, ChoiceDialog, NewFileDialog
from peek.editor import CodeEditor
from peek.explorer import FileExplorer
from peek.file_io import FileOpenError, TextFile, changed_on_disk, read_text_file, write_text_file
from peek.palette import TEXT_SEARCH_PREFIX, ActionPalette, PaletteChoice
from peek.text_search import TextMatch
from peek.theme import THEME_NAME

STATUS_ID = "status"
READ_ONLY_NOTE = "Read-only: unusual line endings"


class PeekApp(App[None]):
  ENABLE_COMMAND_PALETTE = False

  CSS = """
  #workspace {
    height: 1fr;
  }
  FileExplorer {
    width: 32;
    border-right: solid $panel;
    scrollbar-size-vertical: 1;
  }
  #editor {
    width: 1fr;
    border: none;
    padding: 0;
  }
  #status {
    height: 1;
    padding: 0 1;
    background: $panel;
    color: $text-muted;
    text-wrap: nowrap;
    text-overflow: ellipsis;
  }
  """

  # Not priority bindings: those would also fire behind open dialogs.
  BINDINGS: ClassVar[list[BindingType]] = [
    Binding(PALETTE_KEYS, "open_palette", show=False),
    *(
      Binding(command.keys, command.action, show=False)
      for command in COMMANDS
      if command.keys
    ),
  ]

  def __init__(self, root: Path, initial_file: Path | None = None) -> None:
    super().__init__()
    self._root = root
    self._initial_file = initial_file
    self._open_file: TextFile | None = None

  def compose(self) -> ComposeResult:
    with Horizontal(id="workspace"):
      yield FileExplorer(self._root)
      yield CodeEditor()
    yield Static(id=STATUS_ID, markup=False)

  def on_mount(self) -> None:
    self.theme = THEME_NAME
    self._refresh_status()
    if self._initial_file:
      self.open_file(self._initial_file)

  @property
  def _editor(self) -> CodeEditor:
    return self.query_one(CodeEditor)

  @property
  def _has_unsaved_changes(self) -> bool:
    file = self._open_file
    return file is not None and not self._editor.read_only and self._editor.text != file.text

  def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
    self.open_file(event.path)

  def on_text_area_changed(self, _event: TextArea.Changed) -> None:
    self._refresh_status()

  @work
  async def open_file(self, path: Path, match: TextMatch | None = None) -> None:
    if not await self._show_file(path):
      return
    if match:
      self._editor.select_match(match)

  async def _show_file(self, path: Path) -> bool:
    if self._open_file and self._open_file.path == path:
      return True
    try:
      file = read_text_file(path)
    except FileOpenError as error:
      self.notify(str(error), severity="warning")
      return False
    if not await self._confirm_leaving_file():
      return False
    self._open_file = file
    self._editor.show_file(file)
    self._refresh_status()
    return True

  @work
  async def action_save_file(self) -> None:
    await self._save()

  @work
  async def action_new_file(self) -> None:
    name = await self.push_screen_wait(NewFileDialog())
    if name is None:
      return
    path = self._root / name
    try:
      if Path(name).is_absolute() or not path.resolve().is_relative_to(self._root.resolve()):
        self.notify("Enter a path inside this project", severity="warning")
        return
      if path.exists() or path.is_symlink():
        self.notify(f"{name} already exists", severity="warning")
        return
      if not await self._confirm_leaving_file():
        return
      path.parent.mkdir(parents=True, exist_ok=True)
      # Exclusive creation also protects files created while the dialog was open.
      with path.open("x", encoding="utf-8"):
        pass
      file = read_text_file(path)
    except (OSError, ValueError, FileOpenError) as error:
      self.notify(f"Can't create {name}: {error}", severity="error")
      return
    self._open_file = file
    self._editor.show_file(file)
    self._refresh_status()
    await self.query_one(FileExplorer).reload()

  @work
  async def action_delete_file(self) -> None:
    file = self._open_file
    if file is None:
      self.notify("Open a file to delete first")
      return
    prompt = f"Permanently delete {file.path.name}?"
    if self._has_unsaved_changes:
      prompt += " Unsaved changes will also be lost."
    choice = await self.push_screen_wait(ChoiceDialog(prompt, (CANCEL, DELETE)))
    if choice != DELETE.id:
      return
    try:
      file.path.unlink()
    except OSError as error:
      self.notify(f"Can't delete {file.path.name}: {error}", severity="error")
      return
    self._open_file = None
    self._editor.read_only = True
    self._editor.language = None
    self._editor.load_text("")
    self._refresh_status()
    await self.query_one(FileExplorer).reload()
    self.notify(f"Deleted {file.path.name}")

  async def action_quit(self) -> None:
    self._quit_when_safe()

  @work
  async def _quit_when_safe(self) -> None:
    # Ctrl+Q is a priority binding in Textual, so it also fires behind this dialog.
    if isinstance(self.screen, (ChoiceDialog, NewFileDialog)):
      return
    if await self._confirm_leaving_file():
      self.exit()

  def action_open_palette(self) -> None:
    self.push_screen(ActionPalette(COMMANDS, self._root), self._handle_palette_choice)

  def action_search_in_project(self) -> None:
    self.push_screen(
      ActionPalette(COMMANDS, self._root, TEXT_SEARCH_PREFIX),
      self._handle_palette_choice,
    )

  async def _handle_palette_choice(self, choice: PaletteChoice | None) -> None:
    match choice:
      case Path():
        self.open_file(choice)
      case TextMatch():
        self.open_file(choice.file.path, choice)
      case str():
        await self.run_action(choice)

  def action_undo(self) -> None:
    self._editor.undo()

  def action_redo(self) -> None:
    self._editor.redo()

  def action_cut(self) -> None:
    self._editor.action_cut()

  def action_copy(self) -> None:
    if self._editor.selected_text:
      self.copy_to_clipboard(self._editor.selected_text)
    else:
      self.notify("Select some text first")

  def action_paste(self) -> None:
    self._editor.action_paste()

  def action_select_all(self) -> None:
    self._editor.select_all()

  def action_clean_text(self) -> None:
    if self._editor.read_only:
      self.notify("Open an editable file first")
      return
    changed = self._editor.clean_selection_or_file()
    self.notify(f"Cleaned {changed} characters" if changed else "Nothing to clean")

  async def _confirm_leaving_file(self) -> bool:
    if not self._has_unsaved_changes or self._open_file is None:
      return True
    choice = await self.push_screen_wait(ChoiceDialog(
      f"Save changes to {self._open_file.path.name}?",
      (CANCEL, DISCARD, SAVE),
    ))
    if choice == SAVE.id:
      return await self._save()
    return choice == DISCARD.id

  async def _save(self) -> bool:
    file = self._open_file
    if file is None or self._editor.read_only:
      return False
    if changed_on_disk(file):
      choice = await self.push_screen_wait(ChoiceDialog(
        f"{file.path.name} changed on disk since you opened it. Overwrite it?",
        (CANCEL, OVERWRITE),
      ))
      if choice != OVERWRITE.id:
        return False
    try:
      self._open_file = write_text_file(file, self._editor.text)
    except (OSError, UnicodeError) as error:
      self.notify(f"Can't save {file.path.name}: {error}", severity="error")
      return False
    self._refresh_status()
    self.notify(f"Saved {file.path.name}")
    return True

  def _refresh_status(self) -> None:
    self.query_one(f"#{STATUS_ID}", Static).update(self._status_text())

  def _status_text(self) -> str:
    file = self._open_file
    if file is None:
      return ""
    if self._editor.read_only:
      return f"{file.path.name} · {READ_ONLY_NOTE}"
    return f"● {file.path.name}" if self._has_unsaved_changes else file.path.name
