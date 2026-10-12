#!/usr/bin/env python3
"""Generate the Cupcake editor color scheme from its palette.

Upstream ships only a VS Code token map, so the whole scheme is derived here
and written over src/Cupcake.xml, along with src/Cupcake.theme.json, which
recolors the Islands Dark UI. Anything not listed falls through to the
Darcula editor scheme and the Islands Dark theme.
"""
import colorsys
import json
import re
import sys
from pathlib import Path

BG, SURFACE, RAISED, INPUT, DEEP = "2b2746", "332e54", "3c3662", "443e70", "221f38"
FG, COMMENT = "ffffff", "8175d2"
PURPLE, PINK, MAGENTA = "b254ff", "ff4495", "ff7eff"
YELLOW, CYAN = "ffcb5b", "54edff"
ANSI_GREEN = "8af27a"

NORMAL, BOLD, ITALIC, BOLD_ITALIC = "0", "1", "2", "3"
BOXED, UNDERSCORE, WAVE, STRIKEOUT, BOLD_UNDERSCORE = "0", "1", "2", "3", "4"


def mix(color, amount, base=BG):
    """Blend `color` over `base`; how VS Code's alpha colors render on the editor."""
    a = [int(color[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(base[i:i + 2], 16) for i in (0, 2, 4)]
    return "".join(f"{round(y + (x - y) * amount):02x}" for x, y in zip(a, b))


def brighten(color, amount=0.22):
    return mix(FG, amount, base=color)


def attrs(fg=None, bg=None, font=None, effect_color=None, effect=None, stripe=None):
    out = {}
    if fg is not None:
        out["FOREGROUND"] = fg
    if bg is not None:
        out["BACKGROUND"] = bg
    if font is not None:
        out["FONT_TYPE"] = font
    if stripe is not None:
        out["ERROR_STRIPE_COLOR"] = stripe
    if effect_color is not None:
        out["EFFECT_COLOR"] = effect_color
    if effect is not None:
        out["EFFECT_TYPE"] = effect
    return out


SELECTION = mix(PURPLE, 0.4)
GUIDE = mix(FG, 0.12)
MUTED = mix(FG, 0.3)

ADDED, MODIFIED, DELETED = mix(CYAN, 0.55), mix(PURPLE, 0.6), mix(PINK, 0.6)

COLORS = {
    "CARET_COLOR": FG,
    "CARET_ROW_COLOR": SURFACE,
    "SELECTION_BACKGROUND": SELECTION,
    "SELECTION_BACKGROUND_INACTIVE": mix(PURPLE, 0.25),
    "SELECTION_FOREGROUND": "",
    "CONSOLE_BACKGROUND_KEY": BG,
    "GUTTER_BACKGROUND": BG,
    "LINE_NUMBERS_COLOR": MUTED,
    "LINE_NUMBER_ON_CARET_ROW_COLOR": mix(FG, 0.75),
    "ANNOTATIONS_COLOR": COMMENT,
    "ANNOTATIONS_LAST_COMMIT_COLOR": FG,
    "INDENT_GUIDE": GUIDE,
    "SELECTED_INDENT_GUIDE": MUTED,
    "VISUAL_INDENT_GUIDE": GUIDE,
    "STRING_CONTENT_INDENT_GUIDE": GUIDE,
    "RIGHT_MARGIN_COLOR": RAISED,
    "WHITESPACES": mix(FG, 0.2),
    "TEARLINE_COLOR": RAISED,
    "SELECTED_TEARLINE_COLOR": COMMENT,
    "METHOD_SEPARATORS_COLOR": RAISED,
    "SOFT_WRAP_SIGN_COLOR": COMMENT,
    "FOLDED_TEXT_BORDER_COLOR": INPUT,
    "RECENT_LOCATIONS_SELECTION": SURFACE,
    "GRID_STRIPE_COLOR": SURFACE,
    "LOOKUP_COLOR": SURFACE,
    "DOCUMENTATION_COLOR": SURFACE,
    "NOTIFICATION_BACKGROUND": SURFACE,
    "INFORMATION_HINT": SURFACE,
    "QUESTION_HINT": SURFACE,
    "ERROR_HINT": mix(PINK, 0.3),
    "DOC_COMMENT_GUIDE": GUIDE,
    "DOC_COMMENT_LINK": CYAN,
    "MODIFIED_TAB_ICON": PURPLE,
    "SCROLLBAR_THUMB_COLOR": mix(FG, 0.2),

    "ADDED_LINES_COLOR": ADDED,
    "MODIFIED_LINES_COLOR": MODIFIED,
    "DELETED_LINES_COLOR": DELETED,
    "WHITESPACES_MODIFIED_LINES_COLOR": mix(PURPLE, 0.35),
    "IGNORED_ADDED_LINES_BORDER_COLOR": ADDED,
    "IGNORED_MODIFIED_LINES_BORDER_COLOR": MODIFIED,
    "IGNORED_DELETED_LINES_BORDER_COLOR": DELETED,
    "DIFF_SEPARATOR_WAVE": COMMENT,

    "INLINE_REFACTORING_SETTINGS_DEFAULT": SURFACE,
    "INLINE_REFACTORING_SETTINGS_HOVERED": INPUT,
    "INLINE_REFACTORING_SETTINGS_FOCUSED": INPUT,

    "FILESTATUS_ADDED": CYAN,
    "FILESTATUS_COPIED": CYAN,
    "FILESTATUS_MODIFIED": PURPLE,
    "FILESTATUS_DELETED": COMMENT,
    "FILESTATUS_RENAMED": MAGENTA,
    "FILESTATUS_MERGED": MAGENTA,
    "FILESTATUS_SWITCHED": MAGENTA,
    "FILESTATUS_UNKNOWN": PINK,
    "FILESTATUS_OBSOLETE": YELLOW,
    "FILESTATUS_SUPPRESSED": COMMENT,
    "FILESTATUS_HIJACKED": YELLOW,
    "FILESTATUS_NOT_CHANGED": FG,
    "FILESTATUS_NOT_CHANGED_IMMEDIATE": FG,
    "FILESTATUS_NOT_CHANGED_RECURSIVE": FG,
    "FILESTATUS_IDEA_FILESTATUS_IGNORED": COMMENT,
    "FILESTATUS_IDEA_FILESTATUS_DELETED_FROM_FILE_SYSTEM": COMMENT,
    "FILESTATUS_IDEA_FILESTATUS_MERGED_WITH_CONFLICTS": PINK,
    "FILESTATUS_IDEA_FILESTATUS_MERGED_WITH_BOTH_CONFLICTS": PINK,
    "FILESTATUS_IDEA_FILESTATUS_MERGED_WITH_PROPERTY_CONFLICTS": PINK,

    "BLOCK_TERMINAL_BLOCK_BACKGROUND_START": BG,
    "BLOCK_TERMINAL_BLOCK_BACKGROUND_END": BG,
    "BLOCK_TERMINAL_HOVERED_BLOCK_BACKGROUND_START": SURFACE,
    "BLOCK_TERMINAL_HOVERED_BLOCK_BACKGROUND_END": SURFACE,
    "BLOCK_TERMINAL_SELECTED_BLOCK_BACKGROUND": SURFACE,
    "BLOCK_TERMINAL_SELECTED_BLOCK_STROKE_COLOR": INPUT,
    "BLOCK_TERMINAL_INACTIVE_SELECTED_BLOCK_BACKGROUND": SURFACE,
    "BLOCK_TERMINAL_INACTIVE_SELECTED_BLOCK_STROKE_COLOR": RAISED,
    "BLOCK_TERMINAL_ERROR_BLOCK_STROKE_COLOR": PINK,
    "BLOCK_TERMINAL_PROMPT_SEPARATOR_COLOR": RAISED,
    "BLOCK_TERMINAL_GENERATE_COMMAND_CARET_COLOR": FG,
    "BLOCK_TERMINAL_GENERATE_COMMAND_PLACEHOLDER_FOREGROUND": COMMENT,
}

for level, color in enumerate((PURPLE, CYAN, MAGENTA, YELLOW, PINK, COMMENT)):
    COLORS[f"HTML_TAG_TREE_LEVEL{level}"] = color

for index, weight in enumerate((0.55, 0.45, 0.35, 0.25, 0.15), start=1):
    COLORS[f"VCS_ANNOTATIONS_COLOR_{index}"] = mix(PURPLE, weight)


ATTRIBUTES = {}

ATTRIBUTES.update({
    "TEXT": attrs(fg=FG, bg=BG),

    "DEFAULT_KEYWORD": attrs(fg=PURPLE, font=ITALIC),
    "DEFAULT_STRING": attrs(fg=PINK),
    "DEFAULT_NUMBER": attrs(fg=YELLOW),
    "DEFAULT_LINE_COMMENT": attrs(fg=COMMENT, font=ITALIC),
    "DEFAULT_BLOCK_COMMENT": attrs(fg=COMMENT, font=ITALIC),
    "DEFAULT_DOC_COMMENT": attrs(fg=COMMENT, font=ITALIC),
    "DEFAULT_DOC_COMMENT_TAG": attrs(fg=COMMENT, font=BOLD_ITALIC),
    "DEFAULT_DOC_COMMENT_TAG_VALUE": attrs(fg=CYAN, font=ITALIC),
    "DEFAULT_DOC_MARKUP": attrs(fg=MAGENTA),
    "DEFAULT_CONSTANT": attrs(fg=MAGENTA, font=ITALIC),
    "DEFAULT_PREDEFINED_SYMBOL": attrs(fg=PURPLE, font=ITALIC),
    "DEFAULT_IDENTIFIER": attrs(fg=MAGENTA),
    "DEFAULT_LOCAL_VARIABLE": attrs(fg=MAGENTA),
    "DEFAULT_PARAMETER": attrs(fg=MAGENTA),
    "DEFAULT_GLOBAL_VARIABLE": attrs(fg=MAGENTA, font=ITALIC),
    "DEFAULT_INSTANCE_FIELD": attrs(fg=MAGENTA),
    "DEFAULT_STATIC_FIELD": attrs(fg=MAGENTA, font=ITALIC),
    "DEFAULT_FUNCTION_CALL": attrs(fg=YELLOW),
    "DEFAULT_INSTANCE_METHOD": attrs(fg=YELLOW),
    "DEFAULT_STATIC_METHOD": attrs(fg=YELLOW, font=ITALIC),
    "DEFAULT_FUNCTION_DECLARATION": attrs(fg=CYAN),
    "DEFAULT_CLASS_NAME": attrs(fg=CYAN),
    "DEFAULT_CLASS_REFERENCE": attrs(fg=CYAN),
    "DEFAULT_INTERFACE_NAME": attrs(fg=CYAN, font=ITALIC),
    "DEFAULT_LABEL": attrs(fg=FG),
    "DEFAULT_METADATA": attrs(fg=YELLOW, font=ITALIC),
    "DEFAULT_ATTRIBUTE": attrs(fg=YELLOW, font=ITALIC),
    "DEFAULT_TAG": attrs(fg=MAGENTA),
    "DEFAULT_ENTITY": attrs(fg=PURPLE),
    "DEFAULT_OPERATION_SIGN": attrs(fg=FG),
    "DEFAULT_BRACES": attrs(fg=FG),
    "DEFAULT_BRACKETS": attrs(fg=FG),
    "DEFAULT_PARENTHS": attrs(fg=FG),
    "DEFAULT_DOT": attrs(fg=FG),
    "DEFAULT_COMMA": attrs(fg=FG),
    "DEFAULT_SEMICOLON": attrs(fg=FG),
    "DEFAULT_VALID_STRING_ESCAPE": attrs(fg=PURPLE),
    "DEFAULT_INVALID_STRING_ESCAPE": attrs(fg=PINK, effect_color=PINK, effect=WAVE),
    "DEFAULT_REASSIGNED_LOCAL_VARIABLE": attrs(effect_color=COMMENT, effect=UNDERSCORE),
    "DEFAULT_REASSIGNED_PARAMETER": attrs(effect_color=COMMENT, effect=UNDERSCORE),
    "DEFAULT_HIGHLIGHTED_REFERENCE": attrs(effect_color=CYAN, effect=UNDERSCORE),
    "DEFAULT_TEMPLATE_LANGUAGE_COLOR": attrs(bg=mix(FG, 0.04)),
    "INJECTED_LANGUAGE_FRAGMENT": attrs(bg=mix(FG, 0.04)),
})

ATTRIBUTES.update({
    "SEARCH_RESULT_ATTRIBUTES": attrs(bg=mix(YELLOW, 0.35), stripe=YELLOW),
    "WRITE_SEARCH_RESULT_ATTRIBUTES": attrs(bg=mix(PINK, 0.35), stripe=PINK),
    "TEXT_SEARCH_RESULT_ATTRIBUTES": attrs(bg=mix(YELLOW, 0.45), stripe=YELLOW),
    "IDENTIFIER_UNDER_CARET_ATTRIBUTES": attrs(bg=INPUT, stripe=COMMENT),
    "WRITE_IDENTIFIER_UNDER_CARET_ATTRIBUTES": attrs(bg=mix(PINK, 0.25), stripe=PINK),
    "MATCHED_BRACE_ATTRIBUTES": attrs(fg=CYAN, bg=INPUT, font=BOLD),
    "UNMATCHED_BRACE_ATTRIBUTES": attrs(bg=mix(PINK, 0.3)),
    "FOLDED_TEXT_ATTRIBUTES": attrs(fg=COMMENT, bg=SURFACE),
    "HYPERLINK_ATTRIBUTES": attrs(fg=CYAN, effect_color=CYAN, effect=UNDERSCORE),
    "FOLLOWED_HYPERLINK_ATTRIBUTES": attrs(fg=PURPLE, effect_color=PURPLE, effect=UNDERSCORE),
    "INACTIVE_HYPERLINK_ATTRIBUTES": attrs(fg=COMMENT, effect_color=COMMENT, effect=UNDERSCORE),
    "CTRL_CLICKABLE": attrs(fg=CYAN, effect_color=CYAN, effect=UNDERSCORE),
    "TODO_DEFAULT_ATTRIBUTES": attrs(fg=CYAN, font=BOLD_ITALIC, stripe=CYAN),
    "BOOKMARKS_ATTRIBUTES": attrs(bg=SURFACE, stripe=PURPLE),
    "LIVE_TEMPLATE_ATTRIBUTES": attrs(effect_color=CYAN, effect=BOXED),
    "LIVE_TEMPLATE_INACTIVE_SEGMENT": attrs(fg=COMMENT),
    "TEMPLATE_VARIABLE_ATTRIBUTES": attrs(fg=MAGENTA, font=BOLD),
    "BLINKING_HIGHLIGHTS_ATTRIBUTES": attrs(bg=mix(YELLOW, 0.45)),
    "REGEXP_MATCHED_GROUPS": attrs(bg=SURFACE),
    "INFORMATION_ATTRIBUTES": attrs(bg=SURFACE),
    "DOCUMENTATION_CODE": attrs(fg=FG, bg=RAISED),
    "DOC_CODE_INLINE": attrs(fg=FG, bg=RAISED),
    "DOC_CODE_BLOCK": attrs(fg=FG, bg=RAISED),
})

ATTRIBUTES.update({
    "ERRORS_ATTRIBUTES": attrs(effect_color=PINK, effect=WAVE, stripe=PINK),
    "WRONG_REFERENCES_ATTRIBUTES": attrs(fg=PINK, stripe=PINK),
    "RUNTIME_ERROR": attrs(effect_color=PINK, effect=WAVE, stripe=PINK),
    "WARNING_ATTRIBUTES": attrs(effect_color=YELLOW, effect=WAVE, stripe=YELLOW),
    "GENERIC_SERVER_ERROR_OR_WARNING": attrs(effect_color=YELLOW, effect=WAVE, stripe=YELLOW),
    "WEAK_WARNING_ATTRIBUTES": attrs(effect_color=COMMENT, effect=WAVE),
    "INFO_ATTRIBUTES": attrs(effect_color=COMMENT, effect=UNDERSCORE),
    "TYPO": attrs(effect_color=COMMENT, effect=WAVE),
    "NOT_USED_ELEMENT_ATTRIBUTES": attrs(fg=COMMENT),
    "DEPRECATED_ATTRIBUTES": attrs(effect_color=FG, effect=STRIKEOUT),
    "MARKED_FOR_REMOVAL_ATTRIBUTES": attrs(effect_color=PINK, effect=STRIKEOUT),
    "DELETED_TEXT_ATTRIBUTES": attrs(fg=COMMENT, effect_color=COMMENT, effect=STRIKEOUT),
})

ATTRIBUTES.update({
    "BREAKPOINT_ATTRIBUTES": attrs(bg=mix(PINK, 0.25), stripe=PINK),
    "EXECUTIONPOINT_ATTRIBUTES": attrs(bg=mix(PURPLE, 0.45), stripe=PURPLE),
    "NOT_TOP_FRAME_ATTRIBUTES": attrs(bg=SURFACE),
    "DEBUGGER_INLINED_VALUES": attrs(fg=COMMENT, font=ITALIC),
    "DEBUGGER_INLINED_VALUES_MODIFIED": attrs(fg=YELLOW, font=ITALIC),
    "DEBUGGER_INLINED_VALUES_EXECUTION_LINE": attrs(fg=CYAN, font=ITALIC),
    "DEBUGGER_SMART_STEP_INTO_TARGET": attrs(bg=INPUT),
    "DEBUGGER_SMART_STEP_INTO_SELECTION": attrs(bg=SELECTION),
    "EVALUATED_EXPRESSION_ATTRIBUTES": attrs(bg=SURFACE),
    "EVALUATED_EXPRESSION_EXECUTION_LINE_ATTRIBUTES": attrs(bg=INPUT),
    "INLINE_STACK_FRAMES": attrs(fg=COMMENT, font=ITALIC),
})

ATTRIBUTES.update({
    "INLAY_DEFAULT": attrs(fg=COMMENT, bg=SURFACE),
    "INLAY_TEXT_WITHOUT_BACKGROUND": attrs(fg=COMMENT),
    "INLINE_PARAMETER_HINT": attrs(fg=COMMENT, bg=SURFACE),
    "INLINE_PARAMETER_HINT_CURRENT": attrs(fg=FG, bg=INPUT),
    "INLINE_PARAMETER_HINT_HIGHLIGHTED": attrs(fg=FG, bg=INPUT),
    "INLAY_BUTTON_DEFAULT": attrs(fg=COMMENT, bg=SURFACE),
    "INLAY_BUTTON_HOVERED": attrs(fg=FG, bg=INPUT),
    "INLAY_BUTTON_FOCUSED": attrs(fg=FG, bg=INPUT),
    "INLAY_BUTTON_HINT": attrs(fg=COMMENT),
    "CODE_VISION_DEFAULT": attrs(fg=COMMENT),
    "CODE_VISION_HOVERED": attrs(fg=CYAN, effect_color=CYAN, effect=UNDERSCORE),
    "CODE_LENS_BORDER_COLOR": attrs(fg=INPUT),
    "INLINE_SUGGESTION": attrs(fg=COMMENT, font=ITALIC),
    "BREADCRUMBS_DEFAULT": attrs(fg=COMMENT),
    "BREADCRUMBS_HOVERED": attrs(fg=FG, bg=SURFACE),
    "BREADCRUMBS_CURRENT": attrs(fg=FG, bg=INPUT),
    "BREADCRUMBS_INACTIVE": attrs(fg=COMMENT),
})

ANSI = {
    "BLACK": DEEP, "RED": PINK, "GREEN": ANSI_GREEN, "YELLOW": YELLOW,
    "BLUE": PURPLE, "MAGENTA": MAGENTA, "CYAN": CYAN, "WHITE": mix(FG, 0.85),
}
ANSI_BRIGHT = {name: brighten(color) for name, color in ANSI.items()}
ANSI_BRIGHT.update({"BLACK": COMMENT, "WHITE": FG})

for name in ANSI:
    ATTRIBUTES[f"CONSOLE_{name}_OUTPUT"] = attrs(fg=ANSI[name])
    ATTRIBUTES[f"CONSOLE_{name}_BRIGHT_OUTPUT"] = attrs(fg=ANSI_BRIGHT[name])
    ATTRIBUTES[f"BLOCK_TERMINAL_{name}"] = attrs(fg=ANSI[name], bg=ANSI[name], font=NORMAL)
    ATTRIBUTES[f"BLOCK_TERMINAL_{name}_BRIGHT"] = attrs(
        fg=ANSI_BRIGHT[name], bg=ANSI_BRIGHT[name], font=NORMAL
    )

ATTRIBUTES.update({
    "CONSOLE_NORMAL_OUTPUT": attrs(fg=FG),
    "CONSOLE_ERROR_OUTPUT": attrs(fg=PINK),
    "CONSOLE_USER_INPUT": attrs(fg=CYAN, font=ITALIC),
    "CONSOLE_SYSTEM_OUTPUT": attrs(fg=COMMENT),
    "CONSOLE_DARKGRAY_OUTPUT": attrs(fg=COMMENT),
    "CONSOLE_GRAY_OUTPUT": attrs(fg=mix(FG, 0.6)),
    "CONSOLE_RANGE_TO_EXECUTE": attrs(effect_color=PURPLE, effect=BOXED),
    "BLOCK_TERMINAL_COMMAND": attrs(fg=FG, font=BOLD),
    "BLOCK_TERMINAL_SEARCH_ENTRY": attrs(bg=mix(YELLOW, 0.35)),
    "BLOCK_TERMINAL_CURRENT_SEARCH_ENTRY": attrs(bg=mix(PINK, 0.45)),
    "BLOCK_TERMINAL_GENERATE_COMMAND_PROMPT_TEXT": attrs(fg=COMMENT, font=ITALIC),
    "TERMINAL_COMMAND_TO_RUN_USING_IDE": attrs(fg=CYAN, effect_color=CYAN, effect=UNDERSCORE),
    "TERMINAL_CLASS_NAME_LOG_REFERENCE": attrs(fg=CYAN, effect_color=CYAN, effect=UNDERSCORE),
    "LOG_ERROR_OUTPUT": attrs(fg=PINK),
    "LOG_WARNING_OUTPUT": attrs(fg=YELLOW),
    "LOG_INFO_OUTPUT": attrs(fg=FG),
    "LOG_DEBUG_OUTPUT": attrs(fg=COMMENT),
    "LOG_VERBOSE_OUTPUT": attrs(fg=COMMENT),
    "LOG_EXPIRED_ENTRY": attrs(fg=COMMENT, font=ITALIC),
})

ATTRIBUTES.update({
    "DIFF_INSERTED": attrs(bg=mix(CYAN, 0.2), stripe=ADDED),
    "DIFF_MODIFIED": attrs(bg=mix(PURPLE, 0.25), stripe=MODIFIED),
    "DIFF_DELETED": attrs(bg=INPUT, stripe=COMMENT),
    "DIFF_CONFLICT": attrs(bg=mix(PINK, 0.25), stripe=DELETED),
    "DIFF_ABSENT": attrs(bg=SURFACE),
    "DIFF_UNKNOWN": attrs(bg=SURFACE),
    "DIFF_DELETED_FROM_FS": attrs(fg=COMMENT, effect_color=COMMENT, effect=STRIKEOUT),
    "FILESTATUS_ERRORS": attrs(fg=PINK),
})

for i, color in enumerate((PURPLE, CYAN, YELLOW, PINK, MAGENTA)):
    ATTRIBUTES[f"RAINBOW_COLOR{i}"] = attrs(fg=color)

ATTRIBUTES.update({
    "HTML_TAG": attrs(fg=PURPLE),
    "HTML_TAG_NAME": attrs(fg=MAGENTA),
    "HTML_ATTRIBUTE_NAME": attrs(fg=YELLOW, font=ITALIC),
    "HTML_ATTRIBUTE_VALUE": attrs(fg=PINK),
    "HTML_ENTITY_REFERENCE": attrs(fg=PURPLE),
    "XML_TAG": attrs(fg=PURPLE),
    "XML_TAG_NAME": attrs(fg=MAGENTA),
    "XML_ATTRIBUTE_NAME": attrs(fg=YELLOW, font=ITALIC),
    "XML_ATTRIBUTE_VALUE": attrs(fg=PINK),
    "XML_ENTITY_REFERENCE": attrs(fg=PURPLE),
    "CSS.CLASS_NAME": attrs(fg=PURPLE),
    "CSS.IDSELECTOR": attrs(fg=PINK),
    "CSS.TAG_NAME": attrs(fg=CYAN),
    "CSS.PROPERTY_NAME": attrs(fg=MAGENTA),
    "JSON.PROPERTY_KEY": attrs(fg=MAGENTA),
    "JSON.KEYWORD": attrs(fg=PURPLE),
    "YAML_SCALAR_KEY": attrs(fg=MAGENTA),
    "PROPERTIES.KEY": attrs(fg=MAGENTA),
    "INI_SECTION": attrs(fg=PURPLE),
    "MARKDOWN_BOLD": attrs(fg=MAGENTA, font=BOLD),
    "MARKDOWN_ITALIC": attrs(fg=MAGENTA, font=ITALIC),
    "MARKDOWN_BOLD_ITALIC": attrs(fg=MAGENTA, font=BOLD_ITALIC),
    "MARKDOWN_LINK_TEXT": attrs(fg=MAGENTA),
    "MARKDOWN_LIST_ITEM": attrs(fg=PURPLE),
    "RUBY_SYMBOL": attrs(fg=YELLOW),
    "RUBY_CONSTANT": attrs(fg=CYAN),
    "RUBY_CONSTANT_DECLARATION": attrs(fg=CYAN),
})

for level in range(1, 7):
    ATTRIBUTES[f"MARKDOWN_HEADER_LEVEL_{level}"] = attrs(fg=PURPLE, font=BOLD)


ISLANDS_RAMPS = {
    "blue": ("131a28", "182337", "1b283f", "233558", "2a4371", "2e4d89", "2f5eb9", "3871e1",
             "538af9", "71a1fe", "92b7ff", "a7c5ff", "bdd3ff", "d0dffe", "e3ebfe", "f7f8ff"),
    "red": ("291416", "371b1c", "3f1e21", "56272b", "6d3136", "80383e", "a4414a", "c54e58",
            "e4656e", "f57e84", "ff9b9f", "ffb0b2", "ffc4c5", "ffd6d6", "ffe5e5", "fff6f5"),
    "yellow": ("201810", "2c2115", "322517", "44321d", "583e21", "694820", "875817", "a56906",
               "c28013", "d59637", "e4ad5f", "ecbc7b", "f4cd9a", "fadbb3", "fde7c9", "fff6e9"),
    "green": ("111c15", "16261c", "192c20", "203b2a", "274b34", "29583c", "2a6e47", "338555",
              "4e9d6c", "6db083", "8ec39d", "a3cfae", "bbdbc2", "cde5d1", "e2efe2", "f5faf3"),
    "teal": ("111c1b", "152624", "182b2a", "1e3a38", "244a46", "285653", "2a6c67", "31827b",
             "4b9b93", "6aaea6", "8cc1ba", "a2cdc7", "b9d9d4", "cde4e0", "e1eeec", "f5f9f8"),
}

RAMP_HUES = {"blue": PURPLE, "red": PINK, "yellow": YELLOW, "green": ANSI_GREEN, "teal": CYAN}

FRAME = DEEP

PROJECT_GRADIENTS = {
    "g1-amber": YELLOW, "g2-rust": PINK, "g3-olive": ANSI_GREEN,
    "g4-sky": CYAN, "g5-cobalt": PURPLE, "g6-plum": MAGENTA,
    "g7-violet": COMMENT, "g8-ocean": mix(CYAN, 0.5, base=ANSI_GREEN), "g9-grass": ANSI_GREEN,
}


def hex_or_reference(value):
    return f"#{value}" if re.fullmatch(r"[0-9a-f]{6}([0-9a-f]{2})?", value) else value


def rgb(color):
    return [int(color[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def with_hue(color, source):
    """Keep the lightness and saturation of `color`, take the hue of `source`."""
    _, lightness, saturation = colorsys.rgb_to_hls(*rgb(color))
    hue, _, _ = colorsys.rgb_to_hls(*rgb(source))
    return "".join(f"{round(c * 255):02x}" for c in colorsys.hls_to_rgb(hue, lightness, saturation))


def ui_colors():
    grays = [BG, mix(SURFACE, 0.5), SURFACE, RAISED, INPUT]
    grays += [mix(FG, t, base=INPUT) for t in (0.1, 0.2, 0.3, 0.42, 0.54, 0.66, 0.78, 0.86, 0.93, 1.0)]
    named = {f"gray-{(i + 1) * 10}": color for i, color in enumerate(grays)}

    for family, ramp in ISLANDS_RAMPS.items():
        for i, color in enumerate(ramp):
            named[f"{family}-{(i + 1) * 10}"] = with_hue(color, RAMP_HUES[family])

    named.update({
        "transparent": f"{BG}00",
        "editor-text": FG,
        "text-link": "blue-110",
        "main-window-bg": FRAME,
        "main-window-bg-alt": mix(FRAME, 0.5, base=SURFACE),
        "search-match-bg": mix(YELLOW, 0.6),
        "tab-file-color-mask-bg": f"{BG}80",
        "grad-hor-left": f"{BG}33",
        "grad-hor-right": f"{BG}4d",
        "grad-ver-top": f"{BG}1a",
        "grad-ver-bottom": f"{BG}80",
    })

    for group, accent in PROJECT_GRADIENTS.items():
        glow = mix(accent, 0.4, base=FRAME)
        named.update({
            f"grad-{group}-a1": f"{glow}ff",
            f"grad-{group}-a1-transparent": f"{glow}00",
            f"grad-{group}-a1-secondary": mix(accent, 0.1, base=FRAME),
            f"grad-{group}-a2": mix(accent, 0.14, base=FRAME),
            f"grad-{group}-bg": mix(accent, 0.07, base=FRAME),
        })

    return {key: hex_or_reference(value) for key, value in named.items()}


UI = {
    "MainWindow.Tab.background": mix("000000", 0.3, base=FRAME),
    "Editor.ToolTip.selectionBackground": INPUT,
    "List.Tag.background": RAISED,
    "List.Tag.foreground": mix(FG, 0.54, base=INPUT),
    "Debugger.Variables.valueForeground": PINK,
    "Debugger.Variables.changedValueForeground": YELLOW,
    "Debugger.Variables.modifyingValueForeground": YELLOW,
    "Debugger.Variables.typeForeground": COMMENT,
    "Debugger.Variables.collectingDataForeground": COMMENT,
    "Debugger.Variables.evaluatingExpressionForeground": COMMENT,
    "VersionControl.Log.Commit.currentBranchBackground": mix(PURPLE, 0.12),
    "VersionControl.FileHistory.Commit.selectedBranchBackground": mix(PURPLE, 0.12),
    "VersionControl.GitLog.headIconColor": YELLOW,
    "VersionControl.GitLog.localBranchIconColor": CYAN,
    "VersionControl.GitLog.remoteBranchIconColor": PURPLE,
    "VersionControl.MarkerPopup.borderColor": INPUT,
    "DragAndDrop.rowBackground": f"{PURPLE}26",
    "ToolWindow.DragAndDrop.areaBackground": f"{PURPLE}4d",
    "ToolWindow.Button.DragAndDrop.buttonDropBackground": f"{PURPLE}80",
    "MemoryIndicator.usedBackground": mix(PURPLE, 0.4),
    "ScrollBar.thumbColor": f"{COMMENT}59",
    "ScrollBar.hoverThumbColor": f"{COMMENT}8c",
    "ScrollBar.Transparent.thumbColor": f"{COMMENT}59",
    "ScrollBar.Transparent.hoverThumbColor": f"{COMMENT}8c",
    "Slider.buttonColor": mix(FG, 0.66, base=INPUT),
    "Slider.buttonBorderColor": BG,
    "Slider.trackColor": INPUT,
    "FileColor.Yellow": mix(YELLOW, 0.12),
    "FileColor.Green": mix(ANSI_GREEN, 0.12),
    "FileColor.Orange": mix(mix(YELLOW, 0.5, base=PINK), 0.12),
    "FileColor.Violet": mix(PURPLE, 0.15),
    "FileColor.Blue": mix(CYAN, 0.12),
    "FileColor.Rose": mix(PINK, 0.15),
    "FileColor.Gray": RAISED,
}


def render_theme():
    theme = {
        "name": "Cupcake",
        "dark": True,
        "author": "Dmitry Vorotilin",
        "parentTheme": "Islands Dark",
        "editorScheme": "/Cupcake.xml",
        "colors": ui_colors(),
        "ui": {key: hex_or_reference(value) for key, value in UI.items()},
    }
    return json.dumps(theme, indent=2) + "\n"


def render_attribute(name, values):
    lines = [f'    <option name="{name}">', "      <value>"]
    lines += [f'        <option name="{key}" value="{value}" />' for key, value in values.items()]
    lines += ["      </value>", "    </option>"]
    return "\n".join(lines)


def render():
    colors = "\n".join(
        f'    <option name="{key}" value="{COLORS[key]}" />' for key in sorted(COLORS)
    )
    attributes = "\n".join(render_attribute(key, ATTRIBUTES[key]) for key in sorted(ATTRIBUTES))
    return (
        '<scheme name="Cupcake" version="142" parent_scheme="Darcula">\n'
        f"  <colors>\n{colors}\n  </colors>\n"
        f"  <attributes>\n{attributes}\n  </attributes>\n"
        "</scheme>\n"
    )


def main(src):
    Path(src, "Cupcake.xml").write_text(render())
    Path(src, "Cupcake.theme.json").write_text(render_theme())
    print(f"colors     {len(COLORS)}")
    print(f"attributes {len(ATTRIBUTES)}")
    print(f"ui colors  {len(ui_colors())}")
    print(f"ui keys    {len(UI)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "src")
