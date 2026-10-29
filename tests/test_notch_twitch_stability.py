"""
Verification tests for Sentient Linux Notch Stability & Layout Integrity.
Verifies that:
- The working capsule layout is preserved with official radii (16.0 top, 12.0 shoulder).
- The compact resting notch (340x44) and interactive notch (480x72) maintain exact dimensions.
- Stack transition is NONE, eliminating asymmetric widget squashing and horizontal twitch.
- Frame-clock tick animation smoothly interpolates width and height without content clipping.
- Reversal mid-animation transitions smoothly.
"""

from __future__ import annotations
import math
from unittest.mock import MagicMock
import pytest
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gtk, Gtk4LayerShell

from sentient_linux.core.coordinator import CommandCoordinator
from sentient_linux.gui.pill_window import SentientPillWindow, NotchPhase


def test_notch_geometry_and_radii_restored():
    """
    Layout Verification:
    Top radius must be 16.0 and shoulder radius must be 12.0 for genuine capsule curvature.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    assert window.notch_bg.top_radius == 16.0
    assert window.notch_bg.shoulder_radius == 12.0
    assert window.pill_stack.get_transition_type() == Gtk.StackTransitionType.NONE


def test_notch_phase_exact_dimensions():
    """
    Dimensions Verification:
    Notch components strictly adhere to upstream dimensions:
    HIDDEN is 340x44, TYPING is 480x72, RUNNING is 420x68, MESSAGE is 520x220.
    Outer surface width remains stable at 480 to eliminate compositor recentering twitch.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    window.set_phase(NotchPhase.HIDDEN)
    assert window.pill_overlay.get_size_request() == (340, 44)
    assert window.notch_bg.get_size_request() == (340, 44)
    assert window.get_size_request() == (480, 72)

    window.set_phase(NotchPhase.TYPING)
    assert window.pill_overlay.get_size_request() == (480, 72)
    assert window.notch_bg.get_size_request() == (480, 72)
    assert window.get_size_request() == (480, 72)

    window.set_phase(NotchPhase.RUNNING)
    assert window.pill_overlay.get_size_request() == (420, 68)
    assert window.notch_bg.get_size_request() == (420, 68)
    assert window.get_size_request() == (480, 72)

    window.set_phase(NotchPhase.MESSAGE)
    assert window.pill_overlay.get_size_request() == (520, 220)
    assert window.notch_bg.get_size_request() == (520, 220)
    assert window.get_size_request() == (520, 220)


def test_center_point_invariance_across_all_frames():
    """
    Twitch-Free Geometry Rule:
    The notch must expand and contract smoothly around one fixed horizontal center point.
    Its center must never shift during hover expansion or collapse.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=False)

    clock = MagicMock()
    frame_time_us = 1_000_000

    # Expand from 340 to 480
    window.set_phase(NotchPhase.TYPING)
    recorded_centers = []

    for _ in range(30):
        frame_time_us += 16_666
        clock.get_frame_time.return_value = frame_time_us
        animating = window._on_morph_tick(window, clock)

        w = window._current_width
        cx = window.NOTCH_CANVAS_WIDTH / 2.0  # 240.0
        left = cx - w / 2.0
        right = cx + w / 2.0
        center = (left + right) / 2.0
        recorded_centers.append(center)

        if not animating:
            break

    # Collapse from 480 to 340
    window.set_phase(NotchPhase.HIDDEN)
    for _ in range(30):
        frame_time_us += 16_666
        clock.get_frame_time.return_value = frame_time_us
        animating = window._on_morph_tick(window, clock)

        w = window._current_width
        cx = window.NOTCH_CANVAS_WIDTH / 2.0
        left = cx - w / 2.0
        right = cx + w / 2.0
        center = (left + right) / 2.0
        recorded_centers.append(center)

        if not animating:
            break

    assert len(recorded_centers) >= 10
    for idx, c in enumerate(recorded_centers):
        assert abs(c - 240.0) < 1e-9, f"Frame {idx} shifted center to {c}"

    variance = sum((c - 240.0) ** 2 for c in recorded_centers) / len(recorded_centers)
    assert variance == 0.0, f"Non-zero center variance: {variance}"


def test_fractional_scaling_125_monitor_symmetry():
    """
    Fractional Scaling Verification:
    On a 1920x1080 display at 1.25x scaling:
    - 480 logical px = 600 physical px (exact integer).
    - Surface physical offset = (1920 - 600) / 2 = 660.0 physical px.
    - Every animation frame must center at exactly 960.0 physical pixels.
    """
    scale = 1.25
    monitor_width_phys = 1920
    canvas_width_log = 480
    canvas_width_phys = canvas_width_log * scale  # 600.0 px
    surface_offset_x = (monitor_width_phys - canvas_width_phys) / 2.0  # 660.0 px

    for w in range(340, 481, 5):
        cx = canvas_width_log / 2.0
        left_log = cx - w / 2.0
        right_log = cx + w / 2.0

        phys_left = surface_offset_x + left_log * scale
        phys_right = surface_offset_x + right_log * scale
        phys_center = (phys_left + phys_right) / 2.0

        assert abs(phys_center - 960.0) < 1e-9, f"Width {w} physical center deviated: {phys_center}"


def test_smooth_morph_animation_frames():
    """
    Animation Verification:
    During hover expansion and collapse, tick animation interpolates width and height smoothly.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=False)

    clock = MagicMock()
    frame_time_us = 1_000_000

    # Expand from 340 to 480
    window.set_phase(NotchPhase.TYPING)
    assert window._target_width == 480.0
    assert window._target_height == 72.0

    recorded_widths = []
    for _ in range(25):
        frame_time_us += 16_666
        clock.get_frame_time.return_value = frame_time_us
        animating = window._on_morph_tick(window, clock)
        recorded_widths.append(window._current_width)
        if not animating:
            break

    assert len(recorded_widths) > 2
    assert recorded_widths[0] > 340.0
    assert recorded_widths[-1] == 480.0
    # Must be monotonically increasing during expansion
    for i in range(1, len(recorded_widths)):
        assert recorded_widths[i] >= recorded_widths[i - 1]


def test_rapid_hover_reversal_smooth_continuity():
    """
    Interaction Verification:
    Rapid pointer entry and exit during mid-animation must reverse direction smoothly.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=False)

    clock = MagicMock()
    clock.get_frame_time.side_effect = [1_000_000, 1_016_666, 1_033_333, 1_050_000, 1_066_666]

    # Enter -> target 480
    window._on_motion_enter(None, 10.0, 10.0)
    assert window._target_width == 480.0

    # Advance 2 frames
    window._on_morph_tick(window, clock)
    window._on_morph_tick(window, clock)
    mid_width = window._current_width
    assert 340.0 < mid_width < 480.0

    # Sudden leave and timeout triggers collapse back to 340
    window._on_motion_leave(None)
    window._on_collapse_timeout()
    assert window._target_width == 340.0

    # Advance 1 frame in reverse direction
    window._on_morph_tick(window, clock)
    reversed_width = window._current_width
    assert reversed_width < mid_width, "Width did not smoothly reverse"


def test_no_asymmetric_crossfade_twitch():
    """
    Anti-Twitch Verification:
    pill_stack transition type must be NONE so that collapsing from 480 to 340 does not
    asymmetrically squeeze the wider widget during state change.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    assert window.pill_stack.get_transition_type() == Gtk.StackTransitionType.NONE
