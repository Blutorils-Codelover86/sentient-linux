"""
Script to capture and verify notch geometry stability and visual layout integrity.
Captures screenshots of:
1. Resting compact pill (340x44)
2. Mid-expansion morph
3. Hover-expanded interactive notch (480x72)
4. Mid-collapse morph
5. Collapsed resting pill (340x44)
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
    subprocess.run(f"magick {full_path} -crop 680x140+620+940 +repage {crop_path}", shell=True, check=True)
    print(f"Captured {step_name} -> {crop_path}")


def main():
    app = Gtk.Application(application_id="ai.sentient.linux.visualverification")

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
        window = SentientPillWindow(app=application, coordinator=coordinator, reduced_motion=False)
        window.present()

        # Step 1: Initial resting state
        def step1():
            capture_and_crop("1. Resting Compact State (340px)", "notch_visual_step1_resting")
            # Trigger hover expansion
            window._on_motion_enter(None, 10.0, 10.0)
            GLib.timeout_add(70, step2_mid_expand)
            return False

        # Step 2: Mid-expansion frame
        def step2_mid_expand():
            capture_and_crop("2. Mid-Expansion Morph", "notch_visual_step2_mid_expand")
            GLib.timeout_add(300, step3_expanded)
            return False

        # Step 3: Fully expanded
        def step3_expanded():
            capture_and_crop("3. Fully Expanded Notch (480px)", "notch_visual_step3_expanded")
            # Trigger pointer leave to auto-collapse
            window._on_motion_leave(None)
            window._on_collapse_timeout()
            GLib.timeout_add(70, step4_mid_collapse)
            return False

        # Step 4: Mid-collapse frame
        def step4_mid_collapse():
            capture_and_crop("4. Mid-Collapse Morph", "notch_visual_step4_mid_collapse")
            GLib.timeout_add(350, step5_collapsed)
            return False

        # Step 5: Fully collapsed back to resting
        def step5_collapsed():
            capture_and_crop("5. Collapsed Back to Resting (340px)", "notch_visual_step5_collapsed")

            # Generate montage
            montage_path = os.path.join(ARTIFACT_DIR, "notch_visual_restored_montage.png")
            step1_c = os.path.join(ARTIFACT_DIR, "notch_visual_step1_resting_crop.png")
            step2_c = os.path.join(ARTIFACT_DIR, "notch_visual_step2_mid_expand_crop.png")
            step3_c = os.path.join(ARTIFACT_DIR, "notch_visual_step3_expanded_crop.png")
            step4_c = os.path.join(ARTIFACT_DIR, "notch_visual_step4_mid_collapse_crop.png")
            step5_c = os.path.join(ARTIFACT_DIR, "notch_visual_step5_collapsed_crop.png")

            subprocess.run(
                f"magick montage {step1_c} {step2_c} {step3_c} {step4_c} {step5_c} -tile 1x5 -geometry +0+4 {montage_path}",
                shell=True,
                check=True,
            )
            print(f"Generated restored visual montage -> {montage_path}")
            GLib.timeout_add(200, app.quit)
            return False

        GLib.timeout_add(400, step1)

    app.connect("activate", on_activate)
    app.run([])


if __name__ == "__main__":
    main()
