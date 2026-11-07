import pytest

from peek.clean_text import clean_text


@pytest.mark.parametrize(
  ("dirty", "clean"),
  [
    ("“quote” ‘it’s’", "\"quote\" 'it's'"),
    ("a—b–c−d", "a-b-c-d"),
    ("wait…", "wait..."),
    ("a b c", "a b c"),
    ("a​b­c﻿", "abc"),
    ("• item", "- item"),
    ("ﬁne ﬂow", "fine flow"),
  ],
)
def test_replaces_word_characters(dirty: str, clean: str) -> None:
  assert clean_text(dirty)[0] == clean


@pytest.mark.parametrize(
  "text",
  [
    "plain text\n\twith tabs\r\n",
    "café naïve",
    "নমস্কার हिन्दी",
    "family 👨‍👩‍👧 emoji",
    "क्‍ष joiner",
  ],
)
def test_leaves_real_text_alone(text: str) -> None:
  assert clean_text(text) == (text, 0)


def test_counts_changed_characters() -> None:
  assert clean_text("“a”…​")[1] == 4
