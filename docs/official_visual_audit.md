# Official Sentient OS Visual Audit & Design Token Mapping

> **Target:** Sentient OS macOS Upstream → Sentient Linux (MACL Living Intelligence)  
> **Source Files Audited:** `Theme.swift`, `NotchView.swift`, `NotchShape.swift`, `SpinningLogo.swift`, `Orb.swift`, `GlowButton.swift`, `BriefingCard.swift`, `HomeView.swift`, `NotchWindowController.swift`.  
> **Date:** October 2026  

---

## 1. Upstream Visual Philosophy & Design Language

Sentient OS is built upon a dark-only, tactile, and restrained aesthetic:
- **Materiality:** Pure OLED black (`#000000`) and moonlit slate (`#0e0f12`) treated as physical dark glass materials.
- **Glass & Elevation:** Translucent elevated layers (`rgba(255, 255, 255, 0.05)`) bordered by razor-thin edge strokes (`rgba(255, 255, 255, 0.09)`).
- **The AI Spectrum (`GlowHalo.stops`):** The signature gradient that runs across the website, logo, notch borders, and CTA buttons.
- **Typography:** Bold tight-tracked display headers, monospaced all-caps with wide tracking for machine status whispers (`MonoCaps`), and serif-italic for quoted spoken thoughts.
- **Motion:** Physics-based spring animations (`response: 0.52`, `damping: 0.72`) with 5.5-second natural harmonic breathing cycles.

---

## 2. Design Token Extraction

### A. Color Palette

| Token Name | Upstream Code Reference | Hex / RGBA Value | Role / Usage |
|---|---|---|---|
| `bg` | `Theme.bg` | `#000000` | Pure OLED background |
| `panel` | `Theme.panel` | `#0e0f12` (`rgb(14, 15, 18)`) | Moonlit slate panel & cards |
| `cardBG` | `Theme.Ink.cardBG` | `#0c0c0f` (`rgb(12, 12, 15)`) | Deep card surface |
| `elevated` | `Theme.elevated` | `rgba(255, 255, 255, 0.05)` | Glassy interactive elevation |
| `stroke` | `Theme.stroke` | `rgba(255, 255, 255, 0.09)` | Subtle boundary stroke |
| `secondary` | `Theme.secondary` | `rgba(255, 255, 255, 0.55)` | Subdued secondary text |
| `faint` | `Theme.faint` | `rgba(255, 255, 255, 0.32)` | Borders, hints, inactive glyphs |
| `accent` | `Theme.accent` | `#9e8cff` (`rgb(158, 140, 255)`) | Soft violet glow |
| `knowledgeAccent` | `Theme.knowledgeAccent` | `#8ea6ff` (`rgb(142, 166, 255)`) | Starlight periwinkle (interactive) |
| `knowledgeLink` | `Theme.knowledgeLink` | `#6fb6ff` (`rgb(111, 182, 255)`) | Web / note link sky blue |
| `green` | `Theme.Ink.green` | `#4ade80` (`rgb(74, 222, 128)`) | Online / healthy / kept verdict |
| `amber` | `Theme.Ink.amber` | `#ffc371` (`rgb(255, 195, 113)`) | Attention / awaiting approval |
| `gold` | `Theme.Ink.gold` | `#d9b34b` (`rgb(217, 179, 75)`) | Open-source pride mark |
| `red` | `Theme.Ink.red` | `#ff5c5c` (`rgb(255, 92, 92)`) | Alert / STOP / failure |
| `statusInk` | `Theme.Ink.statusInk` | `#e9e7ee` | Primary crisp text |
| `body` | `Theme.Ink.body` | `#9b9aa0` | Secondary description text |

### B. The Canonical AI Spectrum (`GlowHalo.stops`)

The canonical multi-color gradient sequence:
1. Warm Yellow / Gold: `#fde2a3` (`rgb(253, 226, 163)`)
2. Deep Orange: `#ff8e3c` (`rgb(255, 142, 60)`)
3. Crimson Red: `#ff4646` (`rgb(255, 70, 70)`)
4. Hot Pink: `#e8388f` (`rgb(232, 56, 143)`)
5. Deep Purple: `#9b48d4` (`rgb(155, 72, 212)`)
6. Electric Indigo: `#6c5ce5` (`rgb(108, 92, 229)`)
7. Sky Blue: `#4a90e2` (`rgb(74, 144, 226)`)
8. Seam Wrap: `#fde2a3` (smooth cyclical wrap)

In the compact ring and mascot (`SpinningLogo.bandStops`), stop 0 and 7 are deepened to `#f7b23d` (saturated gold) so the ring reads vibrantly without washing out into a white spot.

---

## 3. Official Mascot & Sentient Mark

In upstream Sentient OS, the mascot identity appears in two synchronized forms:
1. **The 2D Living Mark (`SpinningLogo.swift`):**
   - Core: A brilliant white planet dot (`width = size * 0.36`) enveloped by a soft additive glow (`width = size * 0.50`, opacity `0.6`).
   - Inner Frame: A razor-thin white boundary ring (`max(0.75, size * 0.028)`).
   - Spectrum Ring: A thick, sharp, saturated color band (`size * 0.17`) mapped to the AI spectrum, spinning slowly (13 s per cycle during idle; 2 s per cycle during active processing).
2. **The 3D Dimensional Celestial Orb (`Orb.swift`):**
   - Central Core: Glowing white heart dot surrounded by a dark glassy sphere.
   - Orbiting Particle Constellation: 450 fine mineral grains and depth-sorted Keplerian motes that orbit around the planet with two counter-rotating shimmer glints.
   - Harmonic Breathing: A continuous 5.5-second sinusoidal breath (`sin(t * 2 * pi / 5.5)`), pulsing the halo radius by ±3.5%.

### MACL Living Intelligence Enhancement Mapping

| State | Visual Behavior in Linux Port | Upstream Basis |
|---|---|---|
| **Idle** | Stable silhouette, 5.5s subtle breathing pulse, quiet rainbow glow. | `SpinningLogo(fast: false)` + `Orb.mode = .idle` |
| **Listening** | Rhythmic particle flutter, gentle expansion of inner heart glow. | `NotchPhase.listening` |
| **Thinking** | Soft constellation redistribution, 2s accelerated orbit. | `SpinningLogo(fast: true)` + `Orb.mode = .processing` |
| **Acting** | Directed pulse, bright progress illumination along pill rim. | `NotchPhase.running` |
| **Awaiting Approval** | Warm amber luminescence (`Theme.Ink.amber`), waiting indicator. | `Orb.mode = .attention` (`#ffc371`) |
| **Error** | Brief disturbance, subtle red accent (`Theme.Ink.red`), smooth recovery. | `NotchPhase.finishing(.failed)` |

---

## 4. Upstream-to-Linux Component Mapping

| macOS Upstream Component | Linux / Omarchy Implementation | Architectural Rationale |
|---|---|---|
| `NotchWindowController` | `SentientPillWindow` via `Gtk4LayerShell` | Anchored at **bottom-center** (20 px above edge) rather than top notch. |
| `NotchView` & `NotchContent` | GTK4 Custom Widget with Cairo rendering | Reproduces the exact capsule geometry, border stroke, and AI spectrum rim. |
| `SpinningLogo` & `Orb` | `LivingMascot` Cairo procedural renderer | Combines the 2D mark with living particle breathing and stateful reactive motion. |
| `PromptBar` & `SidekickComposer` | `SentientChatBox` with GTK4 Entry & Buttons | Fast text input, desktop context pill, model selector, STOP button. |
| `BriefingCard` & `HomeView` | `SentientExpandedPanel` | Upward-expanding drawer displaying conversation history, context metadata, and controls. |
