from pathlib import Path

EXTENSION_LANGUAGES = {
  ".bash": "bash",
  ".css": "css",
  ".scss": "css",
  ".go": "go",
  ".htm": "html",
  ".html": "html",
  ".java": "java",
  ".cjs": "javascript",
  ".js": "javascript",
  ".mjs": "javascript",
  ".json": "json",
  ".jsonc": "json",
  ".jsx": "jsx",
  ".markdown": "markdown",
  ".md": "markdown",
  ".mdx": "markdown",
  ".py": "python",
  ".pyi": "python",
  ".rs": "rust",
  ".sh": "bash",
  ".sql": "sql",
  ".svg": "xml",
  ".toml": "toml",
  ".cts": "typescript",
  ".mts": "typescript",
  ".ts": "typescript",
  ".tsx": "tsx",
  ".xml": "xml",
  ".yaml": "yaml",
  ".yml": "yaml",
  ".zsh": "bash",
}

FILENAME_LANGUAGES = {
  ".bash_profile": "bash",
  ".bashrc": "bash",
  ".env": "bash",
  ".profile": "bash",
  ".zprofile": "bash",
  ".zshenv": "bash",
  ".zshrc": "bash",
}

PROSE_EXTENSIONS = frozenset({".markdown", ".md", ".mdx", ".txt"})


def language_for(path: Path) -> str | None:
  return FILENAME_LANGUAGES.get(path.name) or EXTENSION_LANGUAGES.get(path.suffix.lower())


def is_prose(path: Path) -> bool:
  return path.suffix.lower() in PROSE_EXTENSIONS


def uses_tab_indent(text: str) -> bool:
  return text.startswith("\t") or "\n\t" in text
