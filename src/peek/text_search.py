import re
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass

from peek.file_io import FileOpenError, read_text_file
from peek.file_search import ProjectFile

MAX_TEXT_MATCHES = 200


@dataclass(frozen=True)
class TextMatch:
  file: ProjectFile
  row: int
  column: int
  length: int
  line: str


def search_text(
  files: Sequence[ProjectFile],
  query: str,
  should_stop: Callable[[], bool] = lambda: False,
  limit: int = MAX_TEXT_MATCHES,
) -> Iterator[TextMatch]:
  """Case-insensitive literal search, yielding at most one match per line."""
  pattern = re.compile(re.escape(query), re.IGNORECASE)
  found = 0
  for file in files:
    if should_stop():
      return
    try:
      text = read_text_file(file.path).text
    except FileOpenError:
      continue
    if pattern.search(text) is None:
      continue
    # splitlines, not split("\n"), so rows line up with TextArea's own lines.
    for row, line in enumerate(text.splitlines()):
      if match := pattern.search(line):
        yield TextMatch(file, row, match.start(), match.end() - match.start(), line)
        found += 1
        if found >= limit:
          return
