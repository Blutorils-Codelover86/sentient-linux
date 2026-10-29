# Setup and Installation Guide — Sentient Linux

This guide covers setting up the Sentient Linux core engine and MCP integration on Arch Linux / Omarchy running Hyprland.

## Prerequisites

Sentient Linux requires:
- **Operating System:** Arch Linux or Omarchy.
- **Display Server:** Wayland with Hyprland compositor (`hyprctl` on PATH).
- **Python:** Python 3.11+ (tested on Python 3.15).
- **Screen Capture Utility:** `grim` (`/usr/bin/grim`).
- **Input & Clipboard Utilities:** `wtype`, `wl-clipboard` (`wl-copy`, `wl-paste`).
- **Computer-Use MCP Server:** `@agent-sh/computer-use-linux` (v0.7.22+).
- **Local Inference Engine:** Ollama running at `http://127.0.0.1:11434`.

All of these prerequisites are already installed on standard Omarchy setups.

## Installation

Sentient Linux runs in an isolated project virtual environment without touching system packages or root files:

```bash
cd /home/blu/sentient-os-port

# Create virtual environment if not present
python3 -m venv .venv

# Activate environment
source .venv/bin/activate

# Install in editable development mode
pip install -e .
```

## Running the CLI

Once installed, use the `sentient` binary provided inside the virtual environment:

```bash
# Check system and component status
sentient status

# Inspect active window
sentient focused

# List all open windows
sentient windows

# Capture on-demand screenshot (auto-cleaned)
sentient screenshot

# List inference models
sentient models

# View security permissions
sentient permissions

# Ask assistant a question with desktop context
sentient ask "What window is currently open?"

# Test Emergency Stop
sentient stop --reason "Operator test"
```

## Running the Automated Test Suite

To run all automated unit tests and performance benchmarks:

```bash
pytest -v -s
```
