"""
Core subsystem for Sentient Linux.
"""

from sentient_linux.core.state_machine import StateMachine, SentientState, StateTransitionError
from sentient_linux.core.events import (
    EventBus,
    SentientEvent,
    StateChangedEvent,
    ContextCapturedEvent,
    ActionProposedEvent,
    ActionExecutedEvent,
    EmergencyStopTriggeredEvent,
    ErrorEvent,
)
from sentient_linux.core.coordinator import CommandCoordinator

__all__ = [
    "StateMachine",
    "SentientState",
    "StateTransitionError",
    "EventBus",
    "SentientEvent",
    "StateChangedEvent",
    "ContextCapturedEvent",
    "ActionProposedEvent",
    "ActionExecutedEvent",
    "EmergencyStopTriggeredEvent",
    "ErrorEvent",
    "CommandCoordinator",
]
