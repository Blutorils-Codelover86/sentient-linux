# Phase 3 Readiness Report & Technical Assessment

## Phase 2 Deliverables Status

| Requirement | Status | Notes |
|---|---|---|
| Read-only Hyprland Inspector | **Completed** | Full support for activewindow, clients, monitors, workspaces. |
| Screenshot Engine (`grim`) | **Completed** | Benchmarked at ~269 ms, mode 0600 temp files, deterministic cleanup. |
| Provider-Independent Router | **Completed** | Dynamic Ollama integration + cloud adapters + capability checking. |
| MCP Integration (`computer-use-linux`) | **Completed** | Stage A mock + Stage B live client + read-only safety gate. |
| Security & Emergency Stop | **Completed** | Default-deny policy, PII scanner, subprocess tracking & termination. |
| Knowledge Storage Engine | **Completed** | Atomic staging, fsync, symlink defense, automatic `.bak` backups. |
| Working CLI Prototype | **Completed** | `status`, `windows`, `focused`, `screenshot`, `models`, `ask`, `permissions`, `stop`. |
| Automated Test Suite | **Completed** | 31 passing unit tests and real hardware benchmarks. |

## Measured Performance Benchmarks

All metrics were captured live on the target machine (Omarchy Linux, Hyprland Wayland session):

- **Window Inspection Latency:**
  - `hyprctl activewindow -j`: ~5.47 ms (min: 5.01 ms, max: 5.86 ms).
  - Provides instantaneous desktop state context without perceptible overhead.
- **Screenshot Capture Latency (`grim`):**
  - Average latency: ~269.05 ms.
  - Average output size: ~974.5 KB (full 1080p display).
- **MCP Client Overhead:**
  - Stage A Mock overhead: ~0.0011 ms per call.
  - Stage B Live MCP JSON-RPC (`list_windows`): ~35.60 ms per round-trip call over stdio.
- **Memory Consumption:**
  - Process peak RSS memory under full pytest suite: ~363.59 MB.
  - Standalone CLI execution consumes < 45 MB RSS.

## Known Limitations in Phase 2

1. **Mutating Desktop Actions Disabled:** In strict accordance with Phase 2 specifications, mutating operations (`click`, `type_text`, `press_key`, `move_window`) are rejected by the security supervisor.
2. **Vision Model Availability:** While local Ollama has 8 models installed (`qwen2.5-coder:3b`, `gemma3:1b`, etc.), a dedicated local vision model (e.g. `llama3.2-vision` or `minicpm-v`) is needed for visual image QA without relying on cloud APIs.
3. **No Continuous Background Capture:** Sentient Linux enforces on-demand capture only.

## Recommendations for Phase 3 (Sentient Experience)

1. **Floating AI Assistant Interface:**
   - Implement the floating top pill / notch overlay using GTK4 or lightweight Wayland layer-shell window matching Omarchy dark theme aesthetics.
   - Bind hotkey (e.g. `Super + Space` or right-side modifier) to toggle the assistant.
2. **Supervised Single-Action Gate:**
   - Implement interactive visual confirmation ("Approve Action: Click [X, Y] in Foot?") before dispatching mutating MCP calls.
   - Dedicate Hyprland Workspace 9 for automated sandbox execution testing.
3. **Local Markdown Vault Synthesis:**
   - Port `VaultGenerator` locked prompts to build initial markdown summaries into `~/Sentient OS - Knowledge Base/`.
   - Add `writingstyle.md` local sample extraction.
4. **Double Tap Contextual Drafting:**
   - Integrate with `wl-copy` and `wtype` to paste unsent drafts in focused fields.
