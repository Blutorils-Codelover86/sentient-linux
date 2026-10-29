"""
Desktop context aggregation for Sentient Linux.
Produces unified snapshots of window focus, workspaces, and on-demand visual context.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sentient_linux.perception.hyprland import HyprlandInspector, WindowInfo, MonitorInfo
from sentient_linux.perception.screenshots import ScreenshotEngine, ScreenshotResult


@dataclass
class DesktopContext:
    timestamp: float
    focused_window: Optional[WindowInfo]
    windows: List[WindowInfo]
    monitors: List[MonitorInfo]
    screenshot: Optional[ScreenshotResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_prompt_context(self) -> str:
        """Render a concise context block for the inference model."""
        lines = ["[DESKTOP CONTEXT]"]
        if self.focused_window:
            w = self.focused_window
            lines.append(
                f"Active Window: \"{w.title}\" (Class: {w.wm_class}, PID: {w.pid}, "
                f"Workspace: {w.workspace_name}, Bounds: {w.geometry.box_str})"
            )
        else:
            lines.append("Active Window: None (Desktop empty or compositor focused)")

        lines.append(f"Open Windows ({len(self.windows)}):")
        for win in self.windows[:10]:  # Cap at 10 to protect context budget
            lines.append(f"- [{win.wm_class}] \"{win.title}\" (WS: {win.workspace_name})")
        if len(self.windows) > 10:
            lines.append(f"- ... and {len(self.windows) - 10} more open windows")

        lines.append(f"Monitors: {len(self.monitors)}")
        if self.screenshot:
            lines.append(f"Screenshot Attached: {self.screenshot.path.name} ({self.screenshot.size_bytes} bytes)")

        return "\n".join(lines)


class ContextManager:
    """Collects desktop context snapshots safely."""

    def __init__(
        self,
        inspector: Optional[HyprlandInspector] = None,
        screenshots: Optional[ScreenshotEngine] = None,
    ) -> None:
        self.inspector = inspector or HyprlandInspector()
        self.screenshots = screenshots or ScreenshotEngine()

    def snapshot(self, include_screenshot: bool = False) -> DesktopContext:
        focused = None
        windows: List[WindowInfo] = []
        monitors: List[MonitorInfo] = []

        try:
            focused = self.inspector.get_focused_window()
            windows = self.inspector.list_windows()
            monitors = self.inspector.list_monitors()
        except Exception as err:
            # Degrade gracefully if Hyprland queries encounter issues
            focused = None

        shot: Optional[ScreenshotResult] = None
        if include_screenshot:
            try:
                shot = self.screenshots.capture()
            except Exception:
                shot = None

        return DesktopContext(
            timestamp=time.time(),
            focused_window=focused,
            windows=windows,
            monitors=monitors,
            screenshot=shot,
        )
