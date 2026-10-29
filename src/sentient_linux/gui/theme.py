"""
Official Sentient OS Theme and Design Tokens for Linux.
Faithfully ported from Sentient OS macOS:
- Theme.swift
- SidekickStyle.swift
- SidekickComposer.swift
- SidekickTranscript.swift
- NotchView.swift & NotchShape.swift
- SpinningLogo.swift
- GlowButton.swift
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

# RGBA tuples (0.0 - 1.0)
ColorRGBA = Tuple[float, float, float, float]
ColorRGB = Tuple[float, float, float]


@dataclass(frozen=True)
class SentientPalette:
    # Upstream SidekickStyle Identity
    sidekick_ink: ColorRGB = (0.93, 0.93, 0.93)            # #ededed - Crisp white ink
    sidekick_secondary: ColorRGB = (0.53, 0.53, 0.53)      # #878787 - Muted secondary text
    sidekick_accent: ColorRGB = (0.84, 0.84, 0.84)         # #d6d6d6 - Subtle highlight
    sidekick_base: ColorRGB = (0.0, 0.0, 0.0)              # #000000 - Pure OLED black
    user_bubble: ColorRGB = (0.075, 0.075, 0.075)          # #131313 - User message card fill

    # Upstream Theme Surfaces
    bg: ColorRGB = (0.0, 0.0, 0.0)                         # Pure OLED black
    panel: ColorRGB = (0.053, 0.058, 0.072)                # Moonlit slate (#0e0f12)
    card_bg: ColorRGB = (0.047, 0.047, 0.059)             # Deep card surface (#0c0c0f)
    elevated: ColorRGBA = (1.0, 1.0, 1.0, 0.05)            # Elevated glass surface
    stroke: ColorRGBA = (1.0, 1.0, 1.0, 0.09)              # Razor 0.75px boundary (0.09 opacity)
    stroke_prominent: ColorRGBA = (1.0, 1.0, 1.0, 0.18)    # Prominent boundary (0.18 opacity)
    secondary: ColorRGBA = (1.0, 1.0, 1.0, 0.55)          # Muted secondary text
    faint: ColorRGBA = (1.0, 1.0, 1.0, 0.32)              # Faint hints & borders

    # Accents & Inks
    accent: ColorRGB = (0.62, 0.55, 1.0)                   # Soft violet glow (#9e8cff)
    knowledge_accent: ColorRGB = (0.557, 0.651, 1.0)       # Starlight periwinkle (#8ea6ff)
    knowledge_link: ColorRGB = (0.435, 0.714, 1.0)         # Sky blue wikilink (#6fb6ff)
    dawn_cyan: ColorRGB = (0.333, 0.757, 0.941)            # Dawn cyan (#55c1f0)
    status_ink: ColorRGB = (0.914, 0.906, 0.933)           # #e9e7ee
    body_ink: ColorRGB = (0.608, 0.604, 0.627)             # #9b9aa0
    label_ink: ColorRGB = (0.431, 0.427, 0.459)            # #6e6d75
    green: ColorRGB = (0.290, 0.871, 0.502)                # #4ade80 (Kept / healthy)
    amber: ColorRGB = (1.0, 0.765, 0.443)                  # #ffc371 (Attention / waiting)
    gold: ColorRGB = (0.851, 0.702, 0.294)                 # #d9b34b (Open-source mark)
    red: ColorRGB = (1.0, 0.36, 0.36)                      # #ff5c5c (Error / alert)

    # Canonical AI Spectrum Stops (GlowHalo.stops from GlowButton.swift)
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

    # Tuned Mascot Ring Stops (SpinningLogo.bandStops with saturated gold seam #f7b23d)
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


# GTK4 CSS Stylesheet for Official Sentient OS Visual Parity
GTK_CSS = """
window.sentient-pill-window {
    background-color: transparent;
}

/* =========================================================================
   BOTTOM-ATTACHED DYNAMIC ISLAND NOTCH (Flush to Screen Bottom Bezel)
   ========================================================================= */
.bottom-notch-pill, .sidekick-pill {
    background-color: transparent;
    border: none;
    padding: 0;
    margin: 0;
}

.bottom-notch-content {
    padding: 0 16px;
    min-height: 40px;
}

/* =========================================================================
   SIDEKICK EXTENDED WINDOW SURFACE (Flush to Screen Bottom Bezel)
   ========================================================================= */
.sidekick-expanded, .living-glass-expanded {
    background-color: #0c0c0e;
    border: 0.75px solid rgba(255, 255, 255, 0.14);
    border-bottom: none;
    border-top-left-radius: 24px;
    border-top-right-radius: 24px;
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
    box-shadow: 0 -24px 64px rgba(0, 0, 0, 0.95), 0 0 1px rgba(255, 255, 255, 0.15);
    padding: 12px 18px 18px 18px;
}

/* Official Sidekick Card Header (uploaded_media_1_1793269445180.png / Hero parity) */
.sidekick-header-card {
    background-color: #121216;
    border: 0.75px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    margin: 4px 6px 4px 6px;
}

.sidekick-header-inner {
    padding: 10px 14px;
}

.sidekick-card-title {
    font-size: 15px;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: -0.2px;
}

.sidekick-card-subtitle {
    font-size: 12px;
    font-weight: 400;
    color: #878787;
}

.sidekick-model-btn {
    background: transparent;
    border: none;
    padding: 0;
}

.sidekick-model-pill {
    background-color: rgba(255, 255, 255, 0.05);
    border: 0.75px solid rgba(255, 255, 255, 0.09);
    border-radius: 12px;
    padding: 4px 10px;
    transition: all 120ms ease;
}

.sidekick-model-btn:hover .sidekick-model-pill {
    background-color: rgba(255, 255, 255, 0.10);
    border-color: rgba(255, 255, 255, 0.20);
}

.sidekick-popover contents {
    background-color: rgba(16, 16, 20, 0.98);
    border: 0.75px solid rgba(255, 255, 255, 0.16);
    border-radius: 14px;
    box-shadow: 0 16px 36px rgba(0, 0, 0, 0.75);
}

.sidekick-model-list {
    padding: 6px 4px;
}

.sidekick-model-item {
    background: transparent;
    border: none;
    border-radius: 8px;
    color: #ededed;
    font-size: 12px;
    font-family: monospace;
    padding: 6px 12px;
    transition: all 120ms ease;
}

.sidekick-model-item:hover {
    background-color: rgba(255, 255, 255, 0.10);
    color: #ffffff;
}

.sidekick-context-bar {
    padding: 2px 14px;
    margin-bottom: 2px;
}

/* =========================================================================
   OFFICIAL TOP NAVIGATION BAR (HomeView.swift topBar parity)
   ========================================================================= */
.sidekick-top-bar {
    padding-bottom: 10px;
    border-bottom: 0.5px solid rgba(255, 255, 255, 0.06);
    margin-bottom: 6px;
}

.sidekick-brand-title {
    font-size: 13.5px;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: -0.1px;
}

.sidekick-proactive-dock {
    background-color: rgba(255, 255, 255, 0.05);
    border: 0.75px solid rgba(255, 255, 255, 0.09);
    border-radius: 14px;
    padding: 3px 10px;
    color: #cfcdd6;
    font-size: 11px;
    font-weight: 500;
    transition: all 140ms ease-out;
}

.sidekick-proactive-dock:hover {
    background-color: rgba(255, 255, 255, 0.10);
    border-color: rgba(255, 255, 255, 0.20);
    color: #ffffff;
}

.sidekick-nav-item {
    background-color: transparent;
    border: none;
    color: #878787;
    font-size: 12px;
    font-weight: 500;
    padding: 5px 8px;
    border-radius: 10px;
    transition: all 140ms ease-out;
}

.sidekick-nav-item:hover {
    background-color: rgba(255, 255, 255, 0.06);
    color: #ffffff;
}

.sidekick-tool-btn {
    min-width: 32px;
    min-height: 32px;
    border-radius: 16px;
    background-color: rgba(255, 255, 255, 0.04);
    border: 0.75px solid rgba(255, 255, 255, 0.08);
    color: #cfcdd6;
    padding: 0;
    font-size: 13px;
    transition: all 140ms ease-out;
}

.sidekick-tool-btn:hover {
    background-color: rgba(255, 255, 255, 0.10);
    border-color: rgba(255, 255, 255, 0.20);
    color: #ffffff;
}

/* =========================================================================
   EMPTY STATE (SidekickTranscript.swift parity)
   ========================================================================= */
.sidekick-empty-title {
    font-size: 23px;
    font-weight: 500;
    color: #ededed;
    letter-spacing: -0.2px;
}

.sidekick-empty-subtitle {
    font-size: 13px;
    color: #878787;
    line-height: 1.4;
}

/* =========================================================================
   MESSAGES & TRANSCRIPT (SidekickTranscript.swift parity)
   ========================================================================= */
.sidekick-transcript {
    padding: 6px 4px;
}

/* User Message: Right-anchored, #131313 fill, radius 18px, padding 12px 17px */
.sidekick-user-bubble {
    background-color: #131313;
    border: 0.75px solid rgba(255, 255, 255, 0.075);
    border-radius: 18px;
    padding: 12px 17px;
    margin-left: 58px;
    margin-bottom: 14px;
    color: #ededed;
    font-size: 14px;
    line-height: 1.45;
}

/* Assistant Message: Left-anchored, transparent background, text #ededed */
.sidekick-assistant-message {
    background-color: transparent;
    padding: 4px 12px;
    margin-right: 14px;
    margin-bottom: 14px;
    color: #ededed;
    font-size: 14px;
    line-height: 1.5;
}

/* Work Disclosure Card (SidekickWorkDisclosure.swift parity) */
.sidekick-work-disclosure {
    background-color: rgba(255, 255, 255, 0.035);
    border: 0.75px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 10px 14px;
    margin-bottom: 12px;
    color: #878787;
    font-size: 12px;
}

.sidekick-work-status {
    font-size: 12px;
    font-weight: 500;
    color: #ededed;
}

/* =========================================================================
   COMPOSER CAPSULE (SidekickComposer.swift parity)
   ========================================================================= */
.sidekick-composer {
    background-color: #141418;
    border: 0.75px solid rgba(255, 255, 255, 0.14);
    border-radius: 18px;
    padding: 10px 14px;
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.40);
    transition: all 180ms ease;
}

.sidekick-composer:focus-within {
    border-color: rgba(255, 255, 255, 0.28);
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.50), 0 0 16px rgba(255, 255, 255, 0.04);
}

.sidekick-entry {
    background-color: transparent;
    border: none;
    outline: none;
    color: #ededed;
    font-size: 15px;
    caret-color: #d6d6d6;
    padding: 4px 6px;
}

.sidekick-entry:focus {
    box-shadow: none;
}

/* Circular 36x36 Send Button (Disabled) */
.sidekick-send-btn-disabled {
    min-width: 36px;
    min-height: 36px;
    border-radius: 18px;
    background-color: rgba(255, 255, 255, 0.055);
    border: 0.75px solid rgba(255, 255, 255, 0.09);
    color: rgba(255, 255, 255, 0.30);
    font-size: 15px;
    font-weight: 600;
    padding: 0;
}

/* Circular 36x36 Send Button (Active with Conic Halo) */
.sidekick-send-btn-active {
    min-width: 36px;
    min-height: 36px;
    border-radius: 18px;
    background-color: #ededed;
    border: 1px solid rgba(255, 255, 255, 0.60);
    color: #000000;
    font-size: 15px;
    font-weight: 700;
    padding: 0;
    box-shadow: 0 0 14px rgba(253, 226, 163, 0.70), 0 0 24px rgba(232, 56, 143, 0.50);
    transition: all 150ms ease;
}

.sidekick-send-btn-active:hover {
    background-color: #ffffff;
    box-shadow: 0 0 18px rgba(253, 226, 163, 0.90), 0 0 30px rgba(232, 56, 143, 0.70);
}

/* Circular 36x36 Stop Button */
.sidekick-stop-btn {
    min-width: 36px;
    min-height: 36px;
    border-radius: 18px;
    background-color: rgba(255, 255, 255, 0.10);
    border: 1px solid rgba(255, 255, 255, 0.18);
    color: #ededed;
    font-size: 12px;
    font-weight: 600;
    padding: 0;
}

.sidekick-stop-btn:hover {
    background-color: rgba(255, 92, 92, 0.25);
    border-color: rgba(255, 92, 92, 0.50);
    color: #ff5c5c;
}

/* =========================================================================
   WHISPER & READ-BACK VOICES
   ========================================================================= */
.whisper-text {
    font-family: monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.2px;
    color: rgba(255, 255, 255, 0.53);
}

.readback-text {
    font-family: serif;
    font-style: italic;
    font-size: 13px;
    color: #ededed;
}

.status-dot-green {
    color: #4ade80;
    font-size: 11px;
}

.status-dot-amber {
    color: #ffc371;
    font-size: 11px;
}
"""
