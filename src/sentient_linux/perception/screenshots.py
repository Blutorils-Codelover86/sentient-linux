"""
Screenshot capture engine for Sentient Linux using grim.
Enforces on-demand capture only, private temporary files (0600), and guaranteed cleanup.
"""

from __future__ import annotations
import logging
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sentient_linux.security.emergency_stop import EmergencyStop
from sentient_linux.security.permissions import Permission, PermissionManager
from sentient_linux.security.policy import PolicyViolationError

logger = logging.getLogger("sentient.perception.screenshots")


class ScreenshotError(RuntimeError):
    """Raised when screenshot capture fails."""
    pass


@dataclass
class ScreenshotResult:
    path: Path
    latency_ms: float
    width: int = 0
    height: int = 0
    size_bytes: int = 0

    def cleanup(self) -> None:
        """Safely delete the temporary screenshot file."""
        if self.path.exists():
            try:
                self.path.unlink()
                logger.debug(f"Cleaned up temporary screenshot: {self.path}")
            except Exception as err:
                logger.warning(f"Failed to delete temporary screenshot {self.path}: {err}")


class ScreenshotEngine:
    """
    On-demand Wayland screen capture using grim.
    Treats all captured image data as untrusted, private user context.
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        grim_path: Optional[str] = None,
    ) -> None:
        self.permissions = permission_manager or PermissionManager()
        self.grim_path = grim_path or shutil.which("grim")
        self.emergency_stop = EmergencyStop()

    def is_available(self) -> bool:
        """Check if grim binary is available on PATH."""
        return bool(self.grim_path)

    def capture(
        self,
        geometry_box: Optional[str] = None,
        output_file: Optional[Path | str] = None,
        image_format: str = "png",
    ) -> ScreenshotResult:
        """
        Capture the screen on explicit request.
        If output_file is None, generates a private temporary file with mode 0600.
        Callers are responsible for calling result.cleanup() on temporary captures.
        """
        self.emergency_stop.check()

        # Enforce permission
        if not self.permissions.is_granted(Permission.SCREENSHOT_CAPTURE):
            raise PolicyViolationError("Screenshot capture permission is not granted.")

        if not self.grim_path:
            raise ScreenshotError("grim binary not found on PATH. Is grim installed?")

        is_temporary = output_file is None
        if is_temporary:
            # Create a private temporary file with 0600 permissions
            fd, tmp_path_str = tempfile.mkstemp(
                prefix="sentient_shot_",
                suffix=f".{image_format}",
            )
            os.close(fd)
            # Ensure permissions are strictly read/write by current user only
            os.chmod(tmp_path_str, 0o600)
            target_path = Path(tmp_path_str)
        else:
            target_path = Path(output_file).expanduser().resolve()
            target_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [self.grim_path]
        if geometry_box:
            cmd.extend(["-g", geometry_box])
        cmd.append(str(target_path))

        start_time = time.perf_counter()
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.emergency_stop.register_process(proc)
            _, stderr = proc.communicate(timeout=5.0)
            self.emergency_stop.unregister_process(proc)
        except subprocess.TimeoutExpired:
            proc.kill()
            self.emergency_stop.unregister_process(proc)
            if is_temporary and target_path.exists():
                target_path.unlink()
            raise ScreenshotError("grim capture timed out after 5.0 seconds")
        except Exception as err:
            if is_temporary and target_path.exists():
                target_path.unlink()
            raise ScreenshotError(f"Screenshot capture execution failed: {err}")

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if proc.returncode != 0:
            if is_temporary and target_path.exists():
                target_path.unlink()
            raise ScreenshotError(f"grim failed with code {proc.returncode}: {stderr.strip()}")

        if not target_path.exists() or target_path.stat().st_size == 0:
            if is_temporary and target_path.exists():
                target_path.unlink()
            raise ScreenshotError("grim capture produced an empty or missing output file")

        size_bytes = target_path.stat().st_size

        return ScreenshotResult(
            path=target_path,
            latency_ms=round(latency_ms, 2),
            size_bytes=size_bytes,
        )
