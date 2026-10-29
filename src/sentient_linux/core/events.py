"""
Event definitions and event bus for Sentient Linux.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Type

from sentient_linux.core.state_machine import SentientState


@dataclass
class SentientEvent:
    timestamp: float = field(default_factory=time.time)


@dataclass
class StateChangedEvent(SentientEvent):
    old_state: SentientState = SentientState.IDLE
    new_state: SentientState = SentientState.IDLE


@dataclass
class ContextCapturedEvent(SentientEvent):
    focused_app: str = ""
    open_window_count: int = 0
    has_screenshot: bool = False


@dataclass
class ActionProposedEvent(SentientEvent):
    action_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_read_only: bool = True


@dataclass
class ActionExecutedEvent(SentientEvent):
    action_type: str = ""
    status: str = "ok"
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmergencyStopTriggeredEvent(SentientEvent):
    reason: str = ""
    processes_terminated: int = 0


@dataclass
class ErrorEvent(SentientEvent):
    error_type: str = ""
    message: str = ""


class EventBus:
    """Simple pub/sub event bus for logging and state observation."""

    def __init__(self) -> None:
        self._subscribers: Dict[Type[SentientEvent], List[Callable[[Any], None]]] = {}

    def subscribe(self, event_type: Type[SentientEvent], callback: Callable[[Any], None]) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(self, event: SentientEvent) -> None:
        event_cls = type(event)
        callbacks = self._subscribers.get(event_cls, [])
        for cb in callbacks:
            try:
                cb(event)
            except Exception:
                pass
