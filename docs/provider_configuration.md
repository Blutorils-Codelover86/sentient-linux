# AI Provider Configuration Guide

Sentient Linux features a provider-independent inference router supporting both on-device local models and optional cloud frontier models.

## Local Provider: Ollama (Default & Recommended)

Sentient connects to the local Ollama daemon at `http://127.0.0.1:11434`.

- **Endpoint:** `http://127.0.0.1:11434`
- **Dynamic Model Discovery:** Sentient automatically scans installed models via `GET /api/tags`.
- **Capability Negotiation:**
  - Standard reasoning: `qwen2.5-coder:3b`, `gemma3:1b`, `qwen3:1.7b`, `llama3.2`.
  - Visual reasoning: Requires an installed vision-capable model (e.g. `llama3.2-vision`, `minicpm-v`, `llava`, `qwen2-vl`).
  - If visual reasoning is requested on a text-only model, Sentient raises `CapabilityUnavailableError` rather than fabricating an answer.

To install models in Ollama:
```bash
ollama pull qwen2.5-coder:3b
ollama pull llama3.2-vision
```

## Optional Cloud Providers (Disabled by Default)

Cloud providers require an API key and explicit user consent.

### OpenAI
1. Set environment variable:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```
2. Grant explicit consent in code or configuration:
   ```python
   from sentient_linux.security.privacy import ConsentManager
   consent = ConsentManager()
   consent.authorize_cloud_destination("api.openai.com")
   ```

### Anthropic
1. Set environment variable:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```
2. Grant explicit consent:
   ```python
   consent.authorize_cloud_destination("api.anthropic.com")
   ```

If consent is not granted, any attempt to dispatch a request to cloud providers will be blocked with `PrivacyError`.
