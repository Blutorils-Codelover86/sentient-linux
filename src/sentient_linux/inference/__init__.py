"""
Inference subsystem for Sentient Linux.
"""

from sentient_linux.inference.ollama import (
    OllamaClient,
    OllamaError,
    CapabilityUnavailableError,
    ModelCapabilities,
)
from sentient_linux.inference.openai_provider import OpenAIProvider
from sentient_linux.inference.anthropic_provider import AnthropicProvider
from sentient_linux.inference.router import InferenceRouter

__all__ = [
    "OllamaClient",
    "OllamaError",
    "CapabilityUnavailableError",
    "ModelCapabilities",
    "OpenAIProvider",
    "AnthropicProvider",
    "InferenceRouter",
]
