_REPLACEMENTS = {
  **dict.fromkeys("“”„‟", '"'),
  **dict.fromkeys("‘’‚‛", "'"),
  **dict.fromkeys("‐‑‒–—―−", "-"),
  **dict.fromkeys("            　", " "),
  # Zero-width joiners (U+200C, U+200D) stay: emoji and Indic scripts depend on them.
  **dict.fromkeys("­​⁠﻿", ""),
  "…": "...",
  "•": "-",
  "ﬀ": "ff",
  "ﬁ": "fi",
  "ﬂ": "fl",
  "ﬃ": "ffi",
  "ﬄ": "ffl",
}
_TRANSLATION = str.maketrans(_REPLACEMENTS)


def clean_text(text: str) -> tuple[str, int]:
  """Returns the cleaned text and how many characters were changed."""
  return text.translate(_TRANSLATION), sum(character in _REPLACEMENTS for character in text)
