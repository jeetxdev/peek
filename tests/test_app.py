from collections.abc import Iterator
from pathlib import Path

import pytest
from textual.pilot import Pilot
from textual.widgets import Input, OptionList, Static
from textual.widgets.text_area import Selection

from peek.app import READ_ONLY_NOTE, STATUS_ID, PeekApp
from peek.commands import COMMANDS
from peek.dialogs import ChoiceDialog
from peek.editor import CodeEditor
from peek.explorer import FileExplorer
from peek.file_search import list_project_files
from peek.palette import (
  NO_MATCHES,
  TEXT_SEARCH_DELAY_SECONDS,
  TEXT_SEARCH_HINT,
  TEXT_SEARCH_PREFIX,
  ActionPalette,
)
from peek.text_search import search_text

TERMINAL_SIZE = (120, 30)
ORIGINAL = "const a: number = 1;\n"
OTHER = "print('other')\n"


@pytest.fixture
def project(tmp_path: Path) -> Iterator[Path]:
  (tmp_path / "a.ts").write_text(ORIGINAL)
  (tmp_path / "b.py").write_text(OTHER)
  (tmp_path / "node_modules").mkdir()
  yield tmp_path


def editor(pilot: Pilot[None]) -> CodeEditor:
  return pilot.app.query_one(CodeEditor)


def status_text(pilot: Pilot[None]) -> str:
  return str(pilot.app.query_one(f"#{STATUS_ID}", Static).render())


async def wait_for_workers_of(pilot: Pilot[None], node: object) -> None:
  """Skips the tree's loader worker, which never exits."""
  workers = [worker for worker in pilot.app.workers if worker.node is node]
  # An empty list would make wait_for_complete wait on every worker.
  if workers:
    await pilot.app.workers.wait_for_complete(workers)
  await pilot.pause()


async def settle(pilot: Pilot[None]) -> None:
  await pilot.pause()
  await wait_for_workers_of(pilot, pilot.app)


async def click_file(pilot: Pilot[None], name: str) -> None:
  tree = pilot.app.query_one(FileExplorer)
  await pilot.pause()
  await tree.reload()
  await pilot.pause()
  line = next(
    index
    for index in range(tree.last_line + 1)
    if (node := tree.get_node_at_line(index)) and str(node.label) == name
  )
  await pilot.click(FileExplorer, offset=(8, line))
  await pilot.pause()


async def click_button(pilot: Pilot[None], selector: str) -> None:
  await pilot.click(selector)
  await pilot.pause()


async def test_click_opens_file_with_highlighting(project: Path) -> None:
  app = PeekApp(project)
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await click_file(pilot, "a.ts")
    await settle(pilot)
    assert editor(pilot).text == ORIGINAL
    assert editor(pilot).language == "typescript"
    assert editor(pilot).has_focus
    assert not editor(pilot).read_only


async def test_explorer_hides_noise(project: Path) -> None:
  app = PeekApp(project)
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    tree = app.query_one(FileExplorer)
    await tree.reload()
    await pilot.pause()
    labels = [str(node.label) for node in tree.root.children]
    assert "node_modules" not in labels


async def test_typing_then_save_shortcut_writes_file(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    assert "●" not in status_text(pilot)
    await pilot.press("x")
    await pilot.pause()
    assert "●" in status_text(pilot)
    await pilot.press("super+s")
    await settle(pilot)
    assert (project / "a.ts").read_text() == f"x{ORIGINAL}"
    assert "●" not in status_text(pilot)


async def test_undo_back_to_saved_text_is_clean(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("x")
    await pilot.pause()
    editor(pilot).undo()
    await pilot.pause()
    assert "●" not in status_text(pilot)


@pytest.mark.parametrize(
  ("keys", "expected"),
  [
    (("x", "super+z"), ORIGINAL),
    (("x", "super+z", "super+y"), f"x{ORIGINAL}"),
    (("x", "super+z", "shift+super+z"), f"x{ORIGINAL}"),
    (("super+a", "super+x"), ""),
    (("ctrl+a", "ctrl+x"), ""),
    (("right", "right", "home", "x"), f"x{ORIGINAL}"),
    (("x", "ctrl+z"), ORIGINAL),
    (("x", "ctrl+z", "ctrl+y"), f"x{ORIGINAL}"),
  ],
)
async def test_editing_shortcuts(project: Path, keys: tuple[str, ...], expected: str) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press(*keys)
    await pilot.pause()
    assert editor(pilot).text == expected


async def test_ctrl_a_selects_whole_file_and_ctrl_c_copies_it(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("ctrl+a")
    await pilot.pause()
    assert editor(pilot).selected_text == ORIGINAL
    await pilot.press("ctrl+c")
    await pilot.pause()
    assert app.clipboard == ORIGINAL


async def test_shortcuts_work_while_explorer_has_focus(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("x")
    app.query_one(FileExplorer).focus()
    await pilot.pause()
    await pilot.press("super+z", "ctrl+a", "super+c")
    await pilot.pause()
    assert editor(pilot).text == ORIGINAL
    assert app.clipboard == ORIGINAL


async def test_palette_lists_every_command_with_its_shortcut(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("super+p")
    await pilot.pause()
    assert isinstance(app.screen, ActionPalette)
    options = app.screen.query_one(OptionList)
    assert options.option_count == len(COMMANDS)
    for row, command in enumerate(COMMANDS):
      line = options.render_line(row).text
      assert line.lstrip().startswith(command.name)
      if command.shortcut:
        assert line.rstrip().endswith(command.shortcut)
        assert line.rstrip().index(command.shortcut) > len(line) // 2
      else:
        assert line.strip() == command.name


async def open_palette(pilot: Pilot[None]) -> ActionPalette:
  await pilot.press("super+p")
  await pilot.pause()
  screen = pilot.app.screen
  assert isinstance(screen, ActionPalette)
  await wait_for_workers_of(pilot, screen)
  return screen


def palette_rows(screen: ActionPalette) -> list[str]:
  options = screen.query_one(OptionList)
  return [options.render_line(row).text.strip() for row in range(options.option_count)]


async def test_palette_search_opens_nested_file_and_shows_folder(project: Path) -> None:
  nested = project / "src" / "components"
  nested.mkdir(parents=True)
  (nested / "button.tsx").write_text("export const Button = 1;\n")
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    screen = await open_palette(pilot)
    await pilot.press(*"butn")
    await pilot.pause()
    row = palette_rows(screen)[0]
    assert row.startswith("button.tsx")
    assert row.endswith("src/components")
    await pilot.press("enter")
    await settle(pilot)
    assert editor(pilot).language == "tsx"
    assert editor(pilot).has_focus


async def test_palette_click_opens_file(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await open_palette(pilot)
    await pilot.press("b", ".", "p")
    await pilot.pause()
    await pilot.click(OptionList, offset=(4, 0))
    await settle(pilot)
    assert editor(pilot).text == OTHER


async def test_palette_lists_files_before_matching_commands(project: Path) -> None:
  (project / "saved.txt").write_text("notes\n")
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    screen = await open_palette(pilot)
    await pilot.press(*"sav")
    await pilot.pause()
    rows = palette_rows(screen)
    assert rows[0].startswith("saved.txt")
    assert rows[1].startswith("Save")


async def test_palette_prefix_limits_results_to_commands(project: Path) -> None:
  (project / "saved.txt").write_text("notes\n")
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("x")
    screen = await open_palette(pilot)
    await pilot.press(">", *"sav")
    await pilot.pause()
    assert len(palette_rows(screen)) == 1
    await pilot.press("enter")
    await settle(pilot)
    assert (project / "a.ts").read_text() == f"x{ORIGINAL}"


async def test_palette_file_with_unsaved_changes_prompts(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("x")
    await open_palette(pilot)
    await pilot.press(*"b.py", "enter")
    await pilot.pause()
    await pilot.pause()
    assert isinstance(app.screen, ChoiceDialog)
    await click_button(pilot, "#cancel")
    await settle(pilot)
    assert editor(pilot).text == f"x{ORIGINAL}"


async def test_palette_long_folder_stays_on_one_row(project: Path) -> None:
  deep = project / "/".join(["very-long-folder-name"] * 6)
  deep.mkdir(parents=True)
  (deep / "deep.ts").write_text("x\n")
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    screen = await open_palette(pilot)
    await pilot.press(*"deep")
    await pilot.pause()
    assert palette_rows(screen)[0].startswith("deep.ts")
    assert "…" in palette_rows(screen)[0]


async def type_text_search(pilot: Pilot[None], screen: ActionPalette, query: str) -> None:
  await pilot.press("percent_sign", *query)
  await pilot.pause(TEXT_SEARCH_DELAY_SECONDS + 0.05)
  await wait_for_workers_of(pilot, screen)


async def test_text_search_opens_file_at_matching_text(project: Path) -> None:
  source = project / "long.ts"
  source.write_text("filler\n" * 400 + "  const needle = 1;\n" + "filler\n" * 400)
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    screen = await open_palette(pilot)
    await type_text_search(pilot, screen, "NEEDLE")
    row = palette_rows(screen)[0]
    assert "const needle = 1;" in row
    assert row.endswith("long.ts:401")
    await pilot.press("enter")
    await settle(pilot)
    await pilot.pause()
    assert editor(pilot).selection == ((400, 8), (400, 14))
    assert editor(pilot).selected_text == "needle"
    assert editor(pilot).has_focus
    assert editor(pilot).scroll_y > 300


async def test_text_search_click_jumps_inside_the_open_file(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    screen = await open_palette(pilot)
    await type_text_search(pilot, screen, "number")
    await pilot.click(OptionList, offset=(4, 0))
    await settle(pilot)
    assert editor(pilot).selected_text == "number"


async def test_search_in_project_command_opens_text_search(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await open_palette(pilot)
    await pilot.press(">", *"search", "enter")
    await pilot.pause()
    await pilot.pause()
    screen = app.screen
    assert isinstance(screen, ActionPalette)
    assert screen.query_one(Input).value == TEXT_SEARCH_PREFIX
    assert palette_rows(screen) == [TEXT_SEARCH_HINT]
    await pilot.press(*"print")
    await pilot.pause(TEXT_SEARCH_DELAY_SECONDS + 0.05)
    await wait_for_workers_of(pilot, screen)
    assert screen.query_one(Input).value == f"{TEXT_SEARCH_PREFIX}print"
    assert palette_rows(screen)[0].endswith("b.py:1")


async def test_text_search_reports_no_matches(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    screen = await open_palette(pilot)
    await type_text_search(pilot, screen, "zzzz")
    assert palette_rows(screen) == [NO_MATCHES]
    await pilot.press("enter")
    await pilot.pause()
    assert isinstance(app.screen, ActionPalette)


async def test_text_search_shows_only_the_latest_query(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    screen = await open_palette(pilot)
    await pilot.press("percent_sign", *"print")
    await pilot.press(*"zz")
    await pilot.pause(TEXT_SEARCH_DELAY_SECONDS + 0.05)
    await wait_for_workers_of(pilot, screen)
    assert palette_rows(screen) == [NO_MATCHES]


async def test_text_search_with_unsaved_changes_prompts(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("x")
    screen = await open_palette(pilot)
    await type_text_search(pilot, screen, "print")
    await pilot.press("enter")
    await pilot.pause()
    await pilot.pause()
    assert isinstance(app.screen, ChoiceDialog)
    await click_button(pilot, "#cancel")
    await settle(pilot)
    assert editor(pilot).text == f"x{ORIGINAL}"


async def test_jump_past_the_end_of_an_edited_file_stays_in_bounds(project: Path) -> None:
  source = project / "c.txt"
  source.write_text("one\ntwo\nneedle\n")
  stale_match = next(search_text(list_project_files(project), "needle"))
  app = PeekApp(project, source)
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    editor(pilot).load_text("short\n")
    editor(pilot).select_match(stale_match)
    await pilot.pause()
    assert editor(pilot).cursor_location[0] <= 1


DIRTY = "“a” — b…\n“c”\n"


async def run_clean_text(pilot: Pilot[None]) -> None:
  await open_palette(pilot)
  await pilot.press(">", *"clean", "enter")
  await settle(pilot)


async def test_clean_text_cleans_whole_file_without_selection(project: Path) -> None:
  source = project / "word.txt"
  source.write_text(DIRTY)
  app = PeekApp(project, source)
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("down", "right")
    await run_clean_text(pilot)
    assert editor(pilot).text == '"a" - b...\n"c"\n'
    assert editor(pilot).cursor_location == (1, 1)
    assert "●" in status_text(pilot)
    assert source.read_text() == DIRTY


async def test_clean_text_only_touches_the_selection(project: Path) -> None:
  source = project / "word.txt"
  source.write_text(DIRTY)
  app = PeekApp(project, source)
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    editor(pilot).selection = Selection((1, 0), (1, 3))
    await run_clean_text(pilot)
    assert editor(pilot).text == '“a” — b…\n"c"\n'


async def test_clean_text_handles_a_backwards_selection(project: Path) -> None:
  source = project / "word.txt"
  source.write_text(DIRTY)
  app = PeekApp(project, source)
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    editor(pilot).selection = Selection((1, 3), (1, 0))
    await run_clean_text(pilot)
    assert editor(pilot).text == '“a” — b…\n"c"\n'


async def test_one_undo_reverses_clean_text(project: Path) -> None:
  source = project / "word.txt"
  source.write_text(DIRTY)
  app = PeekApp(project, source)
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await run_clean_text(pilot)
    await pilot.press("ctrl+z")
    await pilot.pause()
    assert editor(pilot).text == DIRTY
    assert "●" not in status_text(pilot)


async def test_clean_text_keeps_crlf_line_endings(project: Path) -> None:
  source = project / "word.txt"
  source.write_bytes("“a”\r\nb\r\n".encode())
  app = PeekApp(project, source)
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await run_clean_text(pilot)
    await pilot.press("super+s")
    await settle(pilot)
    assert source.read_bytes() == b'"a"\r\nb\r\n'


async def test_clean_text_leaves_read_only_file_alone(project: Path) -> None:
  source = project / "odd.txt"
  source.write_bytes("“a”\x0cb\n".encode())
  app = PeekApp(project, source)
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    assert editor(pilot).read_only
    before = editor(pilot).text
    await run_clean_text(pilot)
    assert editor(pilot).text == before


async def test_clean_text_with_no_file_open_does_nothing(project: Path) -> None:
  app = PeekApp(project)
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await run_clean_text(pilot)
    assert editor(pilot).text == ""


async def test_clean_text_on_clean_file_changes_nothing(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await run_clean_text(pilot)
    assert editor(pilot).text == ORIGINAL
    assert "●" not in status_text(pilot)


async def test_palette_filters_and_enter_runs_command(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("x", "super+p")
    await pilot.pause()
    await pilot.press(*"sav")
    await pilot.pause()
    assert app.screen.query_one(OptionList).option_count == 1
    await pilot.press("enter")
    await settle(pilot)
    assert not isinstance(app.screen, ActionPalette)
    assert (project / "a.ts").read_text() == f"x{ORIGINAL}"
    assert editor(pilot).has_focus


async def test_palette_arrow_keys_pick_a_row(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("x", "super+p")
    await pilot.pause()
    await pilot.press("down", "enter")
    await pilot.pause()
    assert editor(pilot).text == ORIGINAL


async def test_palette_click_runs_command_on_kept_selection(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("super+a", "super+p")
    await pilot.pause()
    copy_row = [command.name for command in COMMANDS].index("Copy")
    await pilot.click(OptionList, offset=(4, copy_row))
    await settle(pilot)
    assert app.clipboard == ORIGINAL
    # Cut sits just above Copy, so a click landing one row off would empty the file.
    assert editor(pilot).text == ORIGINAL


async def test_palette_click_lands_on_the_exact_row(project: Path) -> None:
  (project / "b1.py").write_text("first\n")
  (project / "b2.py").write_text("second\n")
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    screen = await open_palette(pilot)
    await pilot.press("b", ".")
    await pilot.pause()
    rows = palette_rows(screen)
    target = next(index for index, row in enumerate(rows) if row.startswith("b2.py"))
    await pilot.click(OptionList, offset=(4, target))
    await settle(pilot)
    assert editor(pilot).text == "second\n"


async def test_search_box_keeps_focus_after_clicking_the_list(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    screen = await open_palette(pilot)
    await pilot.click(OptionList, offset=(4, 20))
    await pilot.pause()
    assert isinstance(app.screen, ActionPalette)
    assert screen.query_one(Input).has_focus


@pytest.mark.parametrize("close_with", ["escape", "super+p", "ctrl+p"])
async def test_palette_closes_without_running_anything(project: Path, close_with: str) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("super+p")
    await pilot.pause()
    await pilot.press(close_with)
    await pilot.pause()
    assert not isinstance(app.screen, ActionPalette)
    assert editor(pilot).text == ORIGINAL


async def test_clicking_outside_palette_closes_it(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("super+p")
    await pilot.pause()
    await pilot.click(offset=(1, 25))
    await pilot.pause()
    assert not isinstance(app.screen, ActionPalette)


async def test_palette_shows_message_when_nothing_matches(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("super+p")
    await pilot.pause()
    app.screen.query_one(Input).value = "zzz"
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()
    assert isinstance(app.screen, ActionPalette)


async def test_shortcuts_do_not_fire_behind_open_dialog(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("x", "ctrl+q")
    await pilot.pause()
    dialog = app.screen
    assert isinstance(dialog, ChoiceDialog)
    await pilot.press("super+s", "ctrl+q", "super+p")
    await pilot.pause()
    assert app.screen is dialog
    assert (project / "a.ts").read_text() == ORIGINAL


@pytest.mark.parametrize(
  ("button", "expected_a", "expected_text"),
  [
    ("save", f"x{ORIGINAL}", OTHER),
    ("discard", ORIGINAL, OTHER),
    ("cancel", ORIGINAL, f"x{ORIGINAL}"),
  ],
)
async def test_switching_file_with_unsaved_changes_prompts(
  project: Path, button: str, expected_a: str, expected_text: str
) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("x")
    await click_file(pilot, "b.py")
    assert isinstance(app.screen, ChoiceDialog)
    await click_button(pilot, f"#{button}")
    await settle(pilot)
    assert (project / "a.ts").read_text() == expected_a
    assert editor(pilot).text == expected_text


async def test_quit_with_unsaved_changes_can_be_cancelled(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("x")
    await pilot.press("ctrl+q")
    await pilot.pause()
    assert isinstance(app.screen, ChoiceDialog)
    await click_button(pilot, "#cancel")
    await pilot.pause()
    assert app.is_running
    assert editor(pilot).text == f"x{ORIGINAL}"


async def test_save_prompts_when_file_changed_on_disk(project: Path) -> None:
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("x")
    (project / "a.ts").write_text("changed by another program\n")
    await pilot.press("ctrl+s")
    await pilot.pause()
    assert isinstance(app.screen, ChoiceDialog)
    await click_button(pilot, "#cancel")
    await settle(pilot)
    assert (project / "a.ts").read_text() == "changed by another program\n"


@pytest.mark.parametrize(
  "content",
  [b"a\r\nb\nc\n", b"a\x0cb\n", b"a\rb\n", "a b\n".encode()],
)
async def test_files_textarea_would_rewrite_open_read_only(project: Path, content: bytes) -> None:
  path = project / "odd.txt"
  path.write_bytes(content)
  app = PeekApp(project, path)
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    assert editor(pilot).read_only
    assert READ_ONLY_NOTE in app._status_text()
    await pilot.press("x", "ctrl+s")
    await settle(pilot)
    assert path.read_bytes() == content


async def test_unopenable_file_keeps_current_file(project: Path) -> None:
  (project / "c.bin").write_bytes(b"\0\0\0")
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await click_file(pilot, "c.bin")
    await settle(pilot)
    assert editor(pilot).text == ORIGINAL


async def test_copy_and_paste_actions(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.setattr("peek.editor.read_system_clipboard", lambda: "pasted")
  app = PeekApp(project, project / "a.ts")
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    app.action_select_all()
    app.action_copy()
    assert app.clipboard == ORIGINAL
    app.action_paste()
    await pilot.pause()
    assert editor(pilot).text == "pasted"
    assert editor(pilot).has_focus


async def test_tab_indented_file_keeps_tabs(project: Path) -> None:
  path = project / "Makefile"
  path.write_text("all:\n\techo hi\n")
  app = PeekApp(project, path)
  async with app.run_test(size=TERMINAL_SIZE) as pilot:
    await pilot.pause()
    await pilot.press("tab")
    await pilot.pause()
    assert editor(pilot).text.startswith("\tall:")


