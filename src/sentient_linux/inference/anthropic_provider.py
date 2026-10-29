"""
Anthropic Claude cloud inference provider for Sentient Linux.
Disabled by default; requires explicit API key and external data-sharing consent.
"""

from __future__ import annotations
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from sentient_linux.security.emergency_stop import EmergencyStop
from sentient_linux.security.privacy import ConsentManager, PrivacyError

logger = logging.getLogger("sentient.inference.anthropic")


class AnthropicProvider:
    """
    Anthropic API client adapter.
    Enforces privacy consent checks before any network transmission.
    """

    DESTINATION = "api.anthropic.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        consent_manager: Optional[ConsentManager] = None,
        base_url: str = "https://api.anthropic.com/v1",
        timeout: float = 45.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.consent_manager = consent_manager or ConsentManager()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.emergency_stop = EmergencyStop()

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        has_screenshot: bool = False,
    ) -> str:
        self.emergency_stop.check()

        if not self.api_key:
            raise RuntimeError("Anthropic API key not configured. Set ANTHROPIC_API_KEY to enable.")

        # Enforce explicit cloud consent
        payload_desc = "desktop context with screenshot" if has_screenshot else "desktop context and prompt"
        self.consent_manager.enforce_consent(
            provider="Anthropic",
            destination=self.DESTINATION,
            payload_type=payload_desc,
        )

        payload: Dict[str, Any] = {
            "model": model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/messages",
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                contents = data.get("content", [])
                text_parts = [c.get("text", "") for c in contents if c.get("type") == "text"]
                return "".join(text_parts)
        except urllib.error.HTTPError as err:
            self.emergency_stop.check()
            err_msg = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic API error ({err.code}): {err_msg[:200]}")
        except Exception as err:
            self.emergency_stop.check()
            raise RuntimeError(f"Anthropic connection error: {err}")
