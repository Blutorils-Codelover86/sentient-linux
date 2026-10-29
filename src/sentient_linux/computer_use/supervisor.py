"""
Computer-use Action Supervisor for Sentient Linux.
Acts as the authoritative policy firewall between AI reasoning and MCP execution.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional, Union

from sentient_linux.computer_use.action_schema import (
    ActionType,
    ProposedAction,
    SchemaValidationError,
)
from sentient_linux.computer_use.mock_client import MockMCPClient
from sentient_linux.computer_use.mcp_client import LiveMCPClient
from sentient_linux.security.emergency_stop import EmergencyStop
from sentient_linux.security.policy import SecurityPolicy, PolicyViolationError

logger = logging.getLogger("sentient.computer_use.supervisor")


class ActionSupervisor:
    """
    Supervises and gatekeeps all computer-use actions.
    No model output can bypass this supervisor to invoke desktop tools.
    """

    def __init__(
        self,
        policy: Optional[SecurityPolicy] = None,
        client: Optional[Union[LiveMCPClient, MockMCPClient]] = None,
    ) -> None:
        self.policy = policy or SecurityPolicy()
        self.client = client or LiveMCPClient()
        self.emergency_stop = EmergencyStop()

    def execute_action(self, action: ProposedAction) -> Dict[str, Any]:
        """
        Execute an action under deterministic policy surveillance.
        1. Validates action schema.
        2. Evaluates security policy (blocks mutating actions in Phase 2).
        3. Checks Emergency Stop.
        4. Dispatches to MCP client.
        """
        self.emergency_stop.check()

        # Step 1: Schema validation
        action.validate()

        # Step 2: Policy authorization
        self.policy.authorize_action(
            action_name=action.action_type.value,
            params=action.parameters,
            is_read_only=action.is_read_only,
        )

        # Step 3: Dispatch to client
        if isinstance(self.client, MockMCPClient):
            return self.client.execute(action)
        elif isinstance(self.client, LiveMCPClient):
            return self.client.call_tool(
                name=action.action_type.value,
                arguments=action.parameters,
            )
        else:
            raise RuntimeError(f"Unsupported MCP client type: {type(self.client)}")
