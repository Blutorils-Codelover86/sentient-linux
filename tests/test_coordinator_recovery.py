"""
Regression tests for coordinator state machine recovery, error surfacing,
concurrent request serialization, emergency stop, and UI stale callback gating.
"""

from __future__ import annotations
import threading
import time
from unittest.mock import MagicMock, patch
import pytest

from sentient_linux.core.coordinator import CommandCoordinator, TaskResult
from sentient_linux.core.state_machine import SentientState, StateTransitionError
from sentient_linux.security.emergency_stop import EmergencyStop
from sentient_linux.gui.expanded_view import ExpandedView


@pytest.fixture(autouse=True)
def clean_emergency_stop():
    """Ensure emergency stop singleton is clean before and after each test."""
    EmergencyStop().reset()
    yield
    EmergencyStop().reset()


def test_failed_inference_surfaces_actual_error():
    """
    Ensure a failed inference surfaces the actual underlying error
    rather than a StateTransitionError, and leaves coordinator in ERROR.
    """
    coordinator = CommandCoordinator()
    
    # Mock inference to raise a specific underlying exception
    expected_err_msg = "Ollama connection timeout on port 11434"
    coordinator.inference.ask = MagicMock(side_effect=RuntimeError(expected_err_msg))

    with pytest.raises(RuntimeError, match=expected_err_msg):
        coordinator.ask(prompt="Tell me a joke", include_context=False)

    # Coordinator must be in ERROR state
    assert coordinator.state_machine.current_state == SentientState.ERROR


def test_recovery_from_error_to_idle_on_next_request():
    """
    Ensure that when coordinator is in ERROR from a prior failure,
    the next request cleanly recovers ERROR -> IDLE and executes without StateTransitionError.
    """
    coordinator = CommandCoordinator()

    # 1. Trigger an error
    coordinator.inference.ask = MagicMock(side_effect=ValueError("Model not found"))
    with pytest.raises(ValueError, match="Model not found"):
        coordinator.ask(prompt="fail prompt", include_context=False)

    assert coordinator.state_machine.current_state == SentientState.ERROR

    # 2. Next request with working inference
    coordinator.inference.ask = MagicMock(return_value="Recovered successfully!")
    res = coordinator.ask(prompt="hello again", include_context=False)

    assert res == "Recovered successfully!"
    assert coordinator.state_machine.current_state == SentientState.IDLE


def test_recovery_via_reset():
    """
    Ensure reset() transitions ERROR -> IDLE and STOPPED -> IDLE cleanly.
    """
    coordinator = CommandCoordinator()

    # Move to ERROR via valid transition path (IDLE -> PERCEIVING -> ERROR)
    coordinator._set_state(SentientState.PERCEIVING)
    coordinator._set_state(SentientState.ERROR)
    assert coordinator.state_machine.current_state == SentientState.ERROR

    # Reset recovers to IDLE
    coordinator.reset()
    assert coordinator.state_machine.current_state == SentientState.IDLE

    # Trigger STOP
    coordinator.stop(reason="User cancelled")
    assert coordinator.state_machine.current_state == SentientState.STOPPED
    assert coordinator.emergency_stop.is_stopped() is True

    # Reset recovers to IDLE and clears emergency stop
    coordinator.reset()
    assert coordinator.state_machine.current_state == SentientState.IDLE
    assert coordinator.emergency_stop.is_stopped() is False


def test_stop_during_idle_and_subsequent_request():
    """
    Ensure stopping from IDLE transitions to STOPPED, and next ask() recovers cleanly.
    """
    coordinator = CommandCoordinator()
    coordinator.inference.ask = MagicMock(return_value="Task completed")

    coordinator.stop(reason="Testing stop")
    assert coordinator.state_machine.current_state == SentientState.STOPPED

    # ask() should reset emergency stop, transition STOPPED -> IDLE, and complete
    res = coordinator.ask(prompt="test prompt", include_context=False)
    assert res == "Task completed"
    assert coordinator.state_machine.current_state == SentientState.IDLE


def test_coordinator_run_task_returns_task_result():
    """
    Ensure run_task() returns a TaskResult object with summary and success flag.
    """
    coordinator = CommandCoordinator()
    coordinator.inference.ask = MagicMock(return_value="Everything looks nominal.")

    res = coordinator.run_task(prompt="Check system status")
    assert isinstance(res, TaskResult)
    assert res.summary == "Everything looks nominal."
    assert res.success is True
    assert coordinator.state_machine.current_state == SentientState.IDLE


def test_concurrent_requests_serialized():
    """
    Verify that concurrent submissions are serialized by _request_lock,
    preventing state corruption.
    """
    coordinator = CommandCoordinator()
    
    execution_order = []

    def mock_ask(prompt: str, **kwargs):
        execution_order.append(f"start:{prompt}")
        time.sleep(0.05)
        execution_order.append(f"end:{prompt}")
        return f"result:{prompt}"

    coordinator.inference.ask = MagicMock(side_effect=mock_ask)

    t1 = threading.Thread(target=coordinator.ask, kwargs={"prompt": "req1", "include_context": False})
    t2 = threading.Thread(target=coordinator.ask, kwargs={"prompt": "req2", "include_context": False})

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Serialization check: start:req1 must end before req2 starts, or vice versa
    assert execution_order[0].startswith("start:")
    assert execution_order[1] == execution_order[0].replace("start:", "end:")
    assert execution_order[2].startswith("start:")
    assert execution_order[3] == execution_order[2].replace("start:", "end:")
    assert coordinator.state_machine.current_state == SentientState.IDLE


def test_gui_stale_callbacks_discarded():
    """
    Verify ExpandedView discards stale async callbacks when request_id does not match.
    """
    coordinator = CommandCoordinator()
    view = ExpandedView(coordinator=coordinator, on_collapse=lambda: None)

    # Initial request ID
    view._current_request_id = 1
    view._is_running = True

    # Stale callback with req_id = 0 should be discarded
    view._update_work_status("Old stale status", req_id=0)
    assert view._work_status_label is None or view._work_status_label.get_text() != "Old stale status"

    # Stale finish running with req_id = 0 should NOT stop or overwrite running view
    view._finish_running(success=True, message="Stale old result", req_id=0)
    assert view._is_running is True

    # Valid callback with matching req_id = 1
    view._finish_running(success=True, message="Fresh valid result", req_id=1)
    assert view._is_running is False
