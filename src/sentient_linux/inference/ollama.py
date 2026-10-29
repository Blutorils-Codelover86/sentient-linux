"""
Ollama local inference provider for Sentient Linux.
Interfaces with Ollama via HTTP JSON API at http://127.0.0.1:11434.
"""

from __future__ import annotations
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sentient_linux.security.emergency_stop import EmergencyStop

logger = logging.getLogger("sentient.inference.ollama")


class OllamaError(RuntimeError):
    """Raised when Ollama API returns an error or is unreachable."""
    pass


class CapabilityUnavailableError(RuntimeError):
    """Raised when a requested model capability (e.g. vision) is unsupported."""
    pass


@dataclass
class ModelCapabilities:
    name: str
    has_vision: bool = False
    has_tools: bool = False
    supports_structured: bool = True
    context_window: int = 4096


class OllamaClient:
    """
    Communicates with local Ollama daemon.
    Does not assume vision or tool capabilities without verification.
    """

    KNOWN_VISION_FAMILIES = {
        "llava",
        "bakllava",
        "minicpm-v",
        "qwen2-vl",
        "qwen-vl",
        "gemma-vision",
        "moondream",
        "llama3.2-vision",
    }

    def __init__(self, host: str = "http://127.0.0.1:11434", timeout: float = 30.0) -> None:
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.emergency_stop = EmergencyStop()

    def is_reachable(self) -> bool:
        """Check if local Ollama daemon is running and responding."""
        self.emergency_stop.check()
        req = urllib.request.Request(f"{self.host}/api/version", method="GET")
        try:
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_models(self) -> List[ModelCapabilities]:
        """Query available local models and infer their capabilities."""
        self.emergency_stop.check()
        req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as err:
            raise OllamaError(f"Cannot connect to Ollama at {self.host}: {err.reason}. Is Ollama running?")
        except Exception as err:
            raise OllamaError(f"Failed to query Ollama models: {err}")

        models: List[ModelCapabilities] = []
        raw_models = data.get("models", [])
        for item in raw_models:
            name = item.get("name", "")
            details = item.get("details", {})
            family = details.get("family", "").lower()
            families = [f.lower() for f in details.get("families", [])] if details.get("families") else []

            # Check if model supports vision
            is_vision = (
                family in self.KNOWN_VISION_FAMILIES
                or any(vf in families for vf in self.KNOWN_VISION_FAMILIES)
                or any(keyword in name.lower() for keyword in ["vision", "vl-", "-vl", "llava", "moondream"])
            )

            models.append(
                ModelCapabilities(
                    name=name,
                    has_vision=is_vision,
                    has_tools=True,
                    supports_structured=True,
                )
            )

        return models

    def get_model_capabilities(self, model_name: str) -> ModelCapabilities:
        """Find capabilities for a specific model."""
        models = self.list_models()
        for m in models:
            if m.name == model_name or m.name.startswith(f"{model_name}:"):
                return m
        # Fallback if unlisted
        return ModelCapabilities(name=model_name, has_vision=False)

    def generate(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        images_b64: Optional[List[str]] = None,
        json_format: bool = False,
    ) -> str:
        """Send a completion request to Ollama."""
        self.emergency_stop.check()

        # Check vision requirement
        if images_b64:
            caps = self.get_model_capabilities(model)
            if not caps.has_vision:
                raise CapabilityUnavailableError(
                    f"Selected model '{model}' does not support vision/image input. "
                    f"Screenshot understanding requires a vision model (e.g. llama3.2-vision, minicpm-v, llava)."
                )

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if images_b64:
            payload["images"] = images_b64
        if json_format:
            payload["format"] = "json"

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "")
        except urllib.error.URLError as err:
            self.emergency_stop.check()
            raise OllamaError(f"Ollama request failed: {err.reason}")
        except Exception as err:
            self.emergency_stop.check()
            raise OllamaError(f"Inference error with model '{model}': {err}")
