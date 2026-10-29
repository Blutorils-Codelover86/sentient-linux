"""
Unit tests for Sentient Linux GUI components and Living Intelligence states.
"""

from __future__ import annotations
import pytest

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gtk, Gtk4LayerShell

from sentient_linux.core.coordinator import CommandCoordinator
from sentient_linux.gui.theme import THEME, SentientPalette
from sentient_linux.gui.mascot import LivingMascot, MascotState
from sentient_linux.gui.pill_window import SentientPillWindow
from sentient_linux.gui.expanded_view import ExpandedView


def test_theme_palette_values():
    palette = THEME
    assert palette.bg == (0.0, 0.0, 0.0)
    assert len(palette.spectrum_stops) == 8
    assert len(palette.mascot_stops) == 8
    # Seam stop check (saturated gold)
    assert palette.mascot_stops[0] == (0.970, 0.700, 0.240)


def test_living_mascot_state_transitions():
    mascot = LivingMascot(size=28, reduced_motion=True)
    assert mascot.state == MascotState.IDLE

    # Transition to THINKING
    mascot.state = MascotState.THINKING
    assert mascot.state == MascotState.THINKING

    # Transition to AWAITING_APPROVAL
    mascot.state = MascotState.AWAITING_APPROVAL
    assert mascot.state == MascotState.AWAITING_APPROVAL

    # Transition to ERROR
    mascot.state = MascotState.ERROR
    assert mascot.state == MascotState.ERROR
    assert mascot._error_timestamp > 0

    # Transition to ACTING
    mascot.state = MascotState.ACTING
    assert mascot.state == MascotState.ACTING

    # Return to IDLE
    mascot.state = MascotState.IDLE
    assert mascot.state == MascotState.IDLE


def test_living_mascot_reduced_motion_and_low_power():
    mascot = LivingMascot(size=32, low_power=True, reduced_motion=True)
    assert mascot.low_power is True
    assert mascot.reduced_motion is True

    mascot.set_reduced_motion(False)
    assert mascot.reduced_motion is False

    mascot.set_low_power(False)
    assert mascot.low_power is False


def test_pill_window_expansion_and_collapse():
    coordinator = CommandCoordinator()

    window = SentientPillWindow(
        app=None,
        coordinator=coordinator,
        reduced_motion=True,
    )

    # Initially collapsed
    assert window.is_expanded is False
    assert Gtk4LayerShell.is_layer_window(window) is True
    assert Gtk4LayerShell.get_layer(window) == Gtk4LayerShell.Layer.TOP

    # Test expansion
    window.expand()
    assert window.is_expanded is True
    assert Gtk4LayerShell.get_keyboard_mode(window) == Gtk4LayerShell.KeyboardMode.ON_DEMAND

    # Test collapse
    window.collapse()
    assert window.is_expanded is False
    assert Gtk4LayerShell.get_keyboard_mode(window) == Gtk4LayerShell.KeyboardMode.NONE


def test_expanded_view_context_refresh():
    coordinator = CommandCoordinator()
    collapsed = False

    def on_collapse():
        nonlocal collapsed
        collapsed = True

    view = ExpandedView(coordinator=coordinator, on_collapse=on_collapse)
    assert view.coordinator == coordinator

    # Test collapse callback
    view.on_collapse()
    assert collapsed is True
