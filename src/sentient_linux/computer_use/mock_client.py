"""
Stage A Mock MCP Client for Sentient Linux.
Simulates MCP responses for deterministic testing of actions, errors, and cancellation.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from sentient_linux.computer_use.action_schema import ActionType, ProposedAction, SchemaValidationError
from sentient_linux.security.emergency_stop import EmergencyStop


class MockToolError(RuntimeError):
    """Simulated MCP tool error."""
    pass


class MockMCPClient:
    """
    Mock implementation of computer-use MCP client.
    Enables testing window queries, schema validation, simulated tool failures, and cancellation.
    """

    def __init__(
        self,
        simulate_failure: bool = False,
        failure_message: str = "Simulated tool execution failure",
    ) -> None:
        self.simulate_failure = simulate_failure
        self.failure_message = failure_message
        self.executed_actions: List[ProposedAction] = []
        self.emergency_stop = EmergencyStop()

    def execute(self, action: ProposedAction) -> Dict[str, Any]:
        """Execute action mock."""
        self.emergency_stop.check()
        action.validate()

        if self.simulate_failure:
            raise MockToolError(self.failure_message)

        self.executed_actions.append(action)

        if action.action_type == ActionType.LIST_WINDOWS:
            return {
                "backend": "mock",
                "windows": [
                    {
                        "window_id": 1001,
                        "title": "Mock Browser - Sentient OS",
                        "app_id": "org.mozilla.firefox",
                        "focused": True,
                        "workspace": 1,
                        "bounds": {"x": 50, "y": 50, "width": 1200, "height": 800},
                    },
                    {
                        "window_id": 1002,
                        "title": "terminal: blu@omarchy",
                        "app_id": "foot",
                        "focused": False,
                        "workspace": 2,
                        "bounds": {"x": 100, "y": 100, "width": 800, "height": 600},
                    },
                ],
            }

        elif action.action_type == ActionType.FOCUSED_WINDOW:
            return {
                "window_id": 1001,
                "title": "Mock Browser - Sentient OS",
                "app_id": "org.mozilla.firefox",
                "focused": True,
                "workspace": 1,
                "bounds": {"x": 50, "y": 50, "width": 1200, "height": 800},
            }

        elif action.action_type == ActionType.GET_APP_STATE:
            return {
                "readiness": {"ok": True, "backend": "mock"},
                "focused_window": {"title": "Mock Window", "app_id": "mock_app"},
                "tree": {"role": "window", "name": "Mock Window", "children": []},
            }

        elif action.action_type == ActionType.DOCTOR:
            return {"status": "ok", "backend": "mock", "platform": "linux"}

        elif action.action_type in [ActionType.CLICK, ActionType.TYPE_TEXT, ActionType.PRESS_KEY]:
            return {"status": "executed_mock", "action": action.action_type.value}

        return {"status": "ok"}
