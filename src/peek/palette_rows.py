from rich.cells import cell_len
from rich.table import Table
from rich.text import Text

from peek.text_search import TextMatch

PREVIEW_CONTEXT_CHARACTERS = 24
MAX_LOCATION_WIDTH = 34
ELLIPSIS = "…"
MATCH_STYLE = "bold #f9e2af"


def palette_row(label: str, detail: str) -> Table:
  row = Table.grid(expand=True, padding=(0, 1))
  row.add_column(no_wrap=True, min_width=cell_len(label))
  # Rich only shrinks wrappable columns, so the single-line limit goes on the Text.
  row.add_column(justify="right")
  row.add_row(label, Text(detail, style="dim", no_wrap=True, overflow="ellipsis"))
  return row


def _printable(line: str) -> str:
  """Swaps one for one so match offsets stay valid. File content can hold escape codes."""
  return "".join(character if character.isprintable() else " " for character in line)


def _match_preview(match: TextMatch) -> Text:
  line = _printable(match.line)
  indent = len(line) - len(line.lstrip())
  start = max(indent, match.column - PREVIEW_CONTEXT_CHARACTERS)
  prefix = ELLIPSIS if start > indent else ""
  preview = Text(f"{prefix}{line[start:]}", no_wrap=True, overflow="ellipsis")
  highlight_start = len(prefix) + match.column - start
  preview.stylize(MATCH_STYLE, highlight_start, highlight_start + match.length)
  return preview


def _match_location(match: TextMatch) -> str:
  location = f"{match.file.relative_path}:{match.row + 1}"
  if len(location) <= MAX_LOCATION_WIDTH:
    return location
  # The end of the path holds the filename and line, so that's the part to keep.
  return f"{ELLIPSIS}{location[-(MAX_LOCATION_WIDTH - 1):]}"


def text_match_row(match: TextMatch) -> Table:
  location = _match_location(match)
  row = Table.grid(expand=True, padding=(0, 1))
  row.add_column(ratio=1)
  row.add_column(justify="right", no_wrap=True, min_width=cell_len(location))
  row.add_row(_match_preview(match), Text(location, style="dim"))
  return row
