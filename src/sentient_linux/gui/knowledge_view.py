"""
Official Sentient OS Knowledge Vault Port for Linux (GTK4).
Faithful port of upstream KnowledgeView.swift & VaultTree.swift:
- Two-pane split view: moonlit-slate sidebar (folders, pinned Overview, search) and OLED-black reader.
- Hand-rolled editorial Markdown reader with sky-blue [[wikilinks]] navigation and Back trail.
- In-place raw Markdown editor with atomic write and unsaved-edits guard.
- Full local privacy: only touches configured vault directory (~/Sentient OS - Knowledge Base).
"""

from __future__ import annotations
import html
import logging
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Set

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GLib", "2.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Gdk, GLib, Pango

from sentient_linux.knowledge.vault import KnowledgeVault, VaultNode
from sentient_linux.knowledge.storage import KnowledgeStorage
from sentient_linux.gui.markdown_renderer import MarkdownBlockRenderer
from sentient_linux.gui.mascot import LivingMascot, MascotState
from sentient_linux.gui.theme import THEME, GTK_CSS

logger = logging.getLogger("sentient.gui.knowledge_view")


class SentientKnowledgeVaultWindow(Gtk.Window):
    """
    Native GTK4 Knowledge Vault application window.
    Operates independently from the Wayland layer-shell notch.
    """

    DEFAULT_WIDTH = 1060
    DEFAULT_HEIGHT = 680
    MIN_WIDTH = 900
    MIN_HEIGHT = 600

    def __init__(
        self,
        app: Optional[Gtk.Application] = None,
        vault_path: Optional[Path | str] = None,
    ) -> None:
        if app:
            super().__init__(application=app)
        else:
            super().__init__()

        self.custom_vault_path = Path(vault_path).expanduser().resolve() if vault_path else None
        self.vault: Optional[KnowledgeVault] = None
        self.selection: Optional[Path] = None
        self.expanded_folders: Set[Path] = set()
        self.search_query: str = ""

        # Navigation history (back / forward trail for wikilinks)
        self.history: List[Path] = []
        self.history_index: int = -1

        # Current note content: (title, markdown_body)
        self.current_note: Optional[tuple[str, str]] = None

        # Editor state
        self.is_editing: bool = False
        self.saved_text: str = ""
        self.pending_nav_target: Optional[Path] = None

        # Setup Window Properties
        self.set_title("Sentient — Knowledge Vault")
        self.set_default_size(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        self.set_size_request(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.add_css_class("knowledge-window")

        # Load CSS theme
        self._load_css()

        # Build Main View
        self._build_ui()

        # Initial Load
        self.reload_vault()

    def _load_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(GTK_CSS.encode("utf-8"))
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def _build_ui(self) -> None:
        """Build the split-view layout and window chrome."""
        root_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(root_vbox)

        # 1. Top Page Header
        self._build_page_header()
        root_vbox.append(self.header_bar)

        # 2. Main Paned Split View (Sidebar + Reader)
        self.split_pane = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.split_pane.set_position(280)
        self.split_pane.set_wide_handle(True)
        root_vbox.append(self.split_pane)

        # Sidebar (Left)
        self._build_sidebar()
        self.split_pane.set_start_child(self.sidebar_box)

        # Reader Content (Right)
        self._build_reader_pane()
        self.split_pane.set_end_child(self.reader_box)

    # =========================================================================
    # PAGE HEADER
    # =========================================================================

    def _build_page_header(self) -> None:
        """Build top toolbar: Back trail, title, Use with AIs, Edit, Delete, Reveal."""
        self.header_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.header_bar.add_css_class("knowledge-header")

        # Brand Glyph + Title
        logo = LivingMascot(size=18)
        self.header_bar.append(logo)

        brand_lbl = Gtk.Label(label="Knowledge")
        brand_lbl.add_css_class("sidekick-card-title")
        self.header_bar.append(brand_lbl)

        # Back Button (walks wikilink trail)
        self.back_btn = Gtk.Button(label="← Back")
        self.back_btn.add_css_class("knowledge-btn")
        self.back_btn.set_tooltip_text("Previous note (back from wikilink)")
        self.back_btn.set_visible(False)
        self.back_btn.connect("clicked", lambda _: self.request_back())
        self.header_bar.append(self.back_btn)

        # Active note indicator
        self.header_note_lbl = Gtk.Label(label="")
        self.header_note_lbl.add_css_class("whisper-text")
        self.header_note_lbl.set_margin_start(8)
        self.header_bar.append(self.header_note_lbl)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        self.header_bar.append(spacer)

        # "Use with your AIs"
        ai_conn_btn = Gtk.Button(label="🔗 Use with your AIs")
        ai_conn_btn.add_css_class("knowledge-btn")
        ai_conn_btn.set_tooltip_text("Notes are stored 100% locally on this computer.")
        ai_conn_btn.connect("clicked", lambda _: self._show_ai_connections_info())
        self.header_bar.append(ai_conn_btn)

        # Edit / Save Toggle Button
        self.edit_btn = Gtk.Button(label="✏️ Edit")
        self.edit_btn.add_css_class("knowledge-btn")
        self.edit_btn.set_tooltip_text("Edit this note")
        self.edit_btn.set_sensitive(False)
        self.edit_btn.connect("clicked", lambda _: self.toggle_edit_mode())
        self.header_bar.append(self.edit_btn)

        # Move to Trash Button
        self.trash_btn = Gtk.Button(label="🗑️")
        self.trash_btn.add_css_class("knowledge-btn")
        self.trash_btn.set_tooltip_text("Move to Trash")
        self.trash_btn.set_sensitive(False)
        self.trash_btn.connect("clicked", lambda _: self._on_trash_clicked())
        self.header_bar.append(self.trash_btn)

        # Reveal in Files Button
        self.reveal_btn = Gtk.Button(label="📁")
        self.reveal_btn.add_css_class("knowledge-btn")
        self.reveal_btn.set_tooltip_text("Reveal in File Manager")
        self.reveal_btn.set_sensitive(False)
        self.reveal_btn.connect("clicked", lambda _: self._on_reveal_clicked())
        self.header_bar.append(self.reveal_btn)

    # =========================================================================
    # SIDEBAR
    # =========================================================================

    def _build_sidebar(self) -> None:
        """Build moonlit-slate sidebar: header, note count, search, Overview, tree."""
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.sidebar_box.add_css_class("knowledge-sidebar")
        self.sidebar_box.set_size_request(250, -1)

        # Sidebar Header: Title + count + '+' menu
        hdr_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        hdr_box.set_margin_start(16)
        hdr_box.set_margin_end(16)
        hdr_box.set_margin_top(16)
        hdr_box.set_margin_bottom(10)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        sb_title = Gtk.Label(label="Vault Notes")
        sb_title.add_css_class("sidekick-card-subtitle")
        sb_title.set_hexpand(True)
        sb_title.set_xalign(0.0)
        top_row.append(sb_title)

        # New Note '+' button
        new_btn = Gtk.Button(label="+")
        new_btn.add_css_class("notch-icon-btn")
        new_btn.set_tooltip_text("Create new note in vault")
        new_btn.connect("clicked", lambda _: self._prompt_create_note())
        top_row.append(new_btn)
        hdr_box.append(top_row)

        # Note count subtitle
        self.count_lbl = Gtk.Label(label="0 notes")
        self.count_lbl.add_css_class("whisper-text")
        self.count_lbl.set_xalign(0.0)
        hdr_box.append(self.count_lbl)

        # Status line: "Saved locally on this device"
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_box.set_margin_top(4)
        dot = Gtk.Label(label="●")
        dot.add_css_class("status-dot-green")
        status_box.append(dot)
        status_txt = Gtk.Label(label="Saved locally on this device")
        status_txt.add_css_class("whisper-text")
        status_box.append(status_txt)
        hdr_box.append(status_box)

        self.sidebar_box.append(hdr_box)

        # Search Field (Glass card styling)
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_box.add_css_class("knowledge-search-box")
        search_box.set_margin_start(14)
        search_box.set_margin_end(14)
        search_box.set_margin_bottom(10)

        mag_icon = Gtk.Label(label="🔍")
        search_box.append(mag_icon)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Search notes")
        self.search_entry.add_css_class("knowledge-search-entry")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("changed", self._on_search_changed)
        search_box.append(self.search_entry)

        clear_btn = Gtk.Button(label="✕")
        clear_btn.add_css_class("notch-icon-btn")
        clear_btn.connect("clicked", lambda _: self.search_entry.set_text(""))
        search_box.append(clear_btn)

        self.sidebar_box.append(search_box)

        # Scrollable Note Tree List
        self.tree_scroller = Gtk.ScrolledWindow()
        self.tree_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.tree_scroller.set_vexpand(True)

        self.tree_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.tree_box.set_margin_start(10)
        self.tree_box.set_margin_end(10)
        self.tree_box.set_margin_top(6)
        self.tree_box.set_margin_bottom(12)
        self.tree_scroller.set_child(self.tree_box)

        self.sidebar_box.append(self.tree_scroller)

    # =========================================================================
    # READER & EDITOR PANE
    # =========================================================================

    def _build_reader_pane(self) -> None:
        """Build OLED-black reading column and text editor."""
        self.reader_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.reader_box.add_css_class("knowledge-reader")
        self.reader_box.set_hexpand(True)
        self.reader_box.set_vexpand(True)

        # Stack to toggle between (1) Rendered View, (2) Raw Editor, (3) Empty State
        self.reader_stack = Gtk.Stack()
        self.reader_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.reader_stack.set_hexpand(True)
        self.reader_stack.set_vexpand(True)
        self.reader_box.append(self.reader_stack)

        # 1. Rendered Markdown View
        self.render_scroller = Gtk.ScrolledWindow()
        self.render_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.render_scroller.set_hexpand(True)
        self.render_scroller.set_vexpand(True)

        self.render_inner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.render_inner_box.set_margin_start(46)
        self.render_inner_box.set_margin_end(46)
        self.render_inner_box.set_margin_top(24)
        self.render_inner_box.set_margin_bottom(80)
        self.render_inner_box.set_size_request(720, -1)
        self.render_inner_box.set_halign(Gtk.Align.START)
        self.render_scroller.set_child(self.render_inner_box)
        self.reader_stack.add_named(self.render_scroller, "rendered")

        # 2. Raw Markdown Editor View
        self.editor_scroller = Gtk.ScrolledWindow()
        self.editor_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.editor_scroller.set_hexpand(True)
        self.editor_scroller.set_vexpand(True)

        editor_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        editor_inner.set_margin_start(46)
        editor_inner.set_margin_end(46)
        editor_inner.set_margin_top(20)
        editor_inner.set_margin_bottom(20)
        editor_inner.set_size_request(720, -1)
        editor_inner.set_halign(Gtk.Align.START)

        self.editor_filename_lbl = Gtk.Label()
        self.editor_filename_lbl.add_css_class("knowledge-mono-caps")
        self.editor_filename_lbl.set_xalign(0.0)
        editor_inner.append(self.editor_filename_lbl)

        self.editor_text_view = Gtk.TextView()
        self.editor_text_view.add_css_class("knowledge-code-text")
        self.editor_text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.editor_text_view.set_vexpand(True)
        editor_inner.append(self.editor_text_view)

        self.editor_scroller.set_child(editor_inner)
        self.reader_stack.add_named(self.editor_scroller, "editor")

        # 3. Empty State View
        self.empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.empty_box.set_halign(Gtk.Align.CENTER)
        self.empty_box.set_valign(Gtk.Align.CENTER)

        self.empty_mascot = LivingMascot(size=64)
        self.empty_box.append(self.empty_mascot)

        self.empty_title_lbl = Gtk.Label(label="No knowledge base yet")
        self.empty_title_lbl.add_css_class("knowledge-empty-title")
        self.empty_box.append(self.empty_title_lbl)

        self.empty_subtitle_lbl = Gtk.Label(
            label="Your knowledge will appear here after analysis.\nYou can use Sidekick while it is being built."
        )
        self.empty_subtitle_lbl.add_css_class("knowledge-empty-subtitle")
        self.empty_subtitle_lbl.set_justify(Gtk.Justification.CENTER)
        self.empty_box.append(self.empty_subtitle_lbl)

        self.reader_stack.add_named(self.empty_box, "empty")

    # =========================================================================
    # VAULT & NOTE LIFECYCLE
    # =========================================================================

    def reload_vault(self) -> None:
        """Load vault from disk, update tree, and restore current selection."""
        self.vault = KnowledgeVault.load(self.custom_vault_path)

        if not self.vault or (not self.vault.all_notes and not self.vault.readme):
            self.count_lbl.set_text("0 notes")
            self._render_tree()
            self._show_empty_state(
                "No knowledge base yet",
                "Your knowledge will appear here after analysis.\nYou can use Sidekick while it is being built.",
            )
            return

        total_notes = len(self.vault.all_notes)
        self.count_lbl.set_text(f"{total_notes} note{'s' if total_notes != 1 else ''}")

        self._render_tree()

        # If previous selection still exists, re-read it
        if self.selection and (self.selection == self.vault.readme or any(n.path == self.selection for n in self.vault.all_notes)):
            if not self.is_editing:
                self.select_note(self.selection)
            return

        # Otherwise open Overview (README) or first note
        if self.vault.readme:
            self.open_note(self.vault.readme)
        elif self.vault.all_notes:
            self.open_note(self.vault.all_notes[0].path)
        else:
            self._show_empty_state("Select a note", None)

    def _render_tree(self) -> None:
        """Populate sidebar list with pinned Overview, folders, and notes."""
        # Clear existing rows
        while child := self.tree_box.get_first_child():
            self.tree_box.remove(child)

        if not self.vault:
            return

        # If searching, show flat filtered search results
        if self.search_query:
            results = self.vault.search(self.search_query)
            if not results:
                no_matches = Gtk.Label(label="No matches")
                no_matches.add_css_class("whisper-text")
                no_matches.set_xalign(0.0)
                no_matches.set_margin_start(10)
                no_matches.set_margin_top(12)
                self.tree_box.append(no_matches)
                return

            for node in results:
                row = self._create_note_row(node.path, node.name, depth=0)
                self.tree_box.append(row)
            return

        # Pinned Overview (README.md)
        if self.vault.readme:
            overview_row = self._create_overview_row(self.vault.readme)
            self.tree_box.append(overview_row)

        # Folder hierarchy
        for node in self.vault.nodes:
            self._append_node_tree(node, depth=0)

    def _append_node_tree(self, node: VaultNode, depth: int) -> None:
        """Recursively render a folder (with disclosure) or note row."""
        if node.is_folder:
            is_open = node.path in self.expanded_folders
            folder_row = self._create_folder_row(node, depth, is_open)
            self.tree_box.append(folder_row)

            if is_open:
                for child in node.children:
                    self._append_node_tree(child, depth + 1)
        else:
            note_row = self._create_note_row(node.path, node.name, depth)
            self.tree_box.append(note_row)

    def _create_overview_row(self, path: Path) -> Gtk.Widget:
        """Pinned Overview row with brand logo glyph."""
        is_sel = (self.selection == path)
        btn = Gtk.Button()
        btn.add_css_class("knowledge-row")
        if is_sel:
            btn.add_css_class("knowledge-row-selected")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        logo = LivingMascot(size=14)
        box.append(logo)

        lbl = Gtk.Label(label="Overview")
        lbl.set_xalign(0.0)
        lbl.set_hexpand(True)
        box.append(lbl)

        btn.set_child(box)
        btn.connect("clicked", lambda _: self.request_open(path))
        return btn

    def _create_folder_row(self, node: VaultNode, depth: int, is_open: bool) -> Gtk.Widget:
        """Folder disclosure row."""
        btn = Gtk.Button()
        btn.add_css_class("knowledge-row")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_margin_start(depth * 14)

        chevron = Gtk.Label(label="▼" if is_open else "▶")
        chevron.add_css_class("whisper-text")
        box.append(chevron)

        icon = Gtk.Label(label="📁")
        box.append(icon)

        name_lbl = Gtk.Label(label=node.name)
        name_lbl.set_xalign(0.0)
        name_lbl.set_hexpand(True)
        box.append(name_lbl)

        btn.set_child(box)
        btn.connect("clicked", lambda _: self._toggle_folder(node.path))
        return btn

    def _create_note_row(self, path: Path, title: str, depth: int) -> Gtk.Widget:
        """Leaf note row with document icon."""
        is_sel = (self.selection == path)
        btn = Gtk.Button()
        btn.add_css_class("knowledge-row")
        if is_sel:
            btn.add_css_class("knowledge-row-selected")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_margin_start(depth * 14 + 14)

        icon = Gtk.Label(label="📄")
        box.append(icon)

        lbl = Gtk.Label(label=title)
        lbl.set_xalign(0.0)
        lbl.set_hexpand(True)
        box.append(lbl)

        btn.set_child(box)
        btn.connect("clicked", lambda _: self.request_open(path))
        return btn

    def _toggle_folder(self, folder_path: Path) -> None:
        if folder_path in self.expanded_folders:
            self.expanded_folders.remove(folder_path)
        else:
            self.expanded_folders.add(folder_path)
        self._render_tree()

    # =========================================================================
    # NAVIGATION & WIKILINKS
    # =========================================================================

    @property
    def can_go_back(self) -> bool:
        return self.history_index > 0

    def open_note(self, path: Path) -> None:
        """Open a note as a fresh navigation trail (clears back history)."""
        self.history = [path]
        self.history_index = 0
        self.select_note(path)

    def follow_wikilink(self, path: Path) -> None:
        """Follow an internal [[wikilink]] jump (pushes onto back trail)."""
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]

        if not self.history or self.history[-1] != path:
            self.history.append(path)
            self.history_index = len(self.history) - 1

        self.select_note(path)

    def select_note(self, path: Path) -> None:
        """Load and display note content, reveal in folder tree, update toolbar."""
        self.selection = path

        if not self.vault:
            return

        # Reveal in folder tree
        ancestors = self.vault.ancestors(path)
        self.expanded_folders.update(ancestors)
        self._render_tree()

        # Read content
        title, body = self.vault.read(path)
        self.current_note = (title, body)

        # Update Header Chrome
        self.header_note_lbl.set_text(path.name)
        self.back_btn.set_visible(self.can_go_back)
        self.edit_btn.set_sensitive(True)
        self.trash_btn.set_sensitive(path != self.vault.readme)
        self.reveal_btn.set_sensitive(True)

        # Render Content in Reading Pane
        self._render_current_note(path.name, title, body)

    def go_back(self) -> None:
        """Return to previous note along the wikilink trail."""
        if not self.can_go_back:
            return
        self.history_index -= 1
        prev_path = self.history[self.history_index]
        self.select_note(prev_path)

    def _render_current_note(self, filename: str, title: str, body: str) -> None:
        """Render note into the reading column with MarkdownBlockRenderer."""
        # Clear previous widgets
        while child := self.render_inner_box.get_first_child():
            self.render_inner_box.remove(child)

        # 1. Monospace Caps Filename Subtitle
        caps_lbl = Gtk.Label(label=filename)
        caps_lbl.add_css_class("knowledge-mono-caps")
        caps_lbl.set_xalign(0.0)
        caps_lbl.set_margin_bottom(10)
        self.render_inner_box.append(caps_lbl)

        # 2. Promoted H1 Note Title (Serif 30px)
        title_lbl = Gtk.Label(label=title)
        title_lbl.add_css_class("knowledge-title")
        title_lbl.set_xalign(0.0)
        title_lbl.set_wrap(True)
        title_lbl.set_selectable(True)
        title_lbl.set_margin_bottom(20)
        self.render_inner_box.append(title_lbl)

        # 3. Markdown Body Blocks with live [[wikilinks]]
        renderer = MarkdownBlockRenderer(
            markdown=body,
            exists=lambda t: bool(self.vault and self.vault.resolve(t)),
            on_navigate=self._on_wikilink_clicked,
            on_external=self._on_external_link_clicked,
        )
        content_box = renderer.build_widget()
        self.render_inner_box.append(content_box)

        self.reader_stack.set_visible_child_name("rendered")

    def _on_wikilink_clicked(self, target_title: str) -> None:
        """Handle user clicking a resolved [[wikilink]]."""
        if not self.vault:
            return
        target_path = self.vault.resolve(target_title)
        if target_path:
            self.request_follow(target_path)
        else:
            logger.warning(f"Unresolved wikilink clicked: {target_title}")

    def _on_external_link_clicked(self, url: str) -> None:
        """Open external web links via default desktop browser."""
        try:
            subprocess.Popen(["xdg-open", url])
        except Exception as err:
            logger.warning(f"Could not open external link {url}: {err}")

    def _show_empty_state(self, title: str, subtitle: Optional[str]) -> None:
        self.empty_title_lbl.set_text(title)
        if subtitle:
            self.empty_subtitle_lbl.set_text(subtitle)
            self.empty_subtitle_lbl.set_visible(True)
        else:
            self.empty_subtitle_lbl.set_visible(False)
        self.reader_stack.set_visible_child_name("empty")

    # =========================================================================
    # UNSAVED EDITS GUARD & EDITING
    # =========================================================================

    def _is_dirty(self) -> bool:
        if not self.is_editing:
            return False
        buf = self.editor_text_view.get_buffer()
        start, end = buf.get_bounds()
        current_text = buf.get_text(start, end, True)
        return current_text != self.saved_text

    def toggle_edit_mode(self) -> None:
        if self.is_editing:
            self.save_edit()
        else:
            self.begin_edit()

    def begin_edit(self) -> None:
        """Switch to raw Markdown TextEditor."""
        if not self.selection or not self.selection.exists():
            return

        try:
            raw_content = self.selection.read_text(encoding="utf-8")
        except Exception as err:
            raw_content = f"Error reading file: {err}"

        self.saved_text = raw_content
        buf = self.editor_text_view.get_buffer()
        buf.set_text(raw_content)

        self.editor_filename_lbl.set_text(self.selection.name)
        self.is_editing = True
        self.edit_btn.set_label("💾 Save")
        self.edit_btn.add_css_class("knowledge-btn-primary")
        self.reader_stack.set_visible_child_name("editor")
        self.editor_text_view.grab_focus()

    def save_edit(self, completion: Optional[Callable[[], None]] = None) -> None:
        """Atomically commit edited markdown buffer to disk."""
        if not self.is_editing or not self.selection or not self.vault:
            if completion:
                completion()
            return

        buf = self.editor_text_view.get_buffer()
        start, end = buf.get_bounds()
        current_text = buf.get_text(start, end, True)

        try:
            rel_path = self.selection.relative_to(self.vault.root)
            self.vault.storage.write_note(rel_path, current_text, create_backup=True)
            self.saved_text = current_text
            self.is_editing = False
            self.edit_btn.set_label("✏️ Edit")
            self.edit_btn.remove_css_class("knowledge-btn-primary")

            # Re-read and re-render
            self.select_note(self.selection)

            if completion:
                completion()
        except Exception as err:
            logger.error(f"Failed to save note: {err}")

    def exit_edit_discard(self) -> None:
        self.is_editing = False
        self.edit_btn.set_label("✏️ Edit")
        self.edit_btn.remove_css_class("knowledge-btn-primary")
        if self.selection:
            self.select_note(self.selection)

    def request_open(self, target_path: Path) -> None:
        if self._is_dirty():
            self.pending_nav_target = target_path
            self._prompt_unsaved_changes()
        else:
            if self.is_editing:
                self.exit_edit_discard()
            self.open_note(target_path)

    def request_follow(self, target_path: Path) -> None:
        if self._is_dirty():
            self.pending_nav_target = target_path
            self._prompt_unsaved_changes()
        else:
            if self.is_editing:
                self.exit_edit_discard()
            self.follow_wikilink(target_path)

    def request_back(self) -> None:
        if self._is_dirty():
            self._prompt_unsaved_changes(is_back=True)
        else:
            if self.is_editing:
                self.exit_edit_discard()
            self.go_back()

    def _prompt_unsaved_changes(self, is_back: bool = False) -> None:
        """Modal dialog prompting user to Save, Discard, or Cancel."""
        dialog = Gtk.AlertDialog(
            message="You have unsaved edits",
            detail="Save your changes to this note, or discard them?",
            buttons=["Save", "Discard", "Cancel"],
            cancel_button=2,
            default_button=0,
        )

        def on_response(_dialog, result):
            try:
                choice = dialog.choose_finish(result)
                if choice == 0:  # Save
                    self.save_edit(completion=lambda: self._continue_pending_nav(is_back))
                elif choice == 1:  # Discard
                    self.exit_edit_discard()
                    self._continue_pending_nav(is_back)
                else:  # Cancel
                    self.pending_nav_target = None
            except Exception:
                pass

        dialog.choose(self, None, on_response)

    def _continue_pending_nav(self, is_back: bool) -> None:
        if is_back:
            self.go_back()
        elif self.pending_nav_target:
            target = self.pending_nav_target
            self.pending_nav_target = None
            self.follow_wikilink(target)

    # =========================================================================
    # CREATE & TRASH ACTIONS
    # =========================================================================

    def _prompt_create_note(self) -> None:
        """Prompt user for new note name and create it."""
        if not self.vault:
            return

        # Simple input dialog
        win = Gtk.Window(title="New Note")
        win.set_transient_for(self)
        win.set_modal(True)
        win.set_default_size(320, 140)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        win.set_child(box)

        lbl = Gtk.Label(label="Note Name:")
        lbl.set_xalign(0.0)
        box.append(lbl)

        entry = Gtk.Entry()
        entry.set_placeholder_text("Untitled")
        box.append(entry)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda _: win.close())
        btn_box.append(cancel_btn)

        create_btn = Gtk.Button(label="Create")
        create_btn.add_css_class("knowledge-btn-primary")

        def on_create():
            name = entry.get_text().strip() or "Untitled"
            win.close()
            try:
                new_path = self.vault.create_note(dir_path=self.vault.root, name=name)
                self.reload_vault()
                self.open_note(new_path)
                self.begin_edit()
            except Exception as err:
                logger.error(f"Error creating note: {err}")

        create_btn.connect("clicked", lambda _: on_create())
        entry.connect("activate", lambda _: on_create())
        btn_box.append(create_btn)
        box.append(btn_box)

        win.present()
        entry.grab_focus()

    def _on_trash_clicked(self) -> None:
        """Move open note to trash."""
        if not self.selection or not self.vault:
            return
        if self.selection == self.vault.readme:
            return

        to_trash = self.selection
        self.vault.delete_item(to_trash)
        self.reload_vault()

    def _on_reveal_clicked(self) -> None:
        """Reveal file in desktop file manager."""
        if not self.selection:
            return
        try:
            subprocess.Popen(["xdg-open", str(self.selection.parent)])
        except Exception as err:
            logger.warning(f"Failed to reveal in file manager: {err}")

    def _show_ai_connections_info(self) -> None:
        """Show information dialog explaining local privacy and AI access."""
        dialog = Gtk.AlertDialog(
            message="Knowledge Vault Privacy & AI Access",
            detail=(
                "Your notes are stored 100% locally on this computer at:\n"
                f"{self.vault.root if self.vault else '~/Sentient OS - Knowledge Base'}\n\n"
                "• No files are automatically uploaded to any cloud.\n"
                "• Filesystem access is strictly restricted to this vault folder.\n"
                "• AI inference runs locally via your selected local Ollama model,\n"
                "  or strictly via your explicitly authorized provider."
            ),
            buttons=["OK"],
        )
        dialog.show(self)

    def _on_search_changed(self, entry: Gtk.Entry) -> None:
        self.search_query = entry.get_text().strip()
        self._render_tree()
