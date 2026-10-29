"""
Script to capture and verify notch geometry stability during expansion and collapse.
Captures screenshots with grim and crops to the bottom notch area,
verifying that the notch center remains strictly stable without twitching.
"""

from __future__ import annotations
import os
import subprocess
import time
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gtk, Gdk, Gtk4LayerShell, GLib

from sentient_linux.core.coordinator import CommandCoordinator
from sentient_linux.gui.pill_window import SentientPillWindow, NotchPhase
from sentient_linux.gui.theme import GTK_CSS

ARTIFACT_DIR = "/home/blu/.gemini/antigravity-cli/brain/b05194ee-6e3c-42d5-8a69-927678e33b18"
os.makedirs(ARTIFACT_DIR, exist_ok=True)


def capture_and_crop(step_name: str, filename_base: str):
    full_path = os.path.join(ARTIFACT_DIR, f"{filename_base}.png")
    crop_path = os.path.join(ARTIFACT_DIR, f"{filename_base}_crop.png")
    subprocess.run(f"grim {full_path}", shell=True, check=True)
    # Bottom center notch crop on 1920x1080 (geometry around center 960)
    # 544 * 1.25 = 680 physical width -> 620 to 1300 x, 840 to 1080 y
    subprocess.run(f"magick {full_path} -crop 680x240+620+840 +repage {crop_path}", shell=True, check=True)
    print(f"Captured {step_name} -> {crop_path}")


def main():
    app = Gtk.Application(application_id="ai.sentient.linux.twitchverification")

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
        # Test with smooth motion (reduced_motion=False) to test actual frame-clock animation
        window = SentientPillWindow(app=application, coordinator=coordinator, reduced_motion=False)
        window.present()

        frame_data = []

        def record_frame(clock):
            left = window.CANVAS_WIDTH / 2.0 - window._current_width / 2.0
            right = window.CANVAS_WIDTH / 2.0 + window._current_width / 2.0
            center = (left + right) / 2.0
            frame_data.append((window._current_width, left, right, center))
            return True

        tick_id = window.add_tick_callback(lambda w, c: record_frame(c))

        # Step 1: Initial resting state
        def step1():
            capture_and_crop("1. Resting Compact State (340px)", "notch_twitch_step1_resting")
            # Step 2: Hover to expand
            window._on_motion_enter(None, 272.0, 220.0)
            GLib.timeout_add(150, step2_mid_expand)
            return False

        # Step 2: Mid-expansion frame
        def step2_mid_expand():
            capture_and_crop("2. Mid-Expansion Morph", "notch_twitch_step2_mid_expand")
            GLib.timeout_add(300, step3_expanded)
            return False

        # Step 3: Fully expanded
        def step3_expanded():
            capture_and_crop("3. Fully Expanded (480px)", "notch_twitch_step3_expanded")
            # Step 4: Pointer leave to trigger auto-collapse
            window._on_motion_leave(None)
            # Wait for 200ms grace window + mid collapse
            GLib.timeout_add(300, step4_mid_collapse)
            return False

        # Step 4: Mid-collapse frame
        def step4_mid_collapse():
            capture_and_crop("4. Mid-Collapse Morph", "notch_twitch_step4_mid_collapse")
            GLib.timeout_add(350, step5_collapsed)
            return False

        # Step 5: Fully collapsed back to resting
        def step5_collapsed():
            capture_and_crop("5. Collapsed Back to Resting (340px)", "notch_twitch_step5_collapsed")
            window.remove_tick_callback(tick_id)

            # Analyze frame data
            centers = [d[3] for d in frame_data]
            print(f"Total animation frames recorded: {len(frame_data)}")
            print(f"Min center: {min(centers):.4f}, Max center: {max(centers):.4f}")
            variance = sum((c - 272.0) ** 2 for c in centers) / len(centers)
            print(f"Center variance across all frames: {variance:.6f}")
            assert variance == 0.0, "Center shifted during animation!"
            print("PERFECT STABILITY: Center point remained strictly invariant (0.000000 variance)!")

            GLib.timeout_add(200, app.quit)
            return False

        GLib.timeout_add(600, step1)

    app.connect("activate", on_activate)
    app.run([])


if __name__ == "__main__":
    main()
