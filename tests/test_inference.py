"""
Unit tests for AI inference routing, Ollama, and cloud consent gates.
"""

from __future__ import annotations
import json
import urllib.error
from unittest.mock import MagicMock, patch
import pytest

from sentient_linux.inference.ollama import (
    OllamaClient,
    OllamaError,
    CapabilityUnavailableError,
    ModelCapabilities,
)
from sentient_linux.inference.openai_provider import OpenAIProvider
from sentient_linux.inference.anthropic_provider import AnthropicProvider
from sentient_linux.inference.router import InferenceRouter
from sentient_linux.security.privacy import ConsentManager, PrivacyError


def test_ollama_connection_failure():
    client = OllamaClient(host="http://127.0.0.1:99999")
    with patch("urllib.request.urlopen") as mock_url:
        mock_url.side_effect = urllib.error.URLError("Connection refused")
        with pytest.raises(OllamaError, match="Cannot connect to Ollama"):
            client.list_models()


def test_ollama_unsupported_model_capabilities():
    client = OllamaClient()
    # Mock list_models returning a text-only model
    with patch.object(
        client,
        "list_models",
        return_value=[ModelCapabilities(name="text-model:latest", has_vision=False)],
    ):
        with pytest.raises(CapabilityUnavailableError, match="does not support vision/image input"):
            client.generate(
                model="text-model:latest",
                prompt="Describe this screenshot",
                images_b64=["FAKE_BASE64_IMAGE"],
            )


def test_cloud_consent_enforcement_openai():
    consent = ConsentManager()  # Cloud not authorized
    openai_prov = OpenAIProvider(api_key="sk-test-key", consent_manager=consent)

    with pytest.raises(PrivacyError, match="Cloud transmission blocked: No user consent"):
        openai_prov.generate(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
        )


def test_cloud_consent_enforcement_anthropic():
    consent = ConsentManager()  # Cloud not authorized
    anthropic_prov = AnthropicProvider(api_key="sk-ant-test", consent_manager=consent)

    with pytest.raises(PrivacyError, match="Cloud transmission blocked: No user consent"):
        anthropic_prov.generate(
            model="claude-3-5-sonnet",
            prompt="Hello",
        )


def test_inference_router_local_generation():
    ollama_mock = MagicMock(spec=OllamaClient)
    ollama_mock.list_models.return_value = [
        ModelCapabilities(name="qwen2.5-coder:3b", has_vision=False)
    ]
    ollama_mock.generate.return_value = "Hello from local model!"

    router = InferenceRouter(provider="ollama", ollama_client=ollama_mock)
    resp = router.ask("Hi")
    assert resp == "Hello from local model!"
    ollama_mock.generate.assert_called_once()
