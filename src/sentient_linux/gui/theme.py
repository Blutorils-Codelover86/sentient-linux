"""
Official Sentient OS Theme and Design Tokens for Linux.
Extracted from Theme.swift, GlowButton.swift, and SpinningLogo.swift.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple

# RGBA tuples (0.0 - 1.0)
ColorRGBA = Tuple[float, float, float, float]
ColorRGB = Tuple[float, float, float]


@dataclass(frozen=True)
class SentientPalette:
    # Core Surfaces
    bg: ColorRGB = (0.0, 0.0, 0.0)                         # Pure OLED black
    panel: ColorRGB = (0.053, 0.058, 0.072)                # Moonlit slate (#0e0f12)
    card_bg: ColorRGB = (0.047, 0.047, 0.059)             # Deep card surface (#0c0c0f)
    elevated: ColorRGBA = (1.0, 1.0, 1.0, 0.05)            # Elevated glass surface
    stroke: ColorRGBA = (1.0, 1.0, 1.0, 0.09)              # Subtle razor boundary
    secondary: ColorRGBA = (1.0, 1.0, 1.0, 0.55)          # Muted secondary text
    faint: ColorRGBA = (1.0, 1.0, 1.0, 0.32)              # Faint borders & hints

    # Accents
    accent: ColorRGB = (0.62, 0.55, 1.0)                   # Soft violet glow (#9e8cff)
    knowledge_accent: ColorRGB = (0.557, 0.651, 1.0)       # Starlight periwinkle (#8ea6ff)
    knowledge_link: ColorRGB = (0.435, 0.714, 1.0)         # Sky blue wikilink (#6fb6ff)
    dawn_cyan: ColorRGB = (0.333, 0.757, 0.941)            # Dawn cyan (#55c1f0)

    # Inks
    status_ink: ColorRGB = (0.914, 0.906, 0.933)           # #e9e7ee
    body_ink: ColorRGB = (0.608, 0.604, 0.627)             # #9b9aa0
    label_ink: ColorRGB = (0.431, 0.427, 0.459)            # #6e6d75
    green: ColorRGB = (0.290, 0.871, 0.502)                # #4ade80 (Kept / healthy)
    amber: ColorRGB = (1.0, 0.765, 0.443)                  # #ffc371 (Attention / waiting)
    gold: ColorRGB = (0.851, 0.702, 0.294)                 # #d9b34b (Open-source mark)
    red: ColorRGB = (1.0, 0.36, 0.36)                      # #ff5c5c (Error / alert)

    # Canonical AI Spectrum Stops (GlowHalo.stops)
    spectrum_stops: Tuple[ColorRGB, ...] = (
        (0.992, 0.886, 0.639),  # 0: Warm Yellow (#fde2a3)
        (1.000, 0.557, 0.235),  # 1: Orange (#ff8e3c)
        (1.000, 0.275, 0.275),  # 2: Red (#ff4646)
        (0.910, 0.220, 0.561),  # 3: Pink (#e8388f)
        (0.608, 0.282, 0.831),  # 4: Purple (#9b48d4)
        (0.424, 0.361, 0.898),  # 5: Indigo (#6c5ce5)
        (0.290, 0.565, 0.886),  # 6: Blue (#4a90e2)
        (0.992, 0.886, 0.639),  # 7: Warm Yellow wrap
    )

    # Tuned Mascot Ring Stops (SpinningLogo.bandStops with saturated gold seam)
    mascot_stops: Tuple[ColorRGB, ...] = (
        (0.970, 0.700, 0.240),  # Saturated gold seam (#f7b23d)
        (1.000, 0.557, 0.235),  # Orange
        (1.000, 0.275, 0.275),  # Red
        (0.910, 0.220, 0.561),  # Pink
        (0.608, 0.282, 0.831),  # Purple
        (0.424, 0.361, 0.898),  # Indigo
        (0.290, 0.565, 0.886),  # Blue
        (0.970, 0.700, 0.240),  # Saturated gold wrap
    )


THEME = SentientPalette()

# GTK4 CSS Stylesheet for Living Glass surfaces and widgets
GTK_CSS = """
window.sentient-pill-window {
    background-color: transparent;
}

.living-glass-pill {
    background-color: rgba(14, 15, 18, 0.82);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 20px;
    padding: 6px 14px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.65), 0 0 16px rgba(158, 140, 255, 0.15);
    transition: all 200ms cubic-bezier(0.16, 1, 0.3, 1);
}

.living-glass-pill:hover {
    background-color: rgba(22, 23, 28, 0.90);
    border-color: rgba(255, 255, 255, 0.22);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.75), 0 0 24px rgba(158, 140, 255, 0.28);
}

.living-glass-expanded {
    background-color: rgba(12, 12, 15, 0.92);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 24px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.85), 0 0 30px rgba(158, 140, 255, 0.18);
    padding: 18px;
}

.whisper-text {
    font-family: monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
    color: rgba(255, 255, 255, 0.55);
}

.readback-text {
    font-family: serif;
    font-style: italic;
    font-size: 13px;
    color: #e9e7ee;
}

.chat-entry {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 14px;
    color: #e9e7ee;
    padding: 8px 12px;
    font-size: 13px;
    caret-color: #8ea6ff;
}

.chat-entry:focus {
    border-color: rgba(142, 166, 255, 0.50);
    box-shadow: 0 0 12px rgba(142, 166, 255, 0.25);
}

.action-btn {
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 12px;
    color: #cfcdd6;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
    transition: all 150ms ease;
}

.action-btn:hover {
    background-color: rgba(255, 255, 255, 0.12);
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.20);
}

.stop-btn {
    background-color: rgba(255, 92, 92, 0.15);
    border: 1px solid rgba(255, 92, 92, 0.35);
    border-radius: 12px;
    color: #ff5c5c;
    font-weight: 600;
    padding: 4px 10px;
    font-size: 11px;
    letter-spacing: 1px;
}

.stop-btn:hover {
    background-color: rgba(255, 92, 92, 0.30);
    border-color: rgba(255, 92, 92, 0.60);
    color: #ffffff;
}

.context-chip {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 3px 8px;
    font-family: monospace;
    font-size: 10px;
    color: #9b9aa0;
}

.status-dot-green {
    color: #4ade80;
}

.status-dot-amber {
    color: #ffc371;
}

.history-card-user {
    background-color: rgba(255, 255, 255, 0.04);
    border-radius: 12px;
    padding: 8px 12px;
    margin-bottom: 6px;
    color: #e9e7ee;
    font-size: 12.5px;
}

.history-card-assistant {
    background-color: rgba(14, 15, 18, 0.70);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    padding: 8px 12px;
    margin-bottom: 8px;
    color: #cfcdd6;
    font-size: 12.5px;
}
"""
