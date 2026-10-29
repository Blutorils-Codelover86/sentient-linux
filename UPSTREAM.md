# Upstream Lineage & Tracking

- **Upstream Repository:** <https://github.com/Sentient-OS-Labs/sentient-os>
- **Target OS:** Arch Linux / Omarchy
- **Compositor:** Hyprland (Wayland)
- **Upstream Commit/Tag:** Cloned October 29, 2026 (tracking `main`)
- **Upstream License:** GNU Affero General Public License v3.0

## Architecture Comparison

| Domain | Upstream macOS | Linux / Omarchy Port |
|---|---|---|
| **Primary Language** | Swift 6 / SwiftUI / AppKit | Python 3.12+ (standard library + pytest) |
| **Window System** | macOS WindowServer & Quartz | Wayland (Hyprland compositor IPC) |
| **Window Queries** | `AXUIElement` / ScreenCaptureKit | `hyprctl activewindow -j`, `hyprctl clients -j` |
| **Screen Capture** | `/usr/sbin/screencapture` | `grim` (Wayland native capture) |
| **Synthetic Input** | macOS Accessibility / CGEvent | `wtype` (Wayland) / AT-SPI via `computer-use-linux` |
| **Computer-Use Helper** | Proprietary OpenAI DMG extraction | Open `@agent-sh/computer-use-linux` MCP server |
| **On-Device Inference** | Vendored `LiteRT-LM` (Metal shaders) | Local `Ollama` daemon (HTTP JSON API) |
| **Frontier Routing** | `CodexCLI.swift` / `ClaudeCLI.swift` | Provider-agnostic `InferenceRouter` |
| **Knowledge Vault** | `~/Sentient OS - Knowledge Base/` | `~/Sentient OS - Knowledge Base/` (Identical schema) |
| **Overnight Scheduler**| `launchd` plist wake daemon | `systemd --user` timer / service |
| **Security & Permissions**| macOS TCC / Entitlements | Native Linux permission gatekeeper & emergency stop |

## Upstream CLA Notice

The upstream repository includes a Contributor License Agreement (CLA) for contributors intending to merge code back upstream into the dual-licensed commercial edition maintained by Sentient OS Labs. 

This Linux port is maintained downstream as an open-source derivative under the terms of the GNU AGPLv3. Independent forks and downstream distributions under AGPLv3 do not require signing the upstream CLA.
