"""
Bottom-attached Sentient Dynamic Island Notch for Wayland / Hyprland.
Uses Gtk4LayerShell to anchor flush to the bottom screen edge (0px margin).
Renders the exact inverted NotchShape with concave shoulder fillets emerging from the bezel.
Features authentic upstream NotchView running state (GlowHalo edge glow, status narration).
"""

from __future__ import annotations
import ctypes
import logging
import math
import os
import time
from typing import Callable, Optional

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
gi.require_version("GLib", "2.0")
from gi.repository import Gtk, Gdk, Gtk4LayerShell, GLib

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
    - When running: Multi-color edge glow (GlowHalo.stops parity) around perimeter skirt.
    """

    GLOW_STOPS = THEME.spectrum_stops

    def __init__(
        self,
        top_radius: float = 16.0,
        shoulder_radius: float = 12.0,
        has_glow: bool = False,
    ) -> None:
        super().__init__()
        self.top_radius = top_radius
        self.shoulder_radius = shoulder_radius
        self.has_glow = has_glow
        self._glow_angle = 0.0
        self.set_draw_func(self._on_draw)

        if self.has_glow:
            self._timer_id = GLib.timeout_add(33, self._tick_glow)
        else:
            self._timer_id = 0

    def set_glow(self, active: bool) -> None:
        self.has_glow = active
        if active and self._timer_id == 0:
            self._timer_id = GLib.timeout_add(33, self._tick_glow)
        elif not active and self._timer_id != 0:
            GLib.source_remove(self._timer_id)
            self._timer_id = 0
        self.queue_draw()

    def _tick_glow(self) -> bool:
        if not self.has_glow:
            return False
        self._glow_angle = (self._glow_angle + 0.03) % (2 * math.pi)
        self.queue_draw()
        return True

    def _on_draw(self, area: Gtk.DrawingArea, cr: cairo.Context, width: int, height: int) -> None:
        s_r = float(self.shoulder_radius)
        t_r = float(self.top_radius)
        w = float(width)
        h = float(height)

        # 1. Edge Glow (when AI is working / task is running)
        if self.has_glow:
            for lw, alpha in [(8.0, 0.25), (4.0, 0.55), (1.5, 0.95)]:
                cr.save()
                cr.move_to(0, h)
                cr.curve_to(s_r * 0.45, h, s_r, h - s_r * 0.45, s_r, h - s_r)
                cr.line_to(s_r, t_r)
                cr.curve_to(s_r, t_r * 0.45, s_r + t_r * 0.45, 0, s_r + t_r, 0)
                cr.line_to(w - s_r - t_r, 0)
                cr.curve_to(w - s_r - t_r * 0.45, 0, w - s_r, t_r * 0.45, w - s_r, t_r)
                cr.line_to(w - s_r, h - s_r)
                cr.curve_to(w - s_r, h - s_r * 0.45, w - s_r * 0.45, h, w, h)

                # Rotating angular gradient pattern along the skirt
                pat = cairo.LinearGradient(0, 0, w, h)
                n = len(self.GLOW_STOPS)
                for i, (r_c, g_c, b_c) in enumerate(self.GLOW_STOPS):
                    pos = (i / (n - 1) + self._glow_angle / (2 * math.pi)) % 1.0
                    pat.add_color_stop_rgba(pos, r_c, g_c, b_c, alpha)
                cr.set_source(pat)
                cr.set_line_width(lw)
                cr.set_line_cap(cairo.LINE_CAP_ROUND)
                cr.stroke()
                cr.restore()

        # 2. Path for solid fill (including flat bottom along the bezel)
        cr.move_to(0, h)
        cr.curve_to(s_r * 0.45, h, s_r, h - s_r * 0.45, s_r, h - s_r)
        cr.line_to(s_r, t_r)
        cr.curve_to(s_r, t_r * 0.45, s_r + t_r * 0.45, 0, s_r + t_r, 0)
        cr.line_to(w - s_r - t_r, 0)
        cr.curve_to(w - s_r - t_r * 0.45, 0, w - s_r, t_r * 0.45, w - s_r, t_r)
        cr.line_to(w - s_r, h - s_r)
        cr.curve_to(w - s_r, h - s_r * 0.45, w - s_r * 0.45, h, w, h)
        cr.line_to(0, h)
        cr.close_path()

        # Fill dark OLED acrylic (rgba(10, 10, 13, 0.96))
        cr.set_source_rgba(0.04, 0.04, 0.05, 0.96)
        cr.fill()

        # 3. Open Skirt Path (NotchSkirtShape.swift parity): stroke only visible edges
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
    - Synchronous geometry renegotiation ensures zero stretching across the monitor.
    """

    COLLAPSED_WIDTH = 380
    COLLAPSED_HEIGHT = 40
    RUNNING_HEIGHT = 56
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
        self.is_running = False

        self.add_css_class("sentient-pill-window")

        # 1. Initialize Wayland Layer Shell
        self._init_layer_shell()

        # 2. Install CSS Theme
        self._load_css()

        # 3. Create Root Container
        self.root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.root_box.set_halign(Gtk.Align.CENTER)
        self.root_box.set_valign(Gtk.Align.END)
        self.set_child(self.root_box)

        # 4. Build Collapsed Pill and Expanded View
        self._build_collapsed_pill()
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

        # Anchor bottom-center strictly
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.LEFT, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, False)

        # Attached flush to bottom edge: 0 logical pixels margin!
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 0)

        # Zero focus theft when idle
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)

    def _load_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_string(GTK_CSS)
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def _build_collapsed_pill(self) -> None:
        self.pill_overlay = Gtk.Overlay()
        self.pill_overlay.set_halign(Gtk.Align.CENTER)
        self.pill_overlay.set_valign(Gtk.Align.END)
        self.pill_overlay.set_size_request(self.COLLAPSED_WIDTH, self.COLLAPSED_HEIGHT)
        self.pill_overlay.add_css_class("bottom-notch-pill")

        # Background drawing with concave fillets curving into the bezel
        self.notch_bg = BottomNotchShapeBackground(top_radius=16.0, shoulder_radius=12.0)
        self.notch_bg.set_size_request(self.COLLAPSED_WIDTH, self.COLLAPSED_HEIGHT)
        self.pill_overlay.set_child(self.notch_bg)

        # Stack container for Idle Row vs Running Row
        self.pill_stack = Gtk.Stack()
        self.pill_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        # --- View 1: Idle Row ---
        self.idle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.idle_box.add_css_class("bottom-notch-content")
        self.idle_box.set_size_request(self.COLLAPSED_WIDTH, self.COLLAPSED_HEIGHT)

        self.pill_mascot = LivingMascot(
            size=20,
            low_power=self.low_power,
            reduced_motion=self.reduced_motion,
        )
        self.idle_box.append(self.pill_mascot)

        self.pill_label = Gtk.Label(label="“Ask Sidekick…”")
        self.pill_label.add_css_class("readback-text")
        self.pill_label.set_hexpand(True)
        self.pill_label.set_xalign(0.0)
        self.idle_box.append(self.pill_label)

        right_glyph = Gtk.Label(label="⌃")
        right_glyph.add_css_class("whisper-text")
        self.idle_box.append(right_glyph)
        self.pill_stack.add_named(self.idle_box, "idle")

        # --- View 2: Running Computer-Use Row (NotchView parity) ---
        self.running_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.running_box.add_css_class("bottom-notch-content")
        self.running_box.set_size_request(self.COLLAPSED_WIDTH, self.RUNNING_HEIGHT)

        # Top row: Logo + Stop Button
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        running_mascot = LivingMascot(size=18, low_power=self.low_power, reduced_motion=self.reduced_motion)
        running_mascot.set_state(MascotState.THINKING)
        top_row.append(running_mascot)

        run_title = Gtk.Label(label="Sidekick")
        run_title.add_css_class("sidekick-work-status")
        run_title.set_hexpand(True)
        run_title.set_xalign(0.0)
        top_row.append(run_title)

        stop_btn = Gtk.Button(label="■")
        stop_btn.add_css_class("sidekick-stop-btn")
        stop_btn.connect("clicked", lambda _: self.set_running(False))
        top_row.append(stop_btn)
        self.running_box.append(top_row)

        # Bottom row: Monospace Live Status narration
        self.status_line = Gtk.Label(label="mcp: sentient_native/click (completed)...")
        self.status_line.add_css_class("whisper-text")
        self.status_line.set_xalign(0.0)
        self.running_box.append(self.status_line)

        self.pill_stack.add_named(self.running_box, "running")
        self.pill_stack.set_visible_child_name("idle")

        self.pill_overlay.add_overlay(self.pill_stack)

        # Click gesture to expand
        click_gesture = Gtk.GestureClick()
        click_gesture.connect("released", lambda *_: self.expand())
        self.pill_overlay.add_controller(click_gesture)

    def set_running(self, running: bool, status: str = "") -> None:
        """Switch notch presentation between idle whisper and active computer-use narration."""
        self.is_running = running
        self.notch_bg.set_glow(running)
        h = self.RUNNING_HEIGHT if running else self.COLLAPSED_HEIGHT

        if running:
            if status:
                self.status_line.set_text(status)
            self.pill_stack.set_visible_child_name("running")
            self.pill_mascot.set_state(MascotState.THINKING)
        else:
            self.pill_stack.set_visible_child_name("idle")
            self.pill_mascot.set_state(MascotState.IDLE)

        if not self.is_expanded:
            self.pill_overlay.set_size_request(self.COLLAPSED_WIDTH, h)
            self.notch_bg.set_size_request(self.COLLAPSED_WIDTH, h)
            self.set_size_request(self.COLLAPSED_WIDTH, h)
            self.set_default_size(self.COLLAPSED_WIDTH, h)

    def expand(self) -> None:
        """Expand upward into full Sentient Sidekick interface."""
        if self.is_expanded:
            return

        self.is_expanded = True

        # Synchronously hide, swap child, resize, and show to cleanly reallocate surface
        self.set_visible(False)
        if self.pill_overlay.get_parent() == self.root_box:
            self.root_box.remove(self.pill_overlay)
        if self.expanded_view.get_parent() != self.root_box:
            self.root_box.append(self.expanded_view)

        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.ON_DEMAND)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 0)
        self.set_size_request(self.EXPANDED_WIDTH, self.EXPANDED_HEIGHT)
        self.set_default_size(self.EXPANDED_WIDTH, self.EXPANDED_HEIGHT)
        self.set_visible(True)

        self.expanded_view.chat_entry.grab_focus()
        logger.info("Sentient Notch expanded upward.")

    def collapse(self) -> None:
        """Collapse back to bottom-attached dynamic island notch without stretching."""
        self.is_expanded = False
        h = self.RUNNING_HEIGHT if self.is_running else self.COLLAPSED_HEIGHT

        self.set_visible(False)
        if self.expanded_view.get_parent() == self.root_box:
            self.root_box.remove(self.expanded_view)
        if self.pill_overlay.get_parent() != self.root_box:
            self.root_box.append(self.pill_overlay)

        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 0)
        self.pill_overlay.set_size_request(self.COLLAPSED_WIDTH, h)
        self.notch_bg.set_size_request(self.COLLAPSED_WIDTH, h)
        self.set_size_request(self.COLLAPSED_WIDTH, h)
        self.set_default_size(self.COLLAPSED_WIDTH, h)
        self.set_visible(True)
        logger.info("Sentient Notch collapsed to bottom bezel.")

    def _on_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        if keyval == Gdk.KEY_Escape:
            if self.is_expanded:
                self.collapse()
                return True
        return False
