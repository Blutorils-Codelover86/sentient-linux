"""
Pytest configuration for Sentient Linux test suite.
Preloads GTK4 Layer Shell before any Wayland / GTK modules load.
"""

import ctypes
import os

for candidate in ["/usr/lib/libgtk4-layer-shell.so", "/usr/lib64/libgtk4-layer-shell.so"]:
    if os.path.exists(candidate):
        try:
            ctypes.CDLL(candidate, ctypes.RTLD_GLOBAL)
            break
        except Exception:
            pass
