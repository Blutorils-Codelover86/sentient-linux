"""
Comprehensive verification tests for the official Sentient OS Notch hover interaction:
- The compact notch is completely hover-driven.
- Pointer entry smoothly expands compact resting notch into interactive quick prompt (TYPING).
- Pointer leave schedules a 200 ms collapse timer.
- Re-entering pointer cancels pending collapse immediately.
- Keyboard focus, active typing, or running task prevents collapse.
- Active pointer press / drag prevents collapse.
- No expand, collapse, or dropdown buttons in the small notch.
- Full Sidekick conversation remains a separate explicit action (window.expand()).
- STOP from notch cancels task cleanly and recovers state machine.
- Shared conversation store synchronizes seamlessly between Notch and Full Sidekick.
"""

from __future__ import annotations
import time
from unittest.mock import MagicMock
import pytest
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gtk, Gtk4LayerShell, GLib

from sentient_linux.core.coordinator import CommandCoordinator, TaskResult
from sentient_linux.core.state_machine import SentientState
from sentient_linux.security.emergency_stop import EmergencyStop
from sentient_linux.gui.pill_window import SentientPillWindow, NotchPhase
from sentient_linux.gui.mascot import MascotState


@pytest.fixture(autouse=True)
def clean_emergency_stop():
    EmergencyStop().reset()
    yield
    EmergencyStop().reset()


def test_resting_notch_hover_enters_typing_phase():
    """
    Requirement 2: When the pointer enters the compact notch, smoothly expand it
    into the existing small interactive notch (TYPING), not full Sidekick.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    # Initial resting state (HIDDEN)
    assert window.phase == NotchPhase.HIDDEN
    assert window.is_expanded is False
    assert window.pill_stack.get_visible_child_name() == "hidden"
    assert Gtk4LayerShell.get_keyboard_mode(window) == Gtk4LayerShell.KeyboardMode.NONE

    # Pointer enters compact notch
    window._on_motion_enter(None, 10.0, 10.0)

    # Must transition to interactive TYPING phase
    assert window.phase == NotchPhase.TYPING
    # Must NOT have opened full sidekick
    assert window.is_expanded is False
    assert window.pill_stack.get_visible_child_name() == "typing"
    assert Gtk4LayerShell.get_keyboard_mode(window) == Gtk4LayerShell.KeyboardMode.ON_DEMAND
    assert window.typing_entry.get_placeholder_text() == "What can I take over for you?"


def test_pointer_leave_schedules_200ms_collapse():
    """
    Requirement 3: When the pointer leaves the notch, automatically collapse it after 200 ms delay.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    window._on_motion_enter(None, 10.0, 10.0)
    assert window.phase == NotchPhase.TYPING

    # Pointer leaves
    window._on_motion_leave(None)
    assert window._is_pointer_inside is False
    assert window._collapse_timer_id != 0

    # Execute collapse timeout
    window._on_collapse_timeout()
    assert window.phase == NotchPhase.HIDDEN
    assert window.is_expanded is False


def test_pointer_reentry_cancels_pending_collapse():
    """
    Requirement 4: Cancel the pending collapse immediately if the pointer re-enters.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    window._on_motion_enter(None, 10.0, 10.0)
    window._on_motion_leave(None)
    assert window._collapse_timer_id != 0

    # Pointer re-enters within 200 ms
    window._on_motion_enter(None, 10.0, 10.0)
    assert window._collapse_timer_id == 0
    assert window.phase == NotchPhase.TYPING
    assert window._is_pointer_inside is True


def test_typing_text_and_focus_prevents_collapse():
    """
    Requirement 5: Keep the notch open while its input has focus or while user is typing.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    window._on_motion_enter(None, 10.0, 10.0)
    window.typing_entry.set_text("Drafting a prompt...")

    # Pointer leaves while text is present
    window._on_motion_leave(None)
    # Must NOT schedule collapse because text is active
    assert window._collapse_timer_id == 0
    assert window.phase == NotchPhase.TYPING


def test_active_pointer_interaction_prevents_collapse():
    """
    Requirement 6: Do not collapse the notch during an active pointer interaction.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    window._on_motion_enter(None, 10.0, 10.0)
    # Simulate mouse button pressed
    window._on_pointer_pressed(None, 1, 10.0, 10.0)
    assert window._is_pointer_pressed is True

    # Moving outside while pressed
    window._on_motion_leave(None)
    assert window._collapse_timer_id == 0
    assert window.phase == NotchPhase.TYPING

    # Release pointer outside -> now schedules collapse
    window._on_pointer_released(None)
    assert window._is_pointer_pressed is False
    assert window._collapse_timer_id != 0


def test_no_expand_collapse_or_dropdown_buttons_in_small_notch():
    """
    Requirement 1: Remove the expand, collapse, and dropdown buttons from the small notch.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    # Check idle box has no expand label or buttons
    for child in [window.idle_box.get_first_child()]:
        while child:
            if isinstance(child, Gtk.Button):
                pytest.fail("Found button in small idle notch")
            if isinstance(child, Gtk.Label) and child.get_text() in ("⌃", "⌄", "v"):
                pytest.fail("Found expand/collapse chevron in small idle notch")
            child = child.get_next_sibling()

    # Check typing box has only Send button (no expand/collapse buttons)
    top_row = window.typing_box.get_first_child()
    child = top_row.get_first_child() if top_row else None
    buttons = []
    while child:
        if isinstance(child, Gtk.Button):
            buttons.append(child.get_label())
        child = child.get_next_sibling()

    assert buttons == ["↑"], f"Expected only Send button in typing notch, got {buttons}"


def test_escape_in_typing_phase_returns_to_resting_notch():
    """
    Pressing Escape in TYPING cancels input and returns to HIDDEN resting notch.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    window._on_motion_enter(None, 10.0, 10.0)
    assert window.phase == NotchPhase.TYPING

    # Simulate Escape key press
    handled = window._on_key_pressed(None, gi.repository.Gdk.KEY_Escape, 0, 0)
    assert handled is True
    assert window.phase == NotchPhase.HIDDEN
    assert window.is_expanded is False
    assert Gtk4LayerShell.get_keyboard_mode(window) == Gtk4LayerShell.KeyboardMode.NONE


def test_notch_prompt_submission_and_running_phase():
    """
    Submitting a prompt from the notch transitions to RUNNING with edge glow,
    fast mascot spin, and records the message in shared conversation history.
    """
    coordinator = CommandCoordinator()
    coordinator.ask = MagicMock(return_value="Here is the result.")
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    window._on_motion_enter(None, 10.0, 10.0)
    window.typing_entry.set_text("Search documents for report")

    # Submit prompt
    window._on_typing_submit()

    # Must transition to RUNNING
    assert window.phase == NotchPhase.RUNNING
    assert window.is_running is True
    assert window.is_expanded is False
    assert window.notch_bg.has_glow is True
    assert window.running_mascot.state == MascotState.THINKING

    # User prompt must be saved in shared conversation store
    records = coordinator.conversation.records
    assert len(records) >= 1
    assert records[0].role == "user"
    assert records[0].text == "Search documents for report"


def test_task_completion_transitions_to_message_phase():
    """
    When inference finishes, the notch transitions to NotchPhase.MESSAGE (520x220)
    showing the response text and inline reply input without opening full sidekick.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    # Directly finish task with response
    req_id = window._current_request_id
    window._finish_task(success=True, message="Completed successfully with 3 files.", req_id=req_id)

    # Must be in MESSAGE phase
    assert window.phase == NotchPhase.MESSAGE
    assert window.is_expanded is False
    assert window.message_text_label.get_text() == "Completed successfully with 3 files."
    assert window.reply_entry.get_placeholder_text() == "Reply to Sidekick…"
    assert Gtk4LayerShell.get_keyboard_mode(window) == Gtk4LayerShell.KeyboardMode.ON_DEMAND


def test_inline_reply_submits_from_notch_without_opening_full_sidekick():
    """
    Entering a reply in the inline reply bar submits it directly and
    transitions back to RUNNING without opening the full conversation.
    """
    coordinator = CommandCoordinator()
    coordinator.ask = MagicMock(return_value="Follow-up answer.")
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    window.set_phase(NotchPhase.MESSAGE, message_text="Initial answer")
    window.reply_entry.set_text("Tell me more details")

    # Submit inline reply
    window._on_inline_reply_submit()

    assert window.phase == NotchPhase.RUNNING
    assert window.is_expanded is False
    assert window.notch_bg.has_glow is True

    # Check conversation history has both messages
    records = coordinator.conversation.records
    assert any(r.text == "Tell me more details" and r.role == "user" for r in records)


def test_explicit_expand_opens_full_sidekick():
    """
    Requirement 9: Full Sidekick remains a separate explicit action (window.expand()).
    It syncs messages from the shared store and transfers unsubmitted draft text.
    """
    coordinator = CommandCoordinator()
    coordinator.conversation.append_message("user", "First prompt from notch")
    coordinator.conversation.append_message("assistant", "First answer from notch")

    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    # Explicit expand action
    window.expand(draft="Explicit expanded thought")

    assert window.is_expanded is True
    assert Gtk4LayerShell.get_keyboard_mode(window) == Gtk4LayerShell.KeyboardMode.ON_DEMAND
    assert window.expanded_view.chat_entry.get_text() == "Explicit expanded thought"

    # All history from notch must be rendered in the full transcript
    assert len(window.expanded_view._rendered_record_ids) == 2


def test_collapsing_full_sidekick_preserves_draft_and_returns_to_notch():
    """
    Collapsing the full conversation preserves unsubmitted draft text in the shared store,
    sets is_expanded = False, and returns to the notch without deleting history.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    window.expand()
    window.expanded_view.chat_entry.set_text("Draft from expanded composer")

    # Collapse
    window.collapse()

    assert window.is_expanded is False
    assert coordinator.conversation.draft == "Draft from expanded composer"
    assert window.pill_overlay.get_parent() == window.root_box


def test_stop_task_from_notch():
    """
    Requirement 10: Preserve STOP accessibility from notch.
    Clicking STOP immediately cancels task, calls coordinator.stop(),
    updates status to Stopped, and cleanly recovers coordinator state.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    window.submit_prompt("Long running calculation")
    assert coordinator.state_machine.current_state in (SentientState.PERCEIVING, SentientState.REASONING, SentientState.IDLE)

    # Trigger STOP from notch
    window.stop_task()

    assert window.status_line.get_text() == "Stopped"
    assert coordinator.state_machine.current_state == SentientState.STOPPED
    assert coordinator.emergency_stop.is_stopped() is True

    # Coordinator must be able to reset and accept subsequent requests
    coordinator.reset()
    assert coordinator.state_machine.current_state == SentientState.IDLE
    assert coordinator.emergency_stop.is_stopped() is False
