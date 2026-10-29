"""
Automated state capture script for Sentient Linux Notch interaction hierarchy.
Captures:
1. Resting compact notch (HIDDEN)
2. Interactive quick prompt input (TYPING)
3. Active computer-use progress & GlowHalo edge glow (RUNNING)
4. Inline response preview & quick reply (MESSAGE)
5. Full Sidekick conversation (EXPANDED)
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
    # Capture bottom region (center 800px width, bottom 600px height)
    # Using grim to capture full display or crop to bottom center
    cmd = f"grim {output_path}"
    subprocess.run(cmd, shell=True, check=True)
    print(f"Captured {step_name} -> {output_path}")


def main():
    app = Gtk.Application(application_id="ai.sentient.linux.capture")

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

        # Step 1: Capture resting notch (HIDDEN) after 600ms
        def step1():
            capture_step("Phase 1: Resting Notch (HIDDEN)", "notch_phase1_resting.png")
            # Step 2: Open quick input (TYPING)
            window.open_notch_input()
            window.typing_entry.set_text("Summarize open browser tabs")
            GLib.timeout_add(600, step2)
            return False

        def step2():
            capture_step("Phase 2: Quick Input (TYPING)", "notch_phase2_typing.png")
            # Step 3: Enter RUNNING with edge glow
            window.set_phase(NotchPhase.RUNNING)
            window.status_line.set_text("mcp: sentient_native/click (completed)...")
            GLib.timeout_add(600, step3)
            return False

        def step3():
            capture_step("Phase 3: Active Progress (RUNNING)", "notch_phase3_running.png")
            # Step 4: Enter MESSAGE with inline response and reply bar
            sample_answer = "I've checked your browser tabs. You have 3 tabs open: Sentient OS GitHub, Omarchy Documentation, and Arch Linux Wiki."
            window.set_phase(NotchPhase.MESSAGE, message_text=sample_answer)
            window.reply_entry.set_text("Can you export the bookmarks?")
            GLib.timeout_add(600, step4)
            return False

        def step4():
            capture_step("Phase 4: Inline Response & Reply (MESSAGE)", "notch_phase4_message.png")
            # Step 5: Expand into Full Sidekick conversation
            window.expand(draft="Can you export the bookmarks?")
            GLib.timeout_add(700, step5)
            return False

        def step5():
            capture_step("Phase 5: Full Sidekick Conversation (EXPANDED)", "notch_phase5_expanded.png")
            print("All 5 interaction phases captured successfully!")
            GLib.timeout_add(300, app.quit)
            return False

        GLib.timeout_add(700, step1)

    app.connect("activate", on_activate)
    app.run([])


if __name__ == "__main__":
    main()
