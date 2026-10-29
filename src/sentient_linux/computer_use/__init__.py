"""
Computer-use subsystem for Sentient Linux.
"""

from sentient_linux.computer_use.action_schema import (
    ActionType,
    ProposedAction,
    READ_ONLY_ACTIONS,
    MUTATING_ACTIONS,
    SchemaValidationError,
)
from sentient_linux.computer_use.mock_client import MockMCPClient, MockToolError
from sentient_linux.computer_use.mcp_client import LiveMCPClient, MCPClientError
from sentient_linux.computer_use.supervisor import ActionSupervisor

__all__ = [
    "ActionType",
    "ProposedAction",
    "READ_ONLY_ACTIONS",
    "MUTATING_ACTIONS",
    "SchemaValidationError",
    "MockMCPClient",
    "MockToolError",
    "LiveMCPClient",
    "MCPClientError",
    "ActionSupervisor",
]
