"""
Hand-rolled editorial Markdown Block Renderer for Sentient Knowledge Vault.
Direct translation of upstream MarkdownView.swift:
- Fenced code blocks and box-drawing tree rows (├── x) render verbatim in monospace.
- Pinned `#`/`##`/`###` headings render in elegant Serif typography (#ffffff).
- Bullet lists ('- ', '* ', '• ') render with subtle muted bullet markers.
- Inline bold (**b**), italic (*i*), code (`code`), and external links.
- [[wikilinks]] are pre-split:
  * Resolved wikilinks render in sky-blue (Theme.knowledgeLink: #6fb6ff) with underline, emitting on_navigate.
  * Unresolved wikilinks render dimmed (#ffffff with alpha="38%") and inert.
"""

from __future__ import annotations
import html
import re
from typing import Callable, List, Optional
from urllib.parse import quote, unquote

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Pango

WIKI_SCHEME = "sentient-wiki:"


class MarkdownBlockRenderer:
    """Renders vault markdown into a responsive GTK4 vertical block hierarchy."""

    def __init__(
        self,
        markdown: str,
        exists: Callable[[str], bool] = lambda _: False,
        on_navigate: Callable[[str], None] = lambda _: None,
        on_external: Callable[[str], None] = lambda _: None,
    ) -> None:
        self.markdown = markdown
        self.exists = exists
        self.on_navigate = on_navigate
        self.on_external = on_external

    def build_widget(self) -> Gtk.Box:
        """Construct GTK4 Box containing all parsed blocks."""
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        container.add_css_class("knowledge-markdown-container")

        blocks = self._parse_blocks(self.markdown)
        for block_type, data in blocks:
            if block_type == "code":
                container.append(self._build_code_block(data))
            elif block_type == "line":
                container.append(self._build_line_block(data))

        return container

    def _parse_blocks(self, text: str) -> List[tuple[str, any]]:
        """Group markdown into verbatim code/tree blocks and single line blocks."""
        lines = text.split("\n")
        out: List[tuple[str, any]] = []
        i = 0
        n = len(lines)

        while i < n:
            raw_line = lines[i]
            trimmed = raw_line.strip()

            # 1. Fenced Code Block (``` ... ```)
            if trimmed.startswith("```"):
                body: List[str] = []
                i += 1
                while i < n and not lines[i].strip().startswith("```"):
                    body.append(lines[i])
                    i += 1
                i += 1  # Skip closing fence
                if body:
                    out.append(("code", body))

            # 2. Box-Drawing Tree Rows (├── x, └── y, │) outside fences
            elif self._is_tree_row(trimmed):
                body: List[str] = []
                while i < n and self._is_tree_row(lines[i].strip()):
                    body.append(lines[i])
                    i += 1
                out.append(("code", body))

            # 3. Everyday single line block
            else:
                out.append(("line", trimmed))
                i += 1

        return out

    @staticmethod
    def _is_tree_row(trimmed: str) -> bool:
        """Check if line starts with box-drawing characters (vault tree map parity)."""
        if not trimmed:
            return False
        return trimmed[0] in "├└│"

    def _build_code_block(self, lines: List[str]) -> Gtk.Widget:
        """
        Fenced block verbatim: monospace (the machine's voice), whitespace intact,
        neutral ink on a whisper of a panel.
        """
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add_css_class("knowledge-code-block")
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        text_content = "\n".join(lines)
        lbl = Gtk.Label(label=text_content)
        lbl.add_css_class("knowledge-code-text")
        lbl.set_xalign(0.0)
        lbl.set_wrap(False)
        lbl.set_selectable(True)
        box.append(lbl)
        return box

    def _build_line_block(self, s: str) -> Gtk.Widget:
        """Render one line of markdown (or blank spacer / horizontal rule)."""
        # Blank line = vertical spacer (height 9px)
        if not s:
            spacer = Gtk.Box()
            spacer.set_size_request(-1, 9)
            return spacer

        # Horizontal rule (--- / *** / ___)
        if s in ("---", "***", "___"):
            sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            sep.add_css_class("knowledge-divider")
            sep.set_margin_top(12)
            sep.set_margin_bottom(12)
            return sep

        # H3: ### Title (15.5pt, Semibold, Serif)
        if s.startswith("### "):
            text = s[4:].strip()
            lbl = self._create_label(self._inline(text))
            lbl.add_css_class("knowledge-h3")
            lbl.set_margin_top(14)
            lbl.set_margin_bottom(3)
            return lbl

        # H2: ## Section (20pt, Serif, White)
        if s.startswith("## "):
            text = s[3:].strip()
            lbl = self._create_label(self._inline(text))
            lbl.add_css_class("knowledge-h2")
            lbl.set_margin_top(20)
            lbl.set_margin_bottom(4)
            return lbl

        # H1: # Title (25pt, Serif, White)
        if s.startswith("# "):
            text = s[2:].strip()
            lbl = self._create_label(self._inline(text))
            lbl.add_css_class("knowledge-h1")
            lbl.set_margin_top(12)
            lbl.set_margin_bottom(6)
            return lbl

        # Bullet list: "- ", "* ", "• "
        bullet_text = self._bullet_text(s)
        if bullet_text is not None:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.set_margin_top(3)
            row.set_margin_bottom(3)

            marker = Gtk.Label(label="•")
            marker.add_css_class("knowledge-bullet-marker")
            marker.set_valign(Gtk.Align.START)
            row.append(marker)

            content_lbl = self._create_label(self._inline(bullet_text))
            content_lbl.add_css_class("knowledge-body-text")
            content_lbl.set_hexpand(True)
            row.append(content_lbl)
            return row

        # Normal paragraph text (14.5pt, 0.82 opacity)
        lbl = self._create_label(self._inline(s))
        lbl.add_css_class("knowledge-body-text")
        lbl.set_margin_top(4)
        lbl.set_margin_bottom(4)
        return lbl

    @staticmethod
    def _bullet_text(s: str) -> Optional[str]:
        for prefix in ("- ", "* ", "• "):
            if s.startswith(prefix):
                return s[len(prefix):]
        return None

    def _inline(self, text: str) -> str:
        """
        Parse inline markdown and [[wikilinks]].
        Converts to Pango markup safely.
        """
        # Split on [[wikilink]] tokens
        out = ""
        pattern = re.compile(r"\[\[(.*?)\]\]")
        last_idx = 0

        for match in pattern.finditer(text):
            start, end = match.span()
            before = text[last_idx:start]
            if before:
                out += self._format_standard_markdown(before)

            inner = match.group(1)
            out += self._format_wikilink(inner)
            last_idx = end

        if last_idx < len(text):
            out += self._format_standard_markdown(text[last_idx:])

        return out

    def _format_wikilink(self, inner: str) -> str:
        """
        Format [[Title]] or [[Title|alias]].
        Resolved -> sky-blue link (#6fb6ff) with underline.
        Unresolved -> dimmed text (#ffffff with alpha="38%").
        """
        if "|" in inner:
            parts = inner.split("|", 1)
            target = parts[0].strip()
            label = parts[1].strip() or target
        else:
            target = inner.strip()
            label = target

        escaped_label = html.escape(label)

        if self.exists(target):
            # Target resolves: make it a clickable sky-blue link
            uri = f"{WIKI_SCHEME}{quote(target)}"
            return f'<a href="{uri}"><span color="#6fb6ff"><u>{escaped_label}</u></span></a>'
        else:
            # Unresolved: dimmed neutral and inert
            return f'<span color="#ffffff" alpha="38%">{escaped_label}</span>'

    @staticmethod
    def _format_standard_markdown(s: str) -> str:
        """Convert **bold**, *italic*, `code`, and [text](url) to Pango markup."""
        # 1. Escape HTML entities
        escaped = html.escape(s)

        # 2. Code `code` -> <tt><span background="#222228"> code </span></tt>
        escaped = re.sub(
            r"`([^`]+)`",
            r'<tt><span background="#222228"> \1 </span></tt>',
            escaped,
        )

        # 3. Bold **bold** -> <b>bold</b>
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)

        # 4. Italic *italic* -> <i>italic</i>
        escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", escaped)

        # 5. External links [text](url)
        escaped = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            r'<a href="\2"><span color="#6fb6ff"><u>\1</u></span></a>',
            escaped,
        )

        return escaped

    def _create_label(self, markup_text: str) -> Gtk.Label:
        """Create a Gtk.Label with Pango markup and link routing."""
        lbl = Gtk.Label()
        lbl.set_use_markup(True)
        lbl.set_markup(markup_text)
        lbl.set_wrap(True)
        lbl.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        lbl.set_xalign(0.0)
        lbl.set_selectable(True)
        lbl.connect("activate-link", self._on_activate_link)
        return lbl

    def _on_activate_link(self, _label: Gtk.Label, uri: str) -> bool:
        """Route clicked links to either on_navigate (wikilinks) or on_external."""
        if uri.startswith(WIKI_SCHEME):
            target = unquote(uri[len(WIKI_SCHEME):])
            self.on_navigate(target)
            return True
        else:
            self.on_external(uri)
            return True
