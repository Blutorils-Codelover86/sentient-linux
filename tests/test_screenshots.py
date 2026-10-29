"""
Unit tests for screenshot engine and cleanup.
"""

from __future__ import annotations
import os
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from sentient_linux.perception.screenshots import ScreenshotEngine, ScreenshotError
from sentient_linux.security.permissions import Permission, PermissionManager, PermissionState
from sentient_linux.security.policy import PolicyViolationError


def test_screenshot_authorization_required():
    perms = PermissionManager()
    perms.set_state(Permission.SCREENSHOT_CAPTURE, PermissionState.DENIED)
    engine = ScreenshotEngine(permission_manager=perms, grim_path="/usr/bin/grim")

    with pytest.raises(PolicyViolationError, match="Screenshot capture permission is not granted"):
        engine.capture()


def test_screenshot_temporary_file_permissions_and_cleanup(tmp_path: Path):
    perms = PermissionManager()
    engine = ScreenshotEngine(permission_manager=perms, grim_path="/usr/bin/grim")

    # Mock subprocess to write a fake image
    with patch("subprocess.Popen") as mock_popen:
        def fake_grim(*args, **kwargs):
            proc = MagicMock()
            def fake_comm(*a, **kw):
                cmd = args[0]
                target_file = cmd[-1]
                with open(target_file, "wb") as f:
                    f.write(b"FAKE_PNG_BYTES")
                return ("", "")
            proc.communicate.side_effect = fake_comm
            proc.returncode = 0
            return proc

        mock_popen.side_effect = fake_grim

        result = engine.capture()
        assert result.path.exists()
        assert result.size_bytes > 0
        assert result.latency_ms >= 0

        # Check file mode is strictly 0600
        mode = stat.S_IMODE(os.stat(result.path).st_mode)
        assert mode == 0o600

        # Check cleanup removes file
        result.cleanup()
        assert not result.path.exists()


def test_screenshot_explicit_output_destination(tmp_path: Path):
    perms = PermissionManager()
    engine = ScreenshotEngine(permission_manager=perms, grim_path="/usr/bin/grim")
    explicit_dest = tmp_path / "explicit_capture.png"

    with patch("subprocess.Popen") as mock_popen:
        def fake_grim(*args, **kwargs):
            proc = MagicMock()
            def fake_comm(*a, **kw):
                cmd = args[0]
                with open(cmd[-1], "wb") as f:
                    f.write(b"PNG_DATA")
                return ("", "")
            proc.communicate.side_effect = fake_comm
            proc.returncode = 0
            return proc

        mock_popen.side_effect = fake_grim

        result = engine.capture(output_file=explicit_dest)
        assert result.path == explicit_dest
        assert explicit_dest.exists()
