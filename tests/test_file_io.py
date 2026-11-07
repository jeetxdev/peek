from pathlib import Path

import pytest

from peek.file_io import (
  MAX_FILE_BYTES,
  FileOpenError,
  changed_on_disk,
  read_text_file,
  write_text_file,
)


def test_read_keeps_crlf(tmp_path: Path) -> None:
  path = tmp_path / "windows.txt"
  path.write_bytes(b"a\r\nb\r\n")
  assert read_text_file(path).text == "a\r\nb\r\n"


@pytest.mark.parametrize(
  ("name", "content", "message"),
  [
    ("image.bin", b"\x89PNG\0\0", "binary"),
    ("latin.txt", "café".encode("latin-1"), "not UTF-8"),
    ("huge.txt", b"x" * (MAX_FILE_BYTES + 1), "too large"),
  ],
)
def test_read_rejects_unsupported_files(
  tmp_path: Path, name: str, content: bytes, message: str
) -> None:
  path = tmp_path / name
  path.write_bytes(content)
  with pytest.raises(FileOpenError, match=message):
    read_text_file(path)


def test_read_reports_missing_file(tmp_path: Path) -> None:
  with pytest.raises(FileOpenError, match="Can't read"):
    read_text_file(tmp_path / "missing.txt")


def test_write_round_trips_bytes_and_keeps_mode(tmp_path: Path) -> None:
  path = tmp_path / "script.sh"
  path.write_text("old\n")
  path.chmod(0o755)
  write_text_file(read_text_file(path), "café\r\nnew\r\n")
  assert path.read_bytes() == "café\r\nnew\r\n".encode()
  assert path.stat().st_mode & 0o777 == 0o755


def test_write_follows_symlinks(tmp_path: Path) -> None:
  target = tmp_path / "real.txt"
  target.write_text("old\n")
  link = tmp_path / "link.txt"
  link.symlink_to(target)
  write_text_file(read_text_file(link), "new\n")
  assert link.is_symlink()
  assert target.read_text() == "new\n"


def test_write_refuses_read_only_file(tmp_path: Path) -> None:
  path = tmp_path / "locked.txt"
  path.write_text("old\n")
  file = read_text_file(path)
  path.chmod(0o444)
  with pytest.raises(PermissionError):
    write_text_file(file, "new\n")
  assert path.read_text() == "old\n"


def test_write_rejects_unencodable_text_without_touching_file(tmp_path: Path) -> None:
  path = tmp_path / "file.txt"
  path.write_text("old\n")
  with pytest.raises(UnicodeError):
    write_text_file(read_text_file(path), "bad \udc80\n")
  assert [entry.name for entry in tmp_path.iterdir()] == ["file.txt"]
  assert path.read_text() == "old\n"


def test_write_leaves_no_temp_files_behind(tmp_path: Path) -> None:
  path = tmp_path / "file.txt"
  path.write_text("old\n")
  write_text_file(read_text_file(path), "new\n")
  assert [entry.name for entry in tmp_path.iterdir()] == ["file.txt"]


def test_changed_on_disk(tmp_path: Path) -> None:
  path = tmp_path / "file.txt"
  path.write_text("one\n")
  file = read_text_file(path)
  assert not changed_on_disk(file)
  path.write_text("two two\n")
  assert changed_on_disk(file)
  path.unlink()
  assert changed_on_disk(file)
