# Sentient Linux Architecture — Phase 2

## Overview

Sentient OS for Linux is a modular, privacy-first desktop companion engineered specifically for Arch Linux running the Omarchy desktop on the Hyprland Wayland compositor.

Unlike monolithic desktop assistants, Sentient Linux enforces strict architectural separation across five distinct domains:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           1. PERCEPTION LAYER                               │
│  - Hyprland IPC (hyprctl -j)               - Screenshot Capture (grim)      │
│  - Window / Geometry / Title Queries       - Desktop Context Snapshots      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           2. REASONING LAYER                                │
│  - Inference Router                        - Capability Validation          │
│  - Local Ollama (HTTP 127.0.0.1:11434)     - Optional Gated Cloud Providers │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           3. SECURITY & POLICY LAYER                         │
│  - Deterministic Authorization Gate        - Default-Deny Security Model    │
│  - PII Regex Scanner & Sanitizer           - Strict Phase 2 Read-Only Mode  │
│  - Emergency Stop / In-flight Cancellation - Protected System Directories   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           4. EXECUTION LAYER                                │
│  - Action Supervisor                       - Action Schema Validation       │
│  - Live MCP Client (computer-use-linux)    - Stage A Mock Client            │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           5. MEMORY & STORAGE LAYER                         │
│  - Safe Knowledge Storage Engine           - Atomic os.replace File Writes  │
│  - Directory Traversal & Symlink Defenses  - Rollback Backups (.bak)        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Module Directory Structure

```text
src/sentient_linux/
├── core/
│   ├── coordinator.py      # CommandCoordinator: lifecycle and task orchestration
│   ├── state_machine.py    # Deterministic lifecycle states (IDLE, PERCEIVING, REASONING, etc.)
│   └── events.py           # Structured event definitions and event bus
├── perception/
│   ├── hyprland.py         # Read-only hyprctl inspector for windows, monitors, workspaces
│   ├── screenshots.py      # On-demand grim screen capture with 0600 temp file isolation
│   └── context.py          # Unified DesktopContext aggregator
├── inference/
│   ├── router.py           # Multi-provider router with capability negotiation
│   ├── ollama.py           # Local Ollama HTTP JSON client
│   ├── openai_provider.py  # Cloud OpenAI adapter with consent enforcement
│   └── anthropic_provider.py # Cloud Anthropic Claude adapter with consent enforcement
├── computer_use/
│   ├── action_schema.py    # ActionType, ProposedAction, and parameter validators
│   ├── mock_client.py      # Stage A mock MCP client for isolated testing
│   ├── mcp_client.py       # Stage B JSON-RPC stdio client for computer-use-linux
│   └── supervisor.py       # Authoritative ActionSupervisor firewall
├── security/
│   ├── permissions.py      # Fine-grained Permission enum and PermissionManager
│   ├── policy.py           # SecurityPolicy: default-deny, system directory shields
│   ├── privacy.py          # PIIScanner (SSN, credit card, passport) and ConsentManager
│   └── emergency_stop.py   # EmergencyStop controller and child process cleanup
├── knowledge/
│   └── storage.py          # KnowledgeStorage: atomic writes, backup, symlink defenses
└── cli.py                  # Operator command-line interface
```

## Data Flow & Lifecycle

1. **User Request (`ask` / CLI):**
   - The user issues a command or prompt.
   - `CommandCoordinator` verifies `EmergencyStop` is not triggered.
2. **Perception (`snapshot`):**
   - `HyprlandInspector` queries `activewindow`, `clients`, and `monitors` via `hyprctl -j`.
   - If requested, `ScreenshotEngine` invokes `grim` to capture a temporary image with `0600` permissions.
3. **Reasoning (`InferenceRouter`):**
   - Desktop context is formatted into a prompt block.
   - If image is present, the router verifies model vision capability.
   - Local Ollama daemon generates response.
4. **Execution Gate (`ActionSupervisor`):**
   - Any proposed desktop action is validated against schema.
   - `SecurityPolicy` checks permissions. In Phase 2, mutating actions are unconditionally denied.
5. **Deterministic Cleanup:**
   - Temporary screenshot files are deleted via `unlink()`.
   - `EmergencyStop` tracks and registers all active subprocesses.
