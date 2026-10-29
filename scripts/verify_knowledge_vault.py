"""
Automated live visual capture of the Sentient Linux Knowledge Vault.
Launches the native window, captures screenshots of:
1. Default Overview note (pinned README, sidebar tree, rendered markdown, sky-blue wikilinks)
2. Followed [[wikilink]] (expanded folder, Back button in header, active selection)
3. Note search filtering
4. In-place Markdown Editor
5. Empty vault state
"""

from __future__ import annotations
import os
import shutil
import subprocess
import time
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gtk, Gdk, GLib

from sentient_linux.gui.knowledge_view import SentientKnowledgeVaultWindow
from sentient_linux.gui.theme import GTK_CSS

ARTIFACT_DIR = "/home/blu/.gemini/antigravity-cli/brain/b05194ee-6e3c-42d5-8a69-927678e33b18"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

SAMPLE_VAULT_DIR = Path("/tmp/sentient_test_vault")


def setup_sample_vault():
    if SAMPLE_VAULT_DIR.exists():
        shutil.rmtree(SAMPLE_VAULT_DIR)
    SAMPLE_VAULT_DIR.mkdir(parents=True)

    # README.md (Overview)
    readme_content = """# Sentient OS — Knowledge Base

Welcome to your personal intelligence vault. This knowledge base is stored 100% locally on your computer and completely private.

## Vault Map

- `Identity/` — who Jesai is. Start with [[Jesai Tarun - Current Portrait]].
- `Sentient OS/` — product thesis and roadmap. See [[Sentient OS - Product Thesis]].
- Core operating principles: [[Values and Working Style]].
- An *unresolved* note link: [[Uncreated Future Note]].

### Architecture & System Overview

The system uses an Obsidian-style Markdown directory structure combined with a living AI supervisor. Notes can link to each other seamlessly using standard wikilinks.

```
Sentient OS - Knowledge Base/
├── Identity/
│   ├── Jesai Tarun - Current Portrait.md
│   └── Values and Working Style.md
└── Sentient OS/
    ├── Product Thesis.md
    └── Architecture.md
```

All notes remain plain text Markdown on your local drive.
"""
    (SAMPLE_VAULT_DIR / "README.md").write_text(readme_content, encoding="utf-8")

    # Identity
    id_dir = SAMPLE_VAULT_DIR / "Identity"
    id_dir.mkdir()
    portrait = """---
tags: [identity, founder]
---
# Jesai Tarun - Current Portrait

Jesai Tarun is building **Sentient OS**, a privacy-first intelligence layer for a person's digital life.

His center of gravity is [[Sentient OS - Product Thesis]].

## Key Focus Areas

- Privacy-first on-device computer use
- Linux native desktop integration (Omarchy / Hyprland)
- Living Glass interface design
"""
    (id_dir / "Jesai Tarun - Current Portrait.md").write_text(portrait, encoding="utf-8")

    values = """# Values and Working Style

Speed, aesthetic taste, and genuine open-source.
Local computation whenever possible.
"""
    (id_dir / "Values and Working Style.md").write_text(values, encoding="utf-8")

    # Sentient OS
    os_dir = SAMPLE_VAULT_DIR / "Sentient OS"
    os_dir.mkdir()
    thesis = """# Sentient OS - Product Thesis

Sentient OS replaces the fragmented notifications and browser tabs of modern computing with an integrated, on-device intelligence partner.

Related: [[Jesai Tarun - Current Portrait|Jesai's Vision]].
"""
    (os_dir / "Product Thesis.md").write_text(thesis, encoding="utf-8")


def capture(name: str):
    full_path = os.path.join(ARTIFACT_DIR, f"{name}.png")
    crop_path = os.path.join(ARTIFACT_DIR, f"{name}_crop.png")
    # Capture full screen
    subprocess.run(f"grim {full_path}", shell=True, check=True)
    # Crop to the right tiled window (where Knowledge Vault is placed at [775, 36, 734, 816] * 1.25 = [969, 45, 918, 1020])
    subprocess.run(f"magick {full_path} -crop 918x1020+969+45 +repage {crop_path}", shell=True, check=True)
    print(f"Captured: {full_path} and cropped {crop_path}")


def main():
    setup_sample_vault()

    app = Gtk.Application(application_id="ai.sentient.linux.knowledge.verifier")

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

        window = SentientKnowledgeVaultWindow(app=application, vault_path=SAMPLE_VAULT_DIR)
        window.present()

        # Step 1: Capture initial Overview
        def step1():
            capture("knowledge_vault_step1_overview")
            GLib.timeout_add(300, step2)
            return False

        # Step 2: Follow a wikilink to "Jesai Tarun - Current Portrait"
        def step2():
            portrait_path = SAMPLE_VAULT_DIR / "Identity" / "Jesai Tarun - Current Portrait.md"
            window.follow_wikilink(portrait_path)
            capture("knowledge_vault_step2_navigated_note")
            GLib.timeout_add(300, step3)
            return False

        # Step 3: Search filtering for "thesis"
        def step3():
            window.search_entry.set_text("thesis")
            capture("knowledge_vault_step3_search")
            GLib.timeout_add(300, step4)
            return False

        # Step 4: Toggle raw Markdown editor mode
        def step4():
            window.search_entry.set_text("")
            window.begin_edit()
            capture("knowledge_vault_step4_editor")
            GLib.timeout_add(300, step5)
            return False

        # Step 5: Empty state
        def step5():
            empty_vault = Path("/tmp/sentient_empty_vault")
            if empty_vault.exists():
                shutil.rmtree(empty_vault)
            empty_vault.mkdir()
            window.exit_edit_discard()
            window.custom_vault_path = empty_vault
            window.reload_vault()
            capture("knowledge_vault_step5_empty_state")

            GLib.timeout_add(200, app.quit)
            return False

        GLib.timeout_add(500, step1)

    app.connect("activate", on_activate)
    app.run([])


if __name__ == "__main__":
    main()
