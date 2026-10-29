# Linux-Native UI Rendering Architecture Decision

> **Target:** Sentient OS for Linux — Phase 3A Graphical Experience  
> **Compositor:** Hyprland (Wayland) on Arch Linux / Omarchy  
> **Evaluation Date:** October 2026  

---

## 1. Candidate Stacks Evaluated

| Stack | Wayland / Hyprland Support | Transparency & Blur | Bottom-Pill Positioning | Keyboard Focus Control | Performance & Footprint | Verdict |
|---|---|---|---|---|---|---|
| **GTK4 + gtk4-layer-shell + Cairo** | **Native** (`wl-layer-shell`) | Excellent (`cairo` vector canvas + CSS backdrop) | **Direct** (LayerShell bottom anchor + margin) | **On-demand** (no focus theft when idle) | Low CPU, hardware-accelerated, zero extra packages | **Selected** |
| **Qt6 / QML (Quickshell)** | Good (QtWayland) | Good | Possible, but complex standalone lifecycle | Can interfere with Omarchy shell | High memory overhead for standalone app | Secondary |
| **Regular Wayland Window (XDG Toplevel)** | Standard | Compositor dependent | Fragile (requires manual Hyprland window rules) | Tends to steal focus on creation | Good | Rejected for primary pill |
| **Electron / Webview** | Heavy (Chromium) | High resource cost | Layer-shell unsupported without native wrapper | Heavy focus wrestling | > 300 MB idle RAM, slow cold-boot | Rejected |

---

## 2. Rationale for GTK4 + gtk4-layer-shell + Cairo

1. **Native Wayland Layer-Shell Architecture (`gtk4-layer-shell`):**
   - Enables the floating pill to live in the compositor's `TOP` layer, floating above tiled applications without disrupting Hyprland tiling workspaces.
   - Positioning is deterministic and mathematical:
     ```python
     Gtk4LayerShell.init_for_window(window)
     Gtk4LayerShell.set_layer(window, Gtk4LayerShell.Layer.TOP)
     Gtk4LayerShell.set_anchor(window, Gtk4LayerShell.Edge.BOTTOM, True)
     Gtk4LayerShell.set_anchor(window, Gtk4LayerShell.Edge.LEFT, False)
     Gtk4LayerShell.set_anchor(window, Gtk4LayerShell.Edge.RIGHT, False)
     Gtk4LayerShell.set_margin(window, Gtk4LayerShell.Edge.BOTTOM, 20)
     ```
   - Automatically re-centers when display resolution, monitor assignment, or fractional scaling changes.

2. **Strict Keyboard Focus Control:**
   - While in the collapsed pill state (idle), keyboard mode is set to `Gtk4LayerShell.KeyboardMode.NONE`. It can **never** steal keyboard focus from the user's active editor, browser, or terminal.
   - When the user clicks the pill to expand the chat interface, the keyboard mode smoothly transitions to `Gtk4LayerShell.KeyboardMode.ON_DEMAND`, enabling full text input in the chat box.

3. **High-Fidelity Procedural Motion via Cairo:**
   - The official Sentient mascot (central white planet dot, additive glow, and orbiting spectrum ring) is rendered via a custom Cairo drawing surface.
   - Wall-clock-driven animations (`GLib.timeout_add` at 30–60 FPS) eliminate frame drops, decouple UI motion from background Ollama inference, and support instant reduced-motion / low-power fallbacks.

4. **Zero Package Footprint:**
   - `gtk4`, `gtk4-layer-shell`, `cairo`, and `python-gobject` are already present on the system. The application runs entirely within the project-local virtual environment (`.venv`) using system site packages, fulfilling the critical constraint of zero system package modifications.
