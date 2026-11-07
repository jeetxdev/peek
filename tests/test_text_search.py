from pathlib import Path

from rich.console import Console

from peek.file_search import ProjectFile, list_project_files
from peek.palette_rows import ELLIPSIS, text_match_row
from peek.text_search import TextMatch, search_text

ROW_WIDTH = 60


def project(root: Path, files: dict[str, bytes]) -> list[ProjectFile]:
  for relative_path, content in files.items():
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
  return sorted(list_project_files(root), key=lambda file: file.relative_path)


def rendered(match: TextMatch) -> str:
  console = Console(width=ROW_WIDTH, file=None, record=True, color_system=None)
  with console.capture() as capture:
    console.print(text_match_row(match))
  return capture.get().rstrip()


def test_finds_matches_with_row_and_column(tmp_path: Path) -> None:
  files = project(tmp_path, {"a.ts": b"one\n  two Needle\nneedle\n"})
  matches = list(search_text(files, "needle"))
  assert [(match.row, match.column, match.length) for match in matches] == [(1, 6, 6), (2, 0, 6)]


def test_query_is_literal_not_a_regex(tmp_path: Path) -> None:
  files = project(tmp_path, {"a.ts": b"a.b\naxb\n"})
  assert [match.row for match in search_text(files, "a.b")] == [0]


def test_rows_line_up_with_the_editor_on_crlf_and_form_feeds(tmp_path: Path) -> None:
  files = project(tmp_path, {"a.txt": b"one\r\ntwo\x0cneedle\r\n"})
  assert next(search_text(files, "needle")).row == 2


def test_skips_binary_oversized_and_non_utf8_files(tmp_path: Path) -> None:
  files = project(tmp_path, {
    "binary.bin": b"\0needle",
    "huge.txt": b"needle" * 400_000,
    "latin.txt": "needle café".encode("latin-1"),
    "good.txt": b"needle\n",
  })
  assert [match.file.relative_path for match in search_text(files, "needle")] == ["good.txt"]


def test_stops_at_the_limit_and_when_cancelled(tmp_path: Path) -> None:
  files = project(tmp_path, {"a.txt": b"needle\n" * 10})
  assert len(list(search_text(files, "needle", limit=3))) == 3
  assert list(search_text(files, "needle", lambda: True)) == []


def test_preview_keeps_a_far_right_match_visible(tmp_path: Path) -> None:
  files = project(tmp_path, {"a.txt": b"    " + b"x" * 300 + b" needle tail\n"})
  row = rendered(next(search_text(files, "needle")))
  assert "needle" in row
  assert row.endswith("a.txt:1")


def test_long_location_keeps_filename_and_line(tmp_path: Path) -> None:
  folder = "/".join(["some-long-folder-name"] * 4)
  files = project(tmp_path, {f"{folder}/target.ts": b"needle\n"})
  row = rendered(next(search_text(files, "needle")))
  assert ELLIPSIS in row
  assert row.endswith("target.ts:1")


def test_preview_neutralizes_control_characters(tmp_path: Path) -> None:
  files = project(tmp_path, {"a.txt": b"\x1b[2Jbefore needle\tafter\n"})
  row = rendered(next(search_text(files, "needle")))
  assert "\x1b" not in row
  assert "needle after" in row
