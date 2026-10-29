"""
Command-Line Interface for Sentient Linux (Phase 2 Prototype).
Provides operator commands for status, windows, screenshots, models, permissions, and STOP.
"""

from __future__ import annotations
import argparse
import ctypes
import json
import os
import sys
from pathlib import Path

# Preload libgtk4-layer-shell with RTLD_GLOBAL before Gtk/libwayland import
for _candidate in ["/usr/lib/libgtk4-layer-shell.so", "/usr/lib64/libgtk4-layer-shell.so"]:
    if os.path.exists(_candidate):
        try:
            ctypes.CDLL(_candidate, ctypes.RTLD_GLOBAL)
            break
        except Exception:
            pass

from sentient_linux import __version__
from sentient_linux.core.coordinator import CommandCoordinator
from sentient_linux.perception.hyprland import HyprlandInspector
from sentient_linux.perception.screenshots import ScreenshotEngine
from sentient_linux.inference.router import InferenceRouter
from sentient_linux.inference.ollama import OllamaClient
from sentient_linux.computer_use.mcp_client import LiveMCPClient
from sentient_linux.security.permissions import PermissionManager
from sentient_linux.security.emergency_stop import EmergencyStop


def cmd_status(coordinator: CommandCoordinator, args: argparse.Namespace) -> int:
    """Show comprehensive environment and component status."""
    print("=" * 60)
    print(f" Sentient OS for Linux — Status Report (v{__version__})")
    print("=" * 60)

    # 1. Desktop & Session
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "unknown")
    session_type = os.environ.get("XDG_SESSION_TYPE", "unknown")
    print(f"Desktop Session : {desktop} ({session_type})")

    # 2. Hyprland
    inspector = coordinator.inspector
    hypr_ok = inspector.is_available()
    print(f"Hyprland IPC    : {'AVAILABLE' if hypr_ok else 'UNAVAILABLE'} (hyprctl)")

    # 3. Screenshot (grim)
    grim_ok = coordinator.screenshots.is_available()
    print(f"Screen Capture  : {'AVAILABLE' if grim_ok else 'UNAVAILABLE'} (grim)")

    # 4. Inference (Ollama)
    ollama = coordinator.inference.ollama
    ollama_ok = ollama.is_reachable()
    print(f"Local Inference : {'ONLINE' if ollama_ok else 'OFFLINE'} ({ollama.host})")
    if ollama_ok:
        try:
            models = ollama.list_models()
            model_names = [m.name for m in models]
            print(f"  Models ({len(models)}): {', '.join(model_names[:5])}")
        except Exception as e:
            print(f"  Error querying models: {e}")

    # 5. Computer-Use MCP
    mcp_client = LiveMCPClient()
    mcp_ok = mcp_client.is_available()
    print(f"MCP Integration : {'FOUND' if mcp_ok else 'NOT FOUND'} ({mcp_client.command or 'None'})")

    # 6. Emergency Stop
    stop_active = coordinator.emergency_stop.is_stopped()
    print(f"Emergency Stop  : {'TRIGGERED / BLOCKED' if stop_active else 'READY (IDLE)'}")

    # 7. Security Policy Mode
    print("Security Policy : STRICT DEFAULT-DENY (Mutating actions disabled in Phase 2)")
    print("=" * 60)
    return 0


def cmd_windows(coordinator: CommandCoordinator, args: argparse.Namespace) -> int:
    """List open client windows on Hyprland."""
    inspector = coordinator.inspector
    try:
        windows = inspector.list_windows()
    except Exception as err:
        print(f"Error querying windows: {err}", file=sys.stderr)
        return 1

    if not windows:
        print("No open client windows detected.")
        return 0

    print(f"Open Windows ({len(windows)}):")
    print("-" * 75)
    print(f"{'PID':<8} {'WS':<6} {'CLASS':<20} {'FOCUSED':<8} {'TITLE'}")
    print("-" * 75)
    for w in windows:
        focused_str = "YES" if w.focused else "no"
        title_trunc = w.title[:35] + ("..." if len(w.title) > 35 else "")
        print(f"{w.pid:<8} {w.workspace_name:<6} {w.wm_class[:18]:<20} {focused_str:<8} {title_trunc}")
    print("-" * 75)
    return 0


def cmd_focused(coordinator: CommandCoordinator, args: argparse.Namespace) -> int:
    """Display detailed metadata for the currently focused window."""
    inspector = coordinator.inspector
    try:
        w = inspector.get_focused_window()
    except Exception as err:
        print(f"Error querying focused window: {err}", file=sys.stderr)
        return 1

    if not w:
        print("No window currently has focus.")
        return 0

    print("Focused Window Metadata:")
    print("-" * 45)
    print(f"Title         : {w.title}")
    print(f"Class         : {w.wm_class} (initial: {w.initial_class})")
    print(f"PID           : {w.pid}")
    print(f"Workspace     : {w.workspace_name} (ID: {w.workspace_id})")
    print(f"Address       : {w.address}")
    print(f"Geometry      : {w.geometry.box_str}")
    print(f"Floating      : {w.floating}")
    print(f"Fullscreen    : {w.fullscreen}")
    print(f"Monitor ID    : {w.monitor}")
    print("-" * 45)
    return 0


def cmd_screenshot(coordinator: CommandCoordinator, args: argparse.Namespace) -> int:
    """Explicitly capture a screenshot."""
    engine = coordinator.screenshots
    output_path = Path(args.output) if args.output else None

    print("Executing explicit screenshot capture...")
    try:
        result = engine.capture(output_file=output_path)
    except Exception as err:
        print(f"Screenshot capture failed: {err}", file=sys.stderr)
        return 1

    print(f"Capture successful!")
    print(f"Path    : {result.path}")
    print(f"Latency : {result.latency_ms:.2f} ms")
    print(f"Size    : {result.size_bytes} bytes")

    if output_path is None:
        print("Note: Temporary file created with mode 0600. Cleaning up demonstration file...")
        result.cleanup()
        print("Cleaned up successfully.")
    else:
        print(f"Saved explicitly to: {result.path}")
    return 0


def cmd_models(coordinator: CommandCoordinator, args: argparse.Namespace) -> int:
    """List available local and cloud inference models."""
    ollama = coordinator.inference.ollama
    print("Available Inference Models:")
    print("-" * 50)
    print("Local Provider (Ollama @ http://127.0.0.1:11434):")
    try:
        models = ollama.list_models()
        if not models:
            print("  No models downloaded in local Ollama.")
        for m in models:
            vis = "Vision: YES" if m.has_vision else "Vision: no"
            print(f"  - {m.name:<30} [{vis}]")
    except Exception as err:
        print(f"  Ollama offline or unreachable: {err}")

    print("\nCloud Providers (Disabled by default, requires consent):")
    print(f"  - OpenAI (api.openai.com)   : {'CONFIGURED' if coordinator.inference.openai.is_configured() else 'NO API KEY'}")
    print(f"  - Anthropic (api.anthropic.com): {'CONFIGURED' if coordinator.inference.anthropic.is_configured() else 'NO API KEY'}")
    print("-" * 50)
    return 0


def cmd_permissions(coordinator: CommandCoordinator, args: argparse.Namespace) -> int:
    """Display active security permissions and safety boundaries."""
    perms = coordinator.policy.permissions.list_permissions()
    print("Sentient OS Linux — Security Permissions:")
    print("-" * 50)
    for perm_name, state in sorted(perms.items()):
        status_colored = state.upper()
        print(f"  {perm_name:<26} : {status_colored}")
    print("-" * 50)
    print("Safety Rules:")
    print("  * Mutating actions are unconditionally blocked in Phase 2.")
    print("  * System directories (/boot, /etc, ~/.config/hypr) are forbidden.")
    print("  * Default-deny on all ungranted permissions.")
    return 0


def cmd_ask(coordinator: CommandCoordinator, args: argparse.Namespace) -> int:
    """Send an instruction to the assistant with desktop context."""
    prompt = args.prompt
    include_context = not args.no_context
    include_screenshot = args.screenshot

    print(f"Processing instruction: '{prompt}'...")
    if include_screenshot:
        print("Capturing explicit screenshot for visual context...")

    try:
        response = coordinator.ask(
            prompt=prompt,
            include_context=include_context,
            include_screenshot=include_screenshot,
        )
        print("\nResponse:")
        print("=" * 60)
        print(response.strip())
        print("=" * 60)
        return 0
    except Exception as err:
        print(f"Error processing instruction: {err}", file=sys.stderr)
        return 1


def cmd_stop(coordinator: CommandCoordinator, args: argparse.Namespace) -> int:
    """Trigger or test the Emergency Stop mechanism."""
    reason = args.reason or "CLI user initiated STOP"
    stopped = coordinator.stop(reason=reason)
    print(f"Emergency Stop triggered: {reason}")
    print(f"Processes signaled/terminated: {stopped}")
    print("All subsequent operations will be blocked until reset.")
    return 0


def cmd_gui(coordinator: CommandCoordinator, args: argparse.Namespace) -> int:
    """Launch the floating bottom-center Sentient assistant GUI."""
    from sentient_linux.gui.app import run_gui
    print("Launching Sentient Linux GUI (Bottom-center Floating Pill)...")
    return run_gui(
        coordinator=coordinator,
        start_expanded=args.expanded,
        low_power=args.low_power,
        reduced_motion=args.reduced_motion,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="sentient",
        description="Sentient OS for Linux (Omarchy / Hyprland Port)",
    )
    parser.add_argument("--version", action="version", version=f"sentient {__version__}")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # status
    p_status = subparsers.add_parser("status", help="Show system and component status")
    p_status.set_defaults(func=cmd_status)

    # windows
    p_windows = subparsers.add_parser("windows", help="List open windows in Hyprland")
    p_windows.set_defaults(func=cmd_windows)

    # focused
    p_focused = subparsers.add_parser("focused", help="Show currently focused window details")
    p_focused.set_defaults(func=cmd_focused)

    # screenshot
    p_shot = subparsers.add_parser("screenshot", help="Capture on-demand screenshot")
    p_shot.add_argument("-o", "--output", help="Explicit file destination (default: temporary with auto-cleanup)")
    p_shot.set_defaults(func=cmd_screenshot)

    # models
    p_models = subparsers.add_parser("models", help="List available AI inference models")
    p_models.set_defaults(func=cmd_models)

    # permissions
    p_perms = subparsers.add_parser("permissions", help="View security permissions")
    p_perms.set_defaults(func=cmd_permissions)

    # ask
    p_ask = subparsers.add_parser("ask", help="Send instruction to assistant")
    p_ask.add_argument("prompt", help="User instruction or prompt")
    p_ask.add_argument("--no-context", action="store_true", help="Exclude desktop window context")
    p_ask.add_argument("--screenshot", action="store_true", help="Include visual screenshot")
    p_ask.set_defaults(func=cmd_ask)

    # stop
    p_stop = subparsers.add_parser("stop", help="Trigger Emergency Stop")
    p_stop.add_argument("-r", "--reason", help="Reason for stopping")
    p_stop.set_defaults(func=cmd_stop)

    # gui
    p_gui = subparsers.add_parser("gui", help="Launch the bottom-center floating assistant GUI")
    p_gui.add_argument("--expanded", action="store_true", help="Launch directly in expanded panel state")
    p_gui.add_argument("--low-power", action="store_true", help="Enable low-power rendering mode (30 FPS)")
    p_gui.add_argument("--reduced-motion", action="store_true", help="Disable procedural spinning animations")
    p_gui.set_defaults(func=cmd_gui)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    coordinator = CommandCoordinator()
    return args.func(coordinator, args)


if __name__ == "__main__":
    sys.exit(main())
