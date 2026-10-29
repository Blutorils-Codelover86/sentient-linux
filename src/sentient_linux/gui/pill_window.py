"""
Bottom-center floating Sentient Pill window for Wayland / Hyprland.
Uses Gtk4LayerShell to anchor 20px above the bottom screen edge without stealing focus.
Faithful port of NotchView.swift and SidekickPresentation.swift to Wayland.
"""

from __future__ import annotations
import ctypes
import logging
import os
from typing import Optional

# Preload libgtk4-layer-shell with RTLD_GLOBAL before Gtk/libwayland import
for candidate in ["/usr/lib/libgtk4-layer-shell.so", "/usr/lib64/libgtk4-layer-shell.so"]:
    if os.path.exists(candidate):
        try:
            ctypes.CDLL(candidate, ctypes.RTLD_GLOBAL)
            break
        except Exception:
            pass

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, Gtk4LayerShell

from sentient_linux.core.coordinator import CommandCoordinator
from sentient_linux.gui.mascot import LivingMascot, MascotState
from sentient_linux.gui.expanded_view import ExpandedView
from sentient_linux.gui.theme import THEME, GTK_CSS

logger = logging.getLogger("sentient.gui.pill_window")


class SentientPillWindow(Gtk.Window):
    """
    Floating bottom-center Wayland Layer-Shell window.
    Faithful port of Sentient OS Notch & Sidekick interface:
    - Collapsed: Bottom-center glass pill with LivingMascot, serif-italic read-back / status whisper.
    - Expanded: Fluid upward expansion into full Sidekick conversation panel.
    """

    COLLAPSED_WIDTH = 340
    COLLAPSED_HEIGHT = 44
    EXPANDED_WIDTH = 680
    EXPANDED_HEIGHT = 520

    def __init__(
        self,
        app: Optional[Gtk.Application] = None,
        coordinator: Optional[CommandCoordinator] = None,
        low_power: bool = False,
        reduced_motion: bool = False,
    ) -> None:
        if app:
            super().__init__(application=app)
        else:
            super().__init__()
        self.coordinator = coordinator or CommandCoordinator()
        self.low_power = low_power
        self.reduced_motion = reduced_motion
        self.is_expanded = False

        self.add_css_class("sentient-pill-window")

        # 1. Initialize Wayland Layer Shell
        self._init_layer_shell()

        # 2. Main Container
        self.root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self.root_box)

        # 3. Build Collapsed Pill Widget
        self._build_collapsed_pill()

        # 4. Build Expanded Panel Widget
        self.expanded_view = ExpandedView(
            coordinator=self.coordinator,
            on_collapse=self.collapse,
        )

        # 5. Connect Global Keyboard Event (Escape to collapse)
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        # Show initially collapsed
        self.collapse()

    def _init_layer_shell(self) -> None:
        """Configure Wayland layer shell geometry and layer pinning."""
        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.TOP)
        Gtk4LayerShell.set_namespace(self, "sentient-pill")

        # Anchor bottom-center
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.LEFT, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, False)

        # 20 logical pixels above bottom screen edge
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 20)

        # Zero focus theft when idle
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)

    def _build_collapsed_pill(self) -> None:
        self.pill_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.pill_box.add_css_class("sidekick-pill")
        self.pill_box.set_size_request(self.COLLAPSED_WIDTH, self.COLLAPSED_HEIGHT)

        # Living Mascot (22px)
        self.pill_mascot = LivingMascot(
            size=22,
            low_power=self.low_power,
            reduced_motion=self.reduced_motion,
        )
        self.pill_box.append(self.pill_mascot)

        # Upstream Notch Caption: Serif-italic whisper voice ("“Ask Sidekick…”")
        self.pill_label = Gtk.Label(label="“Ask Sidekick…”")
        self.pill_label.add_css_class("readback-text")
        self.pill_label.set_hexpand(True)
        self.pill_label.set_xalign(0.0)
        self.pill_box.append(self.pill_label)

        # Right affordance hint (Super+K / Upward expand glyph)
        right_glyph = Gtk.Label(label="⌃")
        right_glyph.add_css_class("whisper-text")
        self.pill_box.append(right_glyph)

        # Click gesture to expand
        click_gesture = Gtk.GestureClick()
        click_gesture.connect("released", lambda *_: self.expand())
        self.pill_box.add_controller(click_gesture)

    def expand(self) -> None:
        """Expand upward into full Sentient assistant."""
        if self.is_expanded:
            return

        self.is_expanded = True
        self.root_box.remove(self.pill_box)
        self.root_box.append(self.expanded_view)

        # Enable keyboard focus so user can type into entry
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.ON_DEMAND)
        self.set_size_request(self.EXPANDED_WIDTH, self.EXPANDED_HEIGHT)

        self.expanded_view.refresh_context()
        self.expanded_view.chat_entry.grab_focus()
        logger.info("Sentient Pill expanded upward.")

    def collapse(self) -> None:
        """Collapse back to bottom-center floating pill."""
        self.is_expanded = False

        if self.expanded_view.get_parent() == self.root_box:
            self.root_box.remove(self.expanded_view)
        if self.pill_box.get_parent() != self.root_box:
            self.root_box.append(self.pill_box)

        # Release keyboard focus completely
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)
        self.set_size_request(self.COLLAPSED_WIDTH, self.COLLAPSED_HEIGHT)
        logger.info("Sentient Pill collapsed to bottom-center.")

    def _on_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        # Escape key collapses when expanded
        if keyval == Gdk.KEY_Escape:
            if self.is_expanded:
                self.collapse()
                return True
        return False
