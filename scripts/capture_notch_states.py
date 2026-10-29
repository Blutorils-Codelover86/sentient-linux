"""
Automated capture script for hover-driven Sentient Linux Notch interaction.
Validates:
- Compact resting notch has no expand/collapse buttons.
- Pointer hover smoothly expands into small interactive notch (TYPING).
- Moving pointer away collapses after 200ms grace window.
- Typing keeps notch open even if pointer leaves.
"""

from __future__ import annotations
import os
import subprocess
import time
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib

from sentient_linux.core.coordinator import CommandCoordinator
from sentient_linux.gui.pill_window import SentientPillWindow, NotchPhase
from sentient_linux.gui.theme import GTK_CSS

ARTIFACT_DIR = "/home/blu/.gemini/antigravity-cli/brain/b05194ee-6e3c-42d5-8a69-927678e33b18"
os.makedirs(ARTIFACT_DIR, exist_ok=True)


def capture_step(step_name: str, filename: str):
    output_path = os.path.join(ARTIFACT_DIR, filename)
    cmd = f"grim {output_path}"
    subprocess.run(cmd, shell=True, check=True)
    print(f"Captured {step_name} -> {output_path}")


def main():
    app = Gtk.Application(application_id="ai.sentient.linux.hovercapture")

    def on_activate(application):
        provider = Gtk.CssProvider()
        provider.load_from_data(GTK_CSS.encode("utf-8"))
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

        coordinator = CommandCoordinator()
        window = SentientPillWindow(app=application, coordinator=coordinator, reduced_motion=True)
        window.present()

        # Step 1: Capture resting notch (HIDDEN)
        def step1():
            capture_step("1. Resting Compact Notch (No Buttons)", "hover_notch_resting.png")
            # Step 2: Hover pointer enters compact notch -> expands to small interactive notch
            window._on_motion_enter(None, 10.0, 10.0)
            GLib.timeout_add(500, step2)
            return False

        def step2():
            capture_step("2. Hover-Expanded Interactive Notch", "hover_notch_expanded.png")
            # Step 3: Type into entry
            window.typing_entry.set_text("Summarize open workspace")
            # Simulate pointer moving away while typing -> should STAY OPEN
            window._on_motion_leave(None)
            GLib.timeout_add(500, step3)
            return False

        def step3():
            capture_step("3. Typing Keeps Notch Open When Pointer Leaves", "hover_notch_typing_stay.png")
            # Step 4: Clear text and trigger collapse
            window.typing_entry.set_text("")
            window._on_motion_leave(None)
            # Wait past the 200ms grace window
            GLib.timeout_add(350, step4)
            return False

        def step4():
            capture_step("4. Auto-Collapsed After Pointer Leaves", "hover_notch_collapsed.png")
            print("All hover-driven notch states captured successfully!")
            GLib.timeout_add(300, app.quit)
            return False

        GLib.timeout_add(600, step1)

    app.connect("activate", on_activate)
    app.run([])


if __name__ == "__main__":
    main()
