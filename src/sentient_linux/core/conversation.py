"""
Durable conversation store and message records for Sentient Linux.
Maintains state shared between Core Coordinator, Notch, and Full Sidekick interfaces.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import logging
import time
from typing import Callable, List, Optional
import uuid

logger = logging.getLogger("sentient.core.conversation")


@dataclass
class ConversationRecord:
    """A durable conversation message record."""
    id: str
    role: str  # "user" | "assistant"
    text: str
    timestamp: float = field(default_factory=time.time)
    duration_s: float = 0.0
    status: str = "done"  # "done" | "failed" | "stopped"


class ConversationStore:
    """
    Shared conversation store between Notch and Full Sidekick views.
    Maintains message history, draft text, and notifies listeners on change.
    """

    def __init__(self) -> None:
        self.records: List[ConversationRecord] = []
        self.draft: str = ""
        self._listeners: List[Callable[[ConversationRecord], None]] = []

    def add_listener(self, cb: Callable[[ConversationRecord], None]) -> None:
        if cb not in self._listeners:
            self._listeners.append(cb)

    def remove_listener(self, cb: Callable[[ConversationRecord], None]) -> None:
        if cb in self._listeners:
            self._listeners.remove(cb)

    def append_message(
        self,
        role: str,
        text: str,
        duration_s: float = 0.0,
        status: str = "done",
    ) -> ConversationRecord:
        record = ConversationRecord(
            id=str(uuid.uuid4())[:8],
            role=role,
            text=text,
            timestamp=time.time(),
            duration_s=duration_s,
            status=status,
        )
        self.records.append(record)
        for listener in list(self._listeners):
            try:
                listener(record)
            except Exception as err:
                logger.error("Error in conversation listener: %s", err)
        return record

    def clear(self) -> None:
        self.records.clear()
        self.draft = ""

    @property
    def latest_message(self) -> Optional[ConversationRecord]:
        return self.records[-1] if self.records else None
