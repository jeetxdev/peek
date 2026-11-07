import heapq
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

HIDDEN_NAMES = frozenset({
  ".DS_Store",
  ".git",
  ".mypy_cache",
  ".pytest_cache",
  ".venv",
  "__pycache__",
  "node_modules",
})
# Keeps a scan of something like the home folder from running for minutes.
MAX_INDEXED_FILES = 50_000
MAX_RESULTS = 50

NO_MATCH = None


@dataclass(frozen=True)
class ProjectFile:
  path: Path
  relative_path: str
  folder: str
  search_name: str
  search_path: str


def _project_file(path: Path, root: Path) -> ProjectFile:
  relative = path.relative_to(root)
  folder = "" if relative.parent == Path(".") else relative.parent.as_posix()
  return ProjectFile(path, relative.as_posix(), folder, path.name.lower(), relative.as_posix().lower())


def list_project_files(
  root: Path,
  should_stop: Callable[[], bool] = lambda: False,
) -> list[ProjectFile]:
  files: list[ProjectFile] = []
  for folder, subfolders, names in os.walk(root):
    if should_stop():
      break
    subfolders[:] = [name for name in subfolders if name not in HIDDEN_NAMES]
    for name in names:
      if name not in HIDDEN_NAMES:
        files.append(_project_file(Path(folder, name), root))
    if len(files) >= MAX_INDEXED_FILES:
      break
  return files[:MAX_INDEXED_FILES]


def _is_subsequence(query: str, text: str) -> bool:
  remaining = iter(text)
  return all(character in remaining for character in query)


def _match_tier(file: ProjectFile, query: str) -> int | None:
  """Lower is better. Filename hits beat folder hits, as in VS Code."""
  name, path = file.search_name, file.search_path
  if name == query:
    return 0
  if name.startswith(query):
    return 1
  if query in name:
    return 2
  if query in path:
    return 3
  if _is_subsequence(query, name):
    return 4
  if _is_subsequence(query, path):
    return 5
  return NO_MATCH


def search_files(files: list[ProjectFile], query: str, limit: int = MAX_RESULTS) -> list[ProjectFile]:
  needle = query.replace(" ", "").lower()
  if not needle:
    return []
  ranked = (
    (tier, len(file.relative_path), file.relative_path, file)
    for file in files
    if (tier := _match_tier(file, needle)) is not NO_MATCH
  )
  return [match[3] for match in heapq.nsmallest(limit, ranked, key=lambda match: match[:3])]
