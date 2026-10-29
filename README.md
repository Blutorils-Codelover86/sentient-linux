# Sentient OS for Linux (Omarchy / Hyprland Port)

A privacy-centric personal AI desktop companion engineered for Arch Linux running Omarchy on Hyprland. Downstream adaptation of [Sentient OS](https://github.com/Sentient-OS-Labs/sentient-os).

Licensed under the **GNU Affero General Public License Version 3 (AGPL-3.0)**. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).

---

## Architecture

Sentient Linux separates the AI assistance lifecycle into five decoupled layers:

1. **Perception:** Real-time Hyprland window/desktop state queries (`hyprctl -j`) and on-demand screenshot capture (`grim`).
2. **Reasoning:** Provider-agnostic inference router connecting to local Ollama (`http://127.0.0.1:11434`) and optional consent-gated cloud frontier models.
3. **Security:** Deterministic default-deny authorization gate (`SecurityPolicy`), PII scanner/sanitizer, and emergency killswitch (`EmergencyStop`).
4. **Computer Use:** Standard Model Context Protocol (MCP) client communicating with `@agent-sh/computer-use-linux`.
5. **Memory:** Atomic, symlink-safe Markdown knowledge storage (`~/Sentient OS - Knowledge Base/`).

---

## Quickstart

### Prerequisites
- Arch Linux / Omarchy with Hyprland
- Python 3.11+
- `grim`, `wtype`, `wl-clipboard`
- Ollama running locally

### Installation

```bash
cd /home/blu/sentient-os-port

# Create virtualenv and install in editable mode
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Usage

```bash
# Launch the bottom-center floating assistant GUI
sentient gui

# Launch directly in expanded state
sentient gui --expanded

# Low-power / reduced-motion rendering modes
sentient gui --low-power
sentient gui --reduced-motion

# Check status of desktop, Hyprland, Ollama, and MCP
sentient status

# Inspect the active/focused window
sentient focused

# List open client windows
sentient windows

# Capture on-demand screenshot (auto-cleaned)
sentient screenshot

# List inference models
sentient models

# View security permissions
sentient permissions

# Ask assistant a question with desktop context via CLI
sentient ask "What window is currently open?"

# Test Emergency Stop
sentient stop
```

### Running Tests

```bash
pytest -v -s
```

---

## Documentation

- [Official Visual Audit & Design Tokens](docs/official_visual_audit.md)
- [UI Rendering Decision Specification](docs/ui_rendering_decision.md)
- [MACL Living Intelligence Specification](docs/living_intelligence.md)
- [Phase 3A Completion Report](docs/phase3a_completion.md)
- [Architecture Specification](docs/architecture.md)
- [Setup & Installation](docs/setup.md)
- [Security Model & Safety Gates](docs/security_model.md)
- [AI Provider Configuration](docs/provider_configuration.md)
- [Upstream Lineage](UPSTREAM.md)
- [Changelog & Modifications](CHANGES.md)
