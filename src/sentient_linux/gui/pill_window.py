"""
Bottom-attached Sentient Dynamic Island Notch for Wayland / Hyprland.
Uses Gtk4LayerShell to anchor flush to the bottom screen edge (0px margin).
Renders the exact inverted NotchShape with concave shoulder fillets emerging from the bezel.
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

import cairo
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


class BottomNotchShapeBackground(Gtk.DrawingArea):
    """
    Direct Cairo translation of upstream NotchShape.swift inverted for screen bottom:
    - Sits flush against the bottom bezel (margin = 0).
    - Concave shoulder fillets curve gracefully out of the bottom screen edge.
    - Convex top corners round off the visible island.
    - Open skirt stroke highlights the visible perimeter while leaving the bezel line unstroked.
    """

    def __init__(self, top_radius: float = 18.0, shoulder_radius: float = 12.0) -> None:
        super().__init__()
        self.top_radius = top_radius
        self.shoulder_radius = shoulder_radius
        self.set_draw_func(self._on_draw)

    def _on_draw(self, area: Gtk.DrawingArea, cr: cairo.Context, width: int, height: int) -> None:
        s_r = float(self.shoulder_radius)
        t_r = float(self.top_radius)
        w = float(width)
        h = float(height)

        # 1. Path for solid fill (including flat bottom along the bezel)
        cr.move_to(0, h)
        # Left concave shoulder fillet emerging from bezel
        cr.curve_to(s_r * 0.45, h, s_r, h - s_r * 0.45, s_r, h - s_r)
        # Left side
        cr.line_to(s_r, t_r)
        # Top-left convex rounded corner
        cr.curve_to(s_r, t_r * 0.45, s_r + t_r * 0.45, 0, s_r + t_r, 0)
        # Top edge
        cr.line_to(w - s_r - t_r, 0)
        # Top-right convex rounded corner
        cr.curve_to(w - s_r - t_r * 0.45, 0, w - s_r, t_r * 0.45, w - s_r, t_r)
        # Right side
        cr.line_to(w - s_r, h - s_r)
        # Right concave shoulder fillet into bezel
        cr.curve_to(w - s_r, h - s_r * 0.45, w - s_r * 0.45, h, w, h)
        # Bottom edge along bezel
        cr.line_to(0, h)
        cr.close_path()

        # Fill dark OLED acrylic (rgba(10, 10, 13, 0.94))
        cr.set_source_rgba(0.04, 0.04, 0.05, 0.94)
        cr.fill()

        # 2. Open Skirt Path (NotchSkirtShape.swift parity): stroke only visible edges
        cr.move_to(0, h)
        cr.curve_to(s_r * 0.45, h, s_r, h - s_r * 0.45, s_r, h - s_r)
        cr.line_to(s_r, t_r)
        cr.curve_to(s_r, t_r * 0.45, s_r + t_r * 0.45, 0, s_r + t_r, 0)
        cr.line_to(w - s_r - t_r, 0)
        cr.curve_to(w - s_r - t_r * 0.45, 0, w - s_r, t_r * 0.45, w - s_r, t_r)
        cr.line_to(w - s_r, h - s_r)
        cr.curve_to(w - s_r, h - s_r * 0.45, w - s_r * 0.45, h, w, h)

        # Stroke visible razor border (0.75px)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.16)
        cr.set_line_width(0.75)
        cr.stroke()


class SentientPillWindow(Gtk.Window):
    """
    Bottom-attached Wayland Layer-Shell window.
    Faithful port of Sentient OS Notch & Sidekick interface:
    - Collapsed: Attached flush to the bottom screen bezel (0px margin), inverted NotchShape.
    - Expanded: Fluid upward expansion into full Sidekick conversation panel.
    """

    COLLAPSED_WIDTH = 380
    COLLAPSED_HEIGHT = 40
    EXPANDED_WIDTH = 780
    EXPANDED_HEIGHT = 580

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

        # 2. Main Root Container
        self.root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self.root_box)

        # 3. Build Collapsed Notch Island Widget
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

        # Attached flush to bottom edge: 0 logical pixels margin!
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 0)

        # Zero focus theft when idle
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)

    def _build_collapsed_pill(self) -> None:
        # Use Gtk.Overlay with Cairo BottomNotchShapeBackground
        self.pill_overlay = Gtk.Overlay()
        self.pill_overlay.set_size_request(self.COLLAPSED_WIDTH, self.COLLAPSED_HEIGHT)
        self.pill_overlay.add_css_class("bottom-notch-pill")

        # Background drawing with concave fillets curving into the bezel
        self.notch_bg = BottomNotchShapeBackground(top_radius=16.0, shoulder_radius=12.0)
        self.notch_bg.set_hexpand(True)
        self.notch_bg.set_vexpand(True)
        self.pill_overlay.set_child(self.notch_bg)

        # Foreground Content Row
        self.pill_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.pill_content.add_css_class("bottom-notch-content")
        self.pill_content.set_hexpand(True)
        self.pill_content.set_vexpand(True)

        # Official 20px SpinningLogo
        self.pill_mascot = LivingMascot(
            size=20,
            low_power=self.low_power,
            reduced_motion=self.reduced_motion,
        )
        self.pill_content.append(self.pill_mascot)

        # Upstream Notch Caption: Serif-italic whisper voice ("“Ask Sidekick…”")
        self.pill_label = Gtk.Label(label="“Ask Sidekick…”")
        self.pill_label.add_css_class("readback-text")
        self.pill_label.set_hexpand(True)
        self.pill_label.set_xalign(0.0)
        self.pill_content.append(self.pill_label)

        # Right affordance hint (Upward expand glyph)
        right_glyph = Gtk.Label(label="⌃")
        right_glyph.add_css_class("whisper-text")
        self.pill_content.append(right_glyph)

        self.pill_overlay.add_overlay(self.pill_content)

        # Click gesture to expand
        click_gesture = Gtk.GestureClick()
        click_gesture.connect("released", lambda *_: self.expand())
        self.pill_overlay.add_controller(click_gesture)

    def expand(self) -> None:
        """Expand upward into full Sentient Sidekick interface."""
        if self.is_expanded:
            return

        self.is_expanded = True
        self.root_box.remove(self.pill_overlay)
        self.root_box.append(self.expanded_view)

        # Enable keyboard focus so user can type into entry
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.ON_DEMAND)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 0)
        self.set_size_request(self.EXPANDED_WIDTH, self.EXPANDED_HEIGHT)

        self.expanded_view.chat_entry.grab_focus()
        logger.info("Sentient Notch expanded upward.")

    def collapse(self) -> None:
        """Collapse back to bottom-attached dynamic island notch."""
        self.is_expanded = False

        if self.expanded_view.get_parent() == self.root_box:
            self.root_box.remove(self.expanded_view)
        if self.pill_overlay.get_parent() != self.root_box:
            self.root_box.append(self.pill_overlay)

        # Release keyboard focus completely
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 0)
        self.set_size_request(self.COLLAPSED_WIDTH, self.COLLAPSED_HEIGHT)
        logger.info("Sentient Notch collapsed to bottom bezel.")

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
