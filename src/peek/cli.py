from argparse import ArgumentParser
from pathlib import Path

from peek.app import PeekApp


def main() -> None:
  parser = ArgumentParser(prog="v", description="Open a file or folder in peek")
  parser.add_argument("path", nargs="?", default=".", help="file or folder (default: current folder)")
  target = Path(parser.parse_args().path).expanduser().resolve()

  if not target.exists():
    parser.error(f"no such file or folder: {target}")
  if target.is_dir():
    PeekApp(target).run()
  else:
    PeekApp(target.parent, target).run()
