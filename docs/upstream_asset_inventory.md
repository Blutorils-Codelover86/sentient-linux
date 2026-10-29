# Sentient OS Upstream Visual Asset & Design Token Inventory

This inventory documents the exact design tokens, source file paths, colors, typography, dimensions, materials, and procedural visual components from the official Sentient OS macOS codebase (`https://github.com/Sentient-OS-Labs/sentient-os`).

---

## 1. Source File Mapping

| Upstream Source File | Key Responsibilities & Components | Linux Port Destination |
| :--- | :--- | :--- |
| `Sentient OS macOS/Views/Theme.swift` | Global color palette, `Ink` tokens, `MonoCaps`, `GlassCard`, typography rules | `src/sentient_linux/gui/theme.py` |
| `Sentient OS macOS/Views/Sidekick/SidekickStyle.swift` | `SidekickStyle` tokens (`ink`, `secondary`, `accent`, `base`), `SidekickGlass`, `SidekickMark`, `SidekickAtmosphere`, `SidekickWorkingText` | `src/sentient_linux/gui/theme.py`, `src/sentient_linux/gui/glass.py` |
| `Sentient OS macOS/Views/Sidekick/SidekickComposer.swift` | Glass composer capsule, 36×36 circular send/stop button, conic glowing halo, multiline text entry | `src/sentient_linux/gui/expanded_view.py` |
| `Sentient OS macOS/Views/Sidekick/SidekickTranscript.swift` | Empty state (`"A little help. A lot more possible."`), `SidekickMessageRow`, user bubbles, markdown rendering | `src/sentient_linux/gui/expanded_view.py` |
| `Sentient OS macOS/Views/Sidekick/SidekickWorkDisclosure.swift` | Collapsible work disclosure card, live step rows, status line, elapsed timer | `src/sentient_linux/gui/expanded_view.py` |
| `Sentient OS macOS/Notch Magic/SpinningLogo.swift` | 2D brand mark: planet dot, additive heart, fine white ring, saturated spectrum band, spin clock | `src/sentient_linux/gui/mascot.py` |
| `Sentient OS macOS/Views/Orb.swift` | 3D living Orb: `OrbMark` (static glyph), 5.5s harmonic breathing, depth-sorted ring | `src/sentient_linux/gui/mascot.py` |
| `Sentient OS macOS/Views/GlowButton.swift` | Canonical `GlowHalo.stops` conic gradient sequence | `src/sentient_linux/gui/theme.py`, `src/sentient_linux/gui/mascot.py` |
| `Sentient OS macOS/Notch Magic/NotchView.swift` | Collapsed & expanded notch geometry, serif-italic read-back captions, twin control slots | `src/sentient_linux/gui/pill_window.py` |

---

## 2. Color Tokens

### 2.1 Core Monochrome & Ink Palette (`SidekickStyle` & `Theme`)
- **Base / Canvas:** Pure OLED Black `#000000` (`Color.black`)
- **Primary Ink:** Crisp White `#ededed` (`Color(white: 0.93)`)
- **Secondary Ink:** Muted Gray `#878787` (`Color(white: 0.53)`)
- **Accent Ink:** Bright Gray `#d6d6d6` (`Color(white: 0.84)`)
- **Faint:** `rgba(255, 255, 255, 0.32)`
- **Panel Background:** `#0e0f12` (`Color(red: 0.053, green: 0.058, blue: 0.072)`)
- **Card Background:** `#0c0c0f` (`Color(red: 0.047, green: 0.047, blue: 0.059)`)
- **User Message Bubble Fill:** `#131313` (`Color(white: 0.075)`)
- **User Message Bubble Stroke:** `rgba(255, 255, 255, 0.075)`

### 2.2 Semantic Accent Colors (`Theme.Ink` & `Theme`)
- **Success / Survivor Green:** `#4ade80` (`Color(red: 0.290, green: 0.871, blue: 0.502)`)
- **Caution / Warm Amber:** `#ffc371` (`Color(red: 1.0, green: 0.765, blue: 0.443)`)
- **Open-Source Gold:** `#d9b34b` (`Color(red: 0.851, green: 0.702, blue: 0.294)`)
- **Alert / Status Red:** `#ff5c5c` (`Color(red: 1.0, green: 0.36, blue: 0.36)`)
- **Soft Violet Glow:** `#9e8cff` (`Color(red: 0.62, green: 0.55, blue: 1.0)`)
- **Knowledge Wikilink Sky Blue:** `#6fb6ff` (`Color(red: 0.435, green: 0.714, blue: 1.0)`)
- **Dawn Cyan:** `#55c1f0` (`Color(red: 0.333, green: 0.757, blue: 0.941)`)

### 2.3 Sentient Spectrum (`GlowHalo.stops` & `SpinningLogo.bandStops`)
Canonical conic gradient stops for the spinning logo, glowing buttons, and atmospheric halo:

| Stop Index | RGB Float Values | Hex Equivalent | Description |
| :--- | :--- | :--- | :--- |
| **0 (Seam start)** | `(0.970, 0.700, 0.240)` | `#f7b23d` | Saturated Gold (replaces pale `#fde2a3` in `SpinningLogo`) |
| **1** | `(1.000, 0.557, 0.235)` | `#ff8e3c` | Vibrant Orange |
| **2** | `(1.000, 0.275, 0.275)` | `#ff4646` | Radiant Red |
| **3** | `(0.910, 0.220, 0.561)` | `#e8388f` | Saturated Pink |
| **4** | `(0.608, 0.282, 0.831)` | `#9b48d4` | Violet / Purple |
| **5** | `(0.424, 0.361, 0.898)` | `#6c5ce5` | Deep Indigo |
| **6** | `(0.290, 0.565, 0.886)` | `#4a90e2` | Luminous Blue |
| **7 (Seam wrap)** | `(0.970, 0.700, 0.240)` | `#f7b23d` | Smooth seam closure |

---

## 3. Geometry, Spacing & Materials

### 3.1 Acrylic Glass (`SidekickGlass`)
- **Corner Radius:** 18px continuous
- **Fill:** Ultra-thin acrylic: `rgba(17, 17, 20, 0.75)` with deep black layer `rgba(0, 0, 0, 0.70)`
- **Stroke / Border:** Razor 0.75px white border:
  - Standard: `rgba(255, 255, 255, 0.09)`
  - Prominent (composer, dialog): `rgba(255, 255, 255, 0.18)`
- **Drop Shadow:** Double-layer shadow:
  - High blur diffuse: radius 22px, `rgba(255, 255, 255, 0.035)`
  - Depth contact shadow: radius 18px, offset y +12px, `rgba(0, 0, 0, 0.30)`

### 3.2 Pill Window Dimensions (`NotchView` & Linux Bottom Pill)
- **Base Height:** 38px–42px (full capsule radius: 19px–21px)
- **Base Width (Collapsed):** 360px–380px
- **Monitor Placement:** Bottom-center, 20 logical px above bottom screen edge
- **Internal Margins:**
  - Horizontal padding: 14px
  - Control slot size: 22px (exact optical square matching the logo)
  - Text margin: 10px

### 3.3 Expanded Sidekick Dimensions (`SidekickOverviewLayout`)
- **Window Width:** 720px–760px
- **Window Height:** 520px–560px
- **Layout Spacing:**
  - Content padding: Horizontal 28px, Top 18px, Bottom 12px
  - Message bubble spacing: 18px
  - User message indent: Left spacer minimum 58px (right-anchored)
  - Assistant message: Left-anchored, transparent background, right spacer 14px

### 3.4 Composer Capsule (`SidekickComposer`)
- **Capsule Padding:** 17px all sides
- **Send Button:** Exact 36×36 circle
  - *Inactive State:* `rgba(255, 255, 255, 0.055)` background, `rgba(255, 255, 255, 0.09)` stroke, `arrow.up` in `rgba(255, 255, 255, 0.30)`
  - *Active State:* Solid `#ededed` ink fill, pure black `#000000` arrow icon, surrounded by 48×48 blurred conic halo (`blur: 11px`, `opacity: 0.75`) and 39×39 stroke halo (`lineWidth: 3px`, `opacity: 0.95`)
  - *Running State:* 36×36 circle, fill `rgba(255, 255, 255, 0.10)`, stroke `rgba(255, 255, 255, 0.18)`, icon `stop.fill` in `#ededed`

---

## 4. Typography Hierarchy

| Style Role | Font Family | Size | Weight | Color | Tracking / Style |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Empty State Hero** | System Display (SF Pro / Cantarell) | 23px | Medium (500) | `#ededed` | Optical sizing, natural kerning |
| **Empty State Subtitle** | System Display | 13px | Regular (400) | `#878787` | Normal |
| **Composer Input** | System Text | 15px | Regular (400) | `#ededed` | Multi-line 1–5 lines |
| **Pill Whisper / Readback** | System Serif (FreeSerif / Noto Serif) | 13px | Italic (400) | `#ededed` | Wrapped in curly quotes `“…”` |
| **MonoCaps Status Voice** | System Monospace | 10.5px | Medium (500) | `#878787` | Wide letter-spacing +1.2px, ALL-CAPS |
| **User Message Body** | System Text | 14px | Regular (400) | `#ededed` | Crisp readability |
| **Assistant Markdown Body** | System Text | 14px | Regular (400) | `#ededed` | Formatted headers, code blocks |

---

## 5. Living Procedural Motion Rules

1. **Brand Mark Spin Cadence:**
   - Idle Spin: 13.0 seconds per revolution (slow, meditative).
   - Fast / Running Spin: 2.0 seconds per revolution (prompt, energetic).
   - Seamless Speed Anchor: Changes in rotation speed maintain continuous angular position without jump cuts.
2. **Harmonic Heartbeat Breathing:**
   - Harmonic period: 5.5 seconds (`(sin(2πt / 5.5) + 1) / 2`).
   - Breaths through core white heart opacity and ambient halo scale (+3.5%).
3. **Working Text Shimmer:**
   - Sweep interval: 2.8 seconds linear sweep with soft linear gradient mask `[.clear, white(0.75), .clear]`.
4. **Compositor Efficiency:**
   - Frame rate target: 60 FPS active, 30 FPS background, 0 FPS when hidden.
   - Vector-crisp drawing via Cairo; no heavy raster blurs on large canvases.
