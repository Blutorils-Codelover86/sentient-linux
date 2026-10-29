"""
Stage B Live MCP Client for Sentient Linux.
Connects to @agent-sh/computer-use-linux over JSON-RPC 2.0 stdio protocol.
Enforces strict read-only tool gating for Phase 2.
"""

from __future__ import annotations
import json
import logging
import os
import shutil
import subprocess
import threading
from typing import Any, Dict, List, Optional

from sentient_linux.computer_use.action_schema import (
    ActionType,
    MUTATING_ACTIONS,
    READ_ONLY_ACTIONS,
    ProposedAction,
)
from sentient_linux.security.emergency_stop import EmergencyStop
from sentient_linux.security.policy import PolicyViolationError

logger = logging.getLogger("sentient.computer_use.mcp_client")


class MCPClientError(RuntimeError):
    """Raised when an MCP communication or tool call fails."""
    pass


class LiveMCPClient:
    """
    Subprocess JSON-RPC 2.0 client for computer-use-linux MCP server.
    Enforces that mutating tools cannot be invoked during Phase 2.
    """

    DEFAULT_COMMAND = "computer-use-linux"

    def __init__(self, command: Optional[str] = None) -> None:
        self.command = command or self._find_mcp_binary()
        self.proc: Optional[subprocess.Popen] = None
        self._req_id = 0
        self._lock = threading.Lock()
        self.available_tools: List[str] = []
        self.emergency_stop = EmergencyStop()

    def _find_mcp_binary(self) -> Optional[str]:
        # Check PATH first
        path = shutil.which(self.DEFAULT_COMMAND)
        if path:
            return path
        # Check standard mise / npm global locations
        candidate = os.path.expanduser("~/.local/share/mise/installs/node/26.8.2/bin/computer-use-linux")
        if os.path.exists(candidate) and os.access(candidate, os.X_OK):
            return candidate
        return None

    def is_available(self) -> bool:
        return bool(self.command and os.path.exists(self.command))

    def start(self) -> None:
        """Start the MCP server process and perform initialize handshake."""
        self.emergency_stop.check()
        if self.proc and self.proc.poll() is None:
            return

        if not self.command or not os.path.exists(self.command):
            raise MCPClientError(f"computer-use-linux binary not found at '{self.command}'")

        try:
            self.proc = subprocess.Popen(
                [self.command, "mcp"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self.emergency_stop.register_process(self.proc)
        except Exception as err:
            raise MCPClientError(f"Failed to spawn MCP server process: {err}")

        # Send initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "sentient-linux", "version": "0.2.0"},
            },
        }
        resp = self._send_and_receive(init_req)
        if "error" in resp:
            self.stop()
            raise MCPClientError(f"MCP initialize failed: {resp['error']}")

        # List tools
        tools_req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {},
        }
        tools_resp = self._send_and_receive(tools_req)
        tools = tools_resp.get("result", {}).get("tools", [])
        self.available_tools = [t.get("name", "") for t in tools if isinstance(t, dict)]
        logger.info(f"Connected to MCP server. Discovered {len(self.available_tools)} tools.")

    def _next_id(self) -> int:
        with self._lock:
            self._req_id += 1
            return self._req_id

    def _send_and_receive(self, payload: Dict[str, Any], timeout: float = 8.0) -> Dict[str, Any]:
        """Send JSON-RPC message and read one line response."""
        self.emergency_stop.check()
        if not self.proc or self.proc.poll() is not None:
            raise MCPClientError("MCP server process is not running.")

        line = json.dumps(payload) + "\n"
        with self._lock:
            try:
                self.proc.stdin.write(line)
                self.proc.stdin.flush()
                response_line = self.proc.stdout.readline()
            except Exception as err:
                self.emergency_stop.check()
                raise MCPClientError(f"Error communicating with MCP server: {err}")

        if not response_line:
            raise MCPClientError("MCP server closed connection unexpectedly.")

        try:
            return json.loads(response_line)
        except json.JSONDecodeError as err:
            raise MCPClientError(f"Malformed JSON-RPC response from MCP server: {err}")

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke an MCP tool.
        Phase 2 boundary: blocks mutating actions deterministically.
        """
        self.emergency_stop.check()

        # Check if action is mutating
        try:
            action_type = ActionType(name)
            if action_type in MUTATING_ACTIONS:
                raise PolicyViolationError(
                    f"Refusing to execute mutating tool '{name}' on live desktop: "
                    f"mutating desktop operations are strictly disabled in Phase 2."
                )
        except ValueError:
            # If unrecognized tool name, treat as potentially mutating and block
            if name not in ["list_windows", "focused_window", "get_app_state", "list_apps", "doctor", "screenshot"]:
                raise PolicyViolationError(f"Unrecognized or unvetted MCP tool '{name}' is blocked by policy.")

        if not self.proc or self.proc.poll() is not None:
            self.start()

        req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments,
            },
        }

        resp = self._send_and_receive(req)
        if "error" in resp:
            raise MCPClientError(f"Tool '{name}' execution error: {resp['error']}")

        return resp.get("result", {})

    def stop(self) -> None:
        """Terminate MCP server child process."""
        if self.proc:
            try:
                self.emergency_stop.unregister_process(self.proc)
                self.proc.terminate()
                self.proc.wait(timeout=1.0)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            finally:
                self.proc = None
