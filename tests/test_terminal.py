"""Drives the real program over a pty, speaking the protocol Ghostty uses."""

import base64
import fcntl
import os
import pty
import struct
import subprocess
import sys
import termios
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from peek.commands import COMMANDS

COLUMNS, ROWS = 120, 30
CELL_WIDTH, CELL_HEIGHT = 10, 20
TIMEOUT_SECONDS = 10
POLL_SECONDS = 0.02

FIRST_FILE_ROW = 1
FILE_COLUMN = 8
PALETTE_COLUMN = 40
PALETTE_QUIT_ROW = 5 + next(
  index for index, command in enumerate(COMMANDS) if command.action == "quit"
)

MODE_QUERIES = {
  b"\x1b[?2026$p": b"\x1b[?2026;2$y",
  b"\x1b[?2048$p": b"\x1b[?2048;2$y",
}
IN_BAND_SIZE_ENABLE = b"\x1b[?2048h"
IN_BAND_SIZE_REPORT = (
  f"\x1b[48;{ROWS};{COLUMNS};{ROWS * CELL_HEIGHT};{COLUMNS * CELL_WIDTH}t".encode()
)
# Textual requests Kitty "report all keys", so plain letters arrive as CSI u too.
CONTROL_A = b"\x1b[97;5u"
CONTROL_C = b"\x1b[99;5u"
CONTROL_Y = b"\x1b[121;5u"
CONTROL_Z = b"\x1b[122;5u"
COMMAND_P = b"\x1b[112;9u"
COMMAND_S = b"\x1b[115;9u"
COMMAND_X = b"\x1b[120;9u"
LETTER_B = b"\x1b[98;1;98u"
LETTER_DOT = b"\x1b[46;1;46u"
LETTER_H = b"\x1b[104;1;104u"
LETTER_O = b"\x1b[111;1;111u"
LETTER_P = b"\x1b[112;1;112u"
LETTER_T = b"\x1b[116;1;116u"
PERCENT = b"\x1b[53;2;37u"
LETTER_Z = b"\x1b[122;1;122u"
ENTER = b"\x1b[13u"


class FakeGhostty:
  def __init__(self, working_directory: Path) -> None:
    self._master, slave = pty.openpty()
    size = struct.pack(
      "HHHH", ROWS, COLUMNS, COLUMNS * CELL_WIDTH, ROWS * CELL_HEIGHT
    )
    fcntl.ioctl(slave, termios.TIOCSWINSZ, size)
    self.process = subprocess.Popen(
      [sys.executable, "-c", "from peek.cli import main; main()"],
      cwd=working_directory,
      env={**os.environ, "TERM": "xterm-ghostty", "TERM_PROGRAM": "ghostty"},
      stdin=slave,
      stdout=slave,
      stderr=slave,
      start_new_session=True,
    )
    os.close(slave)
    self.output = b""
    self._answered: set[bytes] = set()
    threading.Thread(target=self._read_output, daemon=True).start()

  def _read_output(self) -> None:
    while True:
      try:
        chunk = os.read(self._master, 65536)
      except OSError:
        return
      if not chunk:
        return
      self.output += chunk
      self._answer_queries()

  def _answer_queries(self) -> None:
    for query, answer in MODE_QUERIES.items():
      if query in self.output and query not in self._answered:
        self._answered.add(query)
        self.send(answer)
    if IN_BAND_SIZE_ENABLE in self.output and IN_BAND_SIZE_ENABLE not in self._answered:
      self._answered.add(IN_BAND_SIZE_ENABLE)
      self.send(IN_BAND_SIZE_REPORT)

  def send(self, data: bytes) -> None:
    os.write(self._master, data)

  def click(self, column: int, row: int) -> None:
    pixel_x = column * CELL_WIDTH + CELL_WIDTH // 2 + 1
    pixel_y = row * CELL_HEIGHT + CELL_HEIGHT // 2 + 1
    self.send(f"\x1b[<35;{pixel_x};{pixel_y}M".encode())
    self.send(f"\x1b[<0;{pixel_x};{pixel_y}M".encode())
    self.send(f"\x1b[<0;{pixel_x};{pixel_y}m".encode())

  def wait_for(self, condition: Callable[[], bool], description: str) -> None:
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
      if condition():
        return
      time.sleep(POLL_SECONDS)
    raise AssertionError(f"Timed out waiting for {description}")

  def wait_for_output(self, text: bytes, after: int = 0) -> None:
    self.wait_for(lambda: text in self.output[after:], repr(text))

  def stop(self) -> None:
    if self.process.poll() is None:
      self.process.kill()
    self.process.wait()
    os.close(self._master)


@pytest.fixture
def terminal(tmp_path: Path) -> Iterator[FakeGhostty]:
  (tmp_path / "a.ts").write_text("const total: number = 1;\n")
  (tmp_path / "b.py").write_text("print('other')\n")
  fake = FakeGhostty(tmp_path)
  yield fake
  fake.stop()


def test_full_session_over_ghostty_protocol(terminal: FakeGhostty, tmp_path: Path) -> None:
  source = tmp_path / "a.ts"
  terminal.wait_for_output(b".ts")
  # Clicks only work once pixel mouse reporting has been negotiated.
  terminal.wait_for_output(b"\x1b[?1016h")
  for mode in (b"\x1b[?1003h", b"\x1b[?1006h", b"\x1b[?2004h", b"\x1b[>25u"):
    assert mode in terminal.output

  terminal.click(FILE_COLUMN, FIRST_FILE_ROW)
  terminal.wait_for_output(b"number")

  terminal.send(b"\x1b[200~hello \x1b[201~")
  terminal.wait_for_output("●".encode())

  def saved(text: bytes) -> Callable[[], bool]:
    return lambda: source.read_bytes().startswith(text)

  terminal.send(COMMAND_S)
  terminal.wait_for(saved(b"hello "), "Cmd+S to save")

  terminal.send(LETTER_Z)
  terminal.wait_for_output("● a.ts".encode())
  terminal.send(COMMAND_S)
  terminal.wait_for(saved(b"hello z"), "typed letter to save")
  full_text = source.read_bytes()

  terminal.send(CONTROL_A)
  terminal.send(CONTROL_C)
  terminal.wait_for_output(b"\x1b]52;c;" + base64.b64encode(full_text))

  terminal.send(COMMAND_X)
  terminal.send(COMMAND_S)
  terminal.wait_for(lambda: source.read_bytes() == b"", "Cmd+X to clear the file")

  terminal.send(CONTROL_Z)
  terminal.send(COMMAND_S)
  terminal.wait_for(lambda: source.read_bytes() == full_text, "Ctrl+Z to restore")

  terminal.send(CONTROL_Y)
  terminal.send(COMMAND_S)
  terminal.wait_for(lambda: source.read_bytes() == b"", "Ctrl+Y to redo")

  terminal.send(CONTROL_Z)
  terminal.send(COMMAND_S)
  terminal.wait_for(lambda: source.read_bytes() == full_text, "second Ctrl+Z")

  output_before_search = len(terminal.output)
  terminal.send(COMMAND_P)
  terminal.wait_for_output(b"Select All", after=output_before_search)
  terminal.send(LETTER_B + LETTER_DOT + LETTER_P)
  terminal.wait_for_output(b"b.py", after=output_before_search)
  terminal.send(ENTER)
  terminal.wait_for_output(b"print", after=output_before_search)

  output_before_text_search = len(terminal.output)
  terminal.send(COMMAND_P)
  terminal.wait_for_output(b"Select All", after=output_before_text_search)
  terminal.send(PERCENT + LETTER_O + LETTER_T + LETTER_H)
  terminal.wait_for_output(b"b.py:1", after=output_before_text_search)
  terminal.send(ENTER)
  time.sleep(POLL_SECONDS * 10)

  output_before_reopening = len(terminal.output)
  terminal.send(COMMAND_P)
  terminal.wait_for_output(b"Select All", after=output_before_reopening)
  terminal.click(PALETTE_COLUMN, PALETTE_QUIT_ROW)
  terminal.wait_for(lambda: terminal.process.poll() is not None, "clicking Quit in the palette")
  assert terminal.process.returncode == 0
  for restored in (b"\x1b[?1049l", b"\x1b[?1000l", b"\x1b[?2004l"):
    assert restored in terminal.output
