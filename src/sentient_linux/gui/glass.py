"""
Living Glass container for Sentient Linux.
Renders frosted glass surfaces, subtle depth shadows, and rotating edge highlights.
"""

from __future__ import annotations
import math
import time
from typing import Optional

import cairo
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gtk, GLib

from sentient_linux.gui.theme import THEME


class LivingGlassContainer(Gtk.Box):
    """
    A GTK4 container with custom Cairo background rendering.
    Draws dark acrylic glass, ambient drop shadow, and procedural AI-spectrum rim highlights.
    """

    def __init__(
        self,
        orientation: Gtk.Orientation = Gtk.Orientation.HORIZONTAL,
        spacing: int = 10,
        corner_radius: float = 20.0,
        show_glow_border: bool = True,
    ) -> None:
        super().__init__(orientation=orientation, spacing=spacing)
        self.corner_radius = corner_radius
        self.show_glow_border = show_glow_border
        self.active_glow: bool = False
        self.hovered: bool = False

        self._start_time = time.perf_counter()

        # Connect drawing through a custom Gtk.DrawingArea background or css styling
        self.add_css_class("living-glass-pill")

    def set_active_glow(self, active: bool) -> None:
        self.active_glow = active
        self.queue_draw()

    def set_hovered(self, hovered: bool) -> None:
        self.hovered = hovered
        self.queue_draw()
