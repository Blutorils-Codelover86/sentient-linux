"""
Comprehensive verification tests for the official Sentient OS Notch interaction hierarchy:
- Resting notch click opens interactive quick input (TYPING), NOT the full conversation.
- Quick prompt submission from the notch runs task and transitions to RUNNING with edge glow.
- Task completion displays inline response and reply bar (MESSAGE).
- Inline reply from the notch runs without opening the full conversation.
- Explicit arrow.up.forward.app action opens the full Sidekick conversation (EXPANDED).
- Collapsing the full conversation preserves history and draft without interrupting tasks.
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
from gi.repository import Gtk, Gtk4LayerShell

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


def test_resting_notch_click_opens_typing_not_full_conversation():
    """
    Clicking the resting notch must transition to NotchPhase.TYPING (480x72),
    and must NOT open the full-screen expanded Sidekick conversation.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    # Initial resting state (HIDDEN)
    assert window.phase == NotchPhase.HIDDEN
    assert window.is_expanded is False
    assert window.pill_stack.get_visible_child_name() == "hidden"
    assert Gtk4LayerShell.get_keyboard_mode(window) == Gtk4LayerShell.KeyboardMode.NONE

    # User clicks the resting notch
    window.open_notch_input()

    # Must be in interactive TYPING phase
    assert window.phase == NotchPhase.TYPING
    # Must NOT have opened the full expanded conversation window!
    assert window.is_expanded is False
    assert window.pill_stack.get_visible_child_name() == "typing"
    assert Gtk4LayerShell.get_keyboard_mode(window) == Gtk4LayerShell.KeyboardMode.ON_DEMAND
    assert window.typing_entry.get_placeholder_text() == "What can I take over for you?"


def test_escape_in_typing_phase_returns_to_resting_notch():
    """
    Pressing Escape in TYPING cancels input and returns to HIDDEN resting notch.
    """
    coordinator = CommandCoordinator()
    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    window.open_notch_input()
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

    window.open_notch_input()
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


def test_explicit_expand_opens_full_sidekick_with_draft_and_history():
    """
    Clicking arrow.up.forward.app opens the Full Sidekick conversation (780x580).
    It syncs messages from the shared store and transfers unsubmitted draft text.
    """
    coordinator = CommandCoordinator()
    coordinator.conversation.append_message("user", "First prompt from notch")
    coordinator.conversation.append_message("assistant", "First answer from notch")

    window = SentientPillWindow(coordinator=coordinator, reduced_motion=True)

    # User typed a draft in notch and clicked arrow.up.forward.app
    window.open_notch_input()
    window.typing_entry.set_text("Unfinished typed thought")

    # Explicit expand action
    window.expand(draft="Unfinished typed thought")

    assert window.is_expanded is True
    assert Gtk4LayerShell.get_keyboard_mode(window) == Gtk4LayerShell.KeyboardMode.ON_DEMAND
    assert window.expanded_view.chat_entry.get_text() == "Unfinished typed thought"

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
    Clicking STOP in the notch immediately cancels task, calls coordinator.stop(),
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
