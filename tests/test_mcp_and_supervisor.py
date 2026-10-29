"""
Unit tests for Computer-use Action Supervisor and MCP integration.
"""

from __future__ import annotations
import pytest

from sentient_linux.computer_use.action_schema import (
    ActionType,
    ProposedAction,
    SchemaValidationError,
)
from sentient_linux.computer_use.mock_client import MockMCPClient, MockToolError
from sentient_linux.computer_use.supervisor import ActionSupervisor
from sentient_linux.security.policy import SecurityPolicy, PolicyViolationError


def test_mock_mcp_client_read_only_actions():
    client = MockMCPClient()

    # List windows
    act = ProposedAction(action_type=ActionType.LIST_WINDOWS)
    res = client.execute(act)
    assert res["backend"] == "mock"
    assert len(res["windows"]) == 2

    # Focused window
    act_focused = ProposedAction(action_type=ActionType.FOCUSED_WINDOW)
    res_f = client.execute(act_focused)
    assert res_f["title"] == "Mock Browser - Sentient OS"


def test_mock_mcp_client_simulated_failure():
    client = MockMCPClient(simulate_failure=True, failure_message="Simulated D-Bus timeout")
    act = ProposedAction(action_type=ActionType.LIST_WINDOWS)
    with pytest.raises(MockToolError, match="Simulated D-Bus timeout"):
        client.execute(act)


def test_action_schema_validation_failures():
    # Click with invalid coordinate type
    invalid_click = ProposedAction(action_type=ActionType.CLICK, parameters={"x": "NOT_A_NUMBER"})
    with pytest.raises(SchemaValidationError, match="must be a number"):
        invalid_click.validate()

    # type_text without text param
    invalid_type = ProposedAction(action_type=ActionType.TYPE_TEXT, parameters={})
    with pytest.raises(SchemaValidationError, match="requires 'text' parameter"):
        invalid_type.validate()

    # type_text exceeding length cap
    overflow_type = ProposedAction(action_type=ActionType.TYPE_TEXT, parameters={"text": "A" * 1500})
    with pytest.raises(SchemaValidationError, match="exceeds safety limit"):
        overflow_type.validate()


def test_supervisor_rejects_mutating_actions_in_phase2():
    policy = SecurityPolicy()
    mock_client = MockMCPClient()
    supervisor = ActionSupervisor(policy=policy, client=mock_client)

    # Attempt a click (mutating action)
    click_act = ProposedAction(action_type=ActionType.CLICK, parameters={"x": 100, "y": 200})
    with pytest.raises(PolicyViolationError, match="mutating desktop action"):
        supervisor.execute_action(click_act)

    # Attempt typing text (mutating action)
    type_act = ProposedAction(action_type=ActionType.TYPE_TEXT, parameters={"text": "hello"})
    with pytest.raises(PolicyViolationError, match="mutating desktop action"):
        supervisor.execute_action(type_act)


def test_supervisor_permits_read_only_actions_in_phase2():
    policy = SecurityPolicy()
    mock_client = MockMCPClient()
    supervisor = ActionSupervisor(policy=policy, client=mock_client)

    # List windows should succeed
    list_act = ProposedAction(action_type=ActionType.LIST_WINDOWS)
    res = supervisor.execute_action(list_act)
    assert res["backend"] == "mock"
    assert len(res["windows"]) == 2
