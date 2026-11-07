from collections.abc import Iterable
from pathlib import Path

from textual.widgets import DirectoryTree

from peek.file_search import HIDDEN_NAMES

class FileExplorer(DirectoryTree):
  def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
    return [path for path in paths if path.name not in HIDDEN_NAMES]
