"""
Expanded Sentient interface for Linux.
Provides upward-expanding conversation view, model switcher, context bar, and STOP control.
"""

from __future__ import annotations
import threading
from typing import Callable, List, Optional

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gtk, GLib

from sentient_linux.core.coordinator import CommandCoordinator
from sentient_linux.gui.mascot import LivingMascot, MascotState
from sentient_linux.gui.theme import THEME


class ExpandedView(Gtk.Box):
    """
    Main expanded interaction surface for Sentient Linux.
    Renders conversation stream, desktop context, model selection, and prompt entry.
    """

    def __init__(
        self,
        coordinator: CommandCoordinator,
        on_collapse: Callable[[], None],
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.coordinator = coordinator
        self.on_collapse = on_collapse

        self.add_css_class("living-glass-expanded")
        self.set_size_request(440, 520)

        # 1. Header (Mascot, Wordmark, Model Badge, Collapse)
        self._build_header()

        # 2. Desktop Context Bar
        self._build_context_bar()

        # 3. Conversation Scroll Area
        self._build_conversation_area()

        # 4. Input & Controls
        self._build_input_controls()

        # Initial context refresh
        self.refresh_context()

    def _build_header(self) -> None:
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # Mascot
        self.mascot = LivingMascot(size=32)
        header.append(self.mascot)

        # Brand Title
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_label = Gtk.Label(label="Sentient OS")
        title_label.set_xalign(0.0)
        title_label.set_css_classes(["whisper-text"])
        title_box.append(title_label)

        self.model_label = Gtk.Label(label=f"● {self.coordinator.inference.resolve_model()}")
        self.model_label.set_xalign(0.0)
        self.model_label.add_css_class("status-dot-green")
        title_box.append(self.model_label)
        header.append(title_box)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header.append(spacer)

        # Model selector dropdown
        self.model_drop = Gtk.DropDown.new_from_strings([
            "qwen2.5-coder:3b",
            "gemma3:1b",
            "qwen3:1.7b",
            "llama3.2-1b",
        ])
        self.model_drop.connect("notify::selected-item", self._on_model_selected)
        header.append(self.model_drop)

        # Collapse Button
        collapse_btn = Gtk.Button(label="✕")
        collapse_btn.add_css_class("action-btn")
        collapse_btn.connect("clicked", lambda _: self.on_collapse())
        header.append(collapse_btn)

        self.append(header)

    def _build_context_bar(self) -> None:
        self.context_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.context_label = Gtk.Label(label="Context: Loading...")
        self.context_label.set_xalign(0.0)
        self.context_label.add_css_class("context-chip")
        self.context_label.set_hexpand(True)
        self.context_box.append(self.context_label)

        # Quick refresh button
        refresh_btn = Gtk.Button(label="⟳")
        refresh_btn.add_css_class("action-btn")
        refresh_btn.connect("clicked", lambda _: self.refresh_context())
        self.context_box.append(refresh_btn)

        self.append(self.context_box)

    def _build_conversation_area(self) -> None:
        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.history_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.history_box.set_valign(Gtk.Align.START)

        # Welcome Card
        welcome_card = Gtk.Label(
            label="Welcome to Sentient OS for Linux.\nAsk anything or hand off tasks with context."
        )
        welcome_card.set_wrap(True)
        welcome_card.set_xalign(0.0)
        welcome_card.add_css_class("history-card-assistant")
        self.history_box.append(welcome_card)

        scroller.set_child(self.history_box)
        self.append(scroller)

    def _build_input_controls(self) -> None:
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        # Chat Entry
        self.chat_entry = Gtk.Entry()
        self.chat_entry.set_placeholder_text("Ask Sentient...")
        self.chat_entry.set_hexpand(True)
        self.chat_entry.add_css_class("chat-entry")
        self.chat_entry.connect("activate", self._on_submit_prompt)
        input_row.append(self.chat_entry)

        # Send Button
        send_btn = Gtk.Button(label="↑")
        send_btn.add_css_class("action-btn")
        send_btn.connect("clicked", lambda _: self._on_submit_prompt(self.chat_entry))
        input_row.append(send_btn)

        # Emergency STOP Button
        self.stop_btn = Gtk.Button(label="STOP")
        self.stop_btn.add_css_class("stop-btn")
        self.stop_btn.connect("clicked", self._on_stop_clicked)
        input_row.append(self.stop_btn)

        self.append(input_row)

    def refresh_context(self) -> None:
        """Query active window metadata safely."""
        try:
            win = self.coordinator.inspector.get_focused_window()
            if win:
                title = win.title[:38] + ("..." if len(win.title) > 38 else "")
                self.context_label.set_label(f"Active: [{win.wm_class}] {title} (WS {win.workspace_name})")
            else:
                self.context_label.set_label("Active: Desktop / No Focused Window")
        except Exception:
            self.context_label.set_label("Active: Hyprland Context Unreachable")

    def _on_model_selected(self, dropdown: Gtk.DropDown, _pspec) -> None:
        selected_item = dropdown.get_selected_item()
        if selected_item:
            model_name = selected_item.get_string()
            self.coordinator.inference._configured_model = model_name
            self.model_label.set_label(f"● {model_name}")

    def _on_submit_prompt(self, entry: Gtk.Entry) -> None:
        prompt_text = entry.get_text().strip()
        if not prompt_text:
            return

        entry.set_text("")
        self._append_message("user", prompt_text)

        # Switch mascot to thinking state
        self.mascot.state = MascotState.THINKING

        # Execute inference asynchronously so GTK UI never blocks or stutters
        threading.Thread(target=self._run_inference_thread, args=(prompt_text,), daemon=True).start()

    def _run_inference_thread(self, prompt: str) -> None:
        try:
            response = self.coordinator.ask(prompt=prompt, include_context=True, include_screenshot=False)
            GLib.idle_add(self._on_inference_complete, response)
        except Exception as err:
            GLib.idle_add(self._on_inference_error, str(err))

    def _on_inference_complete(self, response: str) -> bool:
        self.mascot.state = MascotState.IDLE
        self._append_message("assistant", response)
        return False

    def _on_inference_error(self, err_msg: str) -> bool:
        self.mascot.state = MascotState.ERROR
        self._append_message("assistant", f"⚠️ {err_msg}")
        return False

    def _on_stop_clicked(self, _btn: Gtk.Button) -> None:
        self.coordinator.stop(reason="User clicked UI STOP button")
        self.mascot.state = MascotState.ERROR
        self._append_message("assistant", "🛑 Emergency Stop Triggered: Active inference and tasks cancelled.")

    def _append_message(self, sender: str, text: str) -> None:
        lbl = Gtk.Label(label=text)
        lbl.set_wrap(True)
        lbl.set_xalign(0.0)
        lbl.set_selectable(True)
        if sender == "user":
            lbl.add_css_class("history-card-user")
        else:
            lbl.add_css_class("history-card-assistant")
        self.history_box.append(lbl)
