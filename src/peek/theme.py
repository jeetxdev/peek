from rich.style import Style
from textual.widgets.text_area import TextAreaTheme

THEME_NAME = "catppuccin-mocha"
SYNTAX_THEME_NAME = "peek-catppuccin"

BASE = "#1e1e2e"
SURFACE = "#313244"
SURFACE_BRIGHT = "#45475a"
OVERLAY = "#6c7086"
TEXT = "#cdd6f4"
SUBTEXT = "#a6adc8"
MAUVE = "#cba6f7"
RED = "#f38ba8"
PEACH = "#fab387"
YELLOW = "#f9e2af"
GREEN = "#a6e3a1"
TEAL = "#94e2d5"
SKY = "#89dceb"
BLUE = "#89b4fa"
LAVENDER = "#b4befe"

KEYWORD = Style(color=MAUVE)
STRING = Style(color=GREEN)
FUNCTION = Style(color=BLUE)
TYPE = Style(color=YELLOW)
CONSTANT = Style(color=PEACH)
PUNCTUATION = Style(color=SUBTEXT)
OPERATOR = Style(color=SKY)
PROPERTY = Style(color=LAVENDER)

SYNTAX_THEME = TextAreaTheme(
  name=SYNTAX_THEME_NAME,
  base_style=Style(color=TEXT, bgcolor=BASE),
  gutter_style=Style(color=OVERLAY, bgcolor=BASE),
  cursor_style=Style(color=BASE, bgcolor=TEXT),
  cursor_line_style=Style(bgcolor=SURFACE),
  cursor_line_gutter_style=Style(color=TEXT, bgcolor=SURFACE),
  bracket_matching_style=Style(bgcolor=SURFACE_BRIGHT, bold=True),
  selection_style=Style(bgcolor=SURFACE_BRIGHT),
  syntax_styles={
    "attribute": PROPERTY,
    "bold": Style(bold=True),
    "boolean": CONSTANT,
    "class": TYPE,
    "comment": Style(color=OVERLAY, italic=True),
    "conditional": KEYWORD,
    "constant": CONSTANT,
    "constant.builtin": CONSTANT,
    "constructor": TYPE,
    "css.property": PROPERTY,
    "embedded": Style(color=TEXT),
    "exception": KEYWORD,
    "float": CONSTANT,
    "function": FUNCTION,
    "function.builtin": FUNCTION,
    "function.call": FUNCTION,
    "function.method": FUNCTION,
    "heading": Style(color=BLUE, bold=True),
    "heading.marker": Style(color=OVERLAY),
    "include": KEYWORD,
    "info_string": Style(color=GREEN, italic=True),
    "inline_code": STRING,
    "italic": Style(italic=True),
    "json.label": PROPERTY,
    "json.null": CONSTANT,
    "keyword": KEYWORD,
    "keyword.function": KEYWORD,
    "keyword.operator": KEYWORD,
    "keyword.return": KEYWORD,
    "link.label": Style(color=LAVENDER),
    "link.uri": Style(color=BLUE, underline=True),
    "list.marker": Style(color=PEACH),
    "method": FUNCTION,
    "method.call": FUNCTION,
    "number": CONSTANT,
    "operator": OPERATOR,
    "parameter": Style(color=RED),
    "property": PROPERTY,
    "punctuation.bracket": PUNCTUATION,
    "punctuation.delimiter": PUNCTUATION,
    "punctuation.special": OPERATOR,
    "regex.operator": OPERATOR,
    "repeat": KEYWORD,
    "strikethrough": Style(strike=True),
    "string": STRING,
    "string.documentation": STRING,
    "string.special": Style(color=TEAL),
    "tag": Style(color=BLUE),
    "toml.datetime": CONSTANT,
    "toml.type": PROPERTY,
    "type": TYPE,
    "type.builtin": TYPE,
    "type.class": TYPE,
    "variable.builtin": Style(color=RED),
    "variable.parameter": Style(color=RED),
    "yaml.field": PROPERTY,
  },
)
