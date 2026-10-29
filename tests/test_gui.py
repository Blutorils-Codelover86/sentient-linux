"""
Unit tests for Sentient Linux GUI components and Living Intelligence states.
Verifies fidelity to upstream Sentient OS Sidekick design tokens and behaviors.
"""

from __future__ import annotations
import pytest

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gtk, Gtk4LayerShell

from sentient_linux.core.coordinator import CommandCoordinator
from sentient_linux.gui.theme import THEME, SentientPalette
from sentient_linux.gui.mascot import LivingMascot, MascotState, SidekickMark
from sentient_linux.gui.pill_window import SentientPillWindow
from sentient_linux.gui.expanded_view import ExpandedView


def test_theme_palette_values():
    palette = THEME
    assert palette.bg == (0.0, 0.0, 0.0)
    assert len(palette.spectrum_stops) == 8
    assert len(palette.mascot_stops) == 8
    # Seam stop check (saturated gold #f7b23d)
    assert palette.mascot_stops[0] == (0.970, 0.700, 0.240)
    # Upstream SidekickStyle tokens
    assert palette.sidekick_ink == (0.93, 0.93, 0.93)
    assert palette.sidekick_secondary == (0.53, 0.53, 0.53)
    assert palette.sidekick_accent == (0.84, 0.84, 0.84)
    assert palette.user_bubble == (0.075, 0.075, 0.075)


def test_living_mascot_state_transitions():
    mascot = LivingMascot(size=28, reduced_motion=True)
    assert mascot.state == MascotState.IDLE

    # Transition to THINKING (fast spin: 2s period)
    mascot.state = MascotState.THINKING
    assert mascot.state == MascotState.THINKING
    assert mascot._current_period == 2.0

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

    # Return to IDLE (13s period)
    mascot.state = MascotState.IDLE
    assert mascot.state == MascotState.IDLE
    assert mascot._current_period == 13.0


def test_living_mascot_reduced_motion_and_low_power():
    mascot = LivingMascot(size=32, low_power=True, reduced_motion=True)
    assert mascot.low_power is True
    assert mascot.reduced_motion is True

    mascot.set_reduced_motion(False)
    assert mascot.reduced_motion is False

    mascot.set_low_power(False)
    assert mascot.low_power is False


def test_sidekick_mark_widget():
    mark = SidekickMark(size=32, illuminated=True)
    assert mark.size == 32
    assert mark.illuminated is True

    static_mark = SidekickMark(size=18, illuminated=False)
    assert static_mark.size == 18
    assert static_mark.illuminated is False


def test_pill_window_expansion_and_collapse():
    coordinator = CommandCoordinator()

    window = SentientPillWindow(
        app=None,
        coordinator=coordinator,
        reduced_motion=True,
    )

    # Initially collapsed flush to bottom bezel
    assert window.is_expanded is False
    assert Gtk4LayerShell.is_layer_window(window) is True
    assert Gtk4LayerShell.get_layer(window) == Gtk4LayerShell.Layer.TOP
    assert Gtk4LayerShell.get_margin(window, Gtk4LayerShell.Edge.BOTTOM) == 0

    # Test expansion
    window.expand()
    assert window.is_expanded is True
    assert Gtk4LayerShell.get_keyboard_mode(window) == Gtk4LayerShell.KeyboardMode.ON_DEMAND
    assert Gtk4LayerShell.get_margin(window, Gtk4LayerShell.Edge.BOTTOM) == 0

    # Test collapse
    window.collapse()
    assert window.is_expanded is False
    assert Gtk4LayerShell.get_keyboard_mode(window) == Gtk4LayerShell.KeyboardMode.NONE
    assert Gtk4LayerShell.get_margin(window, Gtk4LayerShell.Edge.BOTTOM) == 0


def test_expanded_view_composer_and_empty_state():
    coordinator = CommandCoordinator()
    collapsed = False

    def on_collapse():
        nonlocal collapsed
        collapsed = True

    view = ExpandedView(coordinator=coordinator, on_collapse=on_collapse)
    assert view.coordinator == coordinator

    # Initial empty state present
    assert view.empty_state_box.get_parent() == view.content_box

    # Initial send button is disabled style
    assert "sidekick-send-btn-disabled" in view.send_button.get_css_classes()

    # When user enters text, send button becomes active
    view.chat_entry.set_text("Summarize open windows")
    view._on_entry_changed(view.chat_entry)
    assert "sidekick-send-btn-active" in view.send_button.get_css_classes()

    # When cleared, returns to disabled
    view.chat_entry.set_text("")
    view._on_entry_changed(view.chat_entry)
    assert "sidekick-send-btn-disabled" in view.send_button.get_css_classes()

    # Test collapse callback
    view.on_collapse()
    assert collapsed is True


def test_model_switching_in_gui_and_coordinator():
    coordinator = CommandCoordinator()
    assert coordinator.active_model in ["qwen2.5-coder:3b", "gemma3:1b", "qwen3:1.7b", "heretic-fast:latest"]

    # Switch model programmatically
    coordinator.set_model("gemma3:1b")
    assert coordinator.active_model == "gemma3:1b"

    view = ExpandedView(coordinator=coordinator, on_collapse=lambda: None)
    assert view.model_lbl.get_text() == "gemma3:1b"

    # Switch via GUI view method
    view._select_model("qwen3:1.7b")
    assert coordinator.active_model == "qwen3:1.7b"
    assert view.model_lbl.get_text() == "qwen3:1.7b"
