"""
Inference Router for Sentient Linux.
Orchestrates model selection, capability validation, and execution across local and cloud providers.
"""

from __future__ import annotations
import base64
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sentient_linux.inference.ollama import OllamaClient, OllamaError, CapabilityUnavailableError
from sentient_linux.inference.openai_provider import OpenAIProvider
from sentient_linux.inference.anthropic_provider import AnthropicProvider
from sentient_linux.security.emergency_stop import EmergencyStop
from sentient_linux.security.privacy import ConsentManager

logger = logging.getLogger("sentient.inference.router")


class InferenceRouter:
    """
    Selects inference provider and ensures capability constraints are strictly honored.
    Does not silently fall back from local to cloud providers.
    """

    def __init__(
        self,
        provider: str = "ollama",
        model: Optional[str] = None,
        ollama_client: Optional[OllamaClient] = None,
        consent_manager: Optional[ConsentManager] = None,
    ) -> None:
        self.provider = provider.lower()
        self.consent_manager = consent_manager or ConsentManager()
        self.ollama = ollama_client or OllamaClient()
        self.openai = OpenAIProvider(consent_manager=self.consent_manager)
        self.anthropic = AnthropicProvider(consent_manager=self.consent_manager)
        self.emergency_stop = EmergencyStop()

        # Selected model override
        self._configured_model = model

    def resolve_model(self) -> str:
        """Resolve the active model for the configured provider."""
        if self._configured_model:
            return self._configured_model

        if self.provider == "ollama":
            # Autodetect installed models from Ollama
            try:
                models = self.ollama.list_models()
                if models:
                    # Prefer qwen2.5-coder or gemma or the first available
                    for preferred in ["qwen2.5-coder:3b", "gemma3:1b", "qwen3:1.7b"]:
                        for m in models:
                            if m.name == preferred or m.name.startswith(preferred):
                                return m.name
                    return models[0].name
            except Exception:
                pass
            return "gemma3:1b"
        elif self.provider == "openai":
            return "gpt-4o-mini"
        elif self.provider == "anthropic":
            return "claude-3-5-sonnet-20241022"
        return "default"

    def ask(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        image_path: Optional[Path | str] = None,
        json_format: bool = False,
    ) -> str:
        """
        Send a reasoning prompt to the selected provider.
        If an image is attached, strictly verifies vision capability.
        """
        self.emergency_stop.check()
        model = self.resolve_model()

        images_b64: Optional[List[str]] = None
        has_screenshot = False
        if image_path:
            img = Path(image_path)
            if img.exists():
                has_screenshot = True
                b64_data = base64.b64encode(img.read_bytes()).decode("utf-8")
                images_b64 = [b64_data]

        if self.provider == "ollama":
            return self.ollama.generate(
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                images_b64=images_b64,
                json_format=json_format,
            )
        elif self.provider == "openai":
            messages: List[Dict[str, Any]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            if images_b64:
                content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
                for b64 in images_b64:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    })
                messages.append({"role": "user", "content": content})
            else:
                messages.append({"role": "user", "content": prompt})

            return self.openai.generate(
                model=model,
                messages=messages,
                has_screenshot=has_screenshot,
            )
        elif self.provider == "anthropic":
            return self.anthropic.generate(
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                has_screenshot=has_screenshot,
            )
        else:
            raise ValueError(f"Unknown inference provider '{self.provider}'. Supported: ollama, openai, anthropic.")
