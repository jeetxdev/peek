import errno
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

MAX_FILE_BYTES = 2_000_000
BINARY_SNIFF_BYTES = 8192
ENCODING = "utf-8"


class FileOpenError(Exception):
  """A file that can't be shown in the editor. The message is user-facing."""


@dataclass(frozen=True)
class TextFile:
  path: Path
  text: str
  modified_ns: int


def read_text_file(path: Path) -> TextFile:
  try:
    stat = path.stat()
    if stat.st_size > MAX_FILE_BYTES:
      raise FileOpenError(f"{path.name} is too large to open")
    raw = path.read_bytes()
  except OSError as error:
    raise FileOpenError(f"Can't read {path.name}: {error.strerror}") from error

  if b"\0" in raw[:BINARY_SNIFF_BYTES]:
    raise FileOpenError(f"{path.name} is a binary file")
  try:
    # Decoding bytes directly keeps CRLF intact, unlike Path.read_text.
    text = raw.decode(ENCODING)
  except UnicodeDecodeError as error:
    raise FileOpenError(f"{path.name} is not UTF-8 text") from error
  return TextFile(path, text, stat.st_mtime_ns)


def write_text_file(file: TextFile, text: str) -> TextFile:
  # Resolving first stops os.replace from swapping a symlink for a regular file.
  target = Path(os.path.realpath(file.path))
  # os.replace only needs folder access, so it would overwrite a read-only file.
  if target.exists() and not os.access(target, os.W_OK):
    raise PermissionError(errno.EACCES, os.strerror(errno.EACCES))
  encoded = text.encode(ENCODING)
  descriptor, temp_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
  try:
    with os.fdopen(descriptor, "wb") as temp_file:
      temp_file.write(encoded)
      temp_file.flush()
      os.fsync(temp_file.fileno())
    if target.exists():
      os.chmod(temp_name, target.stat().st_mode)
    os.replace(temp_name, target)
  except BaseException:
    Path(temp_name).unlink(missing_ok=True)
    raise
  return TextFile(file.path, text, target.stat().st_mtime_ns)


def changed_on_disk(file: TextFile) -> bool:
  try:
    return file.path.stat().st_mtime_ns != file.modified_ns
  except OSError:
    return True
