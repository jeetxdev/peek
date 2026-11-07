from pathlib import Path

import pytest

from peek import file_search
from peek.file_search import ProjectFile, list_project_files, search_files


def make_files(root: Path, *relative_paths: str) -> list[ProjectFile]:
  for relative_path in relative_paths:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("")
  return list_project_files(root)


def found(files: list[ProjectFile], query: str) -> list[str]:
  return [file.relative_path for file in search_files(files, query)]


def test_listing_skips_hidden_names_but_keeps_dotfiles(tmp_path: Path) -> None:
  files = make_files(tmp_path, "a.ts", ".env", "node_modules/x.js", ".git/config", "src/.DS_Store")
  assert sorted(file.relative_path for file in files) == [".env", "a.ts"]


def test_listing_stops_at_the_file_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.setattr(file_search, "MAX_INDEXED_FILES", 2)
  assert len(make_files(tmp_path, "a", "b", "c", "d/e", "d/f")) == 2


def test_listing_stops_when_cancelled(tmp_path: Path) -> None:
  make_files(tmp_path, "a.ts")
  assert list_project_files(tmp_path, lambda: True) == []


def test_ranking_prefers_filename_hits_over_folder_hits(tmp_path: Path) -> None:
  files = make_files(tmp_path, "app/index.ts", "src/app.ts", "apple.ts", "app.ts", "my-app.ts")
  assert found(files, "app") == ["app.ts", "apple.ts", "src/app.ts", "my-app.ts", "app/index.ts"]


def test_search_is_fuzzy_and_ignores_case_and_spaces(tmp_path: Path) -> None:
  files = make_files(tmp_path, "src/components/UserProfile.tsx", "readme.md")
  expected = ["src/components/UserProfile.tsx"]
  assert found(files, "uprof") == expected
  assert found(files, "USER PROFILE") == expected
  assert found(files, "src/user") == expected


def test_search_returns_nothing_without_a_match_or_query(tmp_path: Path) -> None:
  files = make_files(tmp_path, "a.ts")
  assert found(files, "zzz") == []
  assert found(files, "  ") == []


def test_search_limits_results(tmp_path: Path) -> None:
  files = make_files(tmp_path, "a1", "a2", "a3")
  assert len(search_files(files, "a", limit=2)) == 2
