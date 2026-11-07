# peek

A light terminal code editor for macOS, built for Ghostty. It has a clickable file tree, syntax highlighting, and a Cmd+P popup for files, commands and text search.

## Install

```sh
brew install uv gh
gh auth login
gh auth setup-git
uv tool install git+https://github.com/jeetxdev/peek
```

`uv` downloads the Python version peek needs, so nothing else is required. The two `gh` steps let `uv` read this private repo. If your shell can't find `v` afterwards, run `uv tool update-shell` and open a new terminal.

To get the latest version:

```sh
uv tool upgrade peek
```

## Use

```sh
v              # current folder
v src/app.ts   # a file, with its folder in the sidebar
```

Press Cmd+P for the popup:

| Type | Result |
|---|---|
| nothing | the action list |
| `app` | files, then matching actions |
| `>sav` | actions only |
| `%needle` | text inside every file in the project |

## Shortcuts

| Action | Shortcut |
|---|---|
| Popup | ⌘P or ⌃P |
| Save | ⌘S |
| Undo / Redo | ⌃Z / ⌃Y |
| Cut | ⌘X |
| Copy | ⌃C |
| Paste | ⌘V |
| Select All | ⌃A |
| Quit | ⌃Q |

Ghostty keeps Cmd+C, Cmd+Z and Cmd+A for itself, which is why those actions use Ctrl.

## Develop

```sh
git clone https://github.com/jeetxdev/peek
cd peek
uv sync
uv run pytest
uv run mypy
uv tool install --editable . --force
```
