import os
import subprocess

PASTE_COMMAND = "pbpaste"
PASTE_TIMEOUT_SECONDS = 2
# pbpaste picks its output encoding from the locale, which may be unset.
PASTE_ENV = {**os.environ, "LC_CTYPE": "UTF-8"}


def read_system_clipboard() -> str:
  """Reads directly because Ghostty asks for permission on terminal clipboard reads."""
  try:
    result = subprocess.run(
      [PASTE_COMMAND],
      capture_output=True,
      check=True,
      encoding="utf-8",
      env=PASTE_ENV,
      timeout=PASTE_TIMEOUT_SECONDS,
    )
  except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
    return ""
  return result.stdout
