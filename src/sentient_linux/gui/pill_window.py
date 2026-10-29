"""
Bottom-attached Sentient Dynamic Island Notch for Wayland / Hyprland.
Uses Gtk4LayerShell to anchor flush to the bottom screen edge (0px margin).
Renders the exact inverted NotchShape with concave shoulder fillets emerging from the bezel.
Faithful port of upstream Sentient OS Notch & Sidekick interaction hierarchy:
- Phase A: Compact resting notch (NotchPhase.HIDDEN: 340x44)
- Phase B1: Interactive notch quick prompt (NotchPhase.TYPING: 480x72)
- Phase B2: Active computer-use progress & GlowHalo edge glow (NotchPhase.RUNNING: 420x68)
- Phase B3: Inline response preview & quick reply (NotchPhase.MESSAGE: 520x220)
- Phase C: Full Sidekick conversation window (780x580, opened via explicit arrow.up.forward.app)
"""

from __future__ import annotations
import ctypes
from enum import Enum
import logging
import math
import os
import threading
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
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Gdk, Gtk4LayerShell, GLib, Pango

from sentient_linux.core.coordinator import CommandCoordinator
from sentient_linux.gui.mascot import LivingMascot, MascotState
from sentient_linux.gui.expanded_view import ExpandedView
from sentient_linux.gui.conversation import ConversationStore, ConversationRecord
from sentient_linux.gui.theme import THEME, GTK_CSS

logger = logging.getLogger("sentient.gui.pill_window")


class NotchPhase(Enum):
    """Upstream NotchPhase parity."""
    HIDDEN = "hidden"    # Idle resting pill flush to bezel (340x44)
    TYPING = "typing"    # Interactive quick prompt field (480x72)
    RUNNING = "running"  # Active computer-use narration & edge glow (420x68)
    MESSAGE = "message"  # Inline response reading & quick reply (520x220)


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
        top_radius: float = 14.0,
        shoulder_radius: float = 10.0,
        has_glow: bool = False,
    ) -> None:
        super().__init__()
        self.top_radius = top_radius
        self.shoulder_radius = shoulder_radius
        self.has_glow = has_glow
        self._glow_angle = 0.0
        self.animated_width = 340.0
        self.animated_height = 44.0
        self.set_draw_func(self._on_draw)

        if self.has_glow:
            self._tick_id = self.add_tick_callback(self._on_tick_glow)
        else:
            self._tick_id = 0

    def set_notch_size(self, width: float, height: float) -> None:
        self.animated_width = width
        self.animated_height = height
        self.queue_draw()

    def set_glow(self, active: bool) -> None:
        self.has_glow = active
        if active and self._tick_id == 0:
            self._tick_id = self.add_tick_callback(self._on_tick_glow)
        elif not active and self._tick_id != 0:
            self.remove_tick_callback(self._tick_id)
            self._tick_id = 0
        self.queue_draw()

    def _on_tick_glow(self, widget, frame_clock) -> bool:
        if not self.has_glow:
            return False
        self._glow_angle = (self._glow_angle + 0.03) % (2 * math.pi)
        self.queue_draw()
        return True

    def _on_draw(self, area: Gtk.DrawingArea, cr: cairo.Context, width: int, height: int) -> None:
        s_r = float(self.shoulder_radius)
        t_r = float(self.top_radius)

        # Center symmetrically on canvas: left = cx - w/2, right = cx + w/2
        cx = float(width) / 2.0
        nw = float(self.animated_width)
        nh = float(self.animated_height)

        # Symmetric coordinate rounding to prevent subpixel jitter
        left = round(cx - nw / 2.0)
        right = round(cx + nw / 2.0)
        top = round(float(height) - nh)
        bottom = float(height)

        # 1. Edge Glow (when AI is working / task is running)
        if self.has_glow:
            for lw, alpha in [(8.0, 0.25), (4.0, 0.55), (1.5, 0.95)]:
                cr.save()
                cr.move_to(left, bottom)
                cr.curve_to(left + s_r * 0.55, bottom, left + s_r, bottom - s_r * 0.45, left + s_r, bottom - s_r)
                cr.line_to(left + s_r, top + t_r)
                cr.curve_to(left + s_r, top + t_r * 0.45, left + s_r + t_r * 0.45, top, left + s_r + t_r, top)
                cr.line_to(right - s_r - t_r, top)
                cr.curve_to(right - s_r - t_r * 0.45, top, right - s_r, top + t_r * 0.45, right - s_r, top + t_r)
                cr.line_to(right - s_r, bottom - s_r)
                cr.curve_to(right - s_r, bottom - s_r * 0.45, right - s_r * 0.55, bottom, right, bottom)

                # Rotating angular gradient pattern along the skirt
                pat = cairo.LinearGradient(left, top, right, bottom)
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
        cr.move_to(left, bottom)
        cr.curve_to(left + s_r * 0.55, bottom, left + s_r, bottom - s_r * 0.45, left + s_r, bottom - s_r)
        cr.line_to(left + s_r, top + t_r)
        cr.curve_to(left + s_r, top + t_r * 0.45, left + s_r + t_r * 0.45, top, left + s_r + t_r, top)
        cr.line_to(right - s_r - t_r, top)
        cr.curve_to(right - s_r - t_r * 0.45, top, right - s_r, top + t_r * 0.45, right - s_r, top + t_r)
        cr.line_to(right - s_r, bottom - s_r)
        cr.curve_to(right - s_r, bottom - s_r * 0.45, right - s_r * 0.55, bottom, right, bottom)
        cr.line_to(left, bottom)
        cr.close_path()

        # Fill dark OLED acrylic (#0c0c0e)
        cr.set_source_rgba(0.047, 0.047, 0.055, 1.0)
        cr.fill()

        # 3. Open Skirt Path (NotchSkirtShape.swift parity): stroke only visible edges
        cr.move_to(left, bottom)
        cr.curve_to(left + s_r * 0.55, bottom, left + s_r, bottom - s_r * 0.45, left + s_r, bottom - s_r)
        cr.line_to(left + s_r, top + t_r)
        cr.curve_to(left + s_r, top + t_r * 0.45, left + s_r + t_r * 0.45, top, left + s_r + t_r, top)
        cr.line_to(right - s_r - t_r, top)
        cr.curve_to(right - s_r - t_r * 0.45, top, right - s_r, top + t_r * 0.45, right - s_r, top + t_r)
        cr.line_to(right - s_r, bottom - s_r)
        cr.curve_to(right - s_r, bottom - s_r * 0.45, right - s_r * 0.55, bottom, right, bottom)

        # Stroke visible razor border (0.75px)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.16)
        cr.set_line_width(0.75)
        cr.stroke()


class SentientPillWindow(Gtk.Window):
    """
    Bottom-attached Wayland Layer-Shell window.
    Faithful port of official Sentient OS Notch & Sidekick interface.
    Separates the Notch interaction hierarchy from the Full Sidekick conversation:
    - Phase A: Compact resting notch (340x44)
    - Phase B1: Interactive notch quick prompt (480x72)
    - Phase B2: Active computer-use progress & GlowHalo edge glow (420x68)
    - Phase B3: Inline response preview & quick reply (520x220)
    - Phase C: Full Sidekick conversation window (780x580)
    """

    # Dimensions per phase (NotchMetrics parity)
    PHASE_DIMENSIONS = {
        NotchPhase.HIDDEN: (340, 44),
        NotchPhase.TYPING: (480, 72),
        NotchPhase.RUNNING: (420, 68),
        NotchPhase.MESSAGE: (520, 220),
    }

    # Outer layer-shell fixed canvas dimensions accommodating maximum interactive notch + slack
    # 544 logical px = 680 physical px at 1.25x scale -> centered at 620 physical px on 1920 display (center = 960.0 px)
    CANVAS_WIDTH = 544
    CANVAS_HEIGHT = 240

    COLLAPSED_WIDTH = 340
    COLLAPSED_HEIGHT = 44
    RUNNING_HEIGHT = 68
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

        self.phase: NotchPhase = NotchPhase.HIDDEN
        self.is_expanded: bool = False
        self.is_running: bool = False
        self._is_pointer_inside: bool = False
        self._is_pointer_pressed: bool = False
        self._collapse_timer_id: int = 0
        self._current_request_id: int = 0
        self._task_start_time: float = 0.0

        # Frame-clock animation state for smooth, twitch-free notch morphing
        self._current_width: float = float(self.COLLAPSED_WIDTH)
        self._current_height: float = float(self.COLLAPSED_HEIGHT)
        self._target_width: float = float(self.COLLAPSED_WIDTH)
        self._target_height: float = float(self.COLLAPSED_HEIGHT)
        self._morph_tick_id: int = 0
        self._last_frame_time: int = 0

        self.add_css_class("sentient-pill-window")

        # 1. Initialize Wayland Layer Shell with fixed canvas
        self._init_layer_shell()

        # 2. Install CSS Theme
        self._load_css()

        # 3. Create Root Container
        self.root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.root_box.set_halign(Gtk.Align.CENTER)
        self.root_box.set_valign(Gtk.Align.END)
        self.root_box.set_size_request(self.CANVAS_WIDTH, self.CANVAS_HEIGHT)
        self.set_child(self.root_box)

        # 4. Build Notch Overlay & Full Expanded View
        self._build_notch_overlay()
        self.expanded_view = ExpandedView(
            coordinator=self.coordinator,
            on_collapse=self.collapse,
        )

        # 5. Global Keyboard Controller
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        # 6. Bind surface input region on realize / map
        self.connect("realize", lambda _: self._update_input_region())
        self.connect("map", lambda _: self._update_input_region())

        # Set fixed outer surface size
        self.set_size_request(self.CANVAS_WIDTH, self.CANVAS_HEIGHT)
        self.set_default_size(self.CANVAS_WIDTH, self.CANVAS_HEIGHT)

        # Set initial resting notch state
        self.set_phase(NotchPhase.HIDDEN)

    def _init_layer_shell(self) -> None:
        """Configure Wayland layer shell geometry and layer pinning."""
        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.TOP)
        Gtk4LayerShell.set_namespace(self, "sentient-notch")

        # Anchor bottom-center strictly
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.LEFT, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, False)

        # Attached flush to bottom edge: 0 logical pixels margin!
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 0)
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

    def _build_notch_overlay(self) -> None:
        """Build the dynamic notch stack with all upstream interactive phases."""
        self.pill_overlay = Gtk.Overlay()
        self.pill_overlay.set_halign(Gtk.Align.CENTER)
        self.pill_overlay.set_valign(Gtk.Align.END)
        self.pill_overlay.set_size_request(self.CANVAS_WIDTH, self.CANVAS_HEIGHT)
        self.pill_overlay.add_css_class("bottom-notch-pill")

        # Inverted NotchShape background canvas
        self.notch_bg = BottomNotchShapeBackground(top_radius=14.0, shoulder_radius=10.0)
        self.notch_bg.set_size_request(self.CANVAS_WIDTH, self.CANVAS_HEIGHT)
        self.notch_bg.set_notch_size(self._current_width, self._current_height)
        self.pill_overlay.set_child(self.notch_bg)

        # Dynamic Stack for Notch Phases
        self.pill_stack = Gtk.Stack()
        self.pill_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.pill_stack.set_transition_duration(180)
        self.pill_stack.set_hhomogeneous(False)
        self.pill_stack.set_vhomogeneous(False)
        self.pill_stack.set_halign(Gtk.Align.CENTER)
        self.pill_stack.set_valign(Gtk.Align.END)

        # --- Phase 1: Idle Resting Notch (NotchPhase.HIDDEN) ---
        self._build_idle_view()

        # --- Phase 2: Interactive Prompt Input (NotchPhase.TYPING) ---
        self._build_typing_view()

        # --- Phase 3: Active Computer-Use Progress (NotchPhase.RUNNING) ---
        self._build_running_view()

        # --- Phase 4: Inline Response & Reply (NotchPhase.MESSAGE) ---
        self._build_message_view()

        self.pill_overlay.add_overlay(self.pill_stack)
        self.root_box.append(self.pill_overlay)

        # Single shared hover region covering compact and expanded geometry
        self._init_hover_controller()

    def _init_hover_controller(self) -> None:
        """
        Unified hover region covering compact and small interactive notch.
        Hover -> Expand small notch -> Move away -> Collapse after 200ms.
        """
        motion_ctrl = Gtk.EventControllerMotion()
        motion_ctrl.connect("enter", self._on_motion_enter)
        motion_ctrl.connect("leave", self._on_motion_leave)
        self.pill_overlay.add_controller(motion_ctrl)

        # Track active pointer clicks/drags to avoid collapsing during interaction
        click_gesture = Gtk.GestureClick()
        click_gesture.connect("pressed", self._on_pointer_pressed)
        click_gesture.connect("released", self._on_pointer_released)
        click_gesture.connect("stopped", self._on_pointer_released)
        self.pill_overlay.add_controller(click_gesture)

        # Focus controller to keep notch open while typing or focused
        focus_ctrl = Gtk.EventControllerFocus()
        focus_ctrl.connect("leave", self._on_focus_leave)
        self.pill_overlay.add_controller(focus_ctrl)

    def _on_motion_enter(self, _ctrl: Gtk.EventControllerMotion, _x: float, _y: float) -> None:
        self._is_pointer_inside = True

        # Requirement 4: Cancel pending collapse immediately if pointer re-enters
        if self._collapse_timer_id != 0:
            GLib.source_remove(self._collapse_timer_id)
            self._collapse_timer_id = 0

        # Requirement 2: Pointer enters compact notch -> smoothly expand into small interactive notch
        if not self.is_expanded and self.phase == NotchPhase.HIDDEN:
            self.set_phase(NotchPhase.TYPING)

    def _on_motion_leave(self, _ctrl: Gtk.EventControllerMotion) -> None:
        self._is_pointer_inside = False
        self._maybe_schedule_collapse()

    def _on_pointer_pressed(self, _gesture, _n_press, _x, _y) -> None:
        self._is_pointer_pressed = True
        if self._collapse_timer_id != 0:
            GLib.source_remove(self._collapse_timer_id)
            self._collapse_timer_id = 0

    def _on_pointer_released(self, _gesture, _n_press=None, _x=None, _y=None) -> None:
        self._is_pointer_pressed = False
        if not self._is_pointer_inside:
            self._maybe_schedule_collapse()

    def _on_focus_leave(self, _ctrl: Gtk.EventControllerFocus) -> None:
        if not self._is_pointer_inside:
            self._maybe_schedule_collapse()

    def _on_entry_focus_changed(self, entry: Gtk.Entry, _param) -> None:
        if not entry.has_focus() and not self._is_pointer_inside:
            self._maybe_schedule_collapse()

    def _maybe_schedule_collapse(self) -> None:
        if self.is_expanded or self.phase == NotchPhase.HIDDEN:
            return

        # Requirement 5: Keep notch open while task is running
        if self.is_running or self.phase == NotchPhase.RUNNING:
            return

        # Keep open while typing entry has focus or text
        if self.phase == NotchPhase.TYPING:
            if self.typing_entry.has_focus() or bool(self.typing_entry.get_text().strip()):
                return

        # Keep open while reply entry has focus or text
        if self.phase == NotchPhase.MESSAGE:
            if self.reply_entry.has_focus() or bool(self.reply_entry.get_text().strip()):
                return

        # Requirement 6: Do not collapse during active pointer interaction
        if self._is_pointer_pressed:
            return

        # Requirement 3: Automatically collapse after 200 ms delay
        if self._collapse_timer_id != 0:
            GLib.source_remove(self._collapse_timer_id)
        self._collapse_timer_id = GLib.timeout_add(200, self._on_collapse_timeout)

    def _on_collapse_timeout(self) -> bool:
        self._collapse_timer_id = 0
        if not self._is_pointer_inside and not self.is_expanded:
            if self.is_running or self.phase == NotchPhase.RUNNING:
                return False
            if self.phase == NotchPhase.TYPING:
                if self.typing_entry.has_focus() or bool(self.typing_entry.get_text().strip()):
                    return False
            if self.phase == NotchPhase.MESSAGE:
                if self.reply_entry.has_focus() or bool(self.reply_entry.get_text().strip()):
                    return False
            if self._is_pointer_pressed:
                return False

            self.set_phase(NotchPhase.HIDDEN)
        return False

    def _build_idle_view(self) -> None:
        """Resting notch (340x44): Completely hover-driven to expand into TYPING."""
        self.idle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.idle_box.add_css_class("bottom-notch-content")
        self.idle_box.set_valign(Gtk.Align.END)
        self.idle_box.set_halign(Gtk.Align.CENTER)
        self.idle_box.set_size_request(340, 44)

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

        # Removed expand glyph ⌃ and click gesture: small notch is hover-driven

        self.pill_stack.add_named(self.idle_box, "hidden")

    def _build_typing_view(self) -> None:
        """Interactive notch for quick prompt (480x72): Esc cancels, Send submits."""
        self.typing_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.typing_box.add_css_class("bottom-notch-content")
        self.typing_box.set_valign(Gtk.Align.END)
        self.typing_box.set_halign(Gtk.Align.CENTER)
        self.typing_box.set_size_request(480, 72)
        self.typing_box.set_margin_start(16)
        self.typing_box.set_margin_end(16)
        self.typing_box.set_margin_top(8)
        self.typing_box.set_margin_bottom(8)

        # Top Bar: Mascot + "Sidekick" + Send (no expand/collapse buttons)
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        mascot = LivingMascot(size=16, low_power=self.low_power, reduced_motion=self.reduced_motion)
        top_row.append(mascot)

        title = Gtk.Label(label="Sidekick")
        title.add_css_class("sidekick-card-subtitle")
        title.set_hexpand(True)
        title.set_xalign(0.0)
        top_row.append(title)

        self.typing_send_btn = Gtk.Button(label="↑")
        self.typing_send_btn.add_css_class("notch-send-pill")
        self.typing_send_btn.set_sensitive(False)
        self.typing_send_btn.connect("clicked", lambda _: self._on_typing_submit())
        top_row.append(self.typing_send_btn)

        self.typing_box.append(top_row)

        # Input Field: "What can I take over for you?"
        self.typing_entry = Gtk.Entry()
        self.typing_entry.set_placeholder_text("What can I take over for you?")
        self.typing_entry.add_css_class("notch-typing-entry")
        self.typing_entry.connect("changed", self._on_typing_changed)
        self.typing_entry.connect("activate", lambda _: self._on_typing_submit())
        self.typing_entry.connect("notify::has-focus", self._on_entry_focus_changed)
        self.typing_box.append(self.typing_entry)

        self.pill_stack.add_named(self.typing_box, "typing")

    def _build_running_view(self) -> None:
        """Active progress notch (420x68): GlowHalo edge glow, status narration, STOP button."""
        self.running_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.running_box.add_css_class("bottom-notch-content")
        self.running_box.set_valign(Gtk.Align.END)
        self.running_box.set_halign(Gtk.Align.CENTER)
        self.running_box.set_size_request(420, 68)
        self.running_box.set_margin_start(16)
        self.running_box.set_margin_end(16)
        self.running_box.set_margin_top(8)
        self.running_box.set_margin_bottom(8)

        # Top row: Logo + Sidekick indicator + STOP (no expand buttons)
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.running_mascot = LivingMascot(size=16, low_power=self.low_power, reduced_motion=self.reduced_motion)
        self.running_mascot.set_state(MascotState.THINKING)
        top_row.append(self.running_mascot)

        run_title = Gtk.Label(label="Sidekick")
        run_title.add_css_class("sidekick-work-status")
        run_title.set_hexpand(True)
        run_title.set_xalign(0.0)
        top_row.append(run_title)

        stop_btn = Gtk.Button(label="■")
        stop_btn.add_css_class("sidekick-stop-btn")
        stop_btn.set_tooltip_text("Stop this task")
        stop_btn.connect("clicked", lambda _: self.stop_task())
        top_row.append(stop_btn)

        self.running_box.append(top_row)

        # Bottom row: Live Monospace status narration
        self.status_line = Gtk.Label(label="Consulting desktop context & reasoning…")
        self.status_line.add_css_class("whisper-text")
        self.status_line.set_xalign(0.0)
        self.status_line.set_ellipsize(Pango.EllipsizeMode.END)
        self.status_line.set_max_width_chars(38)
        self.running_box.append(self.status_line)

        self.pill_stack.add_named(self.running_box, "running")

    def _build_message_view(self) -> None:
        """Inline response & reply view (520x220) (SidekickNotchMessageView parity)."""
        self.message_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.message_box.add_css_class("bottom-notch-content")
        self.message_box.set_valign(Gtk.Align.END)
        self.message_box.set_halign(Gtk.Align.CENTER)
        self.message_box.set_size_request(520, 220)
        self.message_box.set_margin_start(16)
        self.message_box.set_margin_end(16)
        self.message_box.set_margin_top(8)
        self.message_box.set_margin_bottom(10)

        # Header: Mascot + Title + Timestamp + Close
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        msg_mascot = LivingMascot(size=14, low_power=self.low_power, reduced_motion=self.reduced_motion)
        hdr.append(msg_mascot)

        self.msg_title_lbl = Gtk.Label(label="Sidekick")
        self.msg_title_lbl.add_css_class("sidekick-card-subtitle")
        hdr.append(self.msg_title_lbl)

        self.msg_time_lbl = Gtk.Label(label="")
        self.msg_time_lbl.add_css_class("whisper-text")
        self.msg_time_lbl.set_hexpand(True)
        self.msg_time_lbl.set_xalign(0.0)
        hdr.append(self.msg_time_lbl)

        close_btn = Gtk.Button(label="✕")
        close_btn.add_css_class("notch-icon-btn")
        close_btn.set_tooltip_text("Hide response (stays in history)")
        close_btn.connect("clicked", lambda _: self.set_phase(NotchPhase.HIDDEN))
        hdr.append(close_btn)

        self.message_box.append(hdr)

        # Scrollable response text area
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_max_content_height(100)
        scroller.set_min_content_height(50)
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)

        self.message_text_label = Gtk.Label(label="")
        self.message_text_label.add_css_class("notch-message-text")
        self.message_text_label.set_wrap(True)
        self.message_text_label.set_selectable(True)
        self.message_text_label.set_xalign(0.0)
        scroller.set_child(self.message_text_label)
        self.message_box.append(scroller)

        # Reply row (capsule with input and send button)
        reply_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        reply_capsule = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        reply_capsule.add_css_class("notch-reply-box")
        reply_capsule.set_hexpand(True)

        self.reply_entry = Gtk.Entry()
        self.reply_entry.set_placeholder_text("Reply to Sidekick…")
        self.reply_entry.add_css_class("notch-reply-entry")
        self.reply_entry.set_hexpand(True)
        self.reply_entry.connect("activate", lambda _: self._on_inline_reply_submit())
        self.reply_entry.connect("notify::has-focus", self._on_entry_focus_changed)
        reply_capsule.append(self.reply_entry)

        send_reply_btn = Gtk.Button(label="↑")
        send_reply_btn.add_css_class("notch-send-pill")
        send_reply_btn.connect("clicked", lambda _: self._on_inline_reply_submit())
        reply_capsule.append(send_reply_btn)
        reply_row.append(reply_capsule)

        self.message_box.append(reply_row)

        self.pill_stack.add_named(self.message_box, "message")

    def _update_input_region(self) -> None:
        """
        Confine pointer interception strictly to the visible notch silhouette.
        Ensures all transparent areas outside the notch pass clicks and hovers through
        directly to underlying desktop windows without creating an invisible blocking box.
        """
        native = self.get_native()
        if not native:
            return
        surface = native.get_surface()
        if not surface:
            return

        if self.is_expanded:
            rect = cairo.RectangleInt(0, 0, self.EXPANDED_WIDTH, self.EXPANDED_HEIGHT)
        else:
            cx = self.CANVAS_WIDTH / 2.0
            w = self._current_width
            h = self._current_height
            left = max(0, int(math.floor(cx - w / 2.0)))
            top = max(0, int(math.floor(self.CANVAS_HEIGHT - h)))
            width_int = min(self.CANVAS_WIDTH - left, int(math.ceil(w)))
            height_int = min(self.CANVAS_HEIGHT - top, int(math.ceil(h)))
            rect = cairo.RectangleInt(left, top, width_int, height_int)

        region = cairo.Region(rect)
        surface.set_input_region(region)

    def _on_morph_tick(self, _widget: Gtk.Widget, frame_clock: Gdk.FrameClock) -> bool:
        """Frame-clock tick animation for smooth, symmetric notch morphing."""
        if self.is_expanded:
            self._morph_tick_id = 0
            return False

        frame_time = frame_clock.get_frame_time()
        if self._last_frame_time == 0:
            dt = 0.016
        else:
            dt = (frame_time - self._last_frame_time) / 1_000_000.0
            dt = max(0.001, min(0.05, dt))
        self._last_frame_time = frame_time

        tw = self._target_width
        th = self._target_height

        if self.reduced_motion:
            self._current_width = tw
            self._current_height = th
            self.notch_bg.set_notch_size(self._current_width, self._current_height)
            self._update_input_region()
            self._morph_tick_id = 0
            return False

        # Physics-based smooth spring/decay interpolation (~220ms settling time)
        alpha = min(1.0, 1.0 - math.exp(-22.0 * dt))
        dw = tw - self._current_width
        dh = th - self._current_height

        if abs(dw) < 0.25 and abs(dh) < 0.25:
            self._current_width = tw
            self._current_height = th
            self.notch_bg.set_notch_size(self._current_width, self._current_height)
            self._update_input_region()
            self._morph_tick_id = 0
            return False

        self._current_width += dw * alpha
        self._current_height += dh * alpha

        self.notch_bg.set_notch_size(self._current_width, self._current_height)
        self._update_input_region()
        return True

    def open_notch_input(self) -> None:
        """Clicking resting notch enters interactive quick prompt mode."""
        if self.is_running:
            self.set_phase(NotchPhase.RUNNING)
            return
        self.set_phase(NotchPhase.TYPING)

    def set_phase(self, phase: NotchPhase, message_text: str = "") -> None:
        """Switch notch phase and smoothly animate geometry without window resizing."""
        self.phase = phase
        w, h = self.PHASE_DIMENSIONS[phase]

        # Edge glow active during RUNNING phase
        is_running = (phase == NotchPhase.RUNNING)
        self.is_running = is_running
        self.notch_bg.set_glow(is_running)

        if phase == NotchPhase.RUNNING:
            self.running_mascot.set_state(MascotState.THINKING)
        elif phase == NotchPhase.MESSAGE:
            if message_text:
                self.message_text_label.set_text(message_text)
            self.msg_time_lbl.set_text(time.strftime("%H:%M"))
            self.reply_entry.set_text("")
        elif phase == NotchPhase.HIDDEN:
            self.pill_mascot.set_state(MascotState.IDLE)

        self.pill_stack.set_visible_child_name(phase.value)

        if not self.is_expanded:
            self._target_width = float(w)
            self._target_height = float(h)

            if self.reduced_motion:
                self._current_width = float(w)
                self._current_height = float(h)
                self.notch_bg.set_notch_size(float(w), float(h))
                self._update_input_region()
            else:
                if self._morph_tick_id == 0:
                    self._last_frame_time = 0
                    self._morph_tick_id = self.add_tick_callback(self._on_morph_tick)

            # Keyboard focus handling
            if phase in (NotchPhase.TYPING, NotchPhase.MESSAGE):
                Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.ON_DEMAND)
                if phase == NotchPhase.TYPING:
                    self.typing_entry.grab_focus()
                elif phase == NotchPhase.MESSAGE:
                    self.reply_entry.grab_focus()
            else:
                Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)

        logger.info("Sentient Notch transitioned to phase: %s", phase.value)

    def set_running(self, running: bool, status: str = "") -> None:
        """Compatibility method for external task state updates."""
        if running:
            if status:
                self.status_line.set_text(status)
            self.set_phase(NotchPhase.RUNNING)
        else:
            self.set_phase(NotchPhase.HIDDEN)

    def _on_typing_changed(self, entry: Gtk.Entry) -> None:
        text = entry.get_text().strip()
        self.typing_send_btn.set_sensitive(bool(text))
        if not text and not self._is_pointer_inside and not entry.has_focus():
            self._maybe_schedule_collapse()

    def _on_typing_submit(self) -> None:
        prompt = self.typing_entry.get_text().strip()
        if not prompt or self.is_running:
            return
        self.typing_entry.set_text("")
        self.submit_prompt(prompt)

    def _on_inline_reply_submit(self) -> None:
        reply = self.reply_entry.get_text().strip()
        if not reply or self.is_running:
            return
        self.reply_entry.set_text("")
        self.submit_prompt(reply)

    def submit_prompt(self, prompt: str) -> None:
        """Submit a prompt from the notch: records message, enters RUNNING, runs inference."""
        # Reset coordinator if recovering from STOPPED
        try:
            self.coordinator.reset()
        except Exception:
            pass

        self._current_request_id += 1
        req_id = self._current_request_id
        self._task_start_time = time.perf_counter()

        # Record in shared conversation store
        if hasattr(self.coordinator, "conversation") and self.coordinator.conversation:
            self.coordinator.conversation.append_message("user", prompt)

        self.set_phase(NotchPhase.RUNNING)
        self.status_line.set_text("Consulting desktop context & reasoning…")

        # Execute asynchronously
        threading.Thread(target=self._execute_task, args=(prompt, req_id), daemon=True).start()

    def _execute_task(self, prompt: str, req_id: int) -> None:
        if req_id != self._current_request_id:
            return
        try:
            if hasattr(self.coordinator, "run_task"):
                res = self.coordinator.run_task(prompt)
                output = res.summary if hasattr(res, "summary") else str(res)
            else:
                output = self.coordinator.ask(prompt=prompt, include_context=True)
            GLib.idle_add(self._finish_task, True, output, req_id)
        except Exception as err:
            GLib.idle_add(self._finish_task, False, f"Inference error: {err}", req_id)

    def _finish_task(self, success: bool, message: str, req_id: int) -> None:
        if req_id != self._current_request_id:
            return

        elapsed = time.perf_counter() - self._task_start_time

        # Record in shared conversation store
        if hasattr(self.coordinator, "conversation") and self.coordinator.conversation:
            self.coordinator.conversation.append_message(
                role="assistant",
                text=message,
                duration_s=elapsed,
                status="done" if success else "failed",
            )

        if self.is_expanded:
            # If full conversation is open, update it
            self.expanded_view._finish_running(success, message, req_id)
        else:
            # Show inline response in the notch
            self.set_phase(NotchPhase.MESSAGE, message_text=message)

    def stop_task(self) -> None:
        """Cancel active task immediately."""
        self._current_request_id += 1
        req_id = self._current_request_id
        try:
            self.coordinator.stop(reason="User stopped Sidekick task")
        except Exception:
            pass

        if hasattr(self.coordinator, "conversation") and self.coordinator.conversation:
            self.coordinator.conversation.append_message(
                role="assistant",
                text="Task stopped by user.",
                status="stopped",
            )

        self.status_line.set_text("Stopped")
        GLib.timeout_add(1200, lambda: self.set_phase(NotchPhase.HIDDEN) if self.phase == NotchPhase.RUNNING else False)

    def expand(self, draft: str = "") -> None:
        """
        Explicit action to open the Full Sidekick conversation interface (780x580).
        Triggered ONLY via arrow.up.forward.app / Open in Sentient, NOT by clicking the resting notch.
        """
        if self.is_expanded:
            return

        self.is_expanded = True
        if self._morph_tick_id != 0:
            self.remove_tick_callback(self._morph_tick_id)
            self._morph_tick_id = 0

        # Sync conversation records from shared store
        self.expanded_view.sync_from_store()
        if draft:
            self.expanded_view.chat_entry.set_text(draft)

        # Synchronously swap child to expanded view
        self.set_visible(False)
        if self.pill_overlay.get_parent() is not None:
            self.pill_overlay.get_parent().remove(self.pill_overlay)
        if self.expanded_view.get_parent() is None:
            self.root_box.append(self.expanded_view)

        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.ON_DEMAND)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 0)
        self.root_box.set_size_request(self.EXPANDED_WIDTH, self.EXPANDED_HEIGHT)
        self.set_size_request(self.EXPANDED_WIDTH, self.EXPANDED_HEIGHT)
        self.set_default_size(self.EXPANDED_WIDTH, self.EXPANDED_HEIGHT)
        self.set_visible(True)
        self._update_input_region()

        self.expanded_view.chat_entry.grab_focus()
        logger.info("Sentient Sidekick full conversation opened.")

    def collapse(self) -> None:
        """Collapse back to bottom-attached dynamic island notch without discarding state."""
        self.is_expanded = False

        # Preserve any unsubmitted draft in shared store
        draft_text = self.expanded_view.chat_entry.get_text()
        if hasattr(self.coordinator, "conversation") and self.coordinator.conversation and draft_text:
            self.coordinator.conversation.draft = draft_text

        # Restore notch child
        self.set_visible(False)
        if self.expanded_view.get_parent() is not None:
            self.expanded_view.get_parent().remove(self.expanded_view)
        if self.pill_overlay.get_parent() is None:
            self.root_box.append(self.pill_overlay)

        # Restore fixed canvas dimensions and notch geometry
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 0)
        self.root_box.set_size_request(self.CANVAS_WIDTH, self.CANVAS_HEIGHT)
        self.set_size_request(self.CANVAS_WIDTH, self.CANVAS_HEIGHT)
        self.set_default_size(self.CANVAS_WIDTH, self.CANVAS_HEIGHT)
        self.set_phase(self.phase)
        self.set_visible(True)
        self._update_input_region()
        logger.info("Sentient Sidekick collapsed to bottom notch.")

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
            elif self.phase == NotchPhase.TYPING:
                self.typing_entry.set_text("")
                self.set_phase(NotchPhase.HIDDEN)
                return True
            elif self.phase == NotchPhase.MESSAGE:
                self.reply_entry.set_text("")
                self.set_phase(NotchPhase.HIDDEN)
                return True
        return False
