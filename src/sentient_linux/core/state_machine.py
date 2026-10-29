"""
State machine for Sentient Linux.
Enforces deterministic lifecycle transitions.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, Set


class SentientState(str, Enum):
    IDLE = "idle"
    PERCEIVING = "perceiving"
    REASONING = "reasoning"
    WAITING_CONFIRMATION = "waiting_confirmation"
    EXECUTING = "executing"
    FINISHING = "finishing"
    STOPPED = "stopped"
    ERROR = "error"


class StateTransitionError(RuntimeError):
    """Raised when an illegal state transition is attempted."""
    pass


class StateMachine:
    """
    Guarantees that Sentient lifecycle follows strict state progression.
    Any state can transition to STOPPED or ERROR.
    """

    ALLOWED_TRANSITIONS: Dict[SentientState, Set[SentientState]] = {
        SentientState.IDLE: {
            SentientState.PERCEIVING,
            SentientState.REASONING,
            SentientState.STOPPED,
        },
        SentientState.PERCEIVING: {
            SentientState.REASONING,
            SentientState.IDLE,
            SentientState.STOPPED,
            SentientState.ERROR,
        },
        SentientState.REASONING: {
            SentientState.WAITING_CONFIRMATION,
            SentientState.EXECUTING,
            SentientState.FINISHING,
            SentientState.IDLE,
            SentientState.STOPPED,
            SentientState.ERROR,
        },
        SentientState.WAITING_CONFIRMATION: {
            SentientState.EXECUTING,
            SentientState.IDLE,
            SentientState.STOPPED,
            SentientState.ERROR,
        },
        SentientState.EXECUTING: {
            SentientState.FINISHING,
            SentientState.STOPPED,
            SentientState.ERROR,
        },
        SentientState.FINISHING: {
            SentientState.IDLE,
            SentientState.STOPPED,
            SentientState.ERROR,
        },
        SentientState.STOPPED: {
            SentientState.IDLE,
        },
        SentientState.ERROR: {
            SentientState.IDLE,
            SentientState.STOPPED,
        },
    }

    def __init__(self, initial_state: SentientState = SentientState.IDLE) -> None:
        self._current_state = initial_state

    @property
    def current_state(self) -> SentientState:
        return self._current_state

    def transition_to(self, new_state: SentientState) -> None:
        """Attempt to transition to new_state."""
        if new_state == self._current_state:
            return

        allowed = self.ALLOWED_TRANSITIONS.get(self._current_state, set())
        if new_state not in allowed:
            raise StateTransitionError(
                f"Illegal state transition from {self._current_state.value} to {new_state.value}"
            )

        self._current_state = new_state

    def reset(self) -> None:
        """Reset state to IDLE."""
        self._current_state = SentientState.IDLE
