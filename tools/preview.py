#!/usr/bin/env python3
"""Render docs/preview.png: a sample Ruby file colored from the scheme XML.

Tokens map to the keys RubyMine's highlighter emits, and missing keys follow
the same fallback chain the IDE uses, so the picture matches the editor.

    python3 tools/preview.py src/Tomorrow.xml docs/preview.png
"""
import html
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FONT = "Monaco"
FONT_SIZE, LINE_HEIGHT, WIDTH = 13, 21, 820

SAMPLE = '''\
# Retries a block with exponential backoff.
module Bakery
  class Retry
    ATTEMPTS = 3

    def initialize(attempts: ATTEMPTS, delay: 0.5)
      @attempts = attempts
      @delay = delay
    end

    def call(logger = $stdout)
      tries = 0
      begin
        yield tries += 1
      rescue Timeout::Error => error
        logger.puts "retry ##{tries}: #{error.message}"
        sleep(@delay * 2**tries) and retry if tries < @attempts
        raise
      end
    end
  end
end

Bakery::Retry.new(attempts: 5).call { fetch(:menu, cache: true) }
'''

CARET_LINE, CARET_WORD = 12, "tries"

FALLBACKS = {
    "RUBY_KEYWORD": "DEFAULT_KEYWORD",
    "RUBY_COMMENT": "DEFAULT_DOC_COMMENT",
    "RUBY_NUMBER": "DEFAULT_NUMBER",
    "RUBY_STRING": "DEFAULT_STRING",
    "RUBY_INTERPOLATED_STRING": "DEFAULT_STRING",
    "RUBY_EXPR_IN_STRING": "DEFAULT_PARENTHS",
    "RUBY_OPERATION_SIGN": "DEFAULT_OPERATION_SIGN",
    "RUBY_HASH_ASSOC": "DEFAULT_OPERATION_SIGN",
    "RUBY_BRACKETS": "DEFAULT_BRACKETS",
    "RUBY_PARENTHESES": "DEFAULT_PARENTHS",
    "RUBY_BRACES": "DEFAULT_BRACES",
    "RUBY_IDENTIFIER": "DEFAULT_IDENTIFIER",
    "RUBY_METHOD_NAME": "DEFAULT_INSTANCE_METHOD",
    "RUBY_CONSTANT": "DEFAULT_CONSTANT",
    "RUBY_CONSTANT_DECLARATION": "DEFAULT_CONSTANT",
    "RUBY_GVAR": "DEFAULT_GLOBAL_VARIABLE",
    "RUBY_IVAR": "DEFAULT_INSTANCE_FIELD",
    "RUBY_COMMA": "DEFAULT_COMMA",
    "RUBY_DOT": "DEFAULT_DOT",
    "RUBY_COLON": "DEFAULT_DOT",
    "RUBY_LOCAL_VAR_ID": "DEFAULT_LOCAL_VARIABLE",
    "RUBY_PARAMETER_ID": "DEFAULT_PARAMETER",
    "RUBY_SYMBOL": "DEFAULT_INSTANCE_FIELD",
    "RUBY_HASH_KEY": "RUBY_SYMBOL",
    "DEFAULT_GLOBAL_VARIABLE": "DEFAULT_IDENTIFIER",
    "DEFAULT_LOCAL_VARIABLE": "DEFAULT_IDENTIFIER",
    "DEFAULT_PARAMETER": "DEFAULT_IDENTIFIER",
    "DEFAULT_INSTANCE_FIELD": "DEFAULT_IDENTIFIER",
    "DEFAULT_INSTANCE_METHOD": "DEFAULT_FUNCTION_DECLARATION",
    "DEFAULT_DOC_COMMENT": "DEFAULT_BLOCK_COMMENT",
}

KEYWORDS = {
    "module", "class", "def", "end", "begin", "rescue", "yield", "if", "and", "retry",
    "raise", "true", "false", "nil", "self", "do", "return",
}

TOKEN_RE = re.compile(r"""
    (?P<comment>\#.*)
  | (?P<string>"(?:[^"\\]|\\.)*")
  | (?P<hashkey>[a-z_]\w*:(?!:))
  | (?P<symbol>:[a-z_]\w*)
  | (?P<ivar>@\w+)
  | (?P<gvar>\$\w+)
  | (?P<number>\d+(?:\.\d+)?)
  | (?P<constant>[A-Z]\w*)
  | (?P<word>[a-z_]\w*[?!]?)
  | (?P<assoc>=>)
  | (?P<op>\*\*|[+\-*/<>=]=?|&&|\|\|)
  | (?P<colon>::)
  | (?P<dot>\.)
  | (?P<comma>,)
  | (?P<paren>[()])
  | (?P<brace>[{}])
  | (?P<space>\s+)
""", re.VERBOSE)

SIMPLE = {
    "comment": "RUBY_COMMENT", "hashkey": "RUBY_HASH_KEY", "symbol": "RUBY_SYMBOL",
    "ivar": "RUBY_IVAR", "gvar": "RUBY_GVAR", "number": "RUBY_NUMBER",
    "assoc": "RUBY_HASH_ASSOC", "op": "RUBY_OPERATION_SIGN", "colon": "RUBY_COLON",
    "dot": "RUBY_DOT", "comma": "RUBY_COMMA", "paren": "RUBY_PARENTHESES",
    "brace": "RUBY_BRACES", "space": None,
}


def load_scheme(path):
    root = ET.parse(path).getroot()
    colors = {o.get("name"): o.get("value") for o in root.find("colors")}
    attributes = {}
    for option in root.find("attributes"):
        value = option.find("value")
        fields = {} if value is None else {o.get("name"): o.get("value") for o in value}
        attributes[option.get("name")] = {k: v for k, v in fields.items() if v}
    return colors, attributes


def resolve(attributes, key):
    while key not in attributes and key in FALLBACKS:
        key = FALLBACKS[key]
    return attributes.get(key, {})


def hex6(value):
    return "#" + value.rjust(6, "0").lower()


def tokenize_string(text, params, locals_):
    parts, pos = [], 0
    for match in re.finditer(r"#\{([^}]*)\}", text):
        parts.append((text[pos:match.start()], "RUBY_STRING"))
        parts.append(("#{", "RUBY_EXPR_IN_STRING"))
        parts.extend(tokenize_line(match.group(1), params, locals_))
        parts.append(("}", "RUBY_EXPR_IN_STRING"))
        pos = match.end()
    parts.append((text[pos:], "RUBY_STRING"))
    return parts


def tokenize_line(line, params, locals_):
    tokens, previous = [], None
    for match in TOKEN_RE.finditer(line):
        kind, text = match.lastgroup, match.group()
        if kind == "string":
            tokens.extend(tokenize_string(text, params, locals_))
            continue
        if kind == "constant":
            key = "RUBY_CONSTANT_DECLARATION" if previous in ("module", "class") else "RUBY_CONSTANT"
        elif kind == "word":
            if text in KEYWORDS:
                key = "RUBY_KEYWORD"
            elif previous == "def":
                key = "RUBY_METHOD_NAME"
            elif text in params:
                key = "RUBY_PARAMETER_ID"
            elif text in locals_:
                key = "RUBY_LOCAL_VAR_ID"
            else:
                key = "RUBY_IDENTIFIER"
        elif kind == "hashkey" and previous_token_is_def_signature(tokens):
            tokens.append((text[:-1], "RUBY_PARAMETER_ID"))
            tokens.append((":", "RUBY_COLON"))
            previous = text
            continue
        else:
            key = SIMPLE[kind]
        tokens.append((text, key))
        if kind != "space":
            previous = text
    return tokens


def previous_token_is_def_signature(tokens):
    words = [text for text, key in tokens if key]
    return bool(words) and words[0] == "def"


def tokenize(source):
    params, locals_, lines = set(), set(), []
    for line in source.splitlines():
        signature = re.match(r"\s*def \w+\((.*)\)", line)
        if signature:
            params = set(re.findall(r"([a-z_]\w*)(?::| =)", signature.group(1)))
            locals_ = set()
        assigned = re.match(r"\s*([a-z_]\w*) = ", line)
        if assigned and assigned.group(1) not in params:
            locals_.add(assigned.group(1))
        lines.append(tokenize_line(line, params, locals_))
    return lines


def style(attrs):
    rules = []
    if "FOREGROUND" in attrs:
        rules.append(f"color:{hex6(attrs['FOREGROUND'])}")
    if "BACKGROUND" in attrs:
        rules.append(f"background:{hex6(attrs['BACKGROUND'])}")
    font = attrs.get("FONT_TYPE", "0")
    if font in ("1", "3"):
        rules.append("font-weight:bold")
    if font in ("2", "3"):
        rules.append("font-style:italic")
    if attrs.get("EFFECT_TYPE") == "1" and "EFFECT_COLOR" in attrs:
        rules.append(f"text-decoration:underline {hex6(attrs['EFFECT_COLOR'])}")
    return ";".join(rules)


def render(scheme_path, title):
    colors, attributes = load_scheme(scheme_path)
    text = attributes.get("TEXT", {})
    bg, fg = hex6(text.get("BACKGROUND", "ffffff")), hex6(text.get("FOREGROUND", "000000"))
    caret_row = hex6(colors.get("CARET_ROW_COLOR", "f5f5f5"))
    line_number = hex6(colors.get("LINE_NUMBERS_COLOR", "999999"))
    caret_number = hex6(colors.get("LINE_NUMBER_ON_CARET_ROW_COLOR", colors.get("LINE_NUMBERS_COLOR", "999999")))
    gutter = hex6(colors.get("GUTTER_BACKGROUND", text.get("BACKGROUND", "ffffff")))
    caret = hex6(colors.get("CARET_COLOR", "000000"))
    usage = resolve(attributes, "IDENTIFIER_UNDER_CARET_ATTRIBUTES")
    tab_line = hex6(colors.get("TEARLINE_COLOR", colors.get("INDENT_GUIDE", "cccccc")))

    rows = []
    for number, tokens in enumerate(tokenize(SAMPLE), start=1):
        on_caret = number == CARET_LINE
        spans = []
        for token, key in tokens:
            css = style(resolve(attributes, key)) if key else ""
            caret_mark = ""
            if token == CARET_WORD and key == "RUBY_LOCAL_VAR_ID":
                css += f";background:{hex6(usage['BACKGROUND'])}" if "BACKGROUND" in usage else ""
                if on_caret:
                    caret_mark = '<i class="caret"></i>'
            spans.append(f'<span style="{css}">{caret_mark}{html.escape(token)}</span>')
        row_bg = f"background:{caret_row}" if on_caret else ""
        number_color = caret_number if on_caret else line_number
        rows.append(
            f'<div class="row" style="{row_bg}"><span class="ln" style="color:{number_color};'
            f'background:{gutter if not on_caret else caret_row}">{number}</span>'
            f'<span class="code">{"".join(spans) or "&nbsp;"}</span></div>'
        )

    height = 48 + len(rows) * LINE_HEIGHT + 24
    page = f"""<!doctype html><meta charset="utf-8"><style>
html,body{{margin:0;background:{bg};}}
body{{font:{FONT_SIZE}px/{LINE_HEIGHT}px "{FONT}",monospace;color:{fg};-webkit-font-smoothing:antialiased}}
.tab{{height:36px;display:flex;align-items:flex-end;padding:0 0 0 56px;border-bottom:1px solid {tab_line};}}
.tab span{{padding:0 14px 8px;border-bottom:2px solid {caret};font:12px -apple-system,sans-serif;color:{fg}}}
.editor{{padding:12px 0}}
.row{{display:flex;white-space:pre;height:{LINE_HEIGHT}px}}
.ln{{width:40px;text-align:right;padding-right:16px;flex:none}}
.code{{flex:1;padding-left:4px}}
.caret{{display:inline-block;width:2px;height:16px;margin-right:-2px;vertical-align:-3px;background:{caret}}}
</style><div class="tab"><span>{html.escape(title)}</span></div><div class="editor">{"".join(rows)}</div>"""
    return page, height


def main(scheme_path, output):
    page, height = render(scheme_path, "retry.rb")
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp, "preview.html")
        source.write_text(page)
        subprocess.run([
            CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--force-device-scale-factor=2", f"--window-size={WIDTH},{height}",
            f"--screenshot={output}", source.as_uri(),
        ], check=True, capture_output=True)
    print(output)


if __name__ == "__main__":
    main(*sys.argv[1:3])
