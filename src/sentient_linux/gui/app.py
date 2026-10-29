"""
GTK4 Application entry point for Sentient Linux GUI.
Initializes custom styles, displays the bottom-center pill window, and manages lifecycle.
"""

from __future__ import annotations
import ctypes
import os
import signal
import sys
from typing import Optional

# Preload libgtk4-layer-shell with RTLD_GLOBAL before Gtk/libwayland import
for _candidate in ["/usr/lib/libgtk4-layer-shell.so", "/usr/lib64/libgtk4-layer-shell.so"]:
    if os.path.exists(_candidate):
        try:
            ctypes.CDLL(_candidate, ctypes.RTLD_GLOBAL)
            break
        except Exception:
            pass

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib

from sentient_linux.core.coordinator import CommandCoordinator
from sentient_linux.gui.pill_window import SentientPillWindow
from sentient_linux.gui.theme import GTK_CSS


class SentientApplication(Gtk.Application):
    """GTK4 Application instance managing Sentient OS GUI lifecycle."""

    def __init__(
        self,
        coordinator: Optional[CommandCoordinator] = None,
        start_expanded: bool = False,
        low_power: bool = False,
        reduced_motion: bool = False,
    ) -> None:
        super().__init__(application_id="ai.sentient.linux.desktop")
        self.coordinator = coordinator or CommandCoordinator()
        self.start_expanded = start_expanded
        self.low_power = low_power
        self.reduced_motion = reduced_motion
        self.window: Optional[SentientPillWindow] = None

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        self._load_css()

    def do_activate(self) -> None:
        if not self.window:
            self.window = SentientPillWindow(
                app=self,
                coordinator=self.coordinator,
                low_power=self.low_power,
                reduced_motion=self.reduced_motion,
            )

        self.window.present()
        if self.start_expanded:
            self.window.expand()

    def _load_css(self) -> None:
        """Inject Sentient Living Glass CSS styling into Gtk default display."""
        provider = Gtk.CssProvider()
        provider.load_from_data(GTK_CSS.encode("utf-8"))
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )


def run_gui(
    coordinator: Optional[CommandCoordinator] = None,
    start_expanded: bool = False,
    low_power: bool = False,
    reduced_motion: bool = False,
) -> int:
    """Launch the Sentient Linux GUI event loop."""
    app = SentientApplication(
        coordinator=coordinator,
        start_expanded=start_expanded,
        low_power=low_power,
        reduced_motion=reduced_motion,
    )

    # Handle Ctrl+C gracefully
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, app.quit)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, app.quit)

    return app.run([])
