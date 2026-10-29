# Security Model and Safety Specification

Sentient Linux is built around a **deterministic, default-deny security architecture**. AI model output is treated as untrusted data and can never directly invoke desktop actions or system shell commands.

## Core Security Principles

1. **Deterministic Action Firewall (`SecurityPolicy`):**
   - The LLM does not execute commands; it only proposes structured actions (`ProposedAction`).
   - Every proposed action must pass strict schema validation and deterministic policy evaluation by `ActionSupervisor`.
   - In Phase 2, mutating desktop actions (`click`, `type_text`, `press_key`, `move_window`, etc.) are unconditionally rejected.

2. **Protected System Boundaries:**
   - Any file operation or path resolution targeting system-critical directories is rejected with `PolicyViolationError`.
   - Protected paths include:
     - `/boot/`
     - `/etc/`
     - `/root/`
     - `/usr/`
     - `/var/`
     - `~/.config/hypr/` (Hyprland configuration)
     - `~/.config/omarchy/` (Omarchy desktop configuration)
     - `~/.config/systemd/` (Systemd user services)

3. **Privacy-First Data Protection (`PIIScanner`):**
   - Ported from upstream `PIIScan.swift`.
   - Deterministically detects SSNs, Luhn-valid credit card numbers, and passport numbers.
   - Logs are sanitized to prevent accidental leakage of API keys, bearer tokens, or PII.

4. **Default-Deny Cloud Data Transmission (`ConsentManager`):**
   - Cloud providers (OpenAI, Anthropic) are disabled by default.
   - No desktop context, window metadata, or screenshot content is transmitted externally without explicit user authorization designating the exact destination.

5. **Screen Capture Containment:**
   - Screenshots are taken strictly on explicit user demand (`sentient screenshot` or explicit instruction).
   - Captured frames are written to temporary files with mode `0600` (read/write only by the user).
   - Temporary frames are deleted via `unlink()` immediately after the inference request completes.

6. **Emergency Stop (`EmergencyStop`):**
   - Immediate task cancellation mechanism.
   - Tracks active child subprocesses (`grim`, `computer-use-linux`) and terminates them via SIGTERM/SIGKILL.
   - Prevents any new tasks from starting while stopped.
   - Does not claim to reverse actions that were already performed on the desktop.

7. **Knowledge Storage Isolation:**
   - Files are confined to `~/Sentient OS - Knowledge Base/`.
   - Symlinks into or out of the vault are rejected.
   - Path traversal (`../`) is blocked.
   - Atomic writes prevent partial corruption.
