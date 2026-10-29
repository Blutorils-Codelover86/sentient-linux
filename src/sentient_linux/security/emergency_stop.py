"""
Emergency Stop mechanism for Sentient Linux.
Provides immediate cancellation of in-flight tasks, subprocesses, and requests.
"""

from __future__ import annotations
import logging
import os
import signal
import subprocess
import threading
from typing import List, Optional

logger = logging.getLogger("sentient.security.emergency_stop")


class EmergencyStopError(RuntimeError):
    """Raised when an operation is attempted or cancelled due to Emergency Stop."""
    pass


class EmergencyStop:
    """
    Emergency Stop controller.
    Tracks in-flight processes and tasks to ensure prompt termination upon STOP trigger.
    Note: Emergency Stop terminates active operations and prevents new ones, but cannot
    reverse actions that have already been dispatched or completed on the desktop.
    """

    _instance: Optional[EmergencyStop] = None
    _lock = threading.Lock()

    def __new__(cls) -> EmergencyStop:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._stopped = False
        self._stop_reason: Optional[str] = None
        self._tracked_processes: List[subprocess.Popen] = []
        self._proc_lock = threading.Lock()
        self._initialized = True

    def is_stopped(self) -> bool:
        return self._stopped

    def get_reason(self) -> Optional[str]:
        return self._stop_reason

    def check(self) -> None:
        """Raise EmergencyStopError if currently in stopped state."""
        if self._stopped:
            raise EmergencyStopError(f"Emergency stop is active: {self._stop_reason or 'User initiated stop'}")

    def register_process(self, proc: subprocess.Popen) -> None:
        """Track a child subprocess for immediate termination if stopped."""
        with self._proc_lock:
            # Clean up terminated processes
            self._tracked_processes = [p for p in self._tracked_processes if p.poll() is None]
            if self._stopped:
                # If already stopped, terminate immediately
                try:
                    proc.terminate()
                except Exception:
                    pass
                raise EmergencyStopError("Cannot launch process: Emergency stop is active")
            self._tracked_processes.append(proc)

    def unregister_process(self, proc: subprocess.Popen) -> None:
        with self._proc_lock:
            if proc in self._tracked_processes:
                self._tracked_processes.remove(proc)

    def trigger(self, reason: str = "User initiated Emergency Stop") -> int:
        """
        Trigger emergency stop:
        1. Set stopped flag to block any new operations.
        2. Terminate all tracked child subprocesses.
        Returns the number of processes signaled.
        """
        self._stopped = True
        self._stop_reason = reason
        logger.warning(f"EMERGENCY STOP TRIGGERED: {reason}")

        signaled = 0
        with self._proc_lock:
            for proc in self._tracked_processes:
                if proc.poll() is None:
                    try:
                        logger.info(f"Terminating child process PID={proc.pid}")
                        proc.terminate()
                        signaled += 1
                    except Exception as err:
                        logger.error(f"Error terminating process PID={proc.pid}: {err}")
            # Quick grace check, then SIGKILL if still running
            for proc in self._tracked_processes:
                if proc.poll() is None:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            self._tracked_processes.clear()

        return signaled

    def reset(self) -> None:
        """Reset emergency stop state after explicit review."""
        with self._proc_lock:
            self._stopped = False
            self._stop_reason = None
            self._tracked_processes.clear()
        logger.info("Emergency Stop has been reset.")
