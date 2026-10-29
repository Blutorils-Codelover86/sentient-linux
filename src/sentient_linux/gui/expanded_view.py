"""
Expanded Sentient Sidekick interface for Linux.
Faithfully ports the upstream Sidekick experience from macOS:
- Sidekick Card Header (uploaded_media_1_1793269445180.png / Hero.jpg parity):
  Dark card, yellow-orange cursor icon, 'Sidekick / Hand off a task', and GlowProgressBar.
- Context Bar (Hyprland active window / workspace context).
- SidekickTranscript.swift (empty state hero, user bubbles, assistant markdown).
- SidekickWorkDisclosure.swift (step disclosure card, live tool narration).
- SidekickComposer.swift (rounded glass capsule, 36x36 circular send/stop button).
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
from sentient_linux.gui.mascot import LivingMascot, MascotState
from sentient_linux.gui.widgets import SidekickCursorIcon, GlowProgressBarWidget
from sentient_linux.gui.theme import THEME


class ExpandedView(Gtk.Box):
    """
    Main expanded interaction surface for Sentient Sidekick on Linux.
    Direct translation of upstream Sidekick card + SidekickTranscript + SidekickComposer.
    """

    def __init__(
        self,
        coordinator: CommandCoordinator,
        on_collapse: Callable[[], None],
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
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

        # 1. Official Sidekick Header Card (Hero / MCP visual parity)
        self._build_sidekick_card()

        # 2. Context Pill Row
        self._build_context_row()

        # 3. Conversation & Transcript Area (SidekickTranscript.swift)
        self._build_transcript_area()

        # 4. Floating Composer Capsule (SidekickComposer.swift)
        self._build_composer()

    def _build_sidekick_card(self) -> None:
        """
        Build the official Sidekick card matching uploaded_media_1_1793269445180.png:
        - Dark glass card with rounded corners.
        - Left: Squircle icon with bright yellow-orange pointer cursor.
        - Title: 'Sidekick', Subtitle: 'Hand off a task'.
        - Right: Model badge (e.g. qwen2.5-coder:3b), clear chat, collapse chevron.
        - Bottom: Signature GlowProgressBar accent line.
        """
        card_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card_container.add_css_class("sidekick-header-card")

        card_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card_content.add_css_class("sidekick-header-inner")

        # Left: Squircle with glowing cursor icon
        cursor_icon = SidekickCursorIcon(size=38)
        card_content.append(cursor_icon)

        # Title and Subtitle Column
        title_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_col.set_valign(Gtk.Align.CENTER)

        title_label = Gtk.Label(label="Sidekick")
        title_label.add_css_class("sidekick-card-title")
        title_label.set_xalign(0.0)
        title_col.append(title_label)

        sub_label = Gtk.Label(label="Hand off a task")
        sub_label.add_css_class("sidekick-card-subtitle")
        sub_label.set_xalign(0.0)
        title_col.append(sub_label)

        card_content.append(title_col)

        # Spacer pushing controls to the right
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        card_content.append(spacer)

        # Active Model Pill Button with Popover Switcher
        self.model_btn = Gtk.Button()
        self.model_btn.add_css_class("sidekick-model-btn")
        self.model_btn.set_tooltip_text("Click to switch AI model")

        model_pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        model_pill.add_css_class("sidekick-model-pill")
        dot = Gtk.Label(label="●")
        dot.add_css_class("status-dot-green")
        model_pill.append(dot)

        active_name = getattr(self.coordinator, "active_model", "qwen2.5-coder:3b")
        self.model_lbl = Gtk.Label(label=active_name)
        self.model_lbl.add_css_class("whisper-text")
        model_pill.append(self.model_lbl)

        chevron = Gtk.Label(label="▾")
        chevron.add_css_class("whisper-text")
        model_pill.append(chevron)

        self.model_btn.set_child(model_pill)
        self._build_model_popover()
        self.model_btn.connect("clicked", lambda _: self.model_popover.popup())
        card_content.append(self.model_btn)

        # Clear Chat Button
        clear_btn = Gtk.Button(label="🗑")
        clear_btn.set_tooltip_text("Clear Conversation")
        clear_btn.add_css_class("sidekick-tool-btn")
        clear_btn.connect("clicked", lambda _: self.clear_chat())
        card_content.append(clear_btn)

        # Collapse Button (⌄ down chevron)
        collapse_btn = Gtk.Button(label="⌄")
        collapse_btn.set_tooltip_text("Collapse to Bezel (Esc)")
        collapse_btn.add_css_class("sidekick-tool-btn")
        collapse_btn.connect("clicked", lambda _: self.on_collapse())
        card_content.append(collapse_btn)

        card_container.append(card_content)

        # Signature GlowProgressBar line beneath the header
        self.progress_bar = GlowProgressBarWidget(height=3, animated=True)
        card_container.append(self.progress_bar)

        self.append(card_container)

    def _build_model_popover(self) -> None:
        """Popover menu listing available AI models for instantaneous switching."""
        self.model_popover = Gtk.Popover()
        self.model_popover.set_parent(self.model_btn)
        self.model_popover.add_css_class("sidekick-popover")

        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        popover_box.add_css_class("sidekick-model-list")

        header = Gtk.Label(label="SELECT AI MODEL")
        header.add_css_class("whisper-text")
        header.set_xalign(0.0)
        popover_box.append(header)

        # Query installed models from coordinator
        try:
            available = self.coordinator.list_models()
        except Exception:
            available = []

        if not available:
            available = ["qwen2.5-coder:3b", "gemma3:1b", "qwen3:1.7b"]

        for m_name in available:
            btn = Gtk.Button(label=m_name)
            btn.add_css_class("sidekick-model-item")
            btn.set_halign(Gtk.Align.FILL)
            btn.connect("clicked", lambda _, name=m_name: self._select_model(name))
            popover_box.append(btn)

        self.model_popover.set_child(popover_box)

    def _select_model(self, name: str) -> None:
        self.coordinator.set_model(name)
        self.model_lbl.set_text(name)
        self.model_popover.popdown()

    def _build_context_row(self) -> None:
        """Subtle context bar displaying active Hyprland window/desktop context."""
        context_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        context_box.add_css_class("sidekick-context-bar")

        try:
            ctx = self.coordinator.perception.inspect_desktop()
            title = ctx.active_window.title if ctx.active_window else "Desktop"
            app_id = ctx.active_window.app_id if ctx.active_window else "Hyprland"
            desc = f"Context: {app_id} · {title[:36]}"
        except Exception:
            desc = "Context: Desktop"

        self.context_label = Gtk.Label(label=desc)
        self.context_label.add_css_class("whisper-text")
        self.context_label.set_xalign(0.0)
        self.context_label.set_hexpand(True)
        context_box.append(self.context_label)

        self.append(context_box)

    def _build_transcript_area(self) -> None:
        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroller.set_vexpand(True)
        self.scroller.set_hexpand(True)
        self.scroller.add_css_class("sidekick-scroller")

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.content_box.add_css_class("sidekick-transcript")

        # Official Empty State Hero (SidekickTranscript.swift lines 45-65)
        self.empty_state_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.empty_state_box.set_valign(Gtk.Align.CENTER)
        self.empty_state_box.set_halign(Gtk.Align.CENTER)
        self.empty_state_box.set_vexpand(True)
        self.empty_state_box.add_css_class("sidekick-empty-state")

        # 48px SpinningLogo Brand Mark
        hero_logo = LivingMascot(size=48, low_power=False, reduced_motion=False)
        self.empty_state_box.append(hero_logo)

        # "A little help. A lot more possible."
        title = Gtk.Label(label="A little help. A lot more possible.")
        title.add_css_class("sidekick-empty-title")
        self.empty_state_box.append(title)

        # "Ask a question, follow a thought, or hand something over."
        subtitle = Gtk.Label(label="Ask a question, follow a thought, or hand something over.")
        subtitle.add_css_class("sidekick-empty-subtitle")
        self.empty_state_box.append(subtitle)

        self.content_box.append(self.empty_state_box)
        self.scroller.set_child(self.content_box)
        self.append(self.scroller)

    def _build_composer(self) -> None:
        composer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        composer_box.add_css_class("sidekick-composer")

        self.chat_entry = Gtk.Entry()
        self.chat_entry.set_placeholder_text("Ask Sidekick…")
        self.chat_entry.set_hexpand(True)
        self.chat_entry.add_css_class("sidekick-entry")
        self.chat_entry.connect("activate", lambda _: self._on_submit())
        self.chat_entry.connect("changed", self._on_entry_changed)
        composer_box.append(self.chat_entry)

        # Circular 36x36 Send / Stop Button
        self.send_button = Gtk.Button(label="↑")
        self.send_button.set_tooltip_text("Send to Sidekick")
        self.send_button.add_css_class("sidekick-send-btn-disabled")
        self.send_button.connect("clicked", lambda _: self._on_submit())
        composer_box.append(self.send_button)

        self.append(composer_box)

    def _on_entry_changed(self, entry: Gtk.Entry) -> None:
        if self._is_running:
            return
        text = entry.get_text().strip()
        if text:
            self.send_button.remove_css_class("sidekick-send-btn-disabled")
            self.send_button.add_css_class("sidekick-send-btn-active")
        else:
            self.send_button.remove_css_class("sidekick-send-btn-active")
            self.send_button.add_css_class("sidekick-send-btn-disabled")

    def _on_submit(self) -> None:
        if self._is_running:
            self._finish_running(False, "Task stopped by user.")
            return

        prompt = self.chat_entry.get_text().strip()
        if not prompt:
            return

        self.chat_entry.set_text("")
        self._is_running = True
        self.send_button.remove_css_class("sidekick-send-btn-active")
        self.send_button.remove_css_class("sidekick-send-btn-disabled")
        self.send_button.add_css_class("sidekick-stop-btn")
        self.send_button.set_label("■")
        self.send_button.set_tooltip_text("Stop")

        # Hide empty state if present
        if self.empty_state_box.get_parent() == self.content_box:
            self.content_box.remove(self.empty_state_box)

        # 1. Append User Message Bubble
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

        self._scroll_to_bottom()

        # Run task asynchronously
        threading.Thread(target=self._execute_prompt, args=(prompt,), daemon=True).start()

    def _add_work_disclosure(self, initial_status: str) -> None:
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
        GLib.timeout_add(100, self._update_work_timer)

    def _update_work_timer(self) -> bool:
        if not self._is_running:
            return False
        elapsed = time.perf_counter() - self._task_start_time
        if self._work_timer_label:
            self._work_timer_label.set_text(f"{elapsed:.1f}s")
        return True

    def _execute_prompt(self, prompt: str) -> None:
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
        self._is_running = False

        self.send_button.remove_css_class("sidekick-stop-btn")
        self.send_button.set_label("↑")
        self._on_entry_changed(self.chat_entry)

        if self._work_status_label:
            elapsed = time.perf_counter() - self._task_start_time
            self._work_status_label.set_text(f"Completed in {elapsed:.1f}s")

        # Append Assistant Message
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
