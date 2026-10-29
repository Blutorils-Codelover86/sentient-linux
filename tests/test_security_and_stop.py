"""
Unit tests for Security Policy, PII detection, and Emergency Stop.
"""

from __future__ import annotations
import subprocess
import time
from unittest.mock import MagicMock
import pytest

from sentient_linux.security.permissions import Permission, PermissionManager, PermissionState
from sentient_linux.security.policy import SecurityPolicy, PolicyViolationError
from sentient_linux.security.privacy import PIIScanner
from sentient_linux.security.emergency_stop import EmergencyStop, EmergencyStopError


def test_pii_scanner_detections():
    # Valid SSN
    assert PIIScanner.contains_high_risk_pii("User SSN is 123-45-6789 here") is True

    # Valid Luhn card number (Test Visa 4000 0000 0000 0002)
    assert PIIScanner.contains_high_risk_pii("Credit card: 4000-0000-0000-0002") is True

    # Passport
    assert PIIScanner.contains_high_risk_pii("passport: AB123456") is True

    # Benign string
    assert PIIScanner.contains_high_risk_pii("Meeting at 3pm on Friday in room 204") is False


def test_pii_sanitizer_for_logging():
    raw_log = "Error sending request with Bearer sk-1234567890abcdef12345678 for SSN 123-45-6789"
    sanitized = PIIScanner.sanitize_for_logging(raw_log)
    assert "sk-" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized
    assert "123-45-6789" not in sanitized
    assert "[REDACTED_SSN]" in sanitized


def test_policy_forbidden_system_paths():
    policy = SecurityPolicy()

    # /boot check
    with pytest.raises(PolicyViolationError, match="protected system directory"):
        policy.check_path_safety("/boot/grub/grub.cfg")

    # /etc check
    with pytest.raises(PolicyViolationError, match="protected system directory"):
        policy.check_path_safety("/etc/shadow")

    # ~/.config/hypr check
    with pytest.raises(PolicyViolationError, match="protected system directory"):
        policy.check_path_safety("~/.config/hypr/bindings.lua")

    # Safe path check
    policy.check_path_safety("~/Documents/notes.txt")


def test_emergency_stop_mechanism():
    stop = EmergencyStop()
    stop.reset()
    assert not stop.is_stopped()

    # Register a mock process
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.poll.return_value = None
    mock_proc.pid = 9999

    stop.register_process(mock_proc)

    # Trigger stop
    count = stop.trigger(reason="Test Stop")
    assert stop.is_stopped()
    assert count == 1
    mock_proc.terminate.assert_called_once()

    # Further operations must raise EmergencyStopError
    with pytest.raises(EmergencyStopError, match="Emergency stop is active"):
        stop.check()

    # Reset
    stop.reset()
    assert not stop.is_stopped()
    stop.check()  # should not raise
