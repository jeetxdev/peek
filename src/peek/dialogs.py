from dataclasses import dataclass
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label
from textual.widgets.button import ButtonVariant


@dataclass(frozen=True)
class Choice:
  id: str
  label: str
  variant: ButtonVariant = "default"


CANCEL = Choice("cancel", "Cancel")
SAVE = Choice("save", "Save", "primary")
DISCARD = Choice("discard", "Don't Save", "error")
OVERWRITE = Choice("overwrite", "Overwrite", "error")
DELETE = Choice("delete", "Delete", "error")


class ChoiceDialog(ModalScreen[str]):
  """A clickable prompt. Dismisses with the chosen id, or CANCEL on escape."""

  DEFAULT_CSS = """
  ChoiceDialog {
    align: center middle;
  }
  ChoiceDialog > Vertical {
    width: 60;
    max-width: 90%;
    height: auto;
    padding: 1 2;
    border: round $primary;
    background: $surface;
  }
  ChoiceDialog Label {
    width: 100%;
    margin-bottom: 1;
  }
  ChoiceDialog Horizontal {
    height: auto;
    align-horizontal: right;
  }
  ChoiceDialog Button {
    margin-left: 1;
  }
  """

  BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "cancel", show=False)]

  def __init__(self, prompt: str, choices: tuple[Choice, ...]) -> None:
    super().__init__()
    self._prompt = prompt
    self._choices = choices

  def compose(self) -> ComposeResult:
    with Vertical():
      yield Label(self._prompt, markup=False)
      with Horizontal():
        for choice in self._choices:
          yield Button(choice.label, id=choice.id, variant=choice.variant)

  def on_button_pressed(self, event: Button.Pressed) -> None:
    self.dismiss(event.button.id)

  def action_cancel(self) -> None:
    self.dismiss(CANCEL.id)


class NewFileDialog(ModalScreen[str | None]):
  """Collects a project-relative filename; escape leaves the project untouched."""

  DEFAULT_CSS = """
  NewFileDialog {
    align: center middle;
  }
  NewFileDialog > Vertical {
    width: 60;
    max-width: 90%;
    height: auto;
    padding: 1 2;
    border: round $primary;
    background: $surface;
  }
  NewFileDialog Horizontal {
    height: auto;
    align-horizontal: right;
    margin-top: 1;
  }
  NewFileDialog Button {
    margin-left: 1;
  }
  """

  BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "cancel", show=False)]

  def compose(self) -> ComposeResult:
    with Vertical():
      yield Label("New file (path relative to the project)", markup=False)
      yield Input(placeholder="src/example.py", compact=True)
      with Horizontal():
        yield Button("Cancel", id="cancel")
        yield Button("Create", id="create", variant="primary")

  def on_input_submitted(self) -> None:
    self._submit()

  def on_button_pressed(self, event: Button.Pressed) -> None:
    if event.button.id == "create":
      self._submit()
    else:
      self.action_cancel()

  def _submit(self) -> None:
    value = self.query_one(Input).value.strip()
    if value:
      self.dismiss(value)

  def action_cancel(self) -> None:
    self.dismiss(None)
