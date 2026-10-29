"""
Security Policy Engine for Sentient Linux.
Enforces deterministic action authorization independently of model reasoning.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from sentient_linux.security.permissions import Permission, PermissionManager, PermissionState


class PolicyViolationError(PermissionError):
    """Raised when an action violates system security policy."""
    pass


class SecurityPolicy:
    """
    Evaluates actions against deterministic security rules.
    Guarantees:
    - Default-deny on all unconfigured or mutating actions.
    - Zero modification to Omarchy or Hyprland system configs.
    - Path traversal and sensitive directory protection.
    - Strictly read-only execution during Phase 2.
    """

    FORBIDDEN_PATH_PREFIXES = [
        "/boot",
        "/etc",
        "/root",
        "/usr",
        "/var",
        os.path.expanduser("~/.config/hypr"),
        os.path.expanduser("~/.config/omarchy"),
        os.path.expanduser("~/.config/systemd"),
    ]

    def __init__(self, permission_manager: Optional[PermissionManager] = None) -> None:
        self.permissions = permission_manager or PermissionManager()

    def check_path_safety(self, path: str | Path, write: bool = False) -> None:
        """Verify that a target path is outside critical system directories."""
        resolved = Path(path).expanduser().resolve()
        resolved_str = str(resolved)

        for prefix in self.FORBIDDEN_PATH_PREFIXES:
            prefix_resolved = str(Path(prefix).resolve())
            if resolved_str == prefix_resolved or resolved_str.startswith(prefix_resolved + "/"):
                raise PolicyViolationError(
                    f"Access denied to protected system directory: {resolved_str}"
                )

        if write and not self.permissions.is_granted(Permission.FILE_WRITE):
            raise PolicyViolationError(
                f"File write permission denied for path: {resolved_str}"
            )

    def authorize_action(self, action_name: str, params: Dict[str, Any], is_read_only: bool) -> None:
        """
        Deterministic authorization gate.
        All mutating actions in Phase 2 are rejected.
        """
        # Phase 2 boundary check
        if not is_read_only:
            raise PolicyViolationError(
                f"Action '{action_name}' is a mutating desktop action. "
                f"Mutating desktop actions are strictly disabled in Phase 2 prototype."
            )

        # Mapping read-only actions to permissions
        if action_name in ["list_windows", "focused_window", "get_app_state", "windows"]:
            if not self.permissions.is_granted(Permission.WINDOW_METADATA_READ):
                raise PolicyViolationError("Window metadata read permission is not granted.")
        elif action_name in ["screenshot", "capture"]:
            if not self.permissions.is_granted(Permission.SCREENSHOT_CAPTURE):
                raise PolicyViolationError("Screenshot capture permission is not granted.")
        elif action_name in ["read_file"]:
            if not self.permissions.is_granted(Permission.FILE_READ):
                raise PolicyViolationError("File read permission is not granted.")
            if "path" in params:
                self.check_path_safety(params["path"], write=False)
        else:
            # Default deny for any unrecognized action
            raise PolicyViolationError(f"Action '{action_name}' is not recognized or permitted.")
