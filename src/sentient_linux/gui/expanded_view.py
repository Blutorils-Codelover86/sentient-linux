"""
Expanded Sentient Sidekick interface for Linux.
Faithfully ports the upstream Sidekick experience from macOS:
- HomeView.swift topBar (wordmark, proactive dock, nav items)
- SidekickTranscript.swift (empty state hero, user bubbles, assistant markdown)
- SidekickComposer.swift (rounded glass capsule, 36x36 circular send button with conic halo)
- SidekickWorkDisclosure.swift (step disclosure card, live status)
"""

from __future__ import annotations
import threading
import time
from typing import Callable, List, Optional

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gtk, GLib

from sentient_linux.core.coordinator import CommandCoordinator
from sentient_linux.gui.mascot import LivingMascot, MascotState, SidekickMark
from sentient_linux.gui.theme import THEME


class ExpandedView(Gtk.Box):
    """
    Main expanded interaction surface for Sentient Sidekick on Linux.
    Direct translation of upstream HomeView topBar + SidekickTranscript + SidekickComposer.
    """

    def __init__(
        self,
        coordinator: CommandCoordinator,
        on_collapse: Callable[[], None],
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.coordinator = coordinator
        self.on_collapse = on_collapse

        self.add_css_class("sidekick-expanded")
        self.set_size_request(780, 580)

        self._is_running = False
        self._history_records: List[dict] = []
        self._work_card: Optional[Gtk.Box] = None
        self._work_status_label: Optional[Gtk.Label] = None
        self._work_timer_label: Optional[Gtk.Label] = None
        self._task_start_time: float = 0.0

        # 1. Official Top Navigation Bar (HomeView.swift lines 385-430)
        self._build_top_bar()

        # 2. Conversation & Transcript Area (SidekickTranscript.swift)
        self._build_transcript_area()

        # 3. Floating Composer Capsule (SidekickComposer.swift)
        self._build_composer()

    def _build_top_bar(self) -> None:
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        top_bar.add_css_class("sidekick-top-bar")

        # Left 1: SidekickMark (size: 18, illuminated: true)
        mark = SidekickMark(size=18, illuminated=True)
        top_bar.append(mark)

        # Left 2: "Sentient OS" Wordmark (HomeView.swift line 388)
        brand_label = Gtk.Label(label="Sentient OS")
        brand_label.add_css_class("sidekick-brand-title")
        top_bar.append(brand_label)

        # Left 3: Proactive Dock Pill (HomeView.swift lines 432-452)
        proactive_btn = Gtk.Button(label="☵  Proactive")
        proactive_btn.set_tooltip_text("Proactive Intelligence Suggestions")
        proactive_btn.add_css_class("sidekick-proactive-dock")
        top_bar.append(proactive_btn)

        # Spacer pushing navigation to the right
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        top_bar.append(spacer)

        # Right 1: Search Button (HomeView.swift line 393)
        search_btn = Gtk.Button(label="🔍")
        search_btn.set_tooltip_text("Search Conversation (⌘F)")
        search_btn.add_css_class("sidekick-tool-btn")
        top_bar.append(search_btn)

        # Right 2: Clear Chat Button (HomeView.swift line 401)
        clear_btn = Gtk.Button(label="🗑")
        clear_btn.set_tooltip_text("Clear Conversation")
        clear_btn.add_css_class("sidekick-tool-btn")
        clear_btn.connect("clicked", lambda _: self.clear_chat())
        top_bar.append(clear_btn)

        # Right 3: Analysis Status NavItem (HomeView.swift line 410)
        analysis_btn = Gtk.Button(label="●  Analysis")
        analysis_btn.set_tooltip_text("System & Desktop Analysis Status")
        analysis_btn.add_css_class("sidekick-nav-item")
        top_bar.append(analysis_btn)

        # Right 4: Knowledge NavItem (HomeView.swift line 420)
        knowledge_btn = Gtk.Button(label="📚 Knowledge")
        knowledge_btn.set_tooltip_text("Knowledge Vault")
        knowledge_btn.add_css_class("sidekick-nav-item")
        top_bar.append(knowledge_btn)

        # Right 5: Settings Button (HomeView.swift line 423)
        settings_btn = Gtk.Button(label="⚙")
        settings_btn.set_tooltip_text("Settings (⌘,)")
        settings_btn.add_css_class("sidekick-tool-btn")
        top_bar.append(settings_btn)

        # Right 6: Collapse Button (⌄ down chevron)
        collapse_btn = Gtk.Button(label="⌄")
        collapse_btn.set_tooltip_text("Collapse to Bezel (Esc)")
        collapse_btn.add_css_class("sidekick-tool-btn")
        collapse_btn.connect("clicked", lambda _: self.on_collapse())
        top_bar.append(collapse_btn)

        self.append(top_bar)

    def _build_transcript_area() -> None:
        pass

    def _build_transcript_area(self) -> None:
        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_vexpand(True)
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroller.add_css_class("sidekick-transcript")

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.content_box.set_valign(Gtk.Align.START)

        # Upstream Empty State (SidekickTranscript.swift lines 96-103)
        self.empty_state_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.empty_state_box.set_valign(Gtk.Align.CENTER)
        self.empty_state_box.set_vexpand(True)
        self.empty_state_box.set_margin_top(80)
        self.empty_state_box.set_margin_bottom(80)

        # SidekickMark(size: 36, illuminated: true)
        mark = SidekickMark(size=36, illuminated=True)
        mark.set_halign(Gtk.Align.CENTER)
        self.empty_state_box.append(mark)

        # Title: "A little help. A lot more possible."
        title = Gtk.Label(label="A little help. A lot more possible.")
        title.add_css_class("sidekick-empty-title")
        title.set_halign(Gtk.Align.CENTER)
        self.empty_state_box.append(title)

        # Subtitle: "Ask a question, follow a thought, or hand something over."
        subtitle = Gtk.Label(label="Ask a question, follow a thought, or hand something over.")
        subtitle.add_css_class("sidekick-empty-subtitle")
        subtitle.set_halign(Gtk.Align.CENTER)
        self.empty_state_box.append(subtitle)

        self.content_box.append(self.empty_state_box)
        self.scroller.set_child(self.content_box)
        self.append(self.scroller)

    def _build_composer(self) -> None:
        # Capsule container matching SidekickComposer.swift
        self.composer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.composer_box.add_css_class("sidekick-composer")

        # Chat Entry
        self.chat_entry = Gtk.Entry()
        self.chat_entry.set_placeholder_text("Ask Sidekick…")
        self.chat_entry.set_hexpand(True)
        self.chat_entry.add_css_class("sidekick-entry")
        self.chat_entry.connect("activate", self._on_submit_prompt)
        self.chat_entry.connect("changed", self._on_entry_changed)
        self.composer_box.append(self.chat_entry)

        # 36x36 Circular Send / Stop Button (SidekickComposer.swift lines 86-110)
        self.send_button = Gtk.Button(label="↑")
        self.send_button.set_tooltip_text("Send (Return)")
        self.send_button.add_css_class("sidekick-send-btn-disabled")
        self.send_button.connect("clicked", self._on_send_clicked)
        self.composer_box.append(self.send_button)

        self.append(self.composer_box)

    def _on_entry_changed(self, entry: Gtk.Entry) -> None:
        """Update send button style reactively based on text content."""
        if self._is_running:
            return
        text = entry.get_text().strip()
        if text:
            self.send_button.remove_css_class("sidekick-send-btn-disabled")
            self.send_button.add_css_class("sidekick-send-btn-active")
            self.send_button.set_label("↑")
        else:
            self.send_button.remove_css_class("sidekick-send-btn-active")
            self.send_button.add_css_class("sidekick-send-btn-disabled")
            self.send_button.set_label("↑")

    def _on_send_clicked(self, _btn: Gtk.Button) -> None:
        if self._is_running:
            self._on_stop_clicked()
        else:
            self._on_submit_prompt(self.chat_entry)

    def _on_stop_clicked(self) -> None:
        """Emergency stop action."""
        self.coordinator.stop("User clicked stop in Sidekick composer")
        self._finish_running(success=False, message="Task cancelled by user.")

    def _on_submit_prompt(self, entry: Gtk.Entry) -> None:
        prompt = entry.get_text().strip()
        if not prompt or self._is_running:
            return

        entry.set_text("")
        self._is_running = True

        # Switch send button to running stop button
        self.send_button.remove_css_class("sidekick-send-btn-active")
        self.send_button.remove_css_class("sidekick-send-btn-disabled")
        self.send_button.add_css_class("sidekick-stop-btn")
        self.send_button.set_label("■")
        self.send_button.set_tooltip_text("Stop")

        # Hide empty state if present
        if self.empty_state_box.get_parent() == self.content_box:
            self.content_box.remove(self.empty_state_box)

        # 1. Append User Message Bubble (SidekickMessageRow: user bubble)
        user_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        user_row.set_halign(Gtk.Align.END)
        user_label = Gtk.Label(label=prompt)
        user_label.set_wrap(True)
        user_label.set_xalign(0.0)
        user_label.add_css_class("sidekick-user-bubble")
        user_row.append(user_label)
        self.content_box.append(user_row)

        # 2. Add Work Disclosure Card (SidekickWorkDisclosure)
        self._add_work_disclosure("Thinking…")

        # Scroll to bottom
        self._scroll_to_bottom()

        # Run task asynchronously
        threading.Thread(target=self._execute_prompt, args=(prompt,), daemon=True).start()

    def _add_work_disclosure(self, initial_status: str) -> None:
        """Add live work disclosure step card matching upstream."""
        self._task_start_time = time.perf_counter()
        if self._work_card and self._work_card.get_parent() == self.content_box:
            self.content_box.remove(self._work_card)

        self._work_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._work_card.add_css_class("sidekick-work-disclosure")
        self._work_card.set_hexpand(True)

        spin_icon = Gtk.Label(label="◌")
        spin_icon.add_css_class("status-dot-amber")
        self._work_card.append(spin_icon)

        self._work_status_label = Gtk.Label(label=initial_status)
        self._work_status_label.set_xalign(0.0)
        self._work_status_label.set_hexpand(True)
        self._work_status_label.add_css_class("sidekick-work-status")
        self._work_card.append(self._work_status_label)

        self._work_timer_label = Gtk.Label(label="0.0s")
        self._work_timer_label.add_css_class("whisper-text")
        self._work_card.append(self._work_timer_label)

        self.content_box.append(self._work_card)

        # Timer update
        GLib.timeout_add(100, self._update_work_timer)

    def _update_work_timer(self) -> bool:
        if not self._is_running:
            return False
        elapsed = time.perf_counter() - self._task_start_time
        if self._work_timer_label:
            self._work_timer_label.set_text(f"{elapsed:.1f}s")
        return True

    def _execute_prompt(self, prompt: str) -> None:
        """Worker thread to run coordinator task or direct inference."""
        try:
            GLib.idle_add(self._update_work_status, "Consulting desktop context & reasoning…")
            res = self.coordinator.run_task(prompt)
            output = res.summary if res else "Response ready."
            GLib.idle_add(self._finish_running, True, output)
        except Exception as err:
            GLib.idle_add(self._finish_running, False, f"Inference error: {err}")

    def _update_work_status(self, status: str) -> None:
        if self._work_status_label:
            self._work_status_label.set_text(status)

    def _finish_running(self, success: bool, message: str) -> None:
        """Complete task and present assistant response."""
        self._is_running = False

        # Reset send button
        self.send_button.remove_css_class("sidekick-stop-btn")
        self._on_entry_changed(self.chat_entry)

        # Update work disclosure to finished
        if self._work_status_label:
            elapsed = time.perf_counter() - self._task_start_time
            self._work_status_label.set_text(f"Completed in {elapsed:.1f}s")

        # Append Assistant Message (SidekickMessageRow: left aligned, transparent)
        assist_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        assist_row.set_halign(Gtk.Align.START)
        assist_label = Gtk.Label(label=message)
        assist_label.set_wrap(True)
        assist_label.set_xalign(0.0)
        assist_label.add_css_class("sidekick-assistant-message")
        assist_row.append(assist_label)
        self.content_box.append(assist_row)

        self._scroll_to_bottom()

    def clear_chat(self) -> None:
        """Clear transcript and restore empty state."""
        while True:
            child = self.content_box.get_first_child()
            if child is None:
                break
            self.content_box.remove(child)

        self._work_card = None
        self._work_status_label = None
        self._work_timer_label = None
        self.content_box.append(self.empty_state_box)

    def _scroll_to_bottom(self) -> None:
        def _do_scroll():
            adj = self.scroller.get_vadjustment()
            adj.set_value(adj.get_upper() - adj.get_page_size())
        GLib.idle_add(_do_scroll)
