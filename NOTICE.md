# Notice — Sentient OS for Linux (Omarchy Port)

Copyright (C) 2026 Sentient OS Labs and the Sentient OS Linux Port contributors.

This project is a downstream Linux adaptation of Sentient OS, originally created by
Sentient OS Labs (<https://sentient-os.ai/> and <https://github.com/Sentient-OS-Labs/sentient-os>).

## Licensing

This software is distributed under the GNU Affero General Public License Version 3 (AGPL-3.0).
See [LICENSE](LICENSE) for the complete license terms.

## Attribution

- Original Project: **Sentient OS** (macOS)
- Upstream Organization: Sentient OS Labs
- Upstream License: GNU Affero General Public License v3.0
- Downstream Adaptation: **Sentient OS for Linux (Omarchy / Hyprland)**
- Date of Adaptation: October 2026

## Component Attribution & Lineage

1. **Algorithms & Prompt Architecture:**
   - The knowledge base synthesis architecture, byte-budgeted corpus slicing,
     fail-closed triage prompt design, and deterministic PII regex filtering
     are adapted from the upstream Swift codebase (`VaultGenerator.swift`,
     `CorpusSlicer.swift`, `Triage.swift`, and `PIIScan.swift`).

2. **Linux Integrations (Independently Implemented):**
   - Hyprland IPC and Wayland window inspection are independently implemented
     using `hyprctl`.
   - Screen capture pipeline is independently implemented using `grim`.
   - Computer-use execution interfaces with `@agent-sh/computer-use-linux`
     via Model Context Protocol (MCP) JSON-RPC 2.0.
   - Inference routing interfaces with local Ollama (`http://127.0.0.1:11434`)
     and standard OpenAI / Anthropic API specifications.
   - Emergency stop and default-deny security policy are independently
     designed specifically for Linux multi-user desktop security.

3. **Exclusions:**
   - No Apple macOS binaries, DMG images, Sparkle updater assets, or proprietary
     helper applications are bundled, redistributed, or extracted.
