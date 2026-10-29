"""
Hyprland compositor inspection module for Sentient Linux.
Provides read-only queries using hyprctl -j.
"""

from __future__ import annotations
import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sentient_linux.security.emergency_stop import EmergencyStop

logger = logging.getLogger("sentient.perception.hyprland")


class HyprlandError(RuntimeError):
    """Raised when hyprctl fails or returns unexpected data."""
    pass


@dataclass
class WindowGeometry:
    x: int
    y: int
    width: int
    height: int

    @property
    def box_str(self) -> str:
        return f"{self.x},{self.y} {self.width}x{self.height}"


@dataclass
class WindowInfo:
    address: str
    title: str
    wm_class: str
    initial_class: str
    pid: int
    workspace_id: int
    workspace_name: str
    geometry: WindowGeometry
    floating: bool
    focused: bool
    hidden: bool
    monitor: int
    fullscreen: bool
    raw_data: Dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class MonitorInfo:
    id: int
    name: str
    description: str
    width: int
    height: int
    refresh_rate: float
    x: int
    y: int
    scale: float
    focused: bool


@dataclass
class WorkspaceInfo:
    id: int
    name: str
    monitor: str
    windows: int
    has_fullscreen: bool


class HyprlandInspector:
    """
    Read-only inspector for Hyprland desktop environment.
    Strictly queries compositor state via hyprctl JSON output.
    Does not issue mutating dispatcher commands.
    """

    def __init__(self, hyprctl_path: Optional[str] = None) -> None:
        self.hyprctl_path = hyprctl_path or shutil.which("hyprctl")
        self.emergency_stop = EmergencyStop()

    def is_available(self) -> bool:
        """Check if hyprctl binary is available on PATH."""
        return bool(self.hyprctl_path)

    def _run_query(self, subcmd: str) -> Any:
        """Execute a read-only hyprctl command and parse its JSON output."""
        self.emergency_stop.check()

        if not self.hyprctl_path:
            raise HyprlandError("hyprctl binary not found on PATH. Is Hyprland running?")

        cmd = [self.hyprctl_path, subcmd, "-j"]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.emergency_stop.register_process(proc)
            stdout, stderr = proc.communicate(timeout=3.0)
            self.emergency_stop.unregister_process(proc)
        except subprocess.TimeoutExpired:
            proc.kill()
            self.emergency_stop.unregister_process(proc)
            raise HyprlandError(f"hyprctl {subcmd} timed out after 3.0s")
        except Exception as e:
            raise HyprlandError(f"Failed to execute hyprctl {subcmd}: {e}")

        if proc.returncode != 0:
            raise HyprlandError(f"hyprctl {subcmd} returned exit code {proc.returncode}: {stderr.strip()}")

        text = stdout.strip()
        if not text or text == "{}":
            return {}

        try:
            return json.loads(text)
        except json.JSONDecodeError as err:
            raise HyprlandError(f"Failed to parse hyprctl {subcmd} JSON: {err} (Output: {text[:100]})")

    def get_focused_window(self) -> Optional[WindowInfo]:
        """
        Query the currently active/focused window.
        Returns WindowInfo or None if no window has focus.
        """
        data = self._run_query("activewindow")
        if not isinstance(data, dict) or not data or not data.get("address"):
            return None

        return self._parse_window(data, force_focused=True)

    def list_windows(self) -> List[WindowInfo]:
        """Query all open client windows across all workspaces and monitors."""
        data = self._run_query("clients")
        if not isinstance(data, list):
            return []

        active_addr = None
        try:
            active_data = self._run_query("activewindow")
            if isinstance(active_data, dict):
                active_addr = active_data.get("address")
        except Exception:
            pass

        windows: List[WindowInfo] = []
        for item in data:
            if isinstance(item, dict) and item.get("address"):
                is_focused = (item.get("address") == active_addr)
                windows.append(self._parse_window(item, force_focused=is_focused))

        return windows

    def list_monitors(self) -> List[MonitorInfo]:
        """Query multi-monitor topology and scaling."""
        data = self._run_query("monitors")
        if not isinstance(data, list):
            return []

        monitors: List[MonitorInfo] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            monitors.append(
                MonitorInfo(
                    id=int(item.get("id", 0)),
                    name=str(item.get("name", "")),
                    description=str(item.get("description", "")),
                    width=int(item.get("width", 0)),
                    height=int(item.get("height", 0)),
                    refresh_rate=float(item.get("refreshRate", 60.0)),
                    x=int(item.get("x", 0)),
                    y=int(item.get("y", 0)),
                    scale=float(item.get("scale", 1.0)),
                    focused=bool(item.get("focused", False)),
                )
            )
        return monitors

    def list_workspaces(self) -> List[WorkspaceInfo]:
        """Query active workspaces and their window counts."""
        data = self._run_query("workspaces")
        if not isinstance(data, list):
            return []

        workspaces: List[WorkspaceInfo] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            workspaces.append(
                WorkspaceInfo(
                    id=int(item.get("id", 0)),
                    name=str(item.get("name", "")),
                    monitor=str(item.get("monitor", "")),
                    windows=int(item.get("windows", 0)),
                    has_fullscreen=bool(item.get("hasfullscreen", False)),
                )
            )
        return workspaces

    def _parse_window(self, item: Dict[str, Any], force_focused: bool = False) -> WindowInfo:
        at = item.get("at", [0, 0])
        size = item.get("size", [0, 0])
        workspace = item.get("workspace", {})

        return WindowInfo(
            address=str(item.get("address", "")),
            title=str(item.get("title", "")),
            wm_class=str(item.get("class", "")),
            initial_class=str(item.get("initialClass", "")),
            pid=int(item.get("pid", 0)),
            workspace_id=int(workspace.get("id", 0)) if isinstance(workspace, dict) else 0,
            workspace_name=str(workspace.get("name", "")) if isinstance(workspace, dict) else "",
            geometry=WindowGeometry(x=at[0], y=at[1], width=size[0], height=size[1]),
            floating=bool(item.get("floating", False)),
            focused=force_focused or bool(item.get("focusHistoryID") == 0),
            hidden=bool(item.get("hidden", False)),
            monitor=int(item.get("monitor", 0)),
            fullscreen=bool(item.get("fullscreen", False)),
            raw_data=item,
        )
