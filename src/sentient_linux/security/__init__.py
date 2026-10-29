"""
Security subsystem for Sentient Linux.
"""

from sentient_linux.security.permissions import Permission, PermissionManager, PermissionState
from sentient_linux.security.emergency_stop import EmergencyStop, EmergencyStopError
from sentient_linux.security.privacy import PIIScanner, ConsentManager, PrivacyError
from sentient_linux.security.policy import SecurityPolicy, PolicyViolationError

__all__ = [
    "Permission",
    "PermissionManager",
    "PermissionState",
    "EmergencyStop",
    "EmergencyStopError",
    "PIIScanner",
    "ConsentManager",
    "PrivacyError",
    "SecurityPolicy",
    "PolicyViolationError",
]
