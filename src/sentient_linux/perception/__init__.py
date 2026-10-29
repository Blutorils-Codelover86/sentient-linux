"""
Perception subsystem for Sentient Linux.
"""

from sentient_linux.perception.hyprland import (
    HyprlandInspector,
    HyprlandError,
    WindowInfo,
    WindowGeometry,
    MonitorInfo,
    WorkspaceInfo,
)
from sentient_linux.perception.screenshots import (
    ScreenshotEngine,
    ScreenshotError,
    ScreenshotResult,
)
from sentient_linux.perception.context import (
    DesktopContext,
    ContextManager,
)

__all__ = [
    "HyprlandInspector",
    "HyprlandError",
    "WindowInfo",
    "WindowGeometry",
    "MonitorInfo",
    "WorkspaceInfo",
    "ScreenshotEngine",
    "ScreenshotError",
    "ScreenshotResult",
    "DesktopContext",
    "ContextManager",
]
