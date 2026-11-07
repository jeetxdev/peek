from pathlib import Path

import pytest

from peek.languages import is_prose, language_for, uses_tab_indent


@pytest.mark.parametrize(
  ("name", "language"),
  [
    ("app.ts", "typescript"),
    ("App.TSX", "tsx"),
    ("view.jsx", "jsx"),
    ("main.py", "python"),
    (".zshrc", "bash"),
    ("Makefile", None),
  ],
)
def test_language_for(name: str, language: str | None) -> None:
  assert language_for(Path(name)) == language


def test_is_prose() -> None:
  assert is_prose(Path("README.md"))
  assert not is_prose(Path("main.py"))


def test_uses_tab_indent() -> None:
  assert uses_tab_indent("func main() {\n\treturn\n}\n")
  assert not uses_tab_indent("def main():\n  return\n")
