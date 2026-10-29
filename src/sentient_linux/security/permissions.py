"""
Deterministic permission management for Sentient Linux.
Implements a default-deny security model separating read-only queries from mutating operations.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, Set


class Permission(str, Enum):
    WINDOW_METADATA_READ = "window:metadata:read"
    SCREENSHOT_CAPTURE = "screenshot:capture"
    CLIPBOARD_READ = "clipboard:read"
    FILE_READ = "file:read"
    NETWORK_ACCESS = "network:access"
    APPLICATION_CONTROL = "application:control"
    INPUT_SIMULATION = "input:simulation"
    FILE_WRITE = "file:write"


class PermissionState(str, Enum):
    GRANTED = "granted"
    DENIED = "denied"
    PROMPT = "prompt"


class PermissionManager:
    """
    Tracks and enforces fine-grained permission states.
    Phase 2 enforces strict read-only mode where mutating permissions are DENIED.
    """

    def __init__(self, initial_grants: Dict[Permission, PermissionState] | None = None) -> None:
        self._states: Dict[Permission, PermissionState] = {
            Permission.WINDOW_METADATA_READ: PermissionState.GRANTED,
            Permission.SCREENSHOT_CAPTURE: PermissionState.GRANTED,  # User-requested only
            Permission.CLIPBOARD_READ: PermissionState.PROMPT,
            Permission.FILE_READ: PermissionState.PROMPT,
            Permission.NETWORK_ACCESS: PermissionState.PROMPT,
            # Mutating desktop operations are strictly denied in Phase 2 prototype
            Permission.APPLICATION_CONTROL: PermissionState.DENIED,
            Permission.INPUT_SIMULATION: PermissionState.DENIED,
            Permission.FILE_WRITE: PermissionState.DENIED,
        }
        if initial_grants:
            self._states.update(initial_grants)

    def get_state(self, permission: Permission) -> PermissionState:
        return self._states.get(permission, PermissionState.DENIED)

    def is_granted(self, permission: Permission) -> bool:
        return self.get_state(permission) == PermissionState.GRANTED

    def grant(self, permission: Permission) -> None:
        self._states[permission] = PermissionState.GRANTED

    def deny(self, permission: Permission) -> None:
        self._states[permission] = PermissionState.DENIED

    def set_state(self, permission: Permission, state: PermissionState) -> None:
        self._states[permission] = state

    def list_permissions(self) -> Dict[str, str]:
        return {perm.value: state.value for perm, state in self._states.items()}

    def mutating_permissions(self) -> Set[Permission]:
        return {
            Permission.APPLICATION_CONTROL,
            Permission.INPUT_SIMULATION,
            Permission.FILE_WRITE,
        }
