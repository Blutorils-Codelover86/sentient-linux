# Changes and Modifications

Detailed audit of changes from upstream Sentient OS macOS to the Arch Linux / Omarchy port.

## Removed Components (macOS Specific)

- **SwiftUI & AppKit Presentation Layer:** Removed Apple-specific GUI controllers (`NotchWindowController.swift`, `HomeView.swift`, `ConstellationView.swift`, Metal particle shaders).
- **Apple Proprietary Frameworks:** Removed imports of `ScreenCaptureKit`, `ApplicationServices` (`AXUIElement`), `Speech` (`SFSpeechRecognizerEngine`), `SMAppService`, and `Sparkle`.
- **Proprietary Computer Use Helper:** Removed the background downloader and DMG extractor that unpacks OpenAI's macOS-only `Codex Computer Use.app` (`com.openai.sky.CUAService`).
- **macOS Local Sources:** Removed SQLite readers specific to macOS (`Apple Notes`, `Apple Mail`, `iMessage chat.db`).

## Added Components (Linux & Wayland Native)

- **Hyprland Perception Module (`perception/hyprland.py`):**
  - Communicates directly with Hyprland's IPC socket via `hyprctl -j`.
  - Parses window geometries, classes, PIDs, workspace assignments, and multi-monitor topologies.
- **Wayland Screen Capture Engine (`perception/screenshots.py`):**
  - Executes explicit, on-demand captures via `grim`.
  - Enforces `0600` permissions on temporary image files and deterministic deletion in `finally` blocks.
  - Benchmarks execution latency.
- **MCP Computer-Use Integration (`computer_use/`):**
  - Standard JSON-RPC 2.0 client for `@agent-sh/computer-use-linux`.
  - Stage A mock client for safe unit testing and validation.
  - Stage B live MCP integration with enforced read-only gate for Phase 2.
- **Provider-Independent Inference Router (`inference/`):**
  - Native HTTP client for local Ollama daemon (`http://127.0.0.1:11434`).
  - Dynamic discovery of installed models and capability validation (vision, tools, JSON).
  - Cloud provider adapters (OpenAI, Anthropic) gated behind explicit external data-sharing consent.
- **Deterministic Security & Emergency Stop (`security/`):**
  - Default-deny permission model separating read-only queries from mutating desktop actions.
  - Thread-safe `EmergencyStop` mechanism that halts execution, cleans child processes, and prevents subsequent actions.
  - PII regex backstop ported from upstream `PIIScan.swift`.
- **Safe Knowledge Vault Storage (`knowledge/storage.py`):**
  - Path traversal defense, symlink rejection, atomic staging swaps, and automated backup/recovery.
- **Command-Line Interface (`cli.py`):**
  - Standard CLI supporting `status`, `windows`, `focused`, `screenshot`, `models`, `ask`, `permissions`, and `stop`.
