"""
Action schemas and parameter validation for desktop computer use.
Distinguishes read-only queries from mutating actions.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ActionType(str, Enum):
    # Read-only actions
    LIST_WINDOWS = "list_windows"
    FOCUSED_WINDOW = "focused_window"
    GET_APP_STATE = "get_app_state"
    LIST_APPS = "list_apps"
    SCREENSHOT = "screenshot"
    DOCTOR = "doctor"

    # Mutating actions (strictly blocked in Phase 2)
    CLICK = "click"
    TYPE_TEXT = "type_text"
    PRESS_KEY = "press_key"
    DRAG = "drag"
    SCROLL = "scroll"
    SET_VALUE = "set_value"
    PERFORM_ACTION = "perform_action"
    ACTIVATE_WINDOW = "activate_window"
    MOVE_WINDOW = "move_window"
    RESIZE_WINDOW = "resize_window"


READ_ONLY_ACTIONS = {
    ActionType.LIST_WINDOWS,
    ActionType.FOCUSED_WINDOW,
    ActionType.GET_APP_STATE,
    ActionType.LIST_APPS,
    ActionType.SCREENSHOT,
    ActionType.DOCTOR,
}

MUTATING_ACTIONS = {
    ActionType.CLICK,
    ActionType.TYPE_TEXT,
    ActionType.PRESS_KEY,
    ActionType.DRAG,
    ActionType.SCROLL,
    ActionType.SET_VALUE,
    ActionType.PERFORM_ACTION,
    ActionType.ACTIVATE_WINDOW,
    ActionType.MOVE_WINDOW,
    ActionType.RESIZE_WINDOW,
}


class SchemaValidationError(ValueError):
    """Raised when action parameters fail validation."""
    pass


@dataclass
class ProposedAction:
    action_type: ActionType
    parameters: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_read_only(self) -> bool:
        return self.action_type in READ_ONLY_ACTIONS

    @property
    def is_mutating(self) -> bool:
        return self.action_type in MUTATING_ACTIONS

    def validate(self) -> None:
        """Validate parameters according to action schema constraints."""
        params = self.parameters

        if self.action_type == ActionType.CLICK:
            if "x" in params and not isinstance(params["x"], (int, float)):
                raise SchemaValidationError("Click parameter 'x' must be a number.")
            if "y" in params and not isinstance(params["y"], (int, float)):
                raise SchemaValidationError("Click parameter 'y' must be a number.")

        elif self.action_type == ActionType.TYPE_TEXT:
            if "text" not in params:
                raise SchemaValidationError("type_text requires 'text' parameter.")
            if not isinstance(params["text"], str):
                raise SchemaValidationError("type_text 'text' parameter must be a string.")
            if len(params["text"]) > 1000:
                raise SchemaValidationError("type_text length exceeds safety limit of 1000 characters.")

        elif self.action_type == ActionType.PRESS_KEY:
            if "key" not in params:
                raise SchemaValidationError("press_key requires 'key' parameter.")

        elif self.action_type == ActionType.ACTIVATE_WINDOW:
            if "window_id" not in params and "title" not in params and "app_id" not in params:
                raise SchemaValidationError("activate_window requires a target (window_id, title, or app_id).")
