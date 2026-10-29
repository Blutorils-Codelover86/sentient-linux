"""
Unit tests for Hyprland inspector and JSON parsing.
"""

from __future__ import annotations
import json
from unittest.mock import MagicMock, patch
import pytest

from sentient_linux.perception.hyprland import (
    HyprlandInspector,
    HyprlandError,
    WindowInfo,
    WindowGeometry,
)


@pytest.fixture
def sample_clients_json() -> str:
    return json.dumps([
        {
            "address": "0x5649b9455ff0",
            "mapped": True,
            "hidden": False,
            "at": [418, 204],
            "size": [700, 480],
            "workspace": {"id": 2, "name": "2"},
            "floating": True,
            "monitor": 0,
            "class": "imv",
            "title": "imv - test image.png",
            "initialClass": "imv",
            "pid": 57384,
            "focusHistoryID": 1,
            "fullscreen": False,
        },
        {
            "address": "0x5649b9456000",
            "mapped": True,
            "hidden": False,
            "at": [0, 0],
            "size": [1920, 1080],
            "workspace": {"id": 1, "name": "1"},
            "floating": False,
            "monitor": 0,
            "class": "org.mozilla.firefox",
            "title": "Sentient OS - Mozilla Firefox",
            "initialClass": "firefox",
            "pid": 1234,
            "focusHistoryID": 0,
            "fullscreen": True,
        },
    ])


@pytest.fixture
def sample_activewindow_json() -> str:
    return json.dumps({
        "address": "0x5649b9456000",
        "mapped": True,
        "hidden": False,
        "at": [0, 0],
        "size": [1920, 1080],
        "workspace": {"id": 1, "name": "1"},
        "floating": False,
        "monitor": 0,
        "class": "org.mozilla.firefox",
        "title": "Sentient OS - Mozilla Firefox",
        "initialClass": "firefox",
        "pid": 1234,
        "fullscreen": True,
    })


def test_hyprland_parse_clients(sample_clients_json: str, sample_activewindow_json: str):
    inspector = HyprlandInspector(hyprctl_path="/usr/bin/hyprctl")
    with patch.object(inspector, "_run_query") as mock_query:
        def query_side_effect(cmd: str):
            if cmd == "clients":
                return json.loads(sample_clients_json)
            elif cmd == "activewindow":
                return json.loads(sample_activewindow_json)
            return []

        mock_query.side_effect = query_side_effect
        windows = inspector.list_windows()

        assert len(windows) == 2
        imv_win = next(w for w in windows if w.wm_class == "imv")
        assert imv_win.pid == 57384
        assert imv_win.workspace_name == "2"
        assert imv_win.geometry.x == 418
        assert imv_win.geometry.y == 204
        assert imv_win.geometry.width == 700
        assert imv_win.geometry.height == 480
        assert imv_win.floating is True
        assert imv_win.focused is False

        firefox_win = next(w for w in windows if w.wm_class == "org.mozilla.firefox")
        assert firefox_win.focused is True
        assert firefox_win.fullscreen is True


def test_hyprland_focused_window(sample_activewindow_json: str):
    inspector = HyprlandInspector(hyprctl_path="/usr/bin/hyprctl")
    with patch.object(inspector, "_run_query", return_value=json.loads(sample_activewindow_json)):
        focused = inspector.get_focused_window()
        assert focused is not None
        assert focused.title == "Sentient OS - Mozilla Firefox"
        assert focused.focused is True


def test_hyprland_missing_window_condition():
    """Test empty/missing activewindow returns None gracefully."""
    inspector = HyprlandInspector(hyprctl_path="/usr/bin/hyprctl")
    with patch.object(inspector, "_run_query", return_value={}):
        focused = inspector.get_focused_window()
        assert focused is None


def test_hyprland_malformed_json():
    inspector = HyprlandInspector(hyprctl_path="/usr/bin/hyprctl")
    with patch("subprocess.Popen") as mock_popen:
        proc = MagicMock()
        proc.communicate.return_value = ("NOT_VALID_JSON{{{", "")
        proc.returncode = 0
        mock_popen.return_value = proc

        with pytest.raises(HyprlandError, match="Failed to parse hyprctl"):
            inspector.list_windows()
