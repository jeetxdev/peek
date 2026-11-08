# peek

A light terminal code editor for macOS, built for Ghostty. It has a clickable file tree, syntax highlighting, and a Cmd+P popup for files, commands and text search.

## Install

```sh
brew install uv
uv tool install git+https://github.com/jeetxdev/peek
```

`uv` downloads the Python version peek needs, so nothing else is required. If your shell can't find `v` afterwards, run `uv tool update-shell` and open a new terminal.

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

Choose **New File** (or press Cmd+N) to create and open a file using a path relative
to the project. Missing parent folders are created. Existing files are never overwritten.
Choose **Delete File** to permanently delete the open file after confirming. Cancel
keeps the file and any unsaved edits.

## Shortcuts

| Action | Shortcut |
|---|---|
| Popup | ⌘P or ⌃P |
| Save | ⌘S |
| New File | ⌘N or ⌃N |
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
