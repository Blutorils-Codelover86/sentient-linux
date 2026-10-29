"""
Sentient Linux GUI Subsystem.
Implements the bottom-center floating pill, living mascot, and expanded interface.
"""

import ctypes
import os

# Preload libgtk4-layer-shell with RTLD_GLOBAL to satisfy Wayland symbol resolution
for candidate in ["/usr/lib/libgtk4-layer-shell.so", "/usr/lib64/libgtk4-layer-shell.so"]:
    if os.path.exists(candidate):
        try:
            ctypes.CDLL(candidate, ctypes.RTLD_GLOBAL)
            break
        except Exception:
            pass

from sentient_linux.gui.theme import THEME, SentientPalette
from sentient_linux.gui.mascot import LivingMascot, MascotState
from sentient_linux.gui.glass import LivingGlassContainer
from sentient_linux.gui.expanded_view import ExpandedView
from sentient_linux.gui.pill_window import SentientPillWindow
from sentient_linux.gui.knowledge_view import SentientKnowledgeVaultWindow
from sentient_linux.gui.markdown_renderer import MarkdownBlockRenderer
from sentient_linux.gui.app import SentientApplication, run_gui

__all__ = [
    "THEME",
    "SentientPalette",
    "LivingMascot",
    "MascotState",
    "LivingGlassContainer",
    "ExpandedView",
    "SentientPillWindow",
    "SentientKnowledgeVaultWindow",
    "MarkdownBlockRenderer",
    "SentientApplication",
    "run_gui",
]
